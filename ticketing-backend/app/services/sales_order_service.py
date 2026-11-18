from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.models.user import User
from app.schemas.sales_order import UpdateSalesOrderRequest, UpdateGroupTicketTypesOrderRequest


def _is_admin(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _get_event_manageable(db: Session, event_id: str, current_user: User) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if not _is_admin(current_user) and event.promoter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes gestionar este evento",
        )

    if event.status in {"archived", "disabled", "finished"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar la ordenación de este evento",
        )

    return event


def update_event_sales_order(
    db: Session,
    event_id: str,
    current_user: User,
    data: UpdateSalesOrderRequest,
) -> dict:
    event = _get_event_manageable(db, event_id, current_user)

    if not data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar al menos un elemento para ordenar",
        )

    seen = set()

    for index, item in enumerate(data.items, start=1):
        key = f"{item.type}:{item.id}"

        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes repetir elementos en la ordenación",
            )

        seen.add(key)

        if item.type == "ticket_type":
            ticket_type = (
                db.query(TicketType)
                .filter(
                    TicketType.id == item.id,
                    TicketType.event_id == event.id,
                )
                .first()
            )

            if not ticket_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ticket type no encontrado en este evento",
                )

            if ticket_type.sale_group_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se pueden ordenar aquí ticket types sueltos, no tickets dentro de grupos",
                )

            if ticket_type.status != "draft":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se puede reordenar ticket types en draft",
                )

            ticket_type.display_order = index

        elif item.type == "sale_group":
            group = (
                db.query(TicketSaleGroup)
                .filter(
                    TicketSaleGroup.id == item.id,
                    TicketSaleGroup.event_id == event.id,
                )
                .first()
            )

            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Grupo de venta no encontrado en este evento",
                )

            if group.status != "draft":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se puede reordenar grupos en draft",
                )

            group.display_order = index

    db.commit()

    return {
        "success": True,
        "message": "Ordenación del evento actualizada correctamente",
    }


def update_sale_group_ticket_types_order(
    db: Session,
    event_id: str,
    sale_group_id: str,
    current_user: User,
    data: UpdateGroupTicketTypesOrderRequest,
) -> dict:
    event = _get_event_manageable(db, event_id, current_user)

    group = (
        db.query(TicketSaleGroup)
        .filter(
            TicketSaleGroup.id == sale_group_id,
            TicketSaleGroup.event_id == event.id,
        )
        .first()
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grupo de venta no encontrado",
        )

    if group.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede reordenar un grupo en draft",
        )

    if len(data.ticket_type_ids) != len(set(data.ticket_type_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes repetir ticket types en la ordenación",
        )

    current_tickets = (
        db.query(TicketType)
        .filter(TicketType.sale_group_id == group.id)
        .all()
    )

    current_ids = {str(ticket.id) for ticket in current_tickets}
    sent_ids = set(data.ticket_type_ids)

    if current_ids != sent_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar exactamente todos los ticket types del grupo",
        )

    for ticket in current_tickets:
        if ticket.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede reordenar ticket types en draft",
            )

    for index, ticket_type_id in enumerate(data.ticket_type_ids, start=1):
        ticket = next(t for t in current_tickets if str(t.id) == ticket_type_id)
        ticket.sale_order = index

    db.commit()

    return {
        "success": True,
        "message": "Ordenación del grupo actualizada correctamente",
    }