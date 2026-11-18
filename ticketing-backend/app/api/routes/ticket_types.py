from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_promoter_or_admin
from app.models.user import User
from app.schemas.status_action import StatusActionResponse
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeResponse, TicketTypeUpdate
from app.services.ticket_type_service import (
    create_ticket_type,
    delete_ticket_type,
    list_ticket_types_by_event,
    publish_ticket_type,
    update_ticket_type,
)


router = APIRouter(tags=["ticket-types"])


@router.post("/events/{event_id}/ticket-types", response_model=TicketTypeResponse)
def create_ticket_type_route(
    event_id: str,
    data: TicketTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    ticket_type = create_ticket_type(db, event_id, current_user, data)
    return serialize_ticket_type(ticket_type)


@router.get("/events/{event_id}/ticket-types", response_model=list[TicketTypeResponse])
def list_ticket_types_route(
    event_id: str,
    session_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    ticket_types = list_ticket_types_by_event(
        db,
        event_id,
        current_user,
        session_id,
    )
    return [serialize_ticket_type(ticket_type) for ticket_type in ticket_types]


@router.put("/ticket-types/{ticket_type_id}", response_model=TicketTypeResponse)
def update_ticket_type_route(
    ticket_type_id: str,
    data: TicketTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    ticket_type = update_ticket_type(db, ticket_type_id, current_user, data)
    return serialize_ticket_type(ticket_type)


@router.post("/ticket-types/{ticket_type_id}/publish", response_model=TicketTypeResponse)
def publish_ticket_type_route(
    ticket_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    ticket_type = publish_ticket_type(db, ticket_type_id, current_user)
    return serialize_ticket_type(ticket_type)


@router.delete("/ticket-types/{ticket_type_id}", response_model=StatusActionResponse)
def delete_ticket_type_route(
    ticket_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return delete_ticket_type(db, ticket_type_id, current_user)


def serialize_ticket_type(ticket_type):
    return {
        "id": str(ticket_type.id),
        "event_id": str(ticket_type.event_id),
        "session_id": str(ticket_type.session_id) if ticket_type.session_id else None,
        "sale_group_id": str(ticket_type.sale_group_id) if ticket_type.sale_group_id else None,
        "sale_order": ticket_type.sale_order,
        "name": ticket_type.name,
        "description": ticket_type.description,
        "price": ticket_type.price,
        "currency": ticket_type.currency,
        "stock": ticket_type.stock,
        "sold_count": ticket_type.sold_count,
        "max_per_purchase": ticket_type.max_per_purchase,
        "sale_starts_at": ticket_type.sale_starts_at,
        "sale_ends_at": ticket_type.sale_ends_at,
        "is_active": ticket_type.is_active,
        "status": ticket_type.status,
        "display_order": ticket_type.display_order,
        "created_at": ticket_type.created_at,
        "updated_at": ticket_type.updated_at,
    }
