from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_admin
from app.models.user import User
from app.models.order import Order
from app.models.order_contact_change import OrderContactChange
from app.models.order_customer import OrderCustomer
from app.models.payment import Payment
from app.models.event import Event
from app.models.ticket import Ticket
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminEventFeeRequest,
    AdminEventItemResponse,
    AdminPaginatedEventsResponse,
    AdminPaginatedUsersResponse,
    AdminPromoterEventsResponse,
    AdminUpdateEventRequest,
    AdminUpdateUserRolesRequest,
    AdminUserItemResponse,
    AdminCreateUserRequest,
    AdminCreateUserResponse,
)
from app.services.admin_service import (
    get_admin_dashboard,
    list_event_reviews_admin,
    list_events_admin,
    list_promoter_events_admin,
    list_users_admin,
    search_events_admin,
    search_users_admin,
    update_event_admin,
    update_user_roles_admin,
    create_admin_user,
    create_promoter_admin,
)

from app.schemas.soft_delete import SoftDeleteResponse
from app.services.soft_delete_service import (
    soft_delete_event,
    soft_delete_ticket_type,
    soft_delete_user_with_cascade,
)

from app.schemas.status_action import StatusActionResponse
from app.services.user_service import deactivate_user
from app.services.event_service import (
    approve_event_review,
    delete_unpublished_event,
    cancel_event_review,
    request_event_changes,
    set_event_fee,
)
from app.services.event_session_service import (
    approve_event_session_review,
    cancel_event_session_review,
    request_event_session_changes,
)
from app.services.ticket_type_service import disable_ticket_type
from app.services.ticket_service import send_order_tickets_email

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminOrderContactUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    reason: str | None = Field(default=None, max_length=500)


class AdminReviewReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


def _serialize_support_order(order: Order) -> dict:
    payment = order.payments[0] if order.payments else None
    customer_name = order.customer.full_name if order.customer else order.buyer.full_name if order.buyer else None
    customer_email = order.customer.email if order.customer else order.buyer.email if order.buyer else None
    customer_phone = order.customer.phone if order.customer else None

    tickets = [
        {
            "id": str(ticket.id),
            "ticket_code": ticket.ticket_code,
            "status": ticket.status,
            "source": ticket.source,
            "is_valid": ticket.is_valid,
            "ticket_type_name": ticket.ticket_type.name if ticket.ticket_type else None,
            "session": {
                "id": str(ticket.session.id),
                "location_name": ticket.session.location_name,
                "starts_at": ticket.session.starts_at,
            } if ticket.session else None,
        }
        for ticket in order.tickets
    ]

    return {
        "id": str(order.id),
        "status": order.status,
        "total_amount": order.total_amount,
        "currency": order.currency,
        "created_at": order.created_at,
        "event": {
            "id": str(order.event.id),
            "title": order.event.title,
        } if order.event else None,
        "customer": {
            "full_name": customer_name,
            "email": customer_email,
            "phone": customer_phone,
            "source": "guest" if order.customer else "account",
        },
        "payment": {
            "status": payment.status,
            "provider": payment.provider,
            "provider_order_id": payment.provider_order_id,
            "provider_payment_id": payment.provider_payment_id,
        } if payment else None,
        "tickets": tickets,
    }


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return get_admin_dashboard(db)


@router.get("/orders/support")
def admin_search_orders_for_support_route(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    term = q.strip()
    if len(term) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Introduce al menos 3 caracteres para buscar",
        )

    pattern = f"%{term.lower()}%"
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.tickets).joinedload(Ticket.ticket_type),
            joinedload(Order.tickets).joinedload(Ticket.session),
        )
        .outerjoin(OrderCustomer, OrderCustomer.order_id == Order.id)
        .outerjoin(User, User.id == Order.buyer_id)
        .outerjoin(Payment, Payment.order_id == Order.id)
        .outerjoin(Event, Event.id == Order.event_id)
        .outerjoin(Ticket, Ticket.order_id == Order.id)
        .filter(
            (OrderCustomer.email.ilike(pattern))
            | (OrderCustomer.phone.ilike(pattern))
            | (OrderCustomer.full_name.ilike(pattern))
            | (User.email.ilike(pattern))
            | (User.full_name.ilike(pattern))
            | (Payment.provider_order_id.ilike(pattern))
            | (Ticket.ticket_code.ilike(pattern))
        )
        .distinct()
        .order_by(Order.created_at.desc())
        .limit(25)
        .all()
    )
    return [_serialize_support_order(order) for order in orders]


@router.put("/orders/{order_id}/contact")
def admin_update_order_contact_route(
    order_id: str,
    data: AdminOrderContactUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or not order.customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido con datos de contacto no encontrado",
        )

    old_email = order.customer.email
    old_phone = order.customer.phone

    if data.email:
        order.customer.email = data.email.strip().lower()
    if data.phone:
        order.customer.phone = data.phone.strip()

    db.add(
        OrderContactChange(
            order_id=order.id,
            changed_by_user_id=current_user.id,
            old_email=old_email,
            new_email=order.customer.email,
            old_phone=old_phone,
            new_phone=order.customer.phone,
            reason=data.reason,
        )
    )
    db.commit()
    db.refresh(order)
    return _serialize_support_order(order)


@router.post("/orders/{order_id}/resend-tickets")
def admin_resend_order_tickets_route(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )
    return send_order_tickets_email(db, str(order.id), None, force_resend=True)


@router.get("/users", response_model=list[AdminUserItemResponse])
def admin_users_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return list_users_admin(db)


@router.get("/users/search", response_model=AdminPaginatedUsersResponse)
def admin_search_users_route(
    q: str | None = None,
    role: str | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return search_users_admin(db, q=q, role=role, page=page, page_size=page_size)


@router.get("/events", response_model=list[AdminEventItemResponse])
def admin_events_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return list_events_admin(db)


@router.get("/events/search", response_model=AdminPaginatedEventsResponse)
def admin_search_events_route(
    q: str | None = None,
    event_status: str | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return search_events_admin(
        db,
        q=q,
        event_status=event_status,
        page=page,
        page_size=page_size,
    )


@router.get("/promoters/{promoter_id}/events", response_model=AdminPromoterEventsResponse)
def admin_promoter_events_route(
    promoter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return list_promoter_events_admin(db, promoter_id)


@router.get("/events/review-queue", response_model=list[AdminEventItemResponse])
def admin_event_reviews_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return list_event_reviews_admin(db)


@router.put("/users/{user_id}/roles", response_model=AdminUserItemResponse)
def admin_update_user_roles_route(
    user_id: str,
    data: AdminUpdateUserRolesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return update_user_roles_admin(db, user_id, data.roles, current_user)


@router.put("/events/{event_id}", response_model=AdminEventItemResponse)
def admin_update_event_route(
    event_id: str,
    data: AdminUpdateEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return update_event_admin(db, event_id, data)


@router.post("/events/{event_id}/approve-review", response_model=StatusActionResponse)
def admin_approve_event_review_route(
    event_id: str,
    data: AdminEventFeeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return approve_event_review(
        db=db,
        event_id=event_id,
        acted_by_user=current_user,
        platform_fee_type=data.platform_fee_type,
        platform_fee_value=data.platform_fee_value,
    )


@router.put("/events/{event_id}/fee", response_model=AdminEventItemResponse)
def admin_update_event_fee_route(
    event_id: str,
    data: AdminEventFeeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    event = set_event_fee(
        db=db,
        event_id=event_id,
        acted_by_user=current_user,
        platform_fee_type=data.platform_fee_type,
        platform_fee_value=data.platform_fee_value,
    )

    return {
        "id": str(event.id),
        "promoter_id": str(event.promoter_id),
        "title": event.title,
        "location_name": event.location_name,
        "starts_at": event.starts_at,
        "status": event.status,
        "capacity": event.capacity,
        "platform_fee_type": event.platform_fee_type,
        "platform_fee_value": event.platform_fee_value,
        "created_at": event.created_at,
    }


@router.post("/events/{event_id}/request-changes", response_model=StatusActionResponse)
def admin_request_event_changes_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return request_event_changes(db, event_id, current_user)


@router.post("/events/{event_id}/cancel-review", response_model=StatusActionResponse)
def admin_cancel_event_review_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return cancel_event_review(db, event_id, current_user)


@router.post("/event-sessions/{session_id}/approve-review", response_model=StatusActionResponse)
def admin_approve_event_session_review_route(
    session_id: str,
    data: AdminEventFeeRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return approve_event_session_review(
        db=db,
        session_id=session_id,
        acted_by_user=current_user,
        platform_fee_type=data.platform_fee_type if data else None,
        platform_fee_value=data.platform_fee_value if data else None,
    )


@router.post("/event-sessions/{session_id}/request-changes", response_model=StatusActionResponse)
def admin_request_event_session_changes_route(
    session_id: str,
    data: AdminReviewReasonRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return request_event_session_changes(
        db,
        session_id,
        current_user,
        reason=data.reason if data else None,
    )


@router.post("/event-sessions/{session_id}/cancel-review", response_model=StatusActionResponse)
def admin_cancel_event_session_review_route(
    session_id: str,
    data: AdminReviewReasonRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return cancel_event_session_review(
        db,
        session_id,
        current_user,
        reason=data.reason if data else None,
    )


@router.delete("/users/{user_id}", response_model=StatusActionResponse)
def admin_deactivate_user_route(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return deactivate_user(db, user_id, current_user)


@router.delete("/events/{event_id}", response_model=StatusActionResponse)
def admin_archive_event_route(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return delete_unpublished_event(db, event_id, current_user)


@router.delete("/ticket-types/{ticket_type_id}", response_model=StatusActionResponse)
def admin_disable_ticket_type_route(
    ticket_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return disable_ticket_type(db, ticket_type_id, current_user)

@router.post("/users/promoters", response_model=AdminCreateUserResponse)
def admin_create_promoter_route(
    data: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return create_promoter_admin(
        db=db,
        acted_by_user=current_user,
        email=data.email,
        full_name=data.full_name,
        password=data.password,
        phone=data.phone,
        country_code=data.country_code,
    )


@router.post("/users/admins", response_model=AdminCreateUserResponse)
def superadmin_create_admin_route(
    data: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return create_admin_user(
        db=db,
        acted_by_user=current_user,
        email=data.email,
        full_name=data.full_name,
        password=data.password,
        phone=data.phone,
        country_code=data.country_code,
    )
