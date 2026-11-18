from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.ticket import Ticket
from app.models.ticket_type import TicketType
from app.models.ticket_validation import TicketValidation
from app.models.user import User
from app.schemas.event import ALLOWED_EVENT_STATUSES, EventCreate, EventUpdate
from app.models.ticket_sale_group import TicketSaleGroup
from app.services.event_notification_service import send_event_status_email, send_new_event_admin_email
from app.services.validation_station_service import finish_validation_stations_for_session


EVENT_FEE_TYPES = {"percentage", "fixed"}
PROMOTER_DAILY_EVENT_CREATION_LIMIT = 3


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _utc_now():
    return datetime.now(timezone.utc)


def _start_of_utc_day(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def count_events_created_today_by_promoter(db: Session, promoter_id: str, now: datetime | None = None) -> int:
    now = now or _utc_now()
    return int(
        db.query(func.count(Event.id))
        .filter(
            Event.promoter_id == promoter_id,
            Event.created_at >= _start_of_utc_day(now),
        )
        .scalar()
        or 0
    )


def ensure_promoter_can_create_event_today(db: Session, current_user: User) -> int:
    if _is_admin(current_user):
        return 0

    created_today = count_events_created_today_by_promoter(db, str(current_user.id))
    if created_today >= PROMOTER_DAILY_EVENT_CREATION_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Has alcanzado el limite de 3 eventos creados hoy. "
                "Si necesitas crear mas, contacta con soporte."
            ),
        )

    return created_today


def _event_next_session_start(event: Event) -> datetime:
    starts_at = [session.starts_at for session in event.sessions if session.starts_at]
    return min(starts_at) if starts_at else datetime.max.replace(tzinfo=timezone.utc)


def _event_has_started(event: Event, now: datetime) -> bool:
    return any(session.starts_at <= now for session in event.sessions)


def validate_event_fee(platform_fee_type: str, platform_fee_value: Decimal | float | int) -> Decimal:
    if platform_fee_type not in EVENT_FEE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de tarifa inválido",
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


def set_event_fee(
    db: Session,
    event_id: str,
    acted_by_user: User,
    platform_fee_type: str,
    platform_fee_value: Decimal | float | int,
) -> Event:
    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede modificar la tarifa del evento",
        )

    event = get_event_by_id_internal(db, event_id)
    event.platform_fee_type = platform_fee_type
    event.platform_fee_value = validate_event_fee(platform_fee_type, platform_fee_value)

    db.commit()
    db.refresh(event)
    return event


def get_event_financial_summary(db: Session, event_id: str) -> dict:
    paid_orders = (
        db.query(Order)
        .filter(
            Order.event_id == event_id,
            Order.status == "paid",
        )
        .all()
    )
    paid_order_ids = [order.id for order in paid_orders]
    currency = paid_orders[0].currency if paid_orders else "EUR"
    gross_revenue = sum((Decimal(str(order.total_amount)) for order in paid_orders), Decimal("0.00"))

    tickets_sold = 0
    tickets_revenue = Decimal("0.00")
    if paid_order_ids:
        tickets_sold = (
            db.query(func.coalesce(func.sum(OrderItem.quantity), 0))
            .filter(OrderItem.order_id.in_(paid_order_ids))
            .scalar()
            or 0
        )
        tickets_revenue = (
            db.query(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .filter(OrderItem.order_id.in_(paid_order_ids))
            .scalar()
            or Decimal("0.00")
        )
        tickets_revenue = Decimal(str(tickets_revenue))

    platform_revenue = (gross_revenue - tickets_revenue).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    if platform_revenue < 0:
        platform_revenue = Decimal("0.00")

    promoter_revenue = tickets_revenue.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    complimentary_rows = (
        db.query(
            Ticket.ticket_type_id,
            TicketType.name,
            func.count(Ticket.id),
        )
        .join(TicketType, TicketType.id == Ticket.ticket_type_id)
        .filter(
            Ticket.event_id == event_id,
            Ticket.source == "complimentary",
            Ticket.status == "active",
        )
        .group_by(Ticket.ticket_type_id, TicketType.name)
        .all()
    )
    complimentary_by_type = [
        {
            "ticket_type_id": str(ticket_type_id),
            "ticket_type_name": name,
            "quantity": int(quantity or 0),
        }
        for ticket_type_id, name, quantity in complimentary_rows
    ]
    complimentary_total = sum(item["quantity"] for item in complimentary_by_type)

    return {
        "tickets_sold": int(tickets_sold),
        "gross_revenue": gross_revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "platform_revenue": platform_revenue,
        "promoter_revenue": promoter_revenue,
        "tickets_revenue": promoter_revenue,
        "management_fee_revenue": platform_revenue,
        "complimentary_tickets_total": complimentary_total,
        "complimentary_tickets_by_type": complimentary_by_type,
        "currency": currency,
    }


def create_event(db: Session, current_user: User, data: EventCreate) -> Event:
    events_created_before = ensure_promoter_can_create_event_today(db, current_user)

    if data.status not in ALLOWED_EVENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de evento inválido",
        )

    initial_session = data.initial_session
    if initial_session.ends_at and initial_session.ends_at < initial_session.starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin no puede ser anterior a la de inicio",
        )
    
    event_status = data.status if _is_admin(current_user) else "not_reviewed"

    event = Event(
        promoter_id=current_user.id,
        title=data.title,
        description=data.description,
        publish_at=None,
        status=event_status,
        platform_fee_type=None,
        platform_fee_value=None,
    )

    db.add(event)
    db.flush()
    db.add(
        EventSession(
            event_id=event.id,
            title=initial_session.title,
            location_name=initial_session.location_name,
            location_address=initial_session.location_address,
            starts_at=initial_session.starts_at,
            ends_at=initial_session.ends_at,
            capacity=initial_session.capacity,
            status=event_status,
            publish_at=initial_session.publish_at,
            tickets_publish_at=initial_session.tickets_publish_at,
            display_order=initial_session.display_order or 1,
        )
    )
    db.commit()
    db.refresh(event)

    if not _is_admin(current_user):
        send_new_event_admin_email(db, event, events_created_before + 1)

    return event


def list_events(db: Session):
    now = _utc_now()
    finish_events_by_end_time(db, now)

    events = (
        db.query(Event)
        .filter(
            Event.status.in_(["published", "finished"]),
            Event.publish_at <= now,
        )
        .order_by(Event.publish_at.desc(), Event.created_at.desc())
        .all()
    )
    return events


def get_event_by_id(db: Session, event_id: str) -> Event:
    now = _utc_now()
    finish_events_by_end_time(db, now)

    event = (
        db.query(Event)
        .filter(
            Event.id == event_id,
            Event.status.in_(["published", "finished", "sold_out", "cancelled"]),
            Event.publish_at <= now,
        )
        .first()
    )

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    return event


def get_event_by_id_internal(db: Session, event_id: str) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )
    return event


def update_event(db: Session, event_id: str, current_user: User, data: EventUpdate) -> Event:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(current_user) and event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes editar un evento que no es tuyo",
        )

    if not _is_admin(current_user) and event.status != "not_reviewed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El promotor solo puede editar el evento antes de enviarlo a revision",
        )

    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("capacity", None)

    if "status" in update_data and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede cambiar el estado del evento directamente",
        )

    if "status" in update_data and update_data["status"] not in ALLOWED_EVENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de evento inválido",
        )

    first_session = min(event.sessions, key=lambda session: session.starts_at)
    starts_at = first_session.starts_at
    ends_at = first_session.ends_at
    tickets_publish_at = first_session.tickets_publish_at

    if ends_at and ends_at < starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin no puede ser anterior a la de inicio",
        )
        
    if tickets_publish_at and tickets_publish_at >= starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de publicación de entradas debe ser anterior a la fecha de inicio del evento",
        )

    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event


def get_events_by_promoter(db: Session, promoter: User):
    return (
        db.query(Event)
        .filter(
            Event.promoter_id == promoter.id,
            Event.status.in_(
                [
                    "not_reviewed",
                    "in_review",
                    "draft",
                    "published",
                    "unpublished",
                    "cancelled",
                    "finished",
                    "sold_out",
                ]
            ),
        )
        .order_by(Event.created_at.desc())
        .all()
    )

def get_event_detail_for_management(db: Session, event_id: str, current_user: User) -> Event:
    finish_events_by_end_time(db)
    event = get_event_by_id_internal(db, event_id)

    if _is_admin(current_user):
        return event

    if event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes acceder a un evento que no es tuyo",
        )

    return event

def event_has_paid_orders(db: Session, event_id: str) -> bool:
    return (
        db.query(Order)
        .filter(
            Order.event_id == event_id,
            Order.status == "paid",
        )
        .first()
        is not None
    )


def event_has_tickets(db: Session, event_id: str) -> bool:
    return db.query(Ticket).filter(Ticket.event_id == event_id).first() is not None


def event_has_validations(db: Session, event_id: str) -> bool:
    return (
        db.query(TicketValidation)
        .join(Ticket, TicketValidation.ticket_id == Ticket.id, isouter=True)
        .filter(Ticket.event_id == event_id)
        .first()
        is not None
    )


def finish_events_by_end_time(db: Session, now: datetime | None = None) -> bool:
    now = now or _utc_now()
    sessions = (
        db.query(EventSession)
        .filter(
            EventSession.status.in_(["published", "sold_out"]),
            EventSession.ends_at.isnot(None),
            EventSession.ends_at <= now,
        )
        .all()
    )

    if not sessions:
        return False

    affected_events = {session.event for session in sessions}
    for session in sessions:
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

    finished_events = []
    terminal_statuses = {"finished", "cancelled", "disabled", "archived"}
    for event in affected_events:
        if event.sessions and all(session.status in terminal_statuses for session in event.sessions):
            event.status = "finished"
            event.deactivated_at = now
            finished_events.append(event)

    db.commit()
    for event in finished_events:
        send_event_status_email(event)

    return True


def finish_event(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)
    now = _utc_now()

    if not _is_admin(acted_by_user) and event.promoter_id != acted_by_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes finalizar un evento que no es tuyo",
        )

    if event.status == "finished":
        return {
            "success": True,
            "message": "El evento ya estaba finalizado",
            "entity_id": str(event.id),
            "entity_type": "event",
            "status": event.status,
            "changed_at": event.deactivated_at,
        }

    if event.status not in {"published", "sold_out", "finished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede finalizar un evento publicado",
        )

    open_sessions = [
        session
        for session in event.sessions
        if session.status in {"published", "sold_out"}
    ]
    if not _is_admin(acted_by_user) and any(now < session.starts_at for session in open_sessions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El promotor solo puede finalizar el evento cuando todas sus sesiones publicadas hayan empezado",
        )

    event.status = "finished"
    event.deactivated_at = now
    for session in event.sessions:
        if session.status in {"published", "sold_out"}:
            session.status = "finished"
            session.deactivated_at = now
        finish_validation_stations_for_session(db, str(session.id))

    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento finalizado correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.deactivated_at,
    }


def can_archive_event(db: Session, event: Event) -> None:
    now = _utc_now()
    never_published_statuses = {"not_reviewed", "in_review", "draft"}

    if event.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un evento publicado. Debe pasar antes a un estado seguro.",
        )

    if event.status in {"finished", "archived", "disabled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un evento en ese estado",
        )

    if event.status not in never_published_statuses and _event_has_started(event, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un evento que ya ha empezado",
        )

    if event_has_paid_orders(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un evento con pedidos pagados",
        )

    if event_has_tickets(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un evento que ya tiene tickets generados",
        )

    if event_has_validations(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un evento con validaciones registradas",
        )


def archive_event_entity(db: Session, event: Event, now: datetime) -> None:
    if event.status in {"archived", "disabled"}:
        return

    event.status = "archived"
    event.deactivated_at = now
    for session in event.sessions:
        finish_validation_stations_for_session(db, str(session.id))

    ticket_types = db.query(TicketType).filter(TicketType.event_id == event.id).all()
    for ticket_type in ticket_types:
        if ticket_type.status not in {"archived", "disabled"}:
            ticket_type.status = "disabled"
            ticket_type.is_active = False
            ticket_type.deactivated_at = now


def archive_event(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user) and event.promoter_id != acted_by_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes archivar un evento que no es tuyo",
        )

    if event.status in {"archived", "disabled"}:
        return {
            "success": True,
            "message": "El evento ya estaba borrado",
            "entity_id": str(event.id),
            "entity_type": "event",
            "status": "deleted",
            "changed_at": event.deactivated_at,
        }

    can_archive_event(db, event)

    now = _utc_now()
    archive_event_entity(db, event, now)

    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento borrado correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": "deleted",
        "changed_at": event.deactivated_at,
    }


def delete_unpublished_event(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)
    is_admin = _is_admin(acted_by_user)

    if not is_admin and event.promoter_id != acted_by_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes borrar un evento que no es tuyo",
        )

    if event.status in {"published", "sold_out", "finished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden borrar eventos que no esten publicados ni finalizados",
        )

    if event.status in {"archived", "disabled"}:
        return {
            "success": True,
            "message": "El evento ya estaba borrado",
            "entity_id": str(event.id),
            "entity_type": "event",
            "status": "deleted",
            "changed_at": event.deactivated_at,
        }

    if not is_admin and event.status not in {"not_reviewed", "in_review"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El promotor solo puede borrar eventos que aun no han sido aprobados",
        )

    can_archive_event(db, event)

    now = _utc_now()
    if event.status in {"not_reviewed", "in_review"}:
        event_id_value = str(event.id)
        db.delete(event)
        db.commit()
        return {
            "success": True,
            "message": "Evento borrado correctamente",
            "entity_id": event_id_value,
            "entity_type": "event",
            "status": "deleted",
            "changed_at": now,
        }

    archive_event_entity(db, event, now)

    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento borrado correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": "deleted",
        "changed_at": event.deactivated_at,
    }

def can_unpublish_event(db: Session, event: Event) -> None:
    now = _utc_now()

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede despublicar un evento que esté en estado published",
        )

    if _event_has_started(event, now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede despublicar un evento que ya ha empezado",
        )

    if event_has_paid_orders(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede despublicar un evento con pedidos pagados",
        )

    if event_has_tickets(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede despublicar un evento que ya tiene tickets generados",
        )

    if event_has_validations(db, event.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede despublicar un evento con validaciones registradas",
        )


def unpublish_event(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede despublicar eventos",
        )

    if event.status not in {"published", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede despublicar un evento publicado",
        )

    event.status = "unpublished"

    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento despublicado correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.updated_at,
    }

def can_publish_event(db: Session, event: Event) -> None:
    if event.status not in {"draft", "unpublished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede publicar un evento que esté en estado draft",
        )

    if _event_has_started(event, _utc_now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede publicar un evento que ya ha empezado",
        )

    if not event.title or not event.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento debe tener un título válido para publicarse",
        )

    if not event.location_name or not event.location_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento debe tener una ubicación válida para publicarse",
        )

    if event.ends_at and event.ends_at < event.starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin no puede ser anterior a la fecha de inicio",
        )

def can_review_event_basics(event: Event) -> None:
    if not event.title or not event.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento debe tener un título válido",
        )

    if not event.location_name or not event.location_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento debe tener una ubicación válida",
        )

    if event.ends_at and event.ends_at < event.starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin no puede ser anterior a la fecha de inicio",
        )


def ensure_event_ready_for_review(db: Session, event: Event) -> None:
    if event.status != "not_reviewed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede enviar a revisión un evento no revisado",
        )

    can_review_event_basics(event)

    ticket_types = (
        db.query(TicketType)
        .filter(
            TicketType.event_id == event.id,
            TicketType.status.notin_(["disabled", "archived"]),
        )
        .all()
    )

    if not ticket_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes crear al menos un tipo de entrada antes de enviar el evento a revisión",
        )

    for ticket_type in ticket_types:
        if ticket_type.stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El ticket '{ticket_type.name}' debe tener stock antes de enviar a revisión",
            )


def submit_event_for_review(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user) and event.promoter_id != acted_by_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes enviar a revisión un evento que no es tuyo",
        )

    ensure_event_ready_for_review(db, event)

    event.status = "in_review"
    for session in event.sessions:
        if session.status == "not_reviewed":
            session.status = "in_review"
    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento enviado a revisión correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.updated_at,
    }


def approve_event_review(
    db: Session,
    event_id: str,
    acted_by_user: User,
    platform_fee_type: str | None = None,
    platform_fee_value: Decimal | float | int | None = None,
) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede aprobar eventos",
        )

    has_sessions_in_review = any(session.status == "in_review" for session in event.sessions)

    if event.status != "in_review" and not has_sessions_in_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede aprobar un evento en revisión",
        )

    fee_type = platform_fee_type or event.platform_fee_type
    fee_value = platform_fee_value if platform_fee_value is not None else event.platform_fee_value

    if fee_type is None or fee_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes indicar la tarifa del evento antes de aprobarlo",
        )

    event.platform_fee_type = fee_type
    event.platform_fee_value = validate_event_fee(fee_type, fee_value)
    if event.status == "in_review":
        event.status = "draft"
    for session in event.sessions:
        if session.status == "in_review":
            session.status = "draft"
    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento aprobado y devuelto a draft",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.updated_at,
    }


def request_event_changes(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede pedir cambios",
        )

    has_sessions_in_review = any(session.status == "in_review" for session in event.sessions)

    if event.status != "in_review" and not has_sessions_in_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede devolver un evento que está en revisión",
        )

    if event.status == "in_review":
        event.status = "not_reviewed"
    for session in event.sessions:
        if session.status == "in_review":
            session.status = "not_reviewed"
    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento devuelto al promotor para revisión",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.updated_at,
    }


def cancel_event_review(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede cancelar eventos en revisión",
        )

    has_sessions_in_review = any(session.status == "in_review" for session in event.sessions)

    if event.status not in {"not_reviewed", "in_review", "draft"} and not has_sessions_in_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar un evento en ese estado desde revisión",
        )

    if event.status in {"not_reviewed", "in_review", "draft"}:
        event.status = "cancelled"
    for session in event.sessions:
        if session.status in {"not_reviewed", "in_review", "draft"}:
            session.status = "cancelled"
    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento cancelado correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.updated_at,
    }


def publish_event(db: Session, event_id: str, acted_by_user: User) -> dict:
    event = get_event_by_id_internal(db, event_id)

    if not _is_admin(acted_by_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede publicar eventos",
        )

    can_publish_event(db, event)

    now = _utc_now()
    event.status = "published"
    event.publish_at = now

    db.commit()
    db.refresh(event)
    send_event_status_email(event)

    return {
        "success": True,
        "message": "Evento publicado correctamente",
        "entity_id": str(event.id),
        "entity_type": "event",
        "status": event.status,
        "changed_at": event.updated_at,
    }
    
def get_event_ticket_capacity_summary(
    db: Session,
    event_id: str,
    current_user: User,
) -> dict:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if not _is_admin(current_user) and event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes acceder al aforo de un evento que no es tuyo",
        )

    total_session_capacity = (
        db.query(func.coalesce(func.sum(EventSession.capacity), 0))
        .filter(EventSession.event_id == event.id)
        .scalar()
    )
    total_defined_stock = (
        db.query(func.coalesce(func.sum(TicketType.stock), 0))
        .filter(
            TicketType.event_id == event.id,
            TicketType.status.notin_(["disabled", "archived"]),
        )
        .scalar()
    )

    total_session_capacity = int(total_session_capacity or 0)
    total_defined_stock = int(total_defined_stock or 0)
    available_for_new_ticket_types = max(0, total_session_capacity - total_defined_stock)

    return {
        "event_id": str(event.id),
        "capacity": total_session_capacity,
        "defined_ticket_stock": total_defined_stock,
        "available_for_new_ticket_types": available_for_new_ticket_types,
    }
