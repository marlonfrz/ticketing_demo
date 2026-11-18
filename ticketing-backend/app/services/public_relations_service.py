import re
import secrets
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.public_relations import PublicRelations
from app.models.ticket_type import TicketType
from app.models.user import User
from app.schemas.public_relations import PublicRelationsRegisterRequest


def _utc_now():
    return datetime.now(timezone.utc)


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\s+", "", phone.strip())


def _normalize_optional(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _generate_sales_code() -> str:
    return secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()


def _get_event_or_404(db: Session, event_id: str) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return event


def _ensure_event_manageable(event: Event, current_user: User) -> None:
    if _is_admin(current_user) or event.promoter_id == current_user.id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No puedes gestionar los RRPP de un evento que no es tuyo",
    )


def _ensure_event_accepts_public_relations(event: Event) -> None:
    if event.status not in {"draft", "published", "unpublished", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Los RRPP estaran disponibles cuando el evento haya sido aprobado",
        )


def build_public_relations_registration_url(event_id: str) -> str:
    return f"/events/{event_id}/rrpp"


def build_public_relations_sales_url(event_id: str, sales_code: str) -> str:
    return f"/events/{event_id}?rrpp={sales_code}"


def get_public_relations_registration_info(db: Session, event_id: str) -> dict:
    event = _get_event_or_404(db, event_id)
    _ensure_event_accepts_public_relations(event)

    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "event_status": event.status,
    }


def register_public_relations(db: Session, event_id: str, data: PublicRelationsRegisterRequest) -> dict:
    event = _get_event_or_404(db, event_id)
    _ensure_event_accepts_public_relations(event)

    if not data.accept_privacy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes aceptar la politica de privacidad",
        )

    phone = _normalize_phone(data.phone)
    existing = (
        db.query(PublicRelations)
        .filter(PublicRelations.event_id == event.id, PublicRelations.phone == phone)
        .first()
    )

    if existing:
        existing.full_name = data.full_name.strip()
        existing.email = _normalize_optional(data.email)
        existing.social_handle = _normalize_optional(data.social_handle)
        if existing.status == "disabled":
            existing.status = "active"
            existing.deactivated_at = None
        db.commit()
        db.refresh(existing)
        return serialize_public_relations(existing)

    sales_code = _generate_sales_code()
    while (
        db.query(PublicRelations)
        .filter(PublicRelations.event_id == event.id, PublicRelations.sales_code == sales_code)
        .first()
    ):
        sales_code = _generate_sales_code()

    public_relations = PublicRelations(
        event_id=event.id,
        full_name=data.full_name.strip(),
        phone=phone,
        email=_normalize_optional(data.email),
        social_handle=_normalize_optional(data.social_handle),
        sales_code=sales_code,
        status="active",
        accepted_privacy_at=_utc_now(),
    )
    db.add(public_relations)
    db.commit()
    db.refresh(public_relations)
    return serialize_public_relations(public_relations)


def get_public_relations_for_sale(db: Session, event_id: str, sales_code: str | None) -> PublicRelations | None:
    sales_code = (sales_code or "").strip()
    if not sales_code:
        return None

    return (
        db.query(PublicRelations)
        .filter(
            PublicRelations.event_id == event_id,
            PublicRelations.sales_code == sales_code,
            PublicRelations.status == "active",
        )
        .first()
    )


def serialize_public_relations(public_relations: PublicRelations) -> dict:
    event_id = str(public_relations.event_id)
    return {
        "id": str(public_relations.id),
        "event_id": event_id,
        "full_name": public_relations.full_name,
        "phone": public_relations.phone,
        "email": public_relations.email,
        "social_handle": public_relations.social_handle,
        "sales_code": public_relations.sales_code,
        "sales_url": build_public_relations_sales_url(event_id, public_relations.sales_code),
        "status": public_relations.status,
    }


def list_public_relations_summary(db: Session, event_id: str, current_user: User) -> list[dict]:
    event = _get_event_or_404(db, event_id)
    _ensure_event_manageable(event, current_user)

    public_relations_list = (
        db.query(PublicRelations)
        .filter(PublicRelations.event_id == event.id)
        .order_by(PublicRelations.created_at.desc())
        .all()
    )
    if not public_relations_list:
        return []

    rrpp_ids = [item.id for item in public_relations_list]
    rows = (
        db.query(
            Order.public_relations_id,
            OrderItem.session_id,
            EventSession.location_name,
            EventSession.starts_at,
            OrderItem.ticket_type_id,
            TicketType.name.label("ticket_type_name"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(TicketType, TicketType.id == OrderItem.ticket_type_id)
        .join(EventSession, EventSession.id == OrderItem.session_id)
        .filter(
            Order.event_id == event.id,
            Order.status == "paid",
            Order.public_relations_id.in_(rrpp_ids),
        )
        .group_by(
            Order.public_relations_id,
            OrderItem.session_id,
            EventSession.location_name,
            EventSession.starts_at,
            OrderItem.ticket_type_id,
            TicketType.name,
        )
        .all()
    )

    totals_by_rrpp = defaultdict(int)
    ticket_type_breakdown = defaultdict(lambda: defaultdict(int))
    session_breakdown = defaultdict(lambda: defaultdict(lambda: {"quantity": 0, "ticket_types": defaultdict(int)}))
    ticket_type_names: dict[str, str] = {}
    session_meta: dict[str, dict] = {}

    for row in rows:
        rrpp_id = str(row.public_relations_id)
        session_id = str(row.session_id)
        ticket_type_id = str(row.ticket_type_id)
        quantity = int(row.quantity or 0)

        totals_by_rrpp[rrpp_id] += quantity
        ticket_type_breakdown[rrpp_id][ticket_type_id] += quantity
        ticket_type_names[ticket_type_id] = row.ticket_type_name
        session_meta[session_id] = {
            "session_id": session_id,
            "location_name": row.location_name,
            "starts_at": row.starts_at,
        }
        session_breakdown[rrpp_id][session_id]["quantity"] += quantity
        session_breakdown[rrpp_id][session_id]["ticket_types"][ticket_type_id] += quantity

    summaries = []
    for public_relations in public_relations_list:
        rrpp_id = str(public_relations.id)
        by_ticket_type = [
            {
                "ticket_type_id": ticket_type_id,
                "ticket_type_name": ticket_type_names.get(ticket_type_id, "Entrada"),
                "quantity": quantity,
            }
            for ticket_type_id, quantity in sorted(
                ticket_type_breakdown[rrpp_id].items(),
                key=lambda item: ticket_type_names.get(item[0], ""),
            )
        ]

        by_session = []
        for session_id, data in session_breakdown[rrpp_id].items():
            meta = session_meta[session_id]
            by_session.append(
                {
                    **meta,
                    "quantity": data["quantity"],
                    "ticket_types": [
                        {
                            "ticket_type_id": ticket_type_id,
                            "ticket_type_name": ticket_type_names.get(ticket_type_id, "Entrada"),
                            "quantity": quantity,
                        }
                        for ticket_type_id, quantity in sorted(
                            data["ticket_types"].items(),
                            key=lambda item: ticket_type_names.get(item[0], ""),
                        )
                    ],
                }
            )
        by_session.sort(key=lambda item: item["starts_at"])

        serialized = serialize_public_relations(public_relations)
        serialized.update(
            {
                "registration_url": build_public_relations_registration_url(str(event.id)),
                "total_sold": totals_by_rrpp[rrpp_id],
                "by_ticket_type": by_ticket_type,
                "by_session": by_session,
                "created_at": public_relations.created_at,
            }
        )
        summaries.append(serialized)

    return summaries
