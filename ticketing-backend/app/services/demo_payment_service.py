import json
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.payment import Payment
from app.models.ticket_reservation import TicketReservation


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_active_reservation_expiration(
    db: Session,
    order_id: str,
) -> datetime | None:
    reservation = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.order_id == order_id,
            TicketReservation.status == "active",
            TicketReservation.expires_at > _utc_now(),
        )
        .order_by(TicketReservation.expires_at.asc())
        .first()
    )
    return reservation.expires_at if reservation else None


def _build_checkout_url(frontend_base_url: str, session_id: str) -> str:
    query = urlencode({"session_id": session_id})
    return f"{frontend_base_url.rstrip('/')}/payment/demo?{query}"


def create_demo_checkout_session(
    db: Session,
    order: Order,
    payment: Payment,
    frontend_base_url: str,
) -> dict:
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment.id)
        .with_for_update()
        .first()
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado",
        )

    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.event))
        .filter(Order.id == order.id)
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    if order.status != "pending" or payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido ya no está pendiente de pago",
        )

    expires_at = _get_active_reservation_expiration(db, str(order.id))
    if not expires_at:
        payment.status = "failed"
        payment.error_message = "No hay una reserva activa para este pedido"
        order.status = "cancelled"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La reserva ha expirado",
        )

    if payment.provider == "demo" and payment.provider_order_id:
        session_id = payment.provider_order_id
    else:
        session_id = f"demo_{secrets.token_urlsafe(24)}"
        payment.provider = "demo"
        payment.provider_order_id = session_id
        payment.raw_request = json.dumps(
            {
                "mode": "portfolio_demo",
                "order_id": str(order.id),
                "payment_id": str(payment.id),
            }
        )
        payment.error_message = None
        db.commit()
        db.refresh(payment)

    return {
        "payment_id": str(payment.id),
        "order_id": str(order.id),
        "checkout_session_id": session_id,
        "checkout_url": _build_checkout_url(frontend_base_url, session_id),
        "expires_at": expires_at,
    }


def get_demo_checkout_payment(db: Session, session_id: str) -> Payment:
    payment = (
        db.query(Payment)
        .join(Order, Payment.order_id == Order.id)
        .options(joinedload(Payment.order).joinedload(Order.customer))
        .filter(
            Payment.provider == "demo",
            Payment.provider_order_id == session_id,
        )
        .first()
    )
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión de pago no encontrada",
        )
    return payment
