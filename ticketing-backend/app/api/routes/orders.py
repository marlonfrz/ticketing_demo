from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_optional_current_user
from app.models.user import User
from app.schemas.order import OrderResponse,  CheckoutSummaryResponse
from app.services.order_service import (
    get_my_orders,
    get_order_by_id,
    get_checkout_summary,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/my-orders", response_model=list[OrderResponse])
def my_orders_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_orders(db, current_user)

@router.get("/{order_id}/checkout-summary", response_model=CheckoutSummaryResponse)
def get_checkout_summary_route(
    order_id: str,
    x_guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    return get_checkout_summary(db, order_id, current_user, x_guest_token)

@router.get("/{order_id}", response_model=OrderResponse)
def get_order_route(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_order_by_id(db, order_id, current_user)
