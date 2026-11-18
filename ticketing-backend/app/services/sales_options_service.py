from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.services.ticket_inventory_service import (
    get_active_reserved_quantity,
    sync_event_ticket_sales_state,
    sync_ticket_type_sales_state,
)
from app.services.ticket_reservation_service import sync_sale_group_unlocks


LOW_STOCK_THRESHOLD = 5
CASCADE_GROUP_STRATEGIES = {"stock_cascade", "time_and_stock_cascade"}


def _utc_now():
    return datetime.now(timezone.utc)


def get_real_available_stock(db: Session, ticket_type: TicketType) -> int:
    sync_ticket_type_sales_state(db, ticket_type)
    reserved = get_active_reserved_quantity(db, str(ticket_type.id), _utc_now())
    return max(0, ticket_type.stock - ticket_type.sold_count - reserved)


def get_ticket_availability_status(db: Session, ticket_type: TicketType) -> str:
    now = _utc_now()

    if ticket_type.status in {"disabled", "archived"}:
        return "disabled"

    sync_ticket_type_sales_state(db, ticket_type)

    if ticket_type.status != "published":
        if ticket_type.status == "sold_out":
            return "sold_out"
        return "draft"

    if not ticket_type.is_active:
        return "paused"

    if ticket_type.sale_starts_at and now < ticket_type.sale_starts_at:
        return "not_started"

    if ticket_type.sale_ends_at and now > ticket_type.sale_ends_at:
        return "ended"

    available_stock = get_real_available_stock(db, ticket_type)

    if available_stock <= 0:
        return "sold_out"

    if available_stock <= LOW_STOCK_THRESHOLD:
        return "low_stock"

    return "available"


def serialize_ticket_option(db: Session, ticket_type: TicketType) -> dict:
    availability_status = get_ticket_availability_status(db, ticket_type)
    available_stock = get_real_available_stock(db, ticket_type)

    if ticket_type.sale_group_id and ticket_type.sale_unlocked_at is None:
        availability_status = "locked"
        max_selectable_quantity = 0
    else:
        max_selectable_quantity = (
            min(available_stock, ticket_type.max_per_purchase)
            if availability_status in {"available", "low_stock"}
            else 0
        )

    return {
        "id": str(ticket_type.id),
        "name": ticket_type.name,
        "description": ticket_type.description,
        "price": ticket_type.price,
        "currency": ticket_type.currency,
        "status": ticket_type.status,
        "availability_status": availability_status,
        "max_selectable_quantity": max_selectable_quantity,
        "available_quantity": available_stock,
        "max_per_purchase": ticket_type.max_per_purchase,
        "is_low_stock": availability_status == "low_stock",
        "sale_starts_at": ticket_type.sale_starts_at,
        "sale_ends_at": ticket_type.sale_ends_at,
        "sale_unlocked_at": ticket_type.sale_unlocked_at,
        "display_order": ticket_type.display_order,
        "sale_order": ticket_type.sale_order,
    }


def get_event_sales_options(db: Session, event_id: str, session_id: str | None = None) -> dict:
    now = _utc_now()
    sync_event_ticket_sales_state(db, event_id)

    event = (
        db.query(Event)
        .filter(
            Event.id == event_id,
            Event.status == "published",
            Event.publish_at <= now,
        )
        .first()
    )

    if not event:
        return {
            "event_id": event_id,
            "session_id": session_id,
            "items": [],
        }

    if not session_id:
        return {
            "event_id": str(event.id),
            "session_id": None,
            "items": [],
        }

    session = None
    session = (
        db.query(EventSession)
        .filter(
            EventSession.id == session_id,
            EventSession.event_id == event.id,
            EventSession.status.in_(["published", "sold_out"]),
            EventSession.publish_at <= now,
            EventSession.tickets_publish_at <= now,
            or_(EventSession.ends_at.is_(None), EventSession.ends_at >= now),
            EventSession.tickets_activated_at.isnot(None),
        )
        .first()
    )
    if not session:
        return {
            "event_id": str(event.id),
            "session_id": session_id,
            "items": [],
        }

    standalone_query = (
        db.query(TicketType)
        .filter(
            TicketType.event_id == event.id,
            TicketType.sale_group_id.is_(None),
            TicketType.status.in_(["published", "sold_out"]),
        )
    )
    standalone_query = standalone_query.filter(TicketType.session_id == session.id)
    standalone_ticket_types = standalone_query.order_by(
        TicketType.display_order.asc().nullslast(),
        TicketType.created_at.asc(),
    ).all()

    groups_query = (
        db.query(TicketSaleGroup)
        .filter(
            TicketSaleGroup.event_id == event.id,
            TicketSaleGroup.status == "published",
            TicketSaleGroup.is_active == True,
        )
    )
    groups_query = groups_query.filter(TicketSaleGroup.session_id == session.id)
    groups = groups_query.order_by(
        TicketSaleGroup.display_order.asc().nullslast(),
        TicketSaleGroup.created_at.asc(),
    ).all()

    items = []
    sale_groups_changed = False

    for ticket_type in standalone_ticket_types:
        items.append(
            {
                "type": "ticket_type",
                "display_order": ticket_type.display_order,
                "ticket_type": serialize_ticket_option(db, ticket_type),
            }
        )

    for group in groups:
        sale_groups_changed = sync_sale_group_unlocks(db, str(group.id)) or sale_groups_changed
        
        ticket_types = (
            db.query(TicketType)
            .filter(
                TicketType.sale_group_id == group.id,
                TicketType.status.in_(["published", "sold_out"]),
            )
            .order_by(TicketType.sale_order.asc().nullslast(), TicketType.created_at.asc())
            .all()
        )

        serialized_ticket_types = [
            serialize_ticket_option(db, ticket_type)
            for ticket_type in ticket_types
        ]

        if group.strategy in CASCADE_GROUP_STRATEGIES:
            for index, (ticket_type, serialized_ticket_type) in enumerate(
                zip(ticket_types, serialized_ticket_types)
            ):
                if ticket_type.sale_unlocked_at is None:
                    continue
                if serialized_ticket_type["availability_status"] not in {
                    "available",
                    "low_stock",
                }:
                    continue

                cascade_available_quantity = sum(
                    serialized_candidate["available_quantity"]
                    for candidate, serialized_candidate in zip(
                        ticket_types[index:],
                        serialized_ticket_types[index:],
                    )
                    if get_ticket_availability_status(db, candidate)
                    in {"available", "low_stock"}
                )
                serialized_ticket_type["max_selectable_quantity"] = min(
                    cascade_available_quantity,
                    ticket_type.max_per_purchase,
                )
                serialized_ticket_type["is_low_stock"] = (
                    0 < cascade_available_quantity <= LOW_STOCK_THRESHOLD
                )

        items.append(
            {
                "type": "sale_group",
                "id": str(group.id),
                "name": group.name,
                "strategy": group.strategy,
                "display_order": group.display_order,
                "sale_starts_at": group.sale_starts_at,
                "sale_ends_at": group.sale_ends_at,
                "ticket_types": serialized_ticket_types,
            }
        )

    if sale_groups_changed:
        db.commit()

    items.sort(key=lambda item: (item.get("display_order") is None, item.get("display_order") or 999999))

    return {
        "event_id": str(event.id),
        "session_id": str(session.id) if session else None,
        "items": items,
    }
