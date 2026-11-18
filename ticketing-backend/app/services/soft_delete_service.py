from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.ticket_type import TicketType
from app.models.user import User


RETENTION_YEARS = 6


def _utc_now():
    return datetime.now(timezone.utc)


def _build_deleted_email(user_id: str) -> str:
    return f"deleted-user-{user_id}@deleted.local"


def _build_deleted_name(user_id: str) -> str:
    return f"deleted-user-{user_id[:8]}"


def _has_role(user: User, role_name: str) -> bool:
    return any(role.name == role_name for role in user.roles)


def _soft_delete_ticket_type_entity(ticket_type: TicketType, now: datetime) -> None:
    if ticket_type.status == "deleted":
        return

    ticket_type.status = "deleted"
    ticket_type.is_active = False
    ticket_type.deleted_at = now


def _soft_delete_event_entity(db: Session, event: Event, now: datetime) -> None:
    if event.status != "deleted":
        event.status = "deleted"
        event.deleted_at = now

    ticket_types = db.query(TicketType).filter(TicketType.event_id == event.id).all()
    for ticket_type in ticket_types:
        _soft_delete_ticket_type_entity(ticket_type, now)


def _soft_delete_user_entity(db: Session, user: User, now: datetime) -> None:
    user.email = _build_deleted_email(str(user.id))
    user.full_name = _build_deleted_name(str(user.id))
    user.password_hash = "deleted-user-no-login"
    user.is_active = False
    user.status = "deleted"
    user.deleted_at = now
    user.anonymized_at = now
    user.retention_until = now + timedelta(days=RETENTION_YEARS * 365)


def soft_delete_user_with_cascade(
    db: Session,
    user_id: str,
    deleted_by_user: User,
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.status == "deleted":
        return {
            "success": True,
            "message": "El usuario ya estaba borrado lógicamente",
            "entity_id": str(user.id),
            "entity_type": "user",
            "status": user.status,
            "deleted_at": user.deleted_at,
        }

    now = _utc_now()

    # Si el usuario es promoter, borrado lógico en cascada:
    # promoter -> events -> ticket_types
    if _has_role(user, "promoter"):
        promoter_events = db.query(Event).filter(Event.promoter_id == user.id).all()
        for event in promoter_events:
            _soft_delete_event_entity(db, event, now)

    _soft_delete_user_entity(db, user, now)

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Usuario borrado lógicamente correctamente",
        "entity_id": str(user.id),
        "entity_type": "user",
        "status": user.status,
        "deleted_at": user.deleted_at,
    }


def soft_delete_event(db: Session, event_id: str, deleted_by_user: User) -> dict:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if event.status == "deleted":
        return {
            "success": True,
            "message": "El evento ya estaba borrado lógicamente",
            "entity_id": str(event.id),
            "entity_type": "event",
            "status": event.status,
            "deleted_at": event.deleted_at,
        }

    now = _utc_now()

    _soft_delete_event_entity(db, event, now)

    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "message": "Evento borrado lógicamente correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "deleted_at": event.deleted_at,
    }


def soft_delete_ticket_type(db: Session, ticket_type_id: str, deleted_by_user: User) -> dict:
    ticket_type = db.query(TicketType).filter(TicketType.id == ticket_type_id).first()

    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de entrada no encontrado",
        )

    if ticket_type.status == "deleted":
        return {
            "success": True,
            "message": "El ticket type ya estaba borrado lógicamente",
            "entity_id": str(ticket_type.id),
            "entity_type": "ticket_type",
            "status": ticket_type.status,
            "deleted_at": ticket_type.deleted_at,
        }

    now = _utc_now()
    _soft_delete_ticket_type_entity(ticket_type, now)

    db.commit()
    db.refresh(ticket_type)

    return {
        "success": True,
        "message": "Tipo de entrada borrado lógicamente correctamente",
        "entity_id": str(ticket_type.id),
        "entity_type": "ticket_type",
        "status": ticket_type.status,
        "deleted_at": ticket_type.deleted_at,
    }