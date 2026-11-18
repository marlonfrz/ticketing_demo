import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_type import TicketType
from app.models.user import User
from app.services.guest_checkout_access_service import has_valid_guest_checkout_access
from app.services.ticket_inventory_service import sync_ticket_type_sales_state
from app.services.ticket_service import send_order_tickets_email


def _generate_ticket_code() -> str:
    return f"TKT-{secrets.token_hex(8).upper()}"


def _generate_qr_token() -> str:
    return f"qr_{secrets.token_urlsafe(24)}"


def _serialize_payment(payment: Payment) -> dict:
    return {
        "id": str(payment.id),
        "order_id": str(payment.order_id),
        "provider": payment.provider,
        "status": payment.status,
        "amount": payment.amount,
        "currency": payment.currency,
        "provider_order_id": payment.provider_order_id,
        "provider_payment_id": payment.provider_payment_id,
        "raw_request": None,
        "raw_response": None,
        "error_message": payment.error_message,
        "created_at": payment.created_at,
        "updated_at": payment.updated_at,
    }


def _send_order_tickets_by_email(db: Session, order: Order) -> None:
    buyer = db.query(User).filter(User.id == order.buyer_id).first() if order.buyer_id else None
    send_order_tickets_email(db, str(order.id), buyer)


def get_payment_for_order(db: Session, order_id: str, user: User) -> Payment:
    payment = (
        db.query(Payment)
        .join(Order, Payment.order_id == Order.id)
        .filter(Payment.order_id == order_id, Order.buyer_id == user.id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado para este pedido",
        )

    return payment


def get_payment_for_checkout(
    db: Session,
    order_id: str,
    user: User | None = None,
    guest_access_token: str | None = None,
) -> Payment:
    payment = (
        db.query(Payment)
        .join(Order, Payment.order_id == Order.id)
        .options(joinedload(Payment.order).joinedload(Order.customer))
        .filter(Payment.order_id == order_id)
        .first()
    )

    has_user_access = bool(user and payment and payment.order.buyer_id == user.id)
    has_guest_access = bool(
        payment
        and has_valid_guest_checkout_access(payment.order, guest_access_token)
    )

    if not payment or (not has_user_access and not has_guest_access):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado para este pedido",
        )

    return payment


def get_my_payments(db: Session, user: User) -> list[dict]:
    payments = (
        db.query(Payment)
        .join(Order, Payment.order_id == Order.id)
        .filter(Order.buyer_id == user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return [_serialize_payment(payment) for payment in payments]


def _get_confirmable_reservations_for_order(db: Session, order_id: str) -> list[TicketReservation]:
    now = datetime.now(timezone.utc)

    # expirar vencidas de esa order
    expired = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.order_id == order_id,
            TicketReservation.status == "active",
            TicketReservation.expires_at <= now,
        )
        .all()
    )
    for reservation in expired:
        reservation.status = "expired"

    if expired:
        db.flush()

    reservations = (
        db.query(TicketReservation)
        .options(joinedload(TicketReservation.ticket_type))
        .filter(
            TicketReservation.order_id == order_id,
            TicketReservation.status.in_(("active", "expired")),
        )
        .all()
    )

    return reservations


def _confirm_order_from_reservations(
    db: Session,
    order: Order,
    payment: Payment,
    provider_payment_id: str | None = None,
    raw_response: str | None = None,
) -> dict:
    reservations = _get_confirmable_reservations_for_order(db, str(order.id))

    if not reservations:
        payment.status = "failed"
        payment.error_message = "No hay reservas activas válidas para esta order"
        payment.raw_response = raw_response or payment.raw_response
        order.status = "cancelled"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La reserva ha expirado o ya no está disponible",
        )

    ticket_type_ids = sorted({reservation.ticket_type_id for reservation in reservations}, key=str)
    ticket_types = (
        db.query(TicketType)
        .filter(TicketType.id.in_(ticket_type_ids))
        .order_by(TicketType.id.asc())
        .with_for_update()
        .all()
    )
    ticket_types_by_id = {ticket_type.id: ticket_type for ticket_type in ticket_types}
    affected_ticket_types = []

    # Convertir reservas en venta real
    for reservation in reservations:
        ticket_type = ticket_types_by_id.get(reservation.ticket_type_id)

        if not ticket_type:
            payment.status = "failed"
            payment.error_message = "Tipo de entrada no encontrado al confirmar reservas"
            payment.raw_response = raw_response
            order.status = "cancelled"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de entrada no encontrado al confirmar reservas",
            )

        # La reserva ya bloqueaba stock, así que aquí solo consolidamos venta
        ticket_type.sold_count += reservation.quantity
        reservation.status = "converted"
        
        for _ in range(reservation.quantity):
            ticket = Ticket(
                order_id=order.id,
                event_id=order.event_id,
                session_id=reservation.session_id,
                ticket_type_id=reservation.ticket_type_id,
                owner_user_id=order.buyer_id,
                ticket_code=_generate_ticket_code(),
                qr_token=_generate_qr_token(),
                status="active",
                is_valid=True,
            )
            db.add(ticket)

        affected_ticket_types.append(ticket_type)

    payment.status = "succeeded"
    payment.provider_payment_id = provider_payment_id or payment.provider_payment_id
    payment.raw_response = raw_response or "Payment confirmed from reservations"
    payment.updated_at = datetime.now(timezone.utc)

    order.status = "paid"
    order.updated_at = datetime.now(timezone.utc)

    db.flush()
    for ticket_type in affected_ticket_types:
        sync_ticket_type_sales_state(db, ticket_type)

    db.commit()
    db.refresh(payment)
    _send_order_tickets_by_email(db, order)

    return _serialize_payment(payment)


def _confirm_order_without_reservations(
    db: Session,
    order: Order,
    payment: Payment,
    provider_payment_id: str | None = None,
    raw_response: str | None = None,
) -> dict:
    if order.status == "paid":
        payment.status = "succeeded"
        payment.provider_payment_id = provider_payment_id or payment.provider_payment_id
        payment.raw_response = raw_response or payment.raw_response
        db.commit()
        db.refresh(payment)
        return _serialize_payment(payment)

    ticket_type_ids = sorted({item.ticket_type_id for item in order.items}, key=str)
    ticket_types = (
        db.query(TicketType)
        .filter(TicketType.id.in_(ticket_type_ids))
        .order_by(TicketType.id.asc())
        .with_for_update()
        .all()
    )
    ticket_types_by_id = {ticket_type.id: ticket_type for ticket_type in ticket_types}

    for item in order.items:
        ticket_type = ticket_types_by_id.get(item.ticket_type_id)
        if not ticket_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de entrada no encontrado durante la confirmación del pago",
            )

        available_stock = ticket_type.stock - ticket_type.sold_count
        if item.quantity > available_stock:
            payment.status = "failed"
            payment.error_message = f"Sin stock suficiente para {ticket_type.name}"
            payment.raw_response = raw_response
            order.status = "cancelled"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No hay stock suficiente para '{ticket_type.name}'",
            )

    payment.status = "succeeded"
    payment.provider_payment_id = provider_payment_id or payment.provider_payment_id
    payment.raw_response = raw_response or "Demo payment confirmation"
    payment.updated_at = datetime.now(timezone.utc)

    order.status = "paid"
    order.updated_at = datetime.now(timezone.utc)

    for item in order.items:
        ticket_type = ticket_types_by_id[item.ticket_type_id]

        for _ in range(item.quantity):
            ticket = Ticket(
                order_id=order.id,
                event_id=order.event_id,
                session_id=item.session_id,
                ticket_type_id=item.ticket_type_id,
                owner_user_id=order.buyer_id,
                ticket_code=_generate_ticket_code(),
                qr_token=_generate_qr_token(),
                status="active",
                is_valid=True,
            )
            db.add(ticket)

        ticket_type.sold_count += item.quantity
        db.flush()
        sync_ticket_type_sales_state(db, ticket_type)

    db.commit()
    db.refresh(payment)
    _send_order_tickets_by_email(db, order)

    return _serialize_payment(payment)


def confirm_demo_payment(
    db: Session,
    provider_order_id: str,
) -> dict:
    payment = (
        db.query(Payment)
        .filter(
            Payment.provider == "demo",
            Payment.provider_order_id == provider_order_id,
        )
        .with_for_update()
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión de pago no encontrada",
        )

    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == payment.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    if payment.status == "succeeded":
        return _serialize_payment(payment)

    if payment.status != "pending" or order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El pago ya no puede completarse",
        )

    provider_payment_id = f"demo_payment_{secrets.token_hex(12)}"
    raw_response = "Ticketing Demo payment completed"

    reservations_exist = (
        db.query(TicketReservation)
        .filter(TicketReservation.order_id == order.id)
        .first()
        is not None
    )

    if reservations_exist:
        return _confirm_order_from_reservations(
            db=db,
            order=order,
            payment=payment,
            provider_payment_id=provider_payment_id,
            raw_response=raw_response,
        )

    return _confirm_order_without_reservations(
        db=db,
        order=order,
        payment=payment,
        provider_payment_id=provider_payment_id,
        raw_response=raw_response,
    )
