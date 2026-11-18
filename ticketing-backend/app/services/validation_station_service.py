import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket import Ticket
from app.models.ticket_validation import TicketValidation
from app.models.user import User
from app.models.validation_quota_request import ValidationQuotaRequest
from app.models.validation_station import ValidationStation
from app.utils.date_time import format_display_datetime


ACTIVE_STATION_STATUSES = {"pending_activation", "active"}
VALID_QUOTA_REVIEW_STATUSES = {"approved", "rejected"}
VALIDATOR_STATION_COOKIE = "validator_station_session"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _has_role(user: User, role_name: str) -> bool:
    return any(role.name == role_name for role in user.roles)


def _session_label(session: EventSession) -> str:
    return f"{session.location_name} - {format_display_datetime(session.starts_at)}"


def _get_session(db: Session, session_id: str) -> EventSession:
    session = (
        db.query(EventSession)
        .options(joinedload(EventSession.event))
        .filter(EventSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesion no encontrada")
    return session


def _ensure_session_management_access(session: EventSession, user: User) -> None:
    if not _has_role(user, "admin") and session.event.promoter_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes gestionar puestos de validacion de esta sesion",
        )


def _serialize_quota_request(quota_request: ValidationQuotaRequest) -> dict:
    session = quota_request.session
    return {
        "id": str(quota_request.id),
        "session_id": str(quota_request.session_id),
        "event_id": str(session.event_id),
        "event_title": session.event.title,
        "session_label": _session_label(session),
        "requested_count": quota_request.requested_count,
        "approved_count": quota_request.approved_count,
        "status": quota_request.status,
        "promoter_note": quota_request.promoter_note,
        "admin_note": quota_request.admin_note,
        "requested_by_user_id": str(quota_request.requested_by_user_id),
        "requested_by_name": quota_request.requested_by.full_name,
        "reviewed_by_user_id": (
            str(quota_request.reviewed_by_user_id)
            if quota_request.reviewed_by_user_id
            else None
        ),
        "reviewed_at": quota_request.reviewed_at,
        "created_at": quota_request.created_at,
    }


def serialize_validation_station(station: ValidationStation, validated_count: int = 0) -> dict:
    session = station.session
    return {
        "id": str(station.id),
        "session_id": str(station.session_id),
        "event_id": str(session.event_id),
        "event_title": session.event.title,
        "session_label": _session_label(session),
        "name": station.name,
        "responsible_name": station.responsible_name,
        "notes": station.notes,
        "status": station.status,
        "validated_count": validated_count,
        "activated_at": station.activated_at,
        "revoked_at": station.revoked_at,
        "created_at": station.created_at,
    }


def _serialize_station_activity(validation: TicketValidation) -> dict:
    return {
        "id": str(validation.id),
        "validation_station_id": str(validation.validation_station_id),
        "validation_station_name": validation.validation_station.name,
        "ticket_id": str(validation.ticket_id) if validation.ticket_id else None,
        "ticket_code": validation.ticket.ticket_code if validation.ticket else None,
        "result": validation.result,
        "message": validation.message,
        "validation_type": validation.validation_type,
        "notes": validation.notes,
        "validated_at": validation.validated_at,
    }


def _get_approved_quota(db: Session, session_id: str) -> int:
    latest_approved = (
        db.query(ValidationQuotaRequest)
        .filter(
            ValidationQuotaRequest.session_id == session_id,
            ValidationQuotaRequest.status == "approved",
        )
        .order_by(ValidationQuotaRequest.reviewed_at.desc(), ValidationQuotaRequest.created_at.desc())
        .first()
    )
    return latest_approved.approved_count or 0 if latest_approved else 0


def _count_occupied_slots(db: Session, session_id: str) -> int:
    return (
        db.query(ValidationStation)
        .filter(
            ValidationStation.session_id == session_id,
            ValidationStation.status.in_(ACTIVE_STATION_STATUSES),
        )
        .count()
    )


def _count_successful_validations_for_session(db: Session, session_id: str) -> int:
    return (
        db.query(func.count(TicketValidation.id))
        .join(Ticket, TicketValidation.ticket_id == Ticket.id)
        .filter(
            Ticket.session_id == session_id,
            TicketValidation.result == "success",
        )
        .scalar()
        or 0
    )


def _count_successful_validations_by_station(
    db: Session,
    station_ids: list,
) -> dict[str, int]:
    if not station_ids:
        return {}

    rows = (
        db.query(TicketValidation.validation_station_id, func.count(TicketValidation.id))
        .filter(
            TicketValidation.validation_station_id.in_(station_ids),
            TicketValidation.result == "success",
        )
        .group_by(TicketValidation.validation_station_id)
        .all()
    )
    return {str(station_id): count for station_id, count in rows}


def get_validation_session_management(db: Session, session_id: str, current_user: User) -> dict:
    session = _get_session(db, session_id)
    _ensure_session_management_access(session, current_user)
    quota_requests = (
        db.query(ValidationQuotaRequest)
        .options(
            joinedload(ValidationQuotaRequest.session).joinedload(EventSession.event),
            joinedload(ValidationQuotaRequest.requested_by),
        )
        .filter(ValidationQuotaRequest.session_id == session.id)
        .order_by(ValidationQuotaRequest.created_at.desc())
        .all()
    )
    stations = (
        db.query(ValidationStation)
        .options(joinedload(ValidationStation.session).joinedload(EventSession.event))
        .filter(ValidationStation.session_id == session.id)
        .order_by(ValidationStation.created_at.asc())
        .all()
    )
    station_ids = [station.id for station in stations]
    station_validated_counts = _count_successful_validations_by_station(db, station_ids)
    approved_quota = _get_approved_quota(db, str(session.id))
    occupied_slots = _count_occupied_slots(db, str(session.id))
    return {
        "session_id": str(session.id),
        "approved_quota": approved_quota,
        "occupied_slots": occupied_slots,
        "available_slots": max(0, approved_quota - occupied_slots),
        "validated_count": _count_successful_validations_for_session(db, str(session.id)),
        "latest_request": _serialize_quota_request(quota_requests[0]) if quota_requests else None,
        "requests": [_serialize_quota_request(item) for item in quota_requests],
        "stations": [
            serialize_validation_station(
                station,
                station_validated_counts.get(str(station.id), 0),
            )
            for station in stations
        ],
        "recent_validations": [],
    }


def get_validation_station_activity(
    db: Session,
    station_id: str,
    current_user: User,
    limit: int = 50,
    offset: int = 0,
    result: str | None = None,
    ticket_code: str | None = None,
) -> dict:
    station = (
        db.query(ValidationStation)
        .options(joinedload(ValidationStation.session).joinedload(EventSession.event))
        .filter(ValidationStation.id == station_id)
        .first()
    )
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puesto no encontrado")

    _ensure_session_management_access(station.session, current_user)

    query = db.query(TicketValidation).filter(
        TicketValidation.validation_station_id == station.id
    )
    if result:
        query = query.filter(TicketValidation.result == result)
    if ticket_code:
        query = query.join(Ticket, TicketValidation.ticket_id == Ticket.id).filter(
            Ticket.ticket_code.ilike(f"%{ticket_code.strip()}%")
        )

    total = query.count()
    validations = (
        query.options(
            joinedload(TicketValidation.validation_station),
            joinedload(TicketValidation.ticket),
        )
        .order_by(TicketValidation.validated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    station_validated_counts = _count_successful_validations_by_station(db, [station.id])
    return {
        "station": serialize_validation_station(
            station,
            station_validated_counts.get(str(station.id), 0),
        ),
        "items": [_serialize_station_activity(validation) for validation in validations],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def create_validation_quota_request(
    db: Session,
    session_id: str,
    current_user: User,
    requested_count: int,
    promoter_note: str | None,
) -> dict:
    session = _get_session(db, session_id)
    _ensure_session_management_access(session, current_user)
    if session.status not in {"draft", "published", "sold_out", "unpublished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solicita validadores cuando la sesion ya haya superado la revision",
        )
    is_admin = _has_role(current_user, "admin")
    pending_request = (
        db.query(ValidationQuotaRequest)
        .filter(
            ValidationQuotaRequest.session_id == session.id,
            ValidationQuotaRequest.status == "pending",
        )
        .first()
    )
    if pending_request and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una solicitud de validadores pendiente para esta sesion",
        )

    if is_admin and pending_request:
        quota_request = pending_request
        quota_request.requested_count = requested_count
    else:
        quota_request = ValidationQuotaRequest(
            session_id=session.id,
            requested_count=requested_count,
            promoter_note=promoter_note,
            requested_by_user_id=current_user.id,
        )
        db.add(quota_request)

    if is_admin:
        quota_request.status = "approved"
        quota_request.approved_count = requested_count
        quota_request.admin_note = promoter_note
        quota_request.reviewed_by_user_id = current_user.id
        quota_request.reviewed_at = _utc_now()

    db.commit()
    return _serialize_quota_request(
        db.query(ValidationQuotaRequest)
        .options(
            joinedload(ValidationQuotaRequest.session).joinedload(EventSession.event),
            joinedload(ValidationQuotaRequest.requested_by),
        )
        .filter(ValidationQuotaRequest.id == quota_request.id)
        .first()
    )


def list_validation_quota_requests_admin(db: Session, request_status: str | None = None) -> list[dict]:
    query = db.query(ValidationQuotaRequest).options(
        joinedload(ValidationQuotaRequest.session).joinedload(EventSession.event),
        joinedload(ValidationQuotaRequest.requested_by),
    )
    if request_status:
        query = query.filter(ValidationQuotaRequest.status == request_status)
    requests = query.order_by(ValidationQuotaRequest.created_at.desc()).all()
    return [_serialize_quota_request(item) for item in requests]


def review_validation_quota_request(
    db: Session,
    quota_request_id: str,
    current_user: User,
    review_status: str,
    approved_count: int | None,
    admin_note: str | None,
) -> dict:
    if review_status not in VALID_QUOTA_REVIEW_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La solicitud solo se puede aprobar o rechazar",
        )
    quota_request = (
        db.query(ValidationQuotaRequest)
        .options(
            joinedload(ValidationQuotaRequest.session).joinedload(EventSession.event),
            joinedload(ValidationQuotaRequest.requested_by),
        )
        .filter(ValidationQuotaRequest.id == quota_request_id)
        .with_for_update(of=ValidationQuotaRequest)
        .first()
    )
    if not quota_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")
    if quota_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta solicitud ya ha sido revisada",
        )
    if review_status == "approved":
        if approved_count is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Indica cuantos puestos quedan aprobados",
            )
        if approved_count > quota_request.requested_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El cupo aprobado no puede superar la cantidad solicitada",
            )
        occupied_slots = _count_occupied_slots(db, str(quota_request.session_id))
        if approved_count < occupied_slots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existen {occupied_slots} puestos activos o pendientes de activacion",
            )
        quota_request.approved_count = approved_count
    else:
        quota_request.approved_count = None
    quota_request.status = review_status
    quota_request.admin_note = admin_note
    quota_request.reviewed_by_user_id = current_user.id
    quota_request.reviewed_at = _utc_now()
    db.commit()
    db.refresh(quota_request)
    return _serialize_quota_request(quota_request)


def _issue_activation_link(station: ValidationStation) -> dict:
    raw_token = secrets.token_urlsafe(48)
    expires_at = _utc_now() + timedelta(minutes=settings.validation_station_activation_expire_minutes)
    station.activation_token_hash = _hash_token(raw_token)
    station.activation_expires_at = expires_at
    station.access_token_hash = None
    station.access_expires_at = None
    station.status = "pending_activation"
    station.revoked_at = None
    return {
        "station": serialize_validation_station(station),
        "activation_url": (
            f"{settings.frontend_base_url.rstrip('/')}/validator/activate?token={quote(raw_token)}"
        ),
        "activation_expires_at": expires_at,
    }


def create_validation_station(
    db: Session,
    session_id: str,
    current_user: User,
    name: str,
    responsible_name: str | None,
    notes: str | None,
) -> dict:
    session = _get_session(db, session_id)
    _ensure_session_management_access(session, current_user)
    if session.status in {"finished", "deleted", "disabled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden crear puestos para una sesion cerrada",
        )
    approved_quota = _get_approved_quota(db, session_id)
    occupied_slots = _count_occupied_slots(db, session_id)
    if occupied_slots >= approved_quota:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quedan puestos disponibles dentro del cupo aprobado",
        )
    existing_station = (
        db.query(ValidationStation)
        .filter(
            ValidationStation.session_id == session.id,
            ValidationStation.name == name.strip(),
        )
        .first()
    )
    if existing_station:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un puesto con ese nombre en esta sesion",
        )
    station = ValidationStation(
        session_id=session.id,
        name=name.strip(),
        responsible_name=responsible_name.strip() if responsible_name else None,
        notes=notes,
        created_by_user_id=current_user.id,
    )
    db.add(station)
    db.flush()
    result = _issue_activation_link(station)
    db.commit()
    return result


def regenerate_validation_station_link(
    db: Session,
    station_id: str,
    current_user: User,
) -> dict:
    station = (
        db.query(ValidationStation)
        .options(joinedload(ValidationStation.session).joinedload(EventSession.event))
        .filter(ValidationStation.id == station_id)
        .with_for_update(of=ValidationStation)
        .first()
    )
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puesto no encontrado")
    _ensure_session_management_access(station.session, current_user)
    if station.status == "finished" or station.session.status == "finished":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede reactivar un puesto de una sesion finalizada",
        )
    result = _issue_activation_link(station)
    db.commit()
    return result


def revoke_validation_station(db: Session, station_id: str, current_user: User) -> dict:
    station = (
        db.query(ValidationStation)
        .options(joinedload(ValidationStation.session).joinedload(EventSession.event))
        .filter(ValidationStation.id == station_id)
        .with_for_update(of=ValidationStation)
        .first()
    )
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Puesto no encontrado")
    _ensure_session_management_access(station.session, current_user)
    station.status = "revoked"
    station.activation_token_hash = None
    station.activation_expires_at = None
    station.access_token_hash = None
    station.access_expires_at = None
    station.revoked_at = _utc_now()
    db.commit()
    db.refresh(station)
    return serialize_validation_station(station)


def activate_validation_station(
    db: Session,
    token: str,
    responsible_name: str | None,
) -> tuple[dict, str]:
    now = _utc_now()
    station = (
        db.query(ValidationStation)
        .options(joinedload(ValidationStation.session).joinedload(EventSession.event))
        .filter(ValidationStation.activation_token_hash == _hash_token(token))
        .with_for_update(of=ValidationStation)
        .first()
    )
    if not station or station.status != "pending_activation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de activacion no es valido o ya ha sido utilizado",
        )
    activation_expires_at = _as_aware_utc(station.activation_expires_at)
    if not activation_expires_at or activation_expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de activacion ha caducado. Solicita uno nuevo.",
        )
    if station.session.status in {"finished", "deleted", "disabled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sesion de este puesto ya no admite validaciones",
        )
    raw_access_token = secrets.token_urlsafe(48)
    station.responsible_name = responsible_name.strip() if responsible_name else station.responsible_name
    station.activation_token_hash = None
    station.activation_expires_at = None
    station.access_token_hash = _hash_token(raw_access_token)
    station.access_expires_at = now + timedelta(minutes=settings.validation_station_session_expire_minutes)
    station.activated_at = now
    station.status = "active"
    station.revoked_at = None
    db.commit()
    db.refresh(station)
    return serialize_validation_station(station), raw_access_token


def get_current_validation_station(request: Request, db: Session) -> ValidationStation:
    raw_token = request.cookies.get(VALIDATOR_STATION_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Activa este puesto primero")
    station = (
        db.query(ValidationStation)
        .options(joinedload(ValidationStation.session).joinedload(EventSession.event))
        .filter(ValidationStation.access_token_hash == _hash_token(raw_token))
        .first()
    )
    if not station or station.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El acceso de este puesto ya no es valido",
        )
    access_expires_at = _as_aware_utc(station.access_expires_at)
    if not access_expires_at or access_expires_at < _utc_now():
        station.status = "revoked"
        station.access_token_hash = None
        station.access_expires_at = None
        station.revoked_at = _utc_now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesion del puesto ha caducado. Solicita un enlace nuevo.",
        )
    return station


def report_validation_station_incident(
    db: Session,
    station: ValidationStation,
    message: str,
    qr_token: str | None,
) -> dict:
    ticket = None
    if qr_token:
        ticket = db.query(Ticket).filter(Ticket.qr_token == qr_token).first()
        if ticket and ticket.session_id != station.session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La entrada indicada pertenece a otra sesion",
            )
    validation = TicketValidation(
        ticket_id=ticket.id if ticket else None,
        result="reported",
        message="Incidencia registrada por el puesto",
        validation_type="incident",
        validation_station_id=station.id,
        notes=message.strip(),
    )
    db.add(validation)
    db.commit()
    db.refresh(validation)
    validation.validation_station = station
    return _serialize_station_activity(validation)


def finish_validation_stations_for_session(db: Session, session_id: str) -> None:
    stations = db.query(ValidationStation).filter(ValidationStation.session_id == session_id).all()
    for station in stations:
        station.status = "finished"
        station.activation_token_hash = None
        station.activation_expires_at = None
        station.access_token_hash = None
        station.access_expires_at = None
