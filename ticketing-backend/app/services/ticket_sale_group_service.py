from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket import Ticket
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.models.user import User
from app.schemas.ticket_sale_group import (
    ALLOWED_GROUP_STRATEGIES,
    TicketSaleGroupCreate,
    TicketSaleGroupUpdate,
)


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _utc_now():
    return datetime.now(timezone.utc)


def _ensure_can_edit_existing_group(current_user: User, group: TicketSaleGroup) -> None:
    if group.status == "draft" or _is_admin(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo un administrador puede editar grupos de venta publicados",
    )


def _ensure_can_move_ticket_type(current_user: User, ticket_type: TicketType) -> None:
    if ticket_type.status == "draft" or _is_admin(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Solo un administrador puede mover entradas publicadas entre grupos",
    )


def _ensure_session_allows_sale_group_changes(session: EventSession | None) -> None:
    if session and session.status not in {"not_reviewed", "draft", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede modificar la estructura de venta antes de enviar a revision, cuando la sesion esta en draft o pendiente de cambios",
        )


def _ensure_structure_context_allows_sale_group_changes(
    event: Event,
    session: EventSession | None = None,
) -> None:
    event_allows_changes = event.status in {"not_reviewed", "draft"}
    session_allows_changes = session is not None and session.status in {"not_reviewed", "draft", "cancelled"}

    if not event_allows_changes and not session_allows_changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede modificar la estructura de venta antes de enviar a revision, cuando esta en draft o pendiente de cambios",
        )


def get_event_manageable_for_sale_group(db: Session, event_id: str, current_user: User) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if not _is_admin(current_user) and event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes gestionar grupos de venta de un evento que no es tuyo",
        )

    return event


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


def _get_session_for_group(db: Session, event: Event, session_id: str | None) -> EventSession | None:
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


def _get_total_stock_for_event(db: Session, event_id: str, session_id: str | None = None) -> int:
    query = (
        db.query(func.coalesce(func.sum(TicketType.stock), 0))
        .filter(
            TicketType.event_id == event_id,
            TicketType.status != "disabled",
            TicketType.status != "archived",
        )
    )
    if session_id:
        query = query.filter(TicketType.session_id == session_id)

    total = query.scalar()
    return int(total or 0)


def create_ticket_sale_group(
    db: Session,
    event_id: str,
    current_user: User,
    data: TicketSaleGroupCreate,
) -> TicketSaleGroup:
    event = get_event_manageable_for_sale_group(db, event_id, current_user)
    session = _get_session_for_group(db, event, data.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes crear una sesion antes de definir grupos de venta",
        )
    _ensure_structure_context_allows_sale_group_changes(event, session)
    _ensure_session_allows_sale_group_changes(session)
    session_id = str(session.id)
    capacity = session.capacity

    if data.strategy not in ALLOWED_GROUP_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estrategia de grupo de venta inválida",
        )

    sale_orders = [item.sale_order for item in data.ticket_types]
    if len(sale_orders) != len(set(sale_orders)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede repetir sale_order dentro del mismo grupo",
        )

    requested_stock = sum(item.stock for item in data.ticket_types)
    current_total_stock = _get_total_stock_for_event(db, str(event.id), session_id=session_id)
    if current_total_stock + requested_stock > capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El stock total de la sesion superaria su aforo. "
                f"Aforo: {capacity}, stock actual: {current_total_stock}, "
                f"stock solicitado en el grupo: {requested_stock}"
            ),
        )

    group = TicketSaleGroup(
        event_id=event.id,
        session_id=session.id,
        name=data.name,
        strategy="stock_cascade",
        display_order=data.display_order,
        is_active=data.is_active,
        sale_starts_at=None,
        sale_ends_at=None,
    )

    db.add(group)
    db.flush()

    for item in data.ticket_types:

        ticket_type = TicketType(
            event_id=event.id,
            session_id=session.id if session else None,
            sale_group_id=group.id,
            sale_order=item.sale_order,
            name=item.name,
            description=item.description,
            price=item.price,
            currency=item.currency.upper(),
            stock=item.stock,
            sold_count=0,
            max_per_purchase=item.max_per_purchase,
            sale_starts_at=None,
            sale_ends_at=None,
            is_active=item.is_active,
            status="draft",
        )
        db.add(ticket_type)

    db.commit()
    db.refresh(group)
    return group


def list_ticket_sale_groups_by_event(
    db: Session,
    event_id: str,
    current_user: User,
    session_id: str | None = None,
):
    get_event_manageable_for_sale_group(db, event_id, current_user)

    query = db.query(TicketSaleGroup).filter(TicketSaleGroup.event_id == event_id)
    if session_id:
        query = query.filter(TicketSaleGroup.session_id == session_id)

    return query.order_by(
        TicketSaleGroup.display_order.asc().nullslast(),
        TicketSaleGroup.created_at.asc(),
    ).all()


def get_sale_group_by_id(db: Session, sale_group_id: str) -> TicketSaleGroup:
    group = db.query(TicketSaleGroup).filter(TicketSaleGroup.id == sale_group_id).first()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de venta no encontrado",
        )

    return group


def update_ticket_sale_group(
    db: Session,
    sale_group_id: str,
    current_user: User,
    data: TicketSaleGroupUpdate,
) -> TicketSaleGroup:
    group = get_sale_group_by_id(db, sale_group_id)
    event = get_event_manageable_for_sale_group(db, str(group.event_id), current_user)
    _ensure_structure_context_allows_sale_group_changes(event, group.session)
    _ensure_session_allows_sale_group_changes(group.session)
    _ensure_can_edit_existing_group(current_user, group)

    tickets = db.query(TicketType).filter(TicketType.sale_group_id == group.id).all()
    if any(t.status != "draft" for t in tickets) and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede editar un grupo si todos sus tickets están en draft",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "strategy" in update_data and update_data["strategy"] not in ALLOWED_GROUP_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estrategia de grupo de venta inválida",
        )

    for field, value in update_data.items():
        setattr(group, field, value)

    db.commit()
    db.refresh(group)
    return group


def delete_ticket_sale_group(db: Session, sale_group_id: str, current_user: User) -> dict:
    group = get_sale_group_by_id(db, sale_group_id)
    event = get_event_manageable_for_sale_group(db, str(group.event_id), current_user)
    _ensure_structure_context_allows_sale_group_changes(event, group.session)
    _ensure_session_allows_sale_group_changes(group.session)

    tickets = db.query(TicketType).filter(TicketType.sale_group_id == group.id).all()

    for ticket in tickets:
        if ticket.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede borrar un grupo que contiene tickets fuera de draft",
            )

        if ticket.sold_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede borrar un grupo que contiene tickets con ventas",
            )

        has_tickets = db.query(Ticket).filter(Ticket.ticket_type_id == ticket.id).first() is not None
        if has_tickets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede borrar un grupo que contiene tickets ya generados",
            )

        has_active_reservations = (
            db.query(TicketReservation)
            .filter(
                TicketReservation.ticket_type_id == ticket.id,
                TicketReservation.status == "active",
            )
            .first()
            is not None
        )
        if has_active_reservations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede borrar un grupo que contiene reservas activas",
            )

    for ticket in tickets:
        db.delete(ticket)

    group_id_str = str(group.id)
    db.delete(group)
    db.commit()

    return {
        "success": True,
        "message": "Grupo de venta borrado físicamente correctamente",
        "entity_id": group_id_str,
        "entity_type": "ticket_sale_group",
    }


def assign_ticket_type_to_sale_group(
    db: Session,
    ticket_type_id: str,
    current_user: User,
    sale_group_id: str,
    sale_order: int,
) -> TicketType:
    ticket_type = db.query(TicketType).filter(TicketType.id == ticket_type_id).first()

    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de entrada no encontrado",
        )

    group = get_sale_group_by_id(db, sale_group_id)
    event = get_event_manageable_for_sale_group(db, str(group.event_id), current_user)
    _ensure_structure_context_allows_sale_group_changes(event, group.session)
    _ensure_session_allows_sale_group_changes(group.session)

    if ticket_type.event_id != group.event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de entrada y el grupo de venta deben pertenecer al mismo evento",
        )

    if ticket_type.session_id != group.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de entrada y el grupo deben pertenecer a la misma sesion",
        )

    if ticket_type.status != "draft" and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede asignar a grupo un ticket type en draft",
        )

    existing_same_order = (
        db.query(TicketType)
        .filter(
            TicketType.sale_group_id == group.id,
            TicketType.sale_order == sale_order,
            TicketType.id != ticket_type.id,
        )
        .first()
    )

    if existing_same_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe otro tipo de entrada con ese orden dentro del grupo",
        )

    ticket_type.sale_group_id = group.id
    ticket_type.sale_order = sale_order

    db.commit()
    db.refresh(ticket_type)
    return ticket_type


def remove_ticket_type_from_sale_group(
    db: Session,
    ticket_type_id: str,
    current_user: User,
) -> dict:
    ticket_type = db.query(TicketType).filter(TicketType.id == ticket_type_id).first()

    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de entrada no encontrado",
        )

    event = get_event_manageable_for_sale_group(db, str(ticket_type.event_id), current_user)
    _ensure_structure_context_allows_sale_group_changes(event, ticket_type.session)
    _ensure_session_allows_sale_group_changes(ticket_type.session)
    _ensure_can_move_ticket_type(current_user, ticket_type)

    if ticket_type.status != "draft" and not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede quitar de un grupo un ticket type en draft",
        )

    old_group_id = str(ticket_type.sale_group_id) if ticket_type.sale_group_id else None

    ticket_type.sale_group_id = None
    ticket_type.sale_order = None

    db.commit()
    db.refresh(ticket_type)

    return {
        "success": True,
        "message": "Tipo de entrada eliminado del grupo de venta correctamente",
        "ticket_type_id": str(ticket_type.id),
        "sale_group_id": old_group_id,
        "sale_order": None,
    }
    
def publish_ticket_sale_group(
    db: Session,
    sale_group_id: str,
    current_user: User,
) -> TicketSaleGroup:
    group = get_sale_group_by_id(db, sale_group_id)
    event = get_event_manageable_for_sale_group(db, str(group.event_id), current_user)
    _ensure_session_allows_sale_group_changes(group.session)

    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede publicar grupos de venta",
        )

    if event.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El evento debe estar aprobado y publicado antes de publicar grupos de venta",
        )

    if group.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede publicar un grupo en draft",
        )

    ticket_types = (
        db.query(TicketType)
        .filter(TicketType.sale_group_id == group.id)
        .order_by(TicketType.sale_order.asc(), TicketType.created_at.asc())
        .all()
    )

    if not ticket_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede publicar un grupo sin ticket types",
        )

    for ticket_type in ticket_types:
        if ticket_type.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todos los ticket types del grupo deben estar en draft para publicarlo",
            )

        if ticket_type.stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El ticket '{ticket_type.name}' debe tener stock para publicarse",
            )

    now = _utc_now()

    group.status = "published"

    for index, ticket_type in enumerate(ticket_types):
        ticket_type.status = "published"

        if index == 0:
            ticket_type.sale_unlocked_at = now
        else:
            ticket_type.sale_unlocked_at = None


    db.commit()
    db.refresh(group)
    return group
