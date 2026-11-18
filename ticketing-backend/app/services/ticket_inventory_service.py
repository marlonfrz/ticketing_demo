from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_type import TicketType


def get_paid_ticket_count(db: Session, ticket_type_id: str) -> int:
    total = (
        db.query(func.count(Ticket.id))
        .join(Order, Order.id == Ticket.order_id)
        .filter(
            Ticket.ticket_type_id == ticket_type_id,
            Ticket.status == "active",
            Order.status == "paid",
        )
        .scalar()
    )
    return int(total or 0)


def get_active_reserved_quantity(db: Session, ticket_type_id: str, now) -> int:
    total = (
        db.query(func.coalesce(func.sum(TicketReservation.quantity), 0))
        .filter(
            TicketReservation.ticket_type_id == ticket_type_id,
            TicketReservation.status == "active",
            TicketReservation.expires_at > now,
        )
        .scalar()
    )
    return int(total or 0)


def sync_ticket_type_sales_state(db: Session, ticket_type: TicketType) -> bool:
    changed = False
    paid_ticket_count = get_paid_ticket_count(db, str(ticket_type.id))

    if ticket_type.sold_count != paid_ticket_count:
        ticket_type.sold_count = paid_ticket_count
        changed = True

    if ticket_type.status == "sold_out" and paid_ticket_count < ticket_type.stock:
        ticket_type.status = "published"
        ticket_type.is_active = True
        changed = True
    elif ticket_type.status == "published" and paid_ticket_count >= ticket_type.stock:
        ticket_type.status = "sold_out"
        ticket_type.is_active = False
        changed = True

    return changed


def sync_event_ticket_sales_state(db: Session, event_id: str) -> bool:
    ticket_types = db.query(TicketType).filter(TicketType.event_id == event_id).all()
    changed = False

    for ticket_type in ticket_types:
        if ticket_type.status in {"published", "sold_out"}:
            changed = sync_ticket_type_sales_state(db, ticket_type) or changed

    if changed:
        db.commit()

    return changed
