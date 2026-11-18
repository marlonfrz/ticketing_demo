from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.event import Event
from app.models.order import Order
from app.models.order_customer import OrderCustomer
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.ticket_type import TicketType
from app.models.ticket_reservation import TicketReservation
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.guest_checkout_access_service import has_valid_guest_checkout_access

def _utc_now():
    return datetime.now(timezone.utc)


def _to_money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_management_fee(event: Event, ticket_subtotal: Decimal, ticket_quantity: int) -> Decimal:
    fee_value = _to_money(event.platform_fee_value)

    if not event.platform_fee_type or fee_value <= 0:
        return Decimal("0.00")

    if event.platform_fee_type == "percentage":
        return (ticket_subtotal * fee_value / Decimal("100")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    if event.platform_fee_type == "fixed":
        return (fee_value * Decimal(ticket_quantity)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    return Decimal("0.00")

def _serialize_ticket(ticket: Ticket) -> dict:
    session = ticket.session or ticket.event._first_session
    return {
        "id": str(ticket.id),
        "order_id": str(ticket.order_id),
        "event_id": str(ticket.event_id),
        "ticket_type_id": str(ticket.ticket_type_id),
        "owner_user_id": str(ticket.owner_user_id) if ticket.owner_user_id else None,
        "ticket_code": ticket.ticket_code,
        "qr_image_url": f"/tickets/{ticket.id}/qr-image",
        "status": ticket.status,
        "is_valid": ticket.is_valid,
        "issued_at": ticket.issued_at,
        "used_at": ticket.used_at,
        "created_at": ticket.created_at,
        "event": {
            "id": str(ticket.event.id),
            "title": ticket.event.title,
            "starts_at": session.starts_at if session else None,
            "location_name": session.location_name if session else "",
        },
        "session": {
            "id": str(session.id),
            "title": session.title,
            "starts_at": session.starts_at,
            "ends_at": session.ends_at,
            "location_name": session.location_name,
            "location_address": session.location_address,
        } if session else None,
        "ticket_type": {
            "id": str(ticket.ticket_type.id),
            "name": ticket.ticket_type.name,
        },
    }

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

def _serialize_order(order: Order) -> dict:
    return {
        "id": str(order.id),
        "buyer_id": str(order.buyer_id) if order.buyer_id else None,
        "event_id": str(order.event_id),
        "status": order.status,
        "total_amount": order.total_amount,
        "currency": order.currency,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "id": str(item.id),
                "ticket_type_id": str(item.ticket_type_id),
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            }
            for item in order.items
        ],
        "tickets": [_serialize_ticket(ticket) for ticket in order.tickets],
        "payments": [_serialize_payment(payment) for payment in order.payments],
    }

def create_order(db: Session, buyer: User, data: OrderCreate) -> dict:
    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido debe incluir al menos un item",
        )

    event = (
        db.query(Event)
        .filter(
            Event.id == data.event_id,
            Event.status != "deleted",
        )
        .first()
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento no está disponible para compra",
        )

    ticket_type_ids = [item.ticket_type_id for item in data.items]
    ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.id.in_(ticket_type_ids),
            TicketType.event_id == event.id,
            TicketType.status != "deleted",
        )
        .all()
    )

    ticket_type_map = {str(ticket_type.id): ticket_type for ticket_type in ticket_types}

    if len(ticket_types) != len(ticket_type_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más tipos de entrada no pertenecen al evento",
        )

    tickets_subtotal = Decimal("0.00")
    tickets_quantity = 0
    order_items_to_create = []

    for item in data.items:
        ticket_type = ticket_type_map.get(item.ticket_type_id)

        if not ticket_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de entrada no válido: {item.ticket_type_id}",
            )

        if not ticket_type.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El tipo de entrada '{ticket_type.name}' no está activo",
            )

        if item.quantity > ticket_type.max_per_purchase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La cantidad para '{ticket_type.name}' supera el máximo por compra",
            )

        available_stock = ticket_type.stock - ticket_type.sold_count
        if item.quantity > available_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No hay stock suficiente para '{ticket_type.name}'",
            )

        subtotal = Decimal(ticket_type.price) * item.quantity
        tickets_subtotal += subtotal
        tickets_quantity += item.quantity

        order_items_to_create.append(
            {
                "ticket_type": ticket_type,
                "quantity": item.quantity,
                "unit_price": ticket_type.price,
                "subtotal": subtotal,
            }
        )

    currency = order_items_to_create[0]["ticket_type"].currency

    if any(entry["ticket_type"].currency != currency for entry in order_items_to_create):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todos los tipos de entrada del pedido deben tener la misma moneda",
        )

    management_fee = _calculate_management_fee(event, tickets_subtotal, tickets_quantity)
    total_amount = tickets_subtotal + management_fee

    order = Order(
        buyer_id=buyer.id,
        event_id=event.id,
        status="pending",
        total_amount=total_amount,
        currency=currency,
    )
    db.add(order)
    db.flush()

    for entry in order_items_to_create:
        order_item = OrderItem(
            order_id=order.id,
            ticket_type_id=entry["ticket_type"].id,
            quantity=entry["quantity"],
            unit_price=entry["unit_price"],
            subtotal=entry["subtotal"],
        )
        db.add(order_item)

    payment = Payment(
        order_id=order.id,
        provider="demo",
        status="pending",
        amount=total_amount,
        currency=currency,
        provider_order_id=None,
        raw_request=None,
        raw_response=None,
        error_message=None,
    )
    db.add(payment)

    db.commit()

    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.tickets).joinedload(Ticket.event),
            joinedload(Order.tickets).joinedload(Ticket.ticket_type),
            joinedload(Order.payments),
        )
        .filter(Order.id == order.id)
        .first()
    )
    return _serialize_order(order)


def get_my_orders(db: Session, buyer: User) -> list[dict]:
    orders = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.tickets).joinedload(Ticket.event),
            joinedload(Order.tickets).joinedload(Ticket.ticket_type),
            joinedload(Order.payments),
        )
        .filter(Order.buyer_id == buyer.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_serialize_order(order) for order in orders]


def get_order_by_id(db: Session, order_id: str, buyer: User) -> dict:
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.tickets).joinedload(Ticket.event),
            joinedload(Order.tickets).joinedload(Ticket.ticket_type),
            joinedload(Order.payments),
        )
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    if order.buyer_id != buyer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver un pedido que no es tuyo",
        )

    return _serialize_order(order)

def get_checkout_summary(
    db: Session,
    order_id: str,
    buyer: User | None = None,
    guest_access_token: str | None = None,
) -> dict:
    now = _utc_now()

    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.event),
            joinedload(Order.customer),
        )
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    has_user_access = buyer is not None and order.buyer_id == buyer.id
    has_guest_access = has_valid_guest_checkout_access(order, guest_access_token, now=now)

    if not has_user_access and not has_guest_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes acceder a este checkout",
        )

    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order.id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado para este pedido",
        )

    active_reservations = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.order_id == order.id,
            TicketReservation.status == "active",
        )
        .all()
    )

    expired_reservations = [
        reservation
        for reservation in active_reservations
        if reservation.expires_at <= now
    ]

    if expired_reservations:
        for reservation in expired_reservations:
            reservation.status = "expired"

        remaining_active = [
            reservation
            for reservation in active_reservations
            if reservation.expires_at > now
        ]

        if not remaining_active and order.status == "pending":
            order.status = "cancelled"

            if payment.status == "pending":
                payment.status = "failed"
                payment.error_message = "La reserva expiró antes del pago"

        db.commit()
        db.refresh(order)
        db.refresh(payment)

    valid_reservations = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.order_id == order.id,
            TicketReservation.status == "active",
            TicketReservation.expires_at > now,
        )
        .all()
    )

    expires_at = None
    if valid_reservations:
        expires_at = min(reservation.expires_at for reservation in valid_reservations)

    items = []
    tickets_subtotal = Decimal("0.00")

    for item in order.items:
        ticket_type = (
            db.query(TicketType)
            .filter(TicketType.id == item.ticket_type_id)
            .first()
        )

        items.append(
            {
                "ticket_type_id": str(item.ticket_type_id),
                "ticket_type_name": ticket_type.name if ticket_type else "Entrada",
                "sale_group_id": str(ticket_type.sale_group_id)
                if ticket_type and ticket_type.sale_group_id
                else None,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            }
        )
        tickets_subtotal += Decimal(str(item.subtotal or 0))

    total_amount = Decimal(str(order.total_amount or 0))
    management_fee = max(Decimal("0.00"), total_amount - tickets_subtotal)

    return {
        "order_id": str(order.id),
        "event_id": str(order.event_id),
        "event_title": order.event.title if order.event else None,
        "status": order.status,
        "payment_status": payment.status,
        "total_amount": order.total_amount,
        "tickets_subtotal": tickets_subtotal,
        "management_fee": management_fee,
        "currency": order.currency,
        "expires_at": expires_at,
        "items": items,
    }
