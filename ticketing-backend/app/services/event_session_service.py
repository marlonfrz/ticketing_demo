from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket import Ticket
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.models.user import User
from app.schemas.event_session import EventSessionCreate, EventSessionUpdate
from app.services.event_notification_service import send_event_session_status_email
from app.services.validation_station_service import finish_validation_stations_for_session

EVENT_FEE_TYPES = {"percentage", "fixed"}


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _ensure_admin(user: User, action: str) -> None:
    if _is_admin(user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Solo un administrador puede {action}",
    )


def _utc_now():
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def serialize_event_session(session: EventSession) -> dict:
    ticket_types = session.ticket_types or []
    return {
        "id": str(session.id),
        "event_id": str(session.event_id),
        "title": session.title,
        "location_name": session.location_name,
        "location_address": session.location_address,
        "starts_at": session.starts_at,
        "ends_at": session.ends_at,
        "capacity": session.capacity,
        "status": session.status,
        "publish_at": session.publish_at,
        "tickets_publish_at": session.tickets_publish_at,
        "tickets_activated_at": session.tickets_activated_at,
        "display_order": session.display_order,
        "ticket_types_count": len(ticket_types),
        "sold_tickets_count": sum(ticket_type.sold_count or 0 for ticket_type in ticket_types),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def get_event_manageable_by_user(db: Session, event_id: str, current_user: User) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if not _is_admin(current_user) and event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes gestionar sesiones de un evento que no es tuyo",
        )

    return event


def get_session_manageable_by_user(
    db: Session,
    session_id: str,
    current_user: User,
) -> EventSession:
    session = db.query(EventSession).filter(EventSession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesion no encontrada",
        )

    get_event_manageable_by_user(db, str(session.event_id), current_user)
    return session


def ensure_event_allows_session_changes(event: Event) -> None:
    if event.status in {"in_review", "archived", "disabled", "finished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden modificar sesiones en el estado actual del evento",
        )


def ensure_session_dates(starts_at: datetime, ends_at: datetime | None) -> None:
    if ends_at and ends_at < starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin no puede ser anterior al inicio de la sesion",
        )


def validate_event_fee(platform_fee_type: str, platform_fee_value: Decimal | float | int) -> Decimal:
    if platform_fee_type not in EVENT_FEE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de tarifa invalido",
        )

    fee_value = Decimal(str(platform_fee_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if fee_value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La tarifa no puede ser negativa",
        )

    if platform_fee_type == "percentage" and fee_value > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El porcentaje de tarifa no puede superar el 100%",
        )

    return fee_value


def ensure_session_ready_for_review(db: Session, session: EventSession) -> None:
    ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.session_id == session.id,
            TicketType.status.notin_(["disabled", "archived"]),
        )
        .all()
    )

    if not ticket_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes crear al menos un tipo de entrada antes de enviar la sesion a revision",
        )

    for ticket_type in ticket_types:
        if ticket_type.stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El ticket '{ticket_type.name}' debe tener stock antes de enviar a revision",
            )


def list_event_sessions(
    db: Session,
    event_id: str,
    current_user: User,
) -> list[EventSession]:
    get_event_manageable_by_user(db, event_id, current_user)

    return (
        db.query(EventSession)
        .filter(EventSession.event_id == event_id)
        .order_by(
            EventSession.display_order.asc().nullslast(),
            EventSession.starts_at.asc(),
            EventSession.created_at.asc(),
        )
        .all()
    )


def create_event_session(
    db: Session,
    event_id: str,
    current_user: User,
    data: EventSessionCreate,
) -> EventSession:
    event = get_event_manageable_by_user(db, event_id, current_user)
    ensure_event_allows_session_changes(event)
    ensure_session_dates(data.starts_at, data.ends_at)

    initial_status = (
        "draft"
        if _is_admin(current_user) and event.status != "not_reviewed"
        else "not_reviewed"
    )

    session = EventSession(
        event_id=event.id,
        title=data.title,
        location_name=data.location_name,
        location_address=data.location_address,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        capacity=data.capacity,
        status=initial_status,
        publish_at=data.publish_at,
        tickets_publish_at=data.tickets_publish_at,
        display_order=data.display_order,
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_event_session(
    db: Session,
    session_id: str,
    current_user: User,
    data: EventSessionUpdate,
) -> EventSession:
    session = get_session_manageable_by_user(db, session_id, current_user)
    event = session.event
    ensure_event_allows_session_changes(event)

    if session.status == "finished" and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El promotor no puede editar una sesion finalizada",
        )

    if session.status not in {"not_reviewed", "draft", "cancelled"} and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede editar sesiones publicadas",
        )

    update_data = data.model_dump(exclude_unset=True)
    starts_at = update_data.get("starts_at", session.starts_at)
    ends_at = update_data.get("ends_at", session.ends_at)
    ensure_session_dates(starts_at, ends_at)

    if "capacity" in update_data:
        total_stock = (
            db.query(func.coalesce(func.sum(TicketType.stock), 0))
            .filter(
                TicketType.session_id == session.id,
                TicketType.status.notin_(["disabled", "archived"]),
            )
            .scalar()
        )
        if update_data["capacity"] < int(total_stock or 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La capacidad no puede ser menor que el stock ya definido en la sesion",
            )

    for field, value in update_data.items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)
    return session


def duplicate_event_session(
    db: Session,
    session_id: str,
    current_user: User,
) -> EventSession:
    source = get_session_manageable_by_user(db, session_id, current_user)
    event = source.event
    if source.status != "finished":
        ensure_event_allows_session_changes(event)
    elif event.status in {"archived", "disabled", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede duplicar una sesion de un evento cerrado",
        )

    if source.status == "finished" and event.status == "finished":
        event.status = "draft"
        event.deactivated_at = None

    copy = EventSession(
        event_id=source.event_id,
        title=source.title,
        location_name=source.location_name,
        location_address=source.location_address,
        starts_at=source.starts_at,
        ends_at=source.ends_at,
        capacity=source.capacity,
        status="not_reviewed",
        publish_at=None,
        tickets_publish_at=None,
        display_order=(source.display_order or 0) + 1,
    )
    db.add(copy)
    db.flush()

    group_id_map = {}
    groups = (
        db.query(TicketSaleGroup)
        .filter(TicketSaleGroup.session_id == source.id)
        .all()
    )
    for group in groups:
        new_group = TicketSaleGroup(
            event_id=group.event_id,
            session_id=copy.id,
            name=group.name,
            strategy=group.strategy,
            is_active=False,
            sale_starts_at=None,
            sale_ends_at=None,
            status="draft",
            display_order=group.display_order,
        )
        db.add(new_group)
        db.flush()
        group_id_map[group.id] = new_group.id

    ticket_types = (
        db.query(TicketType)
        .filter(TicketType.session_id == source.id)
        .all()
    )
    for ticket_type in ticket_types:
        db.add(
            TicketType(
                event_id=ticket_type.event_id,
                session_id=copy.id,
                sale_group_id=group_id_map.get(ticket_type.sale_group_id),
                sale_order=ticket_type.sale_order,
                display_order=ticket_type.display_order,
                name=ticket_type.name,
                description=ticket_type.description,
                price=ticket_type.price,
                currency=ticket_type.currency,
                stock=ticket_type.stock,
                sold_count=0,
                max_per_purchase=ticket_type.max_per_purchase,
                is_active=True,
                status="draft",
            )
        )

    db.commit()
    db.refresh(copy)
    return copy


def _publish_draft_tickets_for_session(
    db: Session,
    session: EventSession,
    now: datetime,
    require_draft_tickets: bool = True,
) -> int:
    groups = (
        db.query(TicketSaleGroup)
        .filter(
            TicketSaleGroup.session_id == session.id,
            TicketSaleGroup.status == "draft",
        )
        .all()
    )
    ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.session_id == session.id,
            TicketType.status == "draft",
        )
        .order_by(
            TicketType.sale_group_id.asc().nullslast(),
            TicketType.sale_order.asc().nullslast(),
            TicketType.created_at.asc(),
        )
        .all()
    )

    if not ticket_types:
        if require_draft_tickets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La sesion no tiene entradas en borrador para publicar",
            )
        return 0

    for ticket_type in ticket_types:
        if ticket_type.stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El ticket '{ticket_type.name}' debe tener stock para publicarse",
            )

    for group in groups:
        group.status = "published"
        group.sale_starts_at = now
        group.sale_ends_at = None
        group.is_active = True

    for ticket_type in ticket_types:
        ticket_type.status = "published"
        ticket_type.sale_starts_at = now
        ticket_type.sale_ends_at = None
        ticket_type.sale_unlocked_at = None if ticket_type.sale_group_id else now

    published_group_ids = {ticket_type.sale_group_id for ticket_type in ticket_types if ticket_type.sale_group_id}
    for group_id in published_group_ids:
        first_ticket = (
            db.query(TicketType)
            .filter(
                TicketType.sale_group_id == group_id,
                TicketType.status == "published",
            )
            .order_by(TicketType.sale_order.asc(), TicketType.created_at.asc())
            .first()
        )
        if first_ticket:
            first_ticket.sale_unlocked_at = now

    session.tickets_publish_at = now
    session.tickets_activated_at = session.tickets_activated_at or now
    return len(ticket_types)


def publish_event_session(db: Session, session_id: str, current_user: User) -> EventSession:
    _ensure_admin(current_user, "publicar sesiones")
    session = get_session_manageable_by_user(db, session_id, current_user)
    event = session.event

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento principal debe estar publicado antes de publicar una sesion",
        )

    if session.status not in {"draft", "unpublished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede publicar una sesion en borrador o despublicada",
        )

    now = _utc_now()
    require_draft_tickets = session.tickets_activated_at is None
    session.status = "published"
    session.publish_at = now
    _publish_draft_tickets_for_session(
        db,
        session,
        now,
        require_draft_tickets=require_draft_tickets,
    )

    db.commit()
    db.refresh(session)
    return session


def publish_all_event_sessions(db: Session, event_id: str, current_user: User) -> dict:
    _ensure_admin(current_user, "publicar sesiones")
    event = get_event_manageable_by_user(db, event_id, current_user)

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento principal debe estar publicado antes de publicar sus sesiones",
        )

    sessions = (
        db.query(EventSession)
        .filter(
            EventSession.event_id == event.id,
            EventSession.status.in_(["draft", "unpublished"]),
        )
        .order_by(EventSession.starts_at.asc(), EventSession.created_at.asc())
        .all()
    )

    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay sesiones listas para publicar",
        )

    now = _utc_now()
    for session in sessions:
        session.status = "published"
        session.publish_at = now
        _publish_draft_tickets_for_session(
            db,
            session,
            now,
            require_draft_tickets=session.tickets_activated_at is None,
        )

    db.commit()

    return {
        "success": True,
        "message": "Sesiones publicadas correctamente",
        "entity_id": str(event.id),
        "entity_type": "event_sessions",
        "status": "published",
        "changed_at": now,
    }


def unpublish_event_session(db: Session, session_id: str, current_user: User) -> EventSession:
    _ensure_admin(current_user, "despublicar sesiones")
    session = get_session_manageable_by_user(db, session_id, current_user)

    if session.status not in {"published", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede despublicar una sesion publicada",
        )

    session.status = "unpublished"
    db.commit()
    db.refresh(session)
    return session


def finish_event_session(db: Session, session_id: str, current_user: User) -> EventSession:
    session = get_session_manageable_by_user(db, session_id, current_user)

    if session.status not in {"published", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede finalizar una sesion publicada",
        )

    now = _utc_now()
    session_start = _as_aware_utc(session.starts_at)
    if not _is_admin(current_user) and session_start and now < session_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El promotor solo puede finalizar la sesion cuando ya ha empezado",
        )

    session.status = "finished"
    session.deactivated_at = now

    groups = db.query(TicketSaleGroup).filter(TicketSaleGroup.session_id == session.id).all()
    for group in groups:
        group.is_active = False
        group.sale_ends_at = now

    ticket_types = db.query(TicketType).filter(TicketType.session_id == session.id).all()
    for ticket_type in ticket_types:
        ticket_type.sale_ends_at = now

    finish_validation_stations_for_session(db, str(session.id))
    db.commit()
    db.refresh(session)
    return session


def submit_event_session_for_review(db: Session, session_id: str, current_user: User) -> dict:
    session = get_session_manageable_by_user(db, session_id, current_user)

    if session.status not in {"not_reviewed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede enviar a revision una sesion no revisada o pendiente de cambios",
        )

    ensure_session_ready_for_review(db, session)

    session.status = "in_review"
    db.commit()
    db.refresh(session)
    send_event_session_status_email(session)

    return {
        "success": True,
        "message": "Sesion enviada a revision correctamente",
        "entity_id": str(session.id),
        "entity_type": "event_session",
        "status": session.status,
        "changed_at": session.updated_at,
    }


def submit_all_event_sessions_for_review(db: Session, event_id: str, current_user: User) -> dict:
    event = get_event_manageable_by_user(db, event_id, current_user)
    sessions = (
        db.query(EventSession)
        .filter(
            EventSession.event_id == event.id,
            EventSession.status.in_(["not_reviewed", "cancelled"]),
        )
        .order_by(EventSession.starts_at.asc(), EventSession.created_at.asc())
        .all()
    )

    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay sesiones pendientes de enviar a revision",
        )

    submitted_ids: list[str] = []
    for session in sessions:
        try:
            ensure_session_ready_for_review(db, session)
        except HTTPException as exc:
            session_name = session.title or session.location_name
            raise HTTPException(
                status_code=exc.status_code,
                detail=f"La sesion '{session_name}' no esta lista: {exc.detail}",
            ) from exc
        session.status = "in_review"
        submitted_ids.append(str(session.id))

    db.commit()
    for session in sessions:
        send_event_session_status_email(session)

    return {
        "success": True,
        "message": "Sesiones enviadas a revision correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": "in_review",
        "changed_at": _utc_now(),
        "submitted_session_ids": submitted_ids,
        "submitted_count": len(submitted_ids),
    }


def approve_event_session_review(
    db: Session,
    session_id: str,
    acted_by_user: User,
    platform_fee_type: str | None = None,
    platform_fee_value: Decimal | float | int | None = None,
) -> dict:
    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede aprobar sesiones",
        )

    session = db.query(EventSession).filter(EventSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesion no encontrada",
        )

    if session.status != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede aprobar una sesion en revision",
        )

    event = session.event
    fee_type = platform_fee_type or event.platform_fee_type
    fee_value = platform_fee_value if platform_fee_value is not None else event.platform_fee_value

    if fee_type is None or fee_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes indicar la tarifa del evento antes de aprobar la sesion",
        )

    event.platform_fee_type = fee_type
    event.platform_fee_value = validate_event_fee(fee_type, fee_value)
    if event.status in {"not_reviewed", "in_review"}:
        event.status = "draft"
    session.status = "draft"

    db.commit()
    db.refresh(session)
    send_event_session_status_email(session)

    return {
        "success": True,
        "message": "Sesion aprobada y devuelta a borrador",
        "entity_id": str(session.id),
        "entity_type": "event_session",
        "status": session.status,
        "changed_at": session.updated_at,
    }


def request_event_session_changes(
    db: Session,
    session_id: str,
    acted_by_user: User,
    reason: str | None = None,
) -> dict:
    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede pedir cambios",
        )

    session = db.query(EventSession).filter(EventSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesion no encontrada",
        )

    if session.status != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede devolver una sesion que esta en revision",
        )

    session.status = "not_reviewed"
    db.commit()
    db.refresh(session)
    send_event_session_status_email(session, reason)

    return {
        "success": True,
        "message": "Sesion devuelta al promotor para cambios",
        "entity_id": str(session.id),
        "entity_type": "event_session",
        "status": session.status,
        "changed_at": session.updated_at,
    }


def cancel_event_session_review(
    db: Session,
    session_id: str,
    acted_by_user: User,
    reason: str | None = None,
) -> dict:
    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede cancelar sesiones",
        )

    session = db.query(EventSession).filter(EventSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesion no encontrada",
        )

    if session.status not in {"not_reviewed", "in_review", "draft"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede cancelar una sesion no publicada",
        )

    session.status = "cancelled"
    db.commit()
    db.refresh(session)
    send_event_session_status_email(session, reason)

    return {
        "success": True,
        "message": "Sesion cancelada correctamente",
        "entity_id": str(session.id),
        "entity_type": "event_session",
        "status": session.status,
        "changed_at": session.updated_at,
    }


def delete_or_disable_event_session(db: Session, session_id: str, current_user: User) -> dict:
    session = get_session_manageable_by_user(db, session_id, current_user)
    event = session.event

    if event.status != "draft" or session.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden borrar sesiones cuando el evento y la sesion estan en draft",
        )

    session_count = (
        db.query(func.count(EventSession.id))
        .filter(EventSession.event_id == event.id)
        .scalar()
        or 0
    )
    if session_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar la unica sesion del evento",
        )

    generated_tickets = (
        db.query(func.count(Ticket.id))
        .filter(Ticket.session_id == session.id)
        .scalar()
        or 0
    )
    sold_tickets = (
        db.query(func.coalesce(func.sum(TicketType.sold_count), 0))
        .filter(TicketType.session_id == session.id)
        .scalar()
        or 0
    )

    if generated_tickets or int(sold_tickets or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar una sesion con entradas vendidas o generadas",
        )

    session_id_str = str(session.id)
    db.delete(session)
    db.commit()

    return {
        "success": True,
        "message": "Sesion borrada correctamente",
        "entity_id": session_id_str,
        "entity_type": "event_session",
        "status": "deleted",
        "changed_at": _utc_now(),
    }
