from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_optional_current_user
from app.core.rate_limit import reservation_rate_limit
from app.models.user import User
from app.schemas.ticket_reservation import (
    ReservationWithOrderCreateRequest,
    ReservationWithOrderResponse,
)
from app.services.ticket_reservation_service import create_reservation_with_order


router = APIRouter(
    prefix="/events/{event_id}/reservations",
    tags=["reservations"],
)


@router.post("/with-order", response_model=ReservationWithOrderResponse)
def create_reservation_with_order_route(
    event_id: str,
    data: ReservationWithOrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    _: None = Depends(reservation_rate_limit),
):
    return create_reservation_with_order(
        db=db,
        event_id=event_id,
        items=data.items,
        customer_data=data.customer,
        public_relations_code=data.public_relations_code,
        current_user=current_user,
    )
