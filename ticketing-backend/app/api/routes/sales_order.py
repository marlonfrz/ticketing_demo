from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_promoter_or_admin
from app.models.user import User
from app.schemas.sales_order import (
    OrderActionResponse,
    UpdateGroupTicketTypesOrderRequest,
    UpdateSalesOrderRequest,
)
from app.services.sales_order_service import (
    update_event_sales_order,
    update_sale_group_ticket_types_order,
)

router = APIRouter(tags=["sales-order"])


@router.put("/events/{event_id}/sales-order", response_model=OrderActionResponse)
def update_event_sales_order_route(
    event_id: str,
    data: UpdateSalesOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return update_event_sales_order(db, event_id, current_user, data)


@router.put("/events/{event_id}/sale-groups/{sale_group_id}/ticket-types/order", response_model=OrderActionResponse)
def update_sale_group_ticket_types_order_route(
    event_id: str,
    sale_group_id: str,
    data: UpdateGroupTicketTypesOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_promoter_or_admin),
):
    return update_sale_group_ticket_types_order(
        db=db,
        event_id=event_id,
        sale_group_id=sale_group_id,
        current_user=current_user,
        data=data,
    )