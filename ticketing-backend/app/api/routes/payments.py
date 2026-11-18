import ipaddress
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, get_optional_current_user
from app.core.config import settings
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import DemoCheckoutResponse, PaymentResponse
from app.services.demo_payment_service import (
    create_demo_checkout_session,
    get_demo_checkout_payment,
)
from app.services.guest_checkout_access_service import has_valid_guest_checkout_access
from app.services.payment_service import (
    confirm_demo_payment,
    get_my_payments,
    get_payment_for_checkout,
)


router = APIRouter(prefix="/payments", tags=["payments"])


def _is_local_development_origin(origin: str) -> bool:
    if settings.app_env.lower() not in {"development", "dev", "local", "test"}:
        return False

    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return False

    hostname = parsed.hostname.lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_private or address.is_loopback


def _resolve_frontend_base_url(*origins: str | None) -> str:
    configured_base_url = settings.frontend_base_url.rstrip("/")
    allowed_origins = {
        allowed_origin.strip().rstrip("/")
        for allowed_origin in settings.cors_allow_origins.split(",")
        if allowed_origin.strip()
    }

    for origin in origins:
        if not origin:
            continue
        normalized_origin = origin.rstrip("/")
        if normalized_origin in allowed_origins or _is_local_development_origin(
            normalized_origin
        ):
            return normalized_origin
    return configured_base_url


def _ensure_confirm_session_access(
    payment: Payment,
    current_user: User | None,
    guest_access_token: str | None,
) -> None:
    order = payment.order
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    if current_user and order.buyer_id == current_user.id:
        return

    if has_valid_guest_checkout_access(order, guest_access_token):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No puedes confirmar este pago",
    )


@router.get("", response_model=list[PaymentResponse])
def my_payments_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_payments(db, current_user)


@router.post("/demo/checkout/{order_id}", response_model=DemoCheckoutResponse)
def create_demo_checkout_route(
    order_id: str,
    request: Request,
    x_guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    x_checkout_return_origin: str | None = Header(
        default=None,
        alias="X-Checkout-Return-Origin",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    payment = get_payment_for_checkout(db, order_id, current_user, x_guest_token)
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.event))
        .filter(Order.id == payment.order_id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    return create_demo_checkout_session(
        db,
        order,
        payment,
        frontend_base_url=_resolve_frontend_base_url(
            x_checkout_return_origin,
            request.headers.get("origin"),
        ),
    )


@router.post("/demo/confirm-session/{session_id}", response_model=PaymentResponse)
def confirm_demo_session_route(
    session_id: str,
    x_guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    payment = get_demo_checkout_payment(db, session_id)
    _ensure_confirm_session_access(payment, current_user, x_guest_token)
    return confirm_demo_payment(db, session_id)
