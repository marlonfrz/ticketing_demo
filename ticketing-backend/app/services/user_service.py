from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.user import User


RETENTION_YEARS = 6


def _utc_now():
    return datetime.now(timezone.utc)


def _has_role(user: User, role_name: str) -> bool:
    return any(role.name == role_name for role in user.roles)


def deactivate_user(
    db: Session,
    user_id: str,
    acted_by_user: User,
) -> dict:
    from app.services.event_service import can_archive_event, archive_event_entity

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.status == "deactivated":
        return {
            "success": True,
            "message": "La cuenta ya estaba desactivada",
            "entity_id": str(user.id),
            "entity_type": "user",
            "status": user.status,
            "changed_at": user.deactivated_at,
        }

    now = _utc_now()

    if _has_role(user, "promoter"):
        promoter_events = db.query(Event).filter(Event.promoter_id == user.id).all()

        for event in promoter_events:
            if event.status not in {"archived", "disabled", "cancelled", "finished"}:
                can_archive_event(db, event)

        for event in promoter_events:
            archive_event_entity(db, event, now)

    user.is_active = False
    user.status = "deactivated"
    user.deactivated_at = now
    user.retention_until = now + timedelta(days=RETENTION_YEARS * 365)

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Cuenta desactivada correctamente",
        "entity_id": str(user.id),
        "entity_type": "user",
        "status": user.status,
        "changed_at": user.deactivated_at,
    }