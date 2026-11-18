from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.ticket import Ticket
from app.models.ticket_type import TicketType
from app.models.ticket_validation import TicketValidation
from app.models.user import User

def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _event_total_session_capacity(event: Event) -> int:
    return sum(session.capacity or 0 for session in event.sessions)


def _get_event_accessible_by_user(db: Session, event_id: str, current_user: User) -> Event:
    event = db.query(Event).filter(Event.id == event_id, Event.status != "deleted",).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if not _is_admin(current_user) and event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes acceder a un evento que no es tuyo",
        )

    return event


def get_promoter_dashboard(db: Session, promoter: User) -> dict:
    events = (
        db.query(Event)
        .filter(
            Event.promoter_id == promoter.id,
            Event.status != "deleted",
        )
        .all()
    )
    events.sort(key=lambda event: event.starts_at)

    event_ids = [event.id for event in events]

    if not event_ids:
        return {
            "total_events": 0,
            "total_tickets_sold": 0,
            "total_tickets_validated": 0,
            "total_revenue": Decimal("0.00"),
            "upcoming_events": [],
        }

    total_tickets_sold = (
        db.query(func.coalesce(func.sum(TicketType.sold_count), 0))
        .filter(TicketType.event_id.in_(event_ids))
        .scalar()
    ) or 0

    total_tickets_validated = (
        db.query(func.count(Ticket.id))
        .filter(
            Ticket.event_id.in_(event_ids),
            Ticket.status == "used",
        )
        .scalar()
    ) or 0

    paid_order_ids = [
        order_id
        for (order_id,) in db.query(Order.id)
        .filter(Order.event_id.in_(event_ids), Order.status == "paid")
        .all()
    ]
    total_revenue = Decimal("0.00")
    if paid_order_ids:
        total_revenue = (
            db.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .filter(OrderItem.order_id.in_(paid_order_ids))
            .scalar()
        ) or Decimal("0.00")

    upcoming_events = [
        {
            "id": str(event.id),
            "title": event.title,
            "starts_at": event.starts_at,
            "status": event.status,
            "capacity": _event_total_session_capacity(event),
        }
        for event in events[:10]
    ]

    return {
        "total_events": len(events),
        "total_tickets_sold": int(total_tickets_sold),
        "total_tickets_validated": int(total_tickets_validated),
        "total_revenue": total_revenue,
        "upcoming_events": upcoming_events,
    }


def get_event_stats(db: Session, event_id: str, promoter: User) -> dict:
    event = _get_event_accessible_by_user(db, event_id, promoter)

    ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.event_id == event.id,
            TicketType.status != "deleted",
        )
        .order_by(TicketType.created_at.asc())
        .all()
    )

    total_stock_defined = sum(ticket_type.stock for ticket_type in ticket_types)
    total_tickets_sold = sum(ticket_type.sold_count for ticket_type in ticket_types)

    total_tickets_validated = (
        db.query(func.count(Ticket.id))
        .filter(
            Ticket.event_id == event.id,
            Ticket.status == "used",
        )
        .scalar()
    ) or 0

    paid_order_ids = [
        order_id
        for (order_id,) in db.query(Order.id)
        .filter(Order.event_id == event.id, Order.status == "paid")
        .all()
    ]
    total_revenue = Decimal("0.00")
    if paid_order_ids:
        total_revenue = (
            db.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .filter(OrderItem.order_id.in_(paid_order_ids))
            .scalar()
        ) or Decimal("0.00")

    ticket_type_stats = []
    for ticket_type in ticket_types:

        revenue = Decimal(ticket_type.sold_count) * Decimal(ticket_type.price)

        ticket_type_stats.append(
            {
                "ticket_type_id": str(ticket_type.id),
                "ticket_type_name": ticket_type.name,
                "stock": ticket_type.stock,
                "sold_count": ticket_type.sold_count,
                "remaining_stock": ticket_type.stock - ticket_type.sold_count,
                "revenue": revenue,
            }
        )

    return {
        "event_id": str(event.id),
        "title": event.title,
        "status": event.status,
        "capacity": _event_total_session_capacity(event),
        "total_stock_defined": total_stock_defined,
        "total_tickets_sold": total_tickets_sold,
        "total_tickets_validated": int(total_tickets_validated),
        "remaining_capacity": _event_total_session_capacity(event) - total_tickets_sold,
        "total_revenue": total_revenue,
        "ticket_types": ticket_type_stats,
    }


def get_event_orders(db: Session, event_id: str, promoter: User) -> list[dict]:
    event = _get_event_accessible_by_user(db, event_id, promoter)

    orders = (
        db.query(Order)
        .filter(Order.event_id == event.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(order.id),
            "buyer_id": str(order.buyer_id) if order.buyer_id else None,
            "status": order.status,
            "total_amount": order.total_amount,
            "currency": order.currency,
            "created_at": order.created_at,
        }
        for order in orders
    ]


def get_event_validations(db: Session, event_id: str, promoter: User) -> list[dict]:
    event = _get_event_accessible_by_user(db, event_id, promoter)

    validations = (
        db.query(TicketValidation)
        .join(Ticket, TicketValidation.ticket_id == Ticket.id, isouter=True)
        .filter(Ticket.event_id == event.id)
        .order_by(TicketValidation.validated_at.desc())
        .all()
    )

    return [
        {
            "id": str(validation.id),
            "ticket_id": str(validation.ticket_id) if validation.ticket_id else None,
            "result": validation.result,
            "message": validation.message,
            "validation_type": validation.validation_type,
            "device_id": validation.device_id,
            "validated_by_user_id": str(validation.validated_by_user_id) if validation.validated_by_user_id else None,
            "validation_station_id": str(validation.validation_station_id) if validation.validation_station_id else None,
            "validation_station_name": (
                validation.validation_station.name
                if validation.validation_station
                else None
            ),
            "notes": validation.notes,
            "validated_at": validation.validated_at,
        }
        for validation in validations
    ]
