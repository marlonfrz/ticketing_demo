from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket import Ticket
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_type import TicketType
from app.models.user import User
from app.schemas.ticket_type import TicketTypeCreate, TicketTypeUpdate
from app.services.ticket_inventory_service import sync_event_ticket_sales_state

STOCK_ONLY_EVENT_STATUSES = {"published", "sold_out", "unpublished"}
STOCK_ONLY_SESSION_STATUSES = {"published", "sold_out", "unpublished"}


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _utc_now():
    return datetime.now(timezone.utc)


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
            detail="No puedes gestionar ticket types de un evento que no es tuyo",
        )

    return event


def _ensure_structure_context_allows_ticket_changes(event: Event, session: EventSession | None = None):
    event_allows_changes = event.status in {"not_reviewed", "draft"}
    session_allows_changes = session is not None and session.status in {"not_reviewed", "draft", "cancelled"}

    if not event_allows_changes and not session_allows_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede modificar la estructura de venta antes de enviar a revision, cuando esta en draft o pendiente de cambios",
        )


def _ensure_session_allows_ticket_structure_changes(session: EventSession | None):
    if session and session.status not in {"not_reviewed", "draft", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede modificar la estructura de venta antes de enviar a revision, cuando la sesion esta en draft o pendiente de cambios",
        )


def _ensure_user_can_edit_ticket_type(current_user: User, ticket_type: TicketType) -> None:
    if ticket_type.status == "draft" or _is_admin(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo un administrador puede editar tipos de entrada publicados",
    )


def _is_stock_only_update(update_data: dict) -> bool:
    return set(update_data.keys()) == {"stock"}


def _can_update_only_stock(event: Event, ticket_type: TicketType, current_user: User, update_data: dict) -> bool:
    if not _is_stock_only_update(update_data):
        return False

    session_status = ticket_type.session.status if ticket_type.session else None
    return (
        event.status in STOCK_ONLY_EVENT_STATUSES
        and session_status in STOCK_ONLY_SESSION_STATUSES
        and ticket_type.status in {"draft", "published", "sold_out"}
    )


def _get_default_session(db: Session, event: Event) -> EventSession | None:
    return (
        db.query(EventSession)
        .filter(EventSession.event_id == event.id)
        .order_by(
            EventSession.display_order.asc().nullslast(),
            EventSession.starts_at.asc(),
            EventSession.created_at.asc(),
        )
        .first()
    )


def _get_session_for_ticket_type(db: Session, event: Event, session_id: str | None) -> EventSession | None:
    if not session_id:
        return _get_default_session(db, event)

    session = (
        db.query(EventSession)
        .filter(EventSession.id == session_id, EventSession.event_id == event.id)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesion no encontrada para este evento",
        )

    return session


def _get_total_stock_for_event(
    db: Session,
    event_id: str,
    exclude_ticket_type_id: str | None = None,
    session_id: str | None = None,
) -> int:
    query = db.query(func.coalesce(func.sum(TicketType.stock), 0)).filter(
        TicketType.event_id == event_id,
        TicketType.status != "disabled",
        TicketType.status != "archived",
    )

    if session_id:
        query = query.filter(TicketType.session_id == session_id)

    if exclude_ticket_type_id:
        query = query.filter(TicketType.id != exclude_ticket_type_id)

    total = query.scalar()
    return int(total or 0)


def create_ticket_type(db: Session, event_id: str, current_user: User, data: TicketTypeCreate) -> TicketType:
    event = get_event_manageable_by_user(db, event_id, current_user)
    session = _get_session_for_ticket_type(db, event, data.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes crear una sesion antes de definir entradas",
        )
    _ensure_structure_context_allows_ticket_changes(event, session)
    _ensure_session_allows_ticket_structure_changes(session)
    session_id = str(session.id)
    capacity = session.capacity

    current_total_stock = _get_total_stock_for_event(
        db,
        str(event.id),
        session_id=session_id,
    )
    new_total_stock = current_total_stock + data.stock

    if new_total_stock > capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El stock total de la sesion superaria su aforo. "
                f"Aforo: {capacity}, stock actual: {current_total_stock}, "
                f"stock solicitado: {data.stock}"
            ),
        )

    ticket_type = TicketType(
        event_id=event.id,
        session_id=session.id,
        name=data.name,
        description=data.description,
        price=data.price,
        currency=data.currency.upper(),
        stock=data.stock,
        sold_count=0,
        max_per_purchase=data.max_per_purchase,
        display_order=data.display_order,
        sale_starts_at=None,
        sale_ends_at=None,
        is_active=data.is_active,
        status="draft",
    )

    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)
    return ticket_type


def list_ticket_types_by_event(
    db: Session,
    event_id: str,
    current_user: User,
    session_id: str | None = None,
):
    get_event_manageable_by_user(db, event_id, current_user)

    sync_event_ticket_sales_state(db, event_id)

    query = db.query(TicketType).filter(TicketType.event_id == event_id)
    if session_id:
        query = query.filter(TicketType.session_id == session_id)

    return query.order_by(
        TicketType.display_order.asc().nullslast(),
        TicketType.created_at.asc(),
    ).all()


def get_ticket_type_by_id(db: Session, ticket_type_id: str) -> TicketType:
    ticket_type = db.query(TicketType).filter(TicketType.id == ticket_type_id).first()

    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de entrada no encontrado",
        )

    return ticket_type


def update_ticket_type(db: Session, ticket_type_id: str, current_user: User, data: TicketTypeUpdate) -> TicketType:
    ticket_type = get_ticket_type_by_id(db, ticket_type_id)
    event = get_event_manageable_by_user(db, str(ticket_type.event_id), current_user)
    update_data = data.model_dump(exclude_unset=True)
    stock_only_update = _can_update_only_stock(event, ticket_type, current_user, update_data)

    if not stock_only_update:
        _ensure_structure_context_allows_ticket_changes(event, ticket_type.session)
        _ensure_session_allows_ticket_structure_changes(ticket_type.session)

    if not stock_only_update:
        _ensure_user_can_edit_ticket_type(current_user, ticket_type)

    if ticket_type.status != "draft" and not _is_admin(current_user) and not stock_only_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede editar físicamente un tipo de entrada en draft",
        )

    if ticket_type.status != "draft" and "currency" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cambiar la moneda de un tipo de entrada publicado",
        )

    sale_starts_at = update_data.get("sale_starts_at", ticket_type.sale_starts_at)
    sale_ends_at = update_data.get("sale_ends_at", ticket_type.sale_ends_at)

    if sale_starts_at and sale_ends_at and sale_ends_at < sale_starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin de venta no puede ser anterior al inicio",
        )

    if "currency" in update_data and update_data["currency"]:
        update_data["currency"] = update_data["currency"].upper()

    if "stock" in update_data:
        new_stock = update_data["stock"]

        if new_stock < ticket_type.sold_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"No puedes poner un stock menor que las entradas ya vendidas "
                    f"({ticket_type.sold_count})"
                ),
            )

        current_total_stock_without_this = _get_total_stock_for_event(
            db,
            str(event.id),
            exclude_ticket_type_id=str(ticket_type.id),
            session_id=str(ticket_type.session_id) if ticket_type.session_id else None,
        )
        new_total_stock = current_total_stock_without_this + new_stock
        if not ticket_type.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo de entrada debe pertenecer a una sesion",
            )
        capacity = ticket_type.session.capacity

        if new_total_stock > capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El stock total de la sesion superaria su aforo. "
                    f"Aforo: {capacity}, stock restante sin este tipo: {current_total_stock_without_this}, "
                    f"nuevo stock solicitado: {new_stock}"
                ),
            )

    if ticket_type.status != "draft" and "price" in update_data:
        has_generated_tickets = (
            db.query(Ticket)
            .filter(Ticket.ticket_type_id == ticket_type.id)
            .first()
            is not None
        )
        if has_generated_tickets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede cambiar el precio de un tipo publicado que ya tiene entradas generadas",
            )

    for field, value in update_data.items():
        setattr(ticket_type, field, value)

    db.commit()
    if "stock" in update_data:
        sync_event_ticket_sales_state(db, str(event.id))

    db.refresh(ticket_type)
    return ticket_type


def delete_ticket_type(db: Session, ticket_type_id: str, current_user: User) -> dict:
    ticket_type = get_ticket_type_by_id(db, ticket_type_id)
    event = get_event_manageable_by_user(db, str(ticket_type.event_id), current_user)
    _ensure_structure_context_allows_ticket_changes(event, ticket_type.session)
    _ensure_session_allows_ticket_structure_changes(ticket_type.session)

    if ticket_type.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede borrar físicamente un tipo de entrada en draft",
        )

    if ticket_type.sold_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un tipo de entrada con ventas",
        )

    has_tickets = db.query(Ticket).filter(Ticket.ticket_type_id == ticket_type.id).first() is not None
    if has_tickets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un tipo de entrada que ya tiene tickets generados",
        )

    has_active_reservations = (
        db.query(TicketReservation)
        .filter(
            TicketReservation.ticket_type_id == ticket_type.id,
            TicketReservation.status == "active",
        )
        .first()
        is not None
    )
    if has_active_reservations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede borrar un tipo de entrada con reservas activas",
        )

    ticket_type_id_str = str(ticket_type.id)
    db.delete(ticket_type)
    db.commit()

    return {
        "success": True,
        "message": "Tipo de entrada borrado físicamente correctamente",
        "entity_id": ticket_type_id_str,
        "entity_type": "ticket_type",
    }


def can_disable_ticket_type(db: Session, ticket_type: TicketType) -> None:
    event = db.query(Event).filter(Event.id == ticket_type.event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento del tipo de entrada no encontrado",
        )

    session_allows_changes = (
        ticket_type.session is not None
        and ticket_type.session.status in {"not_reviewed", "draft", "cancelled"}
    )
    if event.status not in {"not_reviewed", "draft"} and not session_allows_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden borrar o desactivar entradas antes de enviar a revision o cuando el evento esta en draft",
        )

    if ticket_type.sold_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede desactivar un tipo de entrada que ya tiene ventas",
        )

    if ticket_type.session and _utc_now() >= ticket_type.session.starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede desactivar un tipo de entrada de un evento que ya ha empezado",
        )


def disable_ticket_type(db: Session, ticket_type_id: str, acted_by_user: User) -> dict:
    ticket_type = db.query(TicketType).filter(TicketType.id == ticket_type_id).first()

    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de entrada no encontrado",
        )

    if ticket_type.status in {"archived", "disabled"}:
        return {
            "success": True,
            "message": "El tipo de entrada ya estaba desactivado o archivado",
            "entity_id": str(ticket_type.id),
            "entity_type": "ticket_type",
            "status": ticket_type.status,
            "changed_at": ticket_type.deactivated_at,
        }

    can_disable_ticket_type(db, ticket_type)

    now = _utc_now()
    ticket_type.status = "disabled"
    ticket_type.is_active = False
    ticket_type.deactivated_at = now

    db.commit()
    db.refresh(ticket_type)

    return {
        "success": True,
        "message": "Tipo de entrada desactivado correctamente",
        "entity_id": str(ticket_type.id),
        "entity_type": "ticket_type",
        "status": ticket_type.status,
        "changed_at": ticket_type.deactivated_at,
    }
    
def publish_ticket_type(db: Session, ticket_type_id: str, current_user: User) -> TicketType:
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede publicar entradas",
        )

    ticket_type = get_ticket_type_by_id(db, ticket_type_id)
    event = get_event_manageable_by_user(db, str(ticket_type.event_id), current_user)

    if event.status != "published":
        raise HTTPException(
            status_code=400,
            detail="El evento debe estar aprobado y publicado antes de publicar entradas",
        )

    if ticket_type.status != "draft" and not _is_admin(current_user):
        raise HTTPException(
            status_code=400,
            detail="Solo se puede publicar un ticket en draft",
        )

    if ticket_type.stock <= 0:
        raise HTTPException(
            status_code=400,
            detail="El ticket debe tener stock para publicarse",
        )

    ticket_type.status = "published"
    ticket_type.sale_unlocked_at = _utc_now()

    db.commit()
    db.refresh(ticket_type)
    return ticket_type
