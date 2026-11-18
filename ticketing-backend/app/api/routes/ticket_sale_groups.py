from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_promoter_or_admin
from app.models.user import User
from app.schemas.status_action import StatusActionResponse
from app.schemas.ticket_sale_group import (
    TicketSaleGroupCreate,
    TicketSaleGroupResponse,
    TicketSaleGroupUpdate,
)
from app.schemas.ticket_sale_group_assignment import (
    AssignTicketTypeToSaleGroupRequest,
    RemoveTicketTypeFromSaleGroupResponse,
)
from app.schemas.ticket_type import TicketTypeResponse
from app.services.ticket_sale_group_service import (
    assign_ticket_type_to_sale_group,
    create_ticket_sale_group,
    delete_ticket_sale_group,
    list_ticket_sale_groups_by_event,
    publish_ticket_sale_group,
    remove_ticket_type_from_sale_group,
    update_ticket_sale_group,
)

router = APIRouter(prefix="/events/{event_id}/sale-groups", tags=["ticket-sale-groups"])


@router.post("", response_model=TicketSaleGroupResponse)
def create_ticket_sale_group_route(
    event_id: str,
    data: TicketSaleGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    group = create_ticket_sale_group(db, event_id, current_user, data)
    return {
        "id": str(group.id),
        "event_id": str(group.event_id),
        "session_id": str(group.session_id) if group.session_id else None,
        "name": group.name,
        "strategy": group.strategy,
        "is_active": group.is_active,
        "status": group.status,
        "display_order": group.display_order,
        "sale_starts_at": group.sale_starts_at,
        "sale_ends_at": group.sale_ends_at,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


@router.get("", response_model=list[TicketSaleGroupResponse])
def list_ticket_sale_groups_route(
    event_id: str,
    session_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    groups = list_ticket_sale_groups_by_event(
        db,
        event_id,
        current_user,
        session_id,
    )
    return [
        {
            "id": str(group.id),
            "event_id": str(group.event_id),
            "session_id": str(group.session_id) if group.session_id else None,
            "name": group.name,
            "strategy": group.strategy,
            "is_active": group.is_active,
            "status": group.status,
            "display_order": group.display_order,
            "sale_starts_at": group.sale_starts_at,
            "sale_ends_at": group.sale_ends_at,
            "created_at": group.created_at,
            "updated_at": group.updated_at,
        }
        for group in groups
    ]


@router.put("/{sale_group_id}", response_model=TicketSaleGroupResponse)
def update_ticket_sale_group_route(
    event_id: str,
    sale_group_id: str,
    data: TicketSaleGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    group = update_ticket_sale_group(db, sale_group_id, current_user, data)
    return {
        "id": str(group.id),
        "event_id": str(group.event_id),
        "session_id": str(group.session_id) if group.session_id else None,
        "name": group.name,
        "strategy": group.strategy,
        "is_active": group.is_active,
        "status": group.status,
        "display_order": group.display_order,
        "sale_starts_at": group.sale_starts_at,
        "sale_ends_at": group.sale_ends_at,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


@router.delete("/{sale_group_id}", response_model=StatusActionResponse)
def delete_ticket_sale_group_route(
    event_id: str,
    sale_group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return delete_ticket_sale_group(db, sale_group_id, current_user)


@router.post("/ticket-types/{ticket_type_id}/assign", response_model=TicketTypeResponse)
def assign_ticket_type_to_sale_group_route(
    event_id: str,
    ticket_type_id: str,
    data: AssignTicketTypeToSaleGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    ticket_type = assign_ticket_type_to_sale_group(
        db=db,
        ticket_type_id=ticket_type_id,
        current_user=current_user,
        sale_group_id=data.sale_group_id,
        sale_order=data.sale_order,
    )
    return {
        "id": str(ticket_type.id),
        "event_id": str(ticket_type.event_id),
        "session_id": str(ticket_type.session_id) if ticket_type.session_id else None,
        "sale_group_id": str(ticket_type.sale_group_id) if ticket_type.sale_group_id else None,
        "sale_order": ticket_type.sale_order,
        "display_order": ticket_type.display_order,
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
        "created_at": ticket_type.created_at,
        "updated_at": ticket_type.updated_at,
    }
    
@router.post("/{sale_group_id}/publish", response_model=TicketSaleGroupResponse)
def publish_ticket_sale_group_route(
    event_id: str,
    sale_group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    group = publish_ticket_sale_group(db, sale_group_id, current_user)
    return {
        "id": str(group.id),
        "event_id": str(group.event_id),
        "session_id": str(group.session_id) if group.session_id else None,
        "name": group.name,
        "strategy": group.strategy,
        "is_active": group.is_active,
        "status": group.status,
        "display_order": group.display_order,
        "sale_starts_at": group.sale_starts_at,
        "sale_ends_at": group.sale_ends_at,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }

@router.post("/ticket-types/{ticket_type_id}/remove", response_model=RemoveTicketTypeFromSaleGroupResponse)
def remove_ticket_type_from_sale_group_route(
    event_id: str,
    ticket_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return remove_ticket_type_from_sale_group(
        db=db,
        ticket_type_id=ticket_type_id,
        current_user=current_user,
    )

