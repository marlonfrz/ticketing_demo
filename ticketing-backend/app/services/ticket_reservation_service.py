import secrets
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.models.user import User
from app.services.public_relations_service import get_public_relations_for_sale
from app.models.order import Order
from app.models.order_customer import OrderCustomer
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.services.ticket_inventory_service import (
    get_active_reserved_quantity,
    sync_ticket_type_sales_state,
)


RESERVATION_MINUTES = 30
ALLOWED_GROUP_STRATEGIES = {"stock_cascade", "time_and_stock_cascade", "time_window"}
CASCADE_GROUP_STRATEGIES = {"stock_cascade", "time_and_stock_cascade"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def _utc_now():
    return datetime.now(timezone.utc)


def _expire_old_reservations(db: Session) -> None:
    now = _utc_now()

    expired = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.status == "active",
            TicketReservation.expires_at <= now,
        )
        .all()
    )

    for reservation in expired:
        reservation.status = "expired"

    if expired:
        db.flush()


def _get_sale_group(db: Session, event_id: str, sale_group_id: str) -> TicketSaleGroup:
    group = (
        db.query(TicketSaleGroup)
        .filter(
            TicketSaleGroup.id == sale_group_id,
            TicketSaleGroup.event_id == event_id,
        )
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de venta no encontrado para este evento",
        )

    return group


def _validate_group_window(group: TicketSaleGroup) -> None:
    now = _utc_now()

    if group.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El grupo de venta no está publicado",
        )

    if not group.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El grupo de venta no está activo",
        )

    if group.strategy not in ALLOWED_GROUP_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La estrategia del grupo no es válida",
        )

    if group.sale_starts_at and now < group.sale_starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta de este grupo todavía no ha comenzado",
        )

    if group.sale_ends_at and now > group.sale_ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La venta de este grupo ya ha finalizado",
        )


def _ticket_type_is_time_available(ticket_type: TicketType) -> bool:
    now = _utc_now()

    if not ticket_type.is_active:
        return False

    if ticket_type.status != "published":
        return False

    if ticket_type.sale_starts_at and now < ticket_type.sale_starts_at:
        return False

    if ticket_type.sale_ends_at and now > ticket_type.sale_ends_at:
        return False

    return True


def _validate_ticket_session_available(ticket_type: TicketType) -> None:
    session = ticket_type.session
    now = _utc_now()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El tipo de entrada '{ticket_type.name}' no pertenece a una sesion disponible",
        )

    if session.status not in {"published", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La sesion de '{ticket_type.name}' no esta publicada",
        )

    if session.publish_at and now < session.publish_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La sesion de '{ticket_type.name}' todavia no esta publicada",
        )

    if not session.tickets_activated_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Las entradas de la sesion de '{ticket_type.name}' no estan activadas",
        )

    if not session.tickets_publish_at or now < session.tickets_publish_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Las entradas de la sesion de '{ticket_type.name}' todavia no estan disponibles",
        )

    if session.ends_at and now > session.ends_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La sesion de '{ticket_type.name}' ya ha finalizado",
        )


def _get_reserved_active_quantity(db: Session, ticket_type_id: str) -> int:
    return get_active_reserved_quantity(db, ticket_type_id, _utc_now())


def _get_real_available_stock(db: Session, ticket_type: TicketType) -> int:
    sync_ticket_type_sales_state(db, ticket_type)
    reserved_active = _get_reserved_active_quantity(db, str(ticket_type.id))
    real_available = ticket_type.stock - ticket_type.sold_count - reserved_active
    return max(0, real_available)


def _allocate_cascade_quantity(
    db: Session,
    group: TicketSaleGroup,
    requested_ticket_type: TicketType,
    quantity: int,
    group_ticket_types: list[TicketType],
) -> list[tuple[TicketType, int]]:
    if group.strategy not in CASCADE_GROUP_STRATEGIES:
        return [(requested_ticket_type, quantity)]

    ordered_ticket_types = sorted(
        group_ticket_types,
        key=lambda ticket_type: (
            ticket_type.sale_order is None,
            ticket_type.sale_order or 0,
            ticket_type.created_at,
        ),
    )
    try:
        start_index = next(
            index
            for index, ticket_type in enumerate(ordered_ticket_types)
            if ticket_type.id == requested_ticket_type.id
        )
    except StopIteration as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tramo seleccionado no pertenece al grupo de venta",
        ) from exc

    remaining = quantity
    allocations: list[tuple[TicketType, int]] = []

    for candidate_index, ticket_type in enumerate(
        ordered_ticket_types[start_index:]
    ):
        _validate_ticket_session_available(ticket_type)
        available_stock = _get_real_available_stock(db, ticket_type)

        if available_stock <= 0:
            if candidate_index == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"El tramo '{requested_ticket_type.name}' acaba de agotarse. "
                        "Actualiza la disponibilidad antes de continuar"
                    ),
                )
            continue

        if not _ticket_type_is_time_available(ticket_type):
            break

        allocated_quantity = min(remaining, available_stock)
        allocations.append((ticket_type, allocated_quantity))
        remaining -= allocated_quantity

        if remaining == 0:
            return allocations

    if not allocations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El tramo '{requested_ticket_type.name}' está agotado",
        )

    available_quantity = quantity - remaining
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "No hay suficientes entradas disponibles en los tramos siguientes. "
            f"Disponibles: {available_quantity}, solicitadas: {quantity}"
        ),
    )


def sync_sale_group_unlocks(db: Session, sale_group_id: str) -> bool:
    now = _utc_now()

    ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.sale_group_id == sale_group_id,
            TicketType.status.in_(["published", "sold_out"]),
        )
        .order_by(TicketType.sale_order.asc(), TicketType.created_at.asc())
        .all()
    )

    if not ticket_types:
        return False

    changed = False

    if ticket_types[0].status == "published" and ticket_types[0].sale_unlocked_at is None:
        ticket_types[0].sale_unlocked_at = now
        changed = True

    for ticket_type in ticket_types:
        changed = sync_ticket_type_sales_state(db, ticket_type) or changed

    for index, ticket_type in enumerate(ticket_types[:-1]):
        next_ticket = ticket_types[index + 1]

        if ticket_type.sale_unlocked_at is None:
            break

        available_stock = _get_real_available_stock(db, ticket_type)

        if (
            available_stock <= 0
            and next_ticket.status == "published"
            and next_ticket.sale_unlocked_at is None
        ):
            next_ticket.sale_unlocked_at = now
            changed = True

    if changed:
        db.flush()

    return changed
        

def _cancel_user_active_reservations_for_event(
    db: Session,
    event_id: str,
    user_id: str,
) -> None:
    now = _utc_now()

    active_reservations = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.event_id == event_id,
            TicketReservation.user_id == user_id,
            TicketReservation.status == "active",
            TicketReservation.expires_at > now,
        )
        .all()
    )

    if not active_reservations:
        return

    order_ids = {
        reservation.order_id
        for reservation in active_reservations
        if reservation.order_id is not None
    }

    for reservation in active_reservations:
        reservation.status = "cancelled"

    if order_ids:
        orders = (
            db.query(Order)
            .filter(
                Order.id.in_(order_ids),
                Order.status == "pending",
            )
            .all()
        )

        for order in orders:
            order.status = "cancelled"

        payments = (
            db.query(Payment)
            .filter(
                Payment.order_id.in_(order_ids),
                Payment.status == "pending",
            )
            .all()
        )

        for payment in payments:
            payment.status = "cancelled"
            payment.error_message = "Reserva reemplazada por una nueva"

    db.flush()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_phone(phone: str) -> str:
    normalized = re.sub(r"[^\d+]", "", phone.strip())
    if normalized.startswith("00"):
        normalized = f"+{normalized[2:]}"
    return normalized


def _validate_customer_data(customer_data) -> dict:
    if customer_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indica los datos de contacto para continuar con la compra",
        )

    full_name = customer_data.full_name.strip()
    email = _normalize_email(customer_data.email)
    email_confirm = _normalize_email(customer_data.email_confirm)
    phone = _normalize_phone(customer_data.phone)
    country_code = customer_data.country_code.strip().upper() if customer_data.country_code else None

    if len(full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indica el nombre completo del comprador",
        )

    if not EMAIL_PATTERN.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email del comprador no es valido",
        )

    if email != email_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los emails del comprador no coinciden",
        )

    if len(phone) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indica un telefono de contacto valido",
        )

    if not customer_data.accept_terms or not customer_data.accept_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes aceptar las condiciones de compra y la politica de privacidad",
        )

    return {
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "country_code": country_code,
    }


def create_reservation_with_order(
    db: Session,
    event_id: str,
    items: list,
    customer_data,
    public_relations_code: str | None = None,
    current_user: User | None = None,
) -> dict:
    _expire_old_reservations(db)

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar al menos un tipo de entrada",
        )

    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden reservar entradas de eventos publicados",
        )

    public_relations = get_public_relations_for_sale(
        db,
        str(event.id),
        public_relations_code,
    )
    
    customer = _validate_customer_data(customer_data) if not current_user else None

    if current_user:
        _cancel_user_active_reservations_for_event(
            db=db,
            event_id=str(event.id),
            user_id=str(current_user.id),
        )

    requested_by_ticket_type_id: dict[str, int] = {}

    for item in items:
        ticket_type_id = item.ticket_type_id
        quantity = item.quantity

        if ticket_type_id in requested_by_ticket_type_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes repetir el mismo tipo de entrada en la reserva",
            )

        requested_by_ticket_type_id[ticket_type_id] = quantity

    requested_ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.event_id == event.id,
            TicketType.id.in_(list(requested_by_ticket_type_id.keys())),
        )
        .all()
    )

    if len(requested_ticket_types) != len(requested_by_ticket_type_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uno o varios tipos de entrada no existen para este evento",
        )

    requested_sale_group_ids = {
        ticket_type.sale_group_id
        for ticket_type in requested_ticket_types
        if ticket_type.sale_group_id is not None
    }
    lock_filter = TicketType.id.in_(list(requested_by_ticket_type_id.keys()))
    if requested_sale_group_ids:
        lock_filter = or_(
            lock_filter,
            TicketType.sale_group_id.in_(requested_sale_group_ids),
        )

    locked_ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.event_id == event.id,
            lock_filter,
        )
        .order_by(TicketType.id.asc())
        .with_for_update()
        .all()
    )
    locked_ticket_types_by_id = {
        str(ticket_type.id): ticket_type for ticket_type in locked_ticket_types
    }
    ticket_types = [
        locked_ticket_types_by_id[ticket_type_id]
        for ticket_type_id in requested_by_ticket_type_id
    ]
    group_ticket_types_by_id = {
        str(group_id): [
            ticket_type
            for ticket_type in locked_ticket_types
            if ticket_type.sale_group_id == group_id
        ]
        for group_id in requested_sale_group_ids
    }

    session_ids = {str(ticket_type.session_id) for ticket_type in ticket_types if ticket_type.session_id}
    if len(session_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todas las entradas de una compra deben pertenecer a la misma sesion",
        )
    order_session_id = next(iter(session_ids), None)

    # No permitir comprar dos tickets distintos del mismo grupo en la misma orden.
    # Ejemplo prohibido: Early + General si ambos pertenecen al mismo grupo.
    used_sale_groups: set[str] = set()

    breakdown = []
    currency_values = set()

    for ticket_type in ticket_types:
        quantity = requested_by_ticket_type_id[str(ticket_type.id)]

        _validate_ticket_session_available(ticket_type)

        if ticket_type.sale_group_id:
            sale_group_id = str(ticket_type.sale_group_id)

            if sale_group_id in used_sale_groups:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo puedes comprar un tipo de entrada por cada grupo de venta",
                )

            used_sale_groups.add(sale_group_id)

            sync_sale_group_unlocks(db, sale_group_id)
            db.refresh(ticket_type)

            group = _get_sale_group(db, event_id, sale_group_id)
            _validate_group_window(group)

            if ticket_type.sale_unlocked_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El tramo '{ticket_type.name}' todavía no está disponible para compra",
                )

        if not _ticket_type_is_time_available(ticket_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El tipo de entrada '{ticket_type.name}' no está disponible para reserva",
            )

        if quantity > ticket_type.max_per_purchase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Solo puedes comprar hasta {ticket_type.max_per_purchase} "
                    f"entradas de '{ticket_type.name}' por pedido"
                ),
            )

        allocations = [(ticket_type, quantity)]
        if ticket_type.sale_group_id and group.strategy in CASCADE_GROUP_STRATEGIES:
            allocations = _allocate_cascade_quantity(
                db=db,
                group=group,
                requested_ticket_type=ticket_type,
                quantity=quantity,
                group_ticket_types=group_ticket_types_by_id[sale_group_id],
            )

        for allocated_ticket_type, allocated_quantity in allocations:
            if allocated_ticket_type.id == ticket_type.id and len(allocations) == 1:
                available_stock = _get_real_available_stock(db, allocated_ticket_type)

                if available_stock <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"El tipo de entrada '{allocated_ticket_type.name}' está agotado",
                    )

                if allocated_quantity > available_stock:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"No hay suficientes entradas de '{allocated_ticket_type.name}'. "
                            f"Disponibles: {available_stock}, solicitadas: {allocated_quantity}"
                        ),
                    )

            unit_price = Decimal(allocated_ticket_type.price)
            subtotal = unit_price * allocated_quantity
            currency = allocated_ticket_type.currency.upper()

            currency_values.add(currency)

            breakdown.append(
                {
                    "ticket_type": allocated_ticket_type,
                    "quantity": allocated_quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

    if len(currency_values) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todos los tipos de entrada reservados deben tener la misma moneda",
        )

    currency = currency_values.pop()
    tickets_subtotal = sum(item["subtotal"] for item in breakdown)
    tickets_quantity = sum(item["quantity"] for item in breakdown)
    management_fee = _calculate_management_fee(event, tickets_subtotal, tickets_quantity)
    total_amount = tickets_subtotal + management_fee

    now = _utc_now()
    expires_at = now + timedelta(minutes=RESERVATION_MINUTES)
    reservation_group_token = f"rsv_{secrets.token_urlsafe(18)}"

    order = Order(
        buyer_id=current_user.id if current_user else None,
        event_id=event.id,
        session_id=order_session_id,
        public_relations_id=public_relations.id if public_relations else None,
        status="pending",
        total_amount=total_amount,
        currency=currency,
    )
    db.add(order)
    db.flush()

    order_customer = None
    if customer:
        order_customer = OrderCustomer(
            order_id=order.id,
            full_name=customer["full_name"],
            email=customer["email"],
            phone=customer["phone"],
            country_code=customer["country_code"],
            guest_access_token=f"guest_{secrets.token_urlsafe(32)}",
            guest_access_expires_at=now
            + timedelta(minutes=settings.guest_checkout_access_expire_minutes),
            accepted_terms_at=now,
            accepted_privacy_at=now,
        )
        db.add(order_customer)
        db.flush()

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
    db.flush()

    for item in breakdown:
        ticket_type = item["ticket_type"]

        order_item = OrderItem(
            order_id=order.id,
            ticket_type_id=ticket_type.id,
            session_id=ticket_type.session_id,
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            subtotal=item["subtotal"],
        )
        db.add(order_item)

        reservation = TicketReservation(
            reservation_group_token=reservation_group_token,
            order_id=order.id,
            event_id=event.id,
            session_id=ticket_type.session_id,
            sale_group_id=ticket_type.sale_group_id,
            ticket_type_id=ticket_type.id,
            user_id=current_user.id if current_user else None,
            quantity=item["quantity"],
            status="active",
            expires_at=expires_at,
        )
        db.add(reservation)

    db.commit()

    return {
        "reservation_group_token": reservation_group_token,
        "order_id": str(order.id),
        "payment_id": str(payment.id),
        "event_id": str(event.id),
        "status": order.status,
        "payment_status": payment.status,
        "total_amount": total_amount,
        "tickets_subtotal": tickets_subtotal,
        "management_fee": management_fee,
        "currency": currency,
        "expires_at": expires_at,
        "guest_access_token": order_customer.guest_access_token if order_customer else None,
        "items": [
            {
                "ticket_type_id": str(item["ticket_type"].id),
                "ticket_type_name": item["ticket_type"].name,
                "sale_group_id": str(item["ticket_type"].sale_group_id)
                if item["ticket_type"].sale_group_id
                else None,
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "subtotal": item["subtotal"],
            }
            for item in breakdown
        ],
    }
    
