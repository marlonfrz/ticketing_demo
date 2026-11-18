import secrets
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from html import escape
from io import BytesIO

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
import reportlab
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

from app.models.event import Event
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.ticket import Ticket
from app.models.ticket_validation import TicketValidation
from app.models.ticket_type import TicketType
from app.models.user import User
from app.models.ticket_delivery import TicketDelivery
from app.models.validation_station import ValidationStation
from app.schemas.ticket import ComplimentaryTicketCreateRequest
from app.services.email_service import send_email_with_attachment
from app.services.guest_checkout_access_service import has_valid_guest_checkout_access
from app.services.ticket_inventory_service import (
    get_active_reserved_quantity,
    sync_ticket_type_sales_state,
)
from app.utils.date_time import format_display_datetime, to_display_datetime
from app.utils.qr import generate_qr_png_bytes


def _generate_ticket_code() -> str:
    return f"TKT-{secrets.token_hex(8).upper()}"


def _generate_qr_token() -> str:
    return f"qr_{secrets.token_urlsafe(24)}"


def _has_role(user: User, role_name: str) -> bool:
    return any(role.name == role_name for role in user.roles)


def _is_admin(user: User) -> bool:
    return _has_role(user, "admin")


def _get_ticket_session(ticket: Ticket):
    return ticket.session or ticket.event._first_session


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_datetime(value: datetime | None) -> str:
    if not value:
        return "fecha no definida"
    return format_display_datetime(value)


def _format_session_label(session) -> str:
    if not session:
        return "sesion no definida"
    location = session.location_name or session.title or "sesion"
    return f"{location} - {_format_datetime(session.starts_at)}"


def _ticket_status_label(ticket: Ticket) -> str:
    if not ticket.is_valid:
        return "invalida"
    labels = {
        "active": "activa",
        "used": "usada",
        "cancelled": "cancelada",
    }
    return labels.get(ticket.status, ticket.status)


def _validation_failure(
    db: Session,
    ticket: Ticket,
    result: str,
    message: str,
    validation_owner_kwargs: dict,
    device_id: str | None = None,
    notes: str | None = None,
) -> dict:
    validation = TicketValidation(
        ticket_id=ticket.id,
        result=result,
        message=message,
        validation_type="event_entry",
        device_id=device_id,
        **validation_owner_kwargs,
        notes=notes,
    )
    db.add(validation)
    db.commit()

    return {
        "valid": False,
        "message": message,
        "ticket": serialize_ticket(ticket),
    }


def _ensure_can_manage_event_tickets(db: Session, event_id: str, user: User) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if not _is_admin(user) and event.promoter_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes generar entradas para un evento que no es tuyo",
        )

    return event


def serialize_ticket(ticket: Ticket) -> dict:
    session = _get_ticket_session(ticket)
    return {
        "id": str(ticket.id),
        "order_id": str(ticket.order_id),
        "event_id": str(ticket.event_id),
        "ticket_type_id": str(ticket.ticket_type_id),
        "owner_user_id": str(ticket.owner_user_id) if ticket.owner_user_id else None,
        "generated_by_user_id": str(ticket.generated_by_user_id) if ticket.generated_by_user_id else None,
        "ticket_code": ticket.ticket_code,
        "source": ticket.source,
        "recipient_name": ticket.recipient_name,
        "generation_note": ticket.generation_note,
        "qr_image_url": f"/tickets/{ticket.id}/qr-image",
        "status": ticket.status,
        "is_valid": ticket.is_valid,
        "issued_at": ticket.issued_at,
        "used_at": ticket.used_at,
        "created_at": ticket.created_at,
        "event": {
            "id": str(ticket.event.id),
            "title": ticket.event.title,
            "starts_at": session.starts_at if session else None,
            "location_name": session.location_name if session else "",
        },
        "session": {
            "id": str(session.id),
            "title": session.title,
            "starts_at": session.starts_at,
            "ends_at": session.ends_at,
            "location_name": session.location_name,
            "location_address": session.location_address,
        } if session else None,
        "ticket_type": {
            "id": str(ticket.ticket_type.id),
            "name": ticket.ticket_type.name,
        },
        "generated_by": {
            "id": str(ticket.generated_by.id),
            "full_name": ticket.generated_by.full_name,
            "email": ticket.generated_by.email,
        }
        if ticket.generated_by
        else None,
    }


def get_event_complimentary_tickets_summary(
    db: Session,
    event_id: str,
    user: User,
    session_id: str | None = None,
) -> dict:
    event = _ensure_can_manage_event_tickets(db, event_id, user)

    query = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
            joinedload(Ticket.generated_by),
        )
        .filter(
            Ticket.event_id == event.id,
            Ticket.source == "complimentary",
            Ticket.status == "active",
        )
    )
    if session_id:
        query = query.filter(Ticket.session_id == session_id)

    tickets = query.order_by(Ticket.created_at.desc()).all()

    by_ticket_type = defaultdict(lambda: {"ticket_type_id": "", "ticket_type_name": "", "quantity": 0})
    for ticket in tickets:
        key = str(ticket.ticket_type_id)
        by_ticket_type[key]["ticket_type_id"] = key
        by_ticket_type[key]["ticket_type_name"] = ticket.ticket_type.name
        by_ticket_type[key]["quantity"] += 1

    return {
        "event_id": str(event.id),
        "session_id": session_id,
        "total": len(tickets),
        "by_ticket_type": list(by_ticket_type.values()),
        "tickets": [serialize_ticket(ticket) for ticket in tickets],
    }


def get_complimentary_order_tickets_pdf_for_manager(
    db: Session,
    event_id: str,
    order_id: str,
    user: User,
    session_id: str | None = None,
) -> tuple[bytes, str]:
    event = _ensure_can_manage_event_tickets(db, event_id, user)
    order = (
        db.query(Order)
        .filter(
            Order.id == order_id,
            Order.event_id == event.id,
            Order.status == "paid",
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lote de invitaciones no encontrado",
        )

    ticket_query = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
            joinedload(Ticket.owner),
            joinedload(Ticket.order).joinedload(Order.customer),
        )
        .filter(
            Ticket.order_id == order.id,
            Ticket.event_id == event.id,
            Ticket.source == "complimentary",
            Ticket.status == "active",
        )
    )
    if session_id:
        ticket_query = ticket_query.filter(Ticket.session_id == session_id)

    tickets = ticket_query.order_by(Ticket.created_at.asc()).all()

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay invitaciones disponibles para descargar",
        )

    pdf_bytes = _generate_order_tickets_pdf(tickets)
    filename = f"invitaciones-{str(order.id).split('-')[0]}.pdf"
    return pdf_bytes, filename


def generate_complimentary_tickets(
    db: Session,
    event_id: str,
    current_user: User,
    data: ComplimentaryTicketCreateRequest,
) -> dict:
    event = _ensure_can_manage_event_tickets(db, event_id, current_user)

    if event.status not in {"published", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes generar invitaciones cuando el evento ya esta publicado",
        )

    ticket_type = (
        db.query(TicketType)
        .filter(
            TicketType.id == data.ticket_type_id,
            TicketType.event_id == event.id,
        )
        .with_for_update(of=TicketType)
        .first()
    )

    if not ticket_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de entrada no encontrado para este evento",
        )

    if not data.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selecciona una sesion antes de generar invitaciones",
        )

    if str(ticket_type.session_id) != data.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El tipo de entrada no pertenece a la sesion seleccionada",
        )

    if (
        ticket_type.session
        and (
            ticket_type.session.status not in {"published", "sold_out"}
            or not ticket_type.session.tickets_activated_at
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes generar invitaciones desde sesiones publicadas con entradas activadas",
        )

    if ticket_type.session and ticket_type.session.ends_at:
        now = datetime.now(timezone.utc)
        session_end = _as_aware_utc(ticket_type.session.ends_at)
        if session_end and now > session_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes generar invitaciones de una sesion finalizada",
            )

    if ticket_type.status not in {"published", "sold_out"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes generar invitaciones desde entradas publicadas",
        )

    sync_ticket_type_sales_state(db, ticket_type)
    now = datetime.now(timezone.utc)
    reserved_quantity = get_active_reserved_quantity(db, str(ticket_type.id), now)
    available_stock = ticket_type.stock - ticket_type.sold_count - reserved_quantity

    if data.quantity > available_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No hay stock suficiente. Disponibles ahora: {max(0, available_stock)} "
                f"(descontando reservas activas)."
            ),
        )

    order = Order(
        buyer_id=None,
        event_id=event.id,
        session_id=ticket_type.session_id,
        status="paid",
        total_amount=Decimal("0.00"),
        currency=ticket_type.currency,
    )
    db.add(order)
    db.flush()

    tickets: list[Ticket] = []
    for _ in range(data.quantity):
        ticket = Ticket(
            order_id=order.id,
            event_id=event.id,
            session_id=ticket_type.session_id,
            ticket_type_id=ticket_type.id,
            owner_user_id=None,
            generated_by_user_id=current_user.id,
            ticket_code=_generate_ticket_code(),
            qr_token=_generate_qr_token(),
            source="complimentary",
            recipient_name=data.recipient_name,
            generation_note=data.note,
            status="active",
            is_valid=True,
        )
        db.add(ticket)
        tickets.append(ticket)

    db.flush()
    ticket_ids = [ticket.id for ticket in tickets]
    sync_ticket_type_sales_state(db, ticket_type)
    db.commit()

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
            joinedload(Ticket.generated_by),
        )
        .filter(Ticket.id.in_(ticket_ids))
        .order_by(Ticket.created_at.asc())
        .all()
    )

    return {
        "success": True,
        "event_id": str(event.id),
        "session_id": str(ticket_type.session_id) if ticket_type.session_id else None,
        "ticket_type_id": str(ticket_type.id),
        "quantity": len(tickets),
        "tickets": [serialize_ticket(ticket) for ticket in tickets],
    }


def serialize_validation(validation: TicketValidation) -> dict:
    return {
        "id": str(validation.id),
        "ticket_id": str(validation.ticket_id) if validation.ticket_id else None,
        "result": validation.result,
        "message": validation.message,
        "validation_type": validation.validation_type,
        "device_id": validation.device_id,
        "validated_by_user_id": str(validation.validated_by_user_id) if validation.validated_by_user_id else None,
        "validation_station_id": str(validation.validation_station_id) if validation.validation_station_id else None,
        "notes": validation.notes,
        "validated_at": validation.validated_at,
    }


def get_my_tickets(db: Session, user: User) -> list[dict]:
    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.owner_user_id == user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return [serialize_ticket(ticket) for ticket in tickets]


def get_ticket_by_id(db: Session, ticket_id: str, user: User) -> dict:
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado",
        )

    if ticket.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver un ticket que no es tuyo",
        )

    return serialize_ticket(ticket)


def get_tickets_by_order_id(db: Session, order_id: str, user: User) -> list[dict]:
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    if order.buyer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver tickets de un pedido que no es tuyo",
        )

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.order_id == order.id)
        .order_by(Ticket.created_at.asc())
        .all()
    )

    return [serialize_ticket(ticket) for ticket in tickets]

def get_ticket_model_by_id_for_owner(db: Session, ticket_id: str, user: User) -> Ticket:
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado",
        )

    if ticket.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver un ticket que no es tuyo",
        )

    return ticket


def get_ticket_model_for_promoter_event_access(db: Session, ticket_id: str, promoter: User) -> Ticket:
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado",
        )

    if ticket.event.promoter_id != promoter.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes acceder al QR de un ticket de un evento que no es tuyo",
        )

    return ticket

def validate_ticket_by_qr(
    db: Session,
    qr_token: str,
    validator_user: User | None = None,
    validation_station: ValidationStation | None = None,
    device_id: str | None = None,
    notes: str | None = None,
) -> dict:
    if not validator_user and not validation_station:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificacion de validador requerida",
        )

    validation_owner_kwargs = {
        "validated_by_user_id": validator_user.id if validator_user else None,
        "validation_station_id": validation_station.id if validation_station else None,
    }

    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.session),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.qr_token == qr_token)
        .with_for_update(of=Ticket)
        .first()
    )

    if not ticket:
        validation = TicketValidation(
            ticket_id=None,
            result="invalid",
            message="Ticket no encontrado",
            validation_type="event_entry",
            device_id=device_id,
            **validation_owner_kwargs,
            notes=notes,
        )
        db.add(validation)
        db.commit()

        return {
            "valid": False,
            "message": "Ticket no encontrado",
            "ticket": None,
        }

    if validation_station:
        if ticket.session_id != validation_station.session_id:
            return _validation_failure(
                db,
                ticket,
                "wrong_session",
                (
                    "Esta entrada no es de esta sesion. "
                    f"Pertenece a {_format_session_label(ticket.session)}. "
                    f"Estado de la entrada: {_ticket_status_label(ticket)}."
                ),
                validation_owner_kwargs,
                device_id,
                notes,
            )
    elif not _has_role(validator_user, "admin"):
        is_promoter_owner = (
            _has_role(validator_user, "promoter")
            and ticket.event.promoter_id == validator_user.id
        )
        if not is_promoter_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para validar tickets",
            )

    if not ticket.is_valid or ticket.status == "cancelled":
        return _validation_failure(
            db,
            ticket,
            "cancelled",
            f"Entrada cancelada o invalida. Estado de la entrada: {_ticket_status_label(ticket)}.",
            validation_owner_kwargs,
            device_id,
            notes,
        )

    if ticket.status == "used":
        used_at_text = f" el {_format_datetime(ticket.used_at)}" if ticket.used_at else ""
        return _validation_failure(
            db,
            ticket,
            "already_used",
            f"Esta entrada ya fue validada{used_at_text}. Estado de la entrada: {_ticket_status_label(ticket)}.",
            validation_owner_kwargs,
            device_id,
            notes,
        )

    if ticket.status != "active":
        return _validation_failure(
            db,
            ticket,
            "invalid_status",
            f"Esta entrada no se puede validar con estado {_ticket_status_label(ticket)}.",
            validation_owner_kwargs,
            device_id,
            notes,
        )

    session = ticket.session
    now = datetime.now(timezone.utc)
    if session:
        session_start = _as_aware_utc(session.starts_at)
        session_end = _as_aware_utc(session.ends_at)

        if session.status not in {"published", "sold_out"}:
            return _validation_failure(
                db,
                ticket,
                "invalid_session",
                (
                    "La sesion de esta entrada no esta abierta para canje. "
                    f"Sesion: {_format_session_label(session)}. Estado de sesion: {session.status}."
                ),
                validation_owner_kwargs,
                device_id,
                notes,
            )

        if session_start and now < session_start:
            return _validation_failure(
                db,
                ticket,
                "too_early",
                (
                    "Esta entrada aun no se puede canjear. "
                    f"Pertenece a {_format_session_label(session)}."
                ),
                validation_owner_kwargs,
                device_id,
                notes,
            )

        if session_end and now > session_end:
            return _validation_failure(
                db,
                ticket,
                "session_finished",
                (
                    "La sesion de esta entrada ya ha finalizado. "
                    f"Sesion: {_format_session_label(session)}."
                ),
                validation_owner_kwargs,
                device_id,
                notes,
            )

    ticket.status = "used"
    ticket.used_at = datetime.now(timezone.utc)

    validation = TicketValidation(
        ticket_id=ticket.id,
        result="success",
        message="Ticket validado correctamente",
        validation_type="event_entry",
        device_id=device_id,
        **validation_owner_kwargs,
        notes=notes,
    )
    db.add(validation)

    db.commit()
    db.refresh(ticket)

    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.session),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.id == ticket.id)
        .first()
    )

    return {
        "valid": True,
        "message": "Ticket validado correctamente",
        "ticket": serialize_ticket(ticket),
    }

def get_ticket_validations(db: Session, ticket_id: str, user: User) -> list[dict]:
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado",
        )

    if ticket.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver validaciones de un ticket que no es tuyo",
        )

    validations = (
        db.query(TicketValidation)
        .filter(TicketValidation.ticket_id == ticket.id)
        .order_by(TicketValidation.validated_at.desc())
        .all()
    )

    return [serialize_validation(validation) for validation in validations]


def get_event_tickets_for_promoter(db: Session, event_id: str, promoter: User) -> list[dict]:
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if event.promoter_id != promoter.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes ver tickets de un evento que no es tuyo",
        )

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.ticket_type),
        )
        .filter(Ticket.event_id == event.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )

    return [serialize_ticket(ticket) for ticket in tickets]

def _serialize_delivery(delivery: TicketDelivery) -> dict:
    return {
        "id": str(delivery.id),
        "ticket_id": str(delivery.ticket_id),
        "delivery_channel": delivery.delivery_channel,
        "delivery_status": delivery.delivery_status,
        "recipient_email": delivery.recipient_email,
        "subject": delivery.subject,
        "error_message": delivery.error_message,
        "sent_at": delivery.sent_at,
        "created_at": delivery.created_at,
    }


def _build_ticket_email_html(ticket: Ticket, recipient_name: str | None = None) -> str:
    session = _get_ticket_session(ticket)
    event_title = escape(ticket.event.title)
    event_date = format_display_datetime(session.starts_at)
    greeting = f"Hola {escape(recipient_name)}," if recipient_name else "Hola,"

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <h2>Tu entrada para {event_title}</h2>
        <p>{greeting}</p>
        <p>Aquí tienes los datos de tu ticket:</p>
        <ul>
          <li><strong>Evento:</strong> {event_title}</li>
          <li><strong>Fecha:</strong> {event_date}</li>
          <li><strong>Ubicación:</strong> {session.location_name}</li>
          <li><strong>Tipo de entrada:</strong> {ticket.ticket_type.name}</li>
          <li><strong>Código de ticket:</strong> {ticket.ticket_code}</li>
        </ul>
        <p>Tu entrada esta adjunta en PDF. Presenta ese PDF en el acceso al evento.</p>
      </body>
    </html>
    """


def _build_order_tickets_email_html(
    order: Order,
    tickets: list[Ticket],
    recipient_name: str | None = None,
) -> str:
    event = tickets[0].event
    session = _get_ticket_session(tickets[0])
    event_title = escape(event.title)
    event_date = format_display_datetime(session.starts_at)
    greeting_name = escape(recipient_name.split()[0]) if recipient_name else ""
    greeting = f"Hola {greeting_name}," if greeting_name else "Hola,"
    ticket_count = len(tickets)
    currency = order.currency or "EUR"
    order_reference = str(order.id).split("-")[0].upper()
    total_amount = float(order.total_amount or 0)

    rows = []
    for item in order.items:
        ticket_type_name = item.ticket_type.name if item.ticket_type else "Entrada"
        concept = f"Entrada {ticket_type_name} - {event.title}"
        rows.append(
            f"""
            <tr>
              <td>{escape(concept)}</td>
              <td style="text-align:right;">{float(item.unit_price):.2f} {currency}</td>
              <td style="text-align:center;">{item.quantity}</td>
              <td style="text-align:right;">{float(item.subtotal):.2f} {currency}</td>
            </tr>
            """
        )

    rows_html = "".join(rows)
    tickets_subtotal = sum((float(item.subtotal or 0) for item in order.items), 0.0)
    management_fee = max(0.0, total_amount - tickets_subtotal)

    if management_fee > 0:
        rows_html += f"""
            <tr>
              <td>Gastos de gestion</td>
              <td style="text-align:right;">{management_fee:.2f} {currency}</td>
              <td style="text-align:center;">1</td>
              <td style="text-align:right;">{management_fee:.2f} {currency}</td>
            </tr>
        """

    return f"""
    <html>
      <body style="margin:0; padding:0; background:#f4f5f7; font-family: Arial, sans-serif; color:#111827;">
        <div style="max-width:760px; margin:0 auto; background:#ffffff; padding:34px 28px 38px;">
          <h1 style="margin:0 0 28px; text-align:center; font-size:34px; font-weight:500;">
            {greeting}
          </h1>

          <p style="font-size:18px; line-height:1.5; text-align:center; margin:0 0 18px;">
            Hemos confirmado correctamente el pago de tus entradas para
            <strong>{event_title}</strong>.
          </p>
          <p style="font-size:17px; line-height:1.5; text-align:center; margin:0 0 30px;">
            Encontraras tus entradas en el PDF adjunto a este correo. Cada pagina del documento corresponde a una entrada con su codigo QR.
          </p>

          <div style="margin:24px 0 28px; text-align:center;">
            <p style="margin:0; font-size:15px; color:#6b7280;">Pedido</p>
            <p style="margin:6px 0 0; font-size:24px; font-weight:700;">#{order_reference}</p>
          </div>

          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse; font-size:16px;">
            <thead>
              <tr style="background:#111827; color:#ffffff;">
                <th style="padding:13px 12px; text-align:left;">Concepto</th>
                <th style="padding:13px 12px; text-align:right;">Precio</th>
                <th style="padding:13px 12px; text-align:center;">Cantidad</th>
                <th style="padding:13px 12px; text-align:right;">Subtotal</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
              <tr>
                <td colspan="3" style="border-top:1px solid #d1d5db; padding:14px 12px; font-weight:700;">Total</td>
                <td style="border-top:1px solid #d1d5db; padding:14px 12px; text-align:right; font-weight:700;">{total_amount:.2f} {currency}</td>
              </tr>
            </tbody>
          </table>

          <div style="margin-top:28px; padding:18px 20px; background:#f9fafb; border:1px solid #e5e7eb;">
            <p style="margin:0 0 8px; font-size:16px;"><strong>Evento:</strong> {event_title}</p>
            <p style="margin:0 0 8px; font-size:16px;"><strong>Fecha:</strong> {event_date}</p>
            <p style="margin:0 0 8px; font-size:16px;"><strong>Ubicación:</strong> {escape(session.location_name)}</p>
            <p style="margin:0; font-size:16px;"><strong>Entradas:</strong> {ticket_count}</p>
          </div>

          <h2 style="margin:34px 0 10px; text-align:center; font-size:24px;">Tus entradas</h2>
          <p style="font-size:15px; line-height:1.5; text-align:center; color:#4b5563; margin:0;">
            El archivo PDF adjunto contiene tus entradas. Presentalo en el acceso al evento.
          </p>
        </div>
      </body>
    </html>
    """


def _register_ticket_pdf_fonts() -> tuple[str, str]:
    fonts_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    regular_path = fonts_dir / "Vera.ttf"
    bold_path = fonts_dir / "VeraBd.ttf"

    if regular_path.exists() and bold_path.exists():
        if "TicketSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("TicketSans", str(regular_path)))
        if "TicketSans-Bold" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("TicketSans-Bold", str(bold_path)))
        return "TicketSans", "TicketSans-Bold"

    return "Helvetica", "Helvetica-Bold"


def _build_pdf_style(
    name: str,
    font_name: str,
    font_size: int,
    leading: int,
    color: str,
    alignment: int = 0,
) -> ParagraphStyle:
    return ParagraphStyle(
        name=name,
        fontName=font_name,
        fontSize=font_size,
        leading=leading,
        textColor=HexColor(color),
        alignment=alignment,
        spaceAfter=0,
        spaceBefore=0,
    )


def _draw_pdf_paragraph(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    top_y: float,
    width: float,
    style: ParagraphStyle,
) -> float:
    paragraph = Paragraph(escape(str(text or "-")), style)
    _, height = paragraph.wrap(width, 1000)
    paragraph.drawOn(pdf, x, top_y - height)
    return top_y - height


def _draw_pdf_centered_text(
    pdf: canvas.Canvas,
    text: str,
    center_x: float,
    y: float,
    font_name: str,
    font_size: int,
    color: str,
) -> None:
    pdf.setFont(font_name, font_size)
    pdf.setFillColor(HexColor(color))
    text_width = pdfmetrics.stringWidth(text, font_name, font_size)
    pdf.drawString(center_x - text_width / 2, y, text)


def _generate_order_tickets_pdf(tickets: list[Ticket]) -> bytes:
    pdf_buffer = BytesIO()
    page_width, page_height = 420, 640
    margin = 24
    content_width = page_width - margin * 2
    font_regular, font_bold = _register_ticket_pdf_fonts()

    title_style = _build_pdf_style("ticket_title", font_bold, 20, 24, "#18181b")
    subtitle_style = _build_pdf_style("ticket_subtitle", font_bold, 12, 15, "#3f3f46")
    body_bold_style = _build_pdf_style("ticket_body_bold", font_bold, 11, 14, "#18181b")
    small_style = _build_pdf_style("ticket_small", font_regular, 9, 12, "#52525b")
    footer_style = _build_pdf_style("ticket_footer", font_regular, 8, 11, "#52525b")

    weekday_names = [
        "lunes",
        "martes",
        "miércoles",
        "jueves",
        "viernes",
        "sábado",
        "domingo",
    ]
    month_names = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]

    def draw_order_row(
        pdf: canvas.Canvas,
        label: str,
        value: str,
        x: float,
        y: float,
        row_width: float,
    ) -> None:
        pdf.setFont(font_bold, 9)
        pdf.setFillColor(HexColor("#3f3f46"))
        pdf.drawString(x, y, label)
        pdf.setFont(font_regular, 9)
        pdf.setFillColor(HexColor("#52525b"))
        pdf.drawRightString(x + row_width, y, value)

    def draw_section(
        pdf: canvas.Canvas,
        label: str,
        value: str,
        x: float,
        top_y: float,
        section_width: float,
        secondary: str | None = None,
    ) -> float:
        pdf.setFont(font_bold, 7)
        pdf.setFillColor(HexColor("#71717a"))
        pdf.drawString(x, top_y - 7, label.upper())
        top_y -= 18
        top_y = _draw_pdf_paragraph(
            pdf,
            value,
            x,
            top_y,
            section_width,
            body_bold_style,
        )
        if secondary:
            top_y -= 4
            top_y = _draw_pdf_paragraph(
                pdf,
                secondary,
                x,
                top_y,
                section_width,
                small_style,
            )
        top_y -= 12
        pdf.setStrokeColor(HexColor("#e4e4e7"))
        pdf.setLineWidth(0.8)
        pdf.line(x, top_y, x + section_width, top_y)
        return top_y - 12

    pdf = canvas.Canvas(pdf_buffer, pagesize=(page_width, page_height))

    for index, ticket in enumerate(tickets, start=1):
        event = ticket.event
        session = _get_ticket_session(ticket)
        order = ticket.order
        buyer_name = (
            ticket.recipient_name
            if ticket.recipient_name
            else ticket.owner.full_name
            if ticket.owner
            else order.customer.full_name
            if order and order.customer
            else "Asistente"
        )
        order_reference = str(order.id).split("-")[0].upper() if order else "-"
        order_total = f"{float(order.total_amount):.2f} {order.currency}" if order else "-"
        purchase_date = (
            format_display_datetime(order.created_at, "%d/%m/%Y - %H:%M")
            if order
            else "-"
        )
        event_start = to_display_datetime(session.starts_at)
        event_end = to_display_datetime(session.ends_at) if session.ends_at else None
        event_day = weekday_names[event_start.weekday()]
        event_month = month_names[event_start.month - 1]
        event_date = (
            f"{event_day.capitalize()} {event_start.day:02d} de "
            f"{event_month} de {event_start.year}"
        )
        event_time = event_start.strftime("%H:%M")
        if event_end:
            event_time = f"{event_time} a {event_end.strftime('%H:%M')}"

        pdf.setFillColor(HexColor("#f4f4f5"))
        pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setStrokeColor(HexColor("#e4e4e7"))
        pdf.setLineWidth(0.8)
        pdf.roundRect(
            margin - 8,
            margin - 8,
            content_width + 16,
            page_height - margin * 2 + 16,
            16,
            stroke=1,
            fill=1,
        )

        top_y = page_height - 36
        top_y = _draw_pdf_paragraph(
            pdf,
            event.title.upper(),
            margin,
            top_y,
            content_width,
            title_style,
        )
        top_y -= 8

        pdf.setFont(font_bold, 10)
        pdf.setFillColor(HexColor("#7c3aed"))
        pdf.drawString(margin, top_y - 10, event_date)
        top_y -= 18
        pdf.drawString(margin, top_y - 10, f"De {event_time}")
        top_y -= 26

        top_y = _draw_pdf_paragraph(
            pdf,
            ticket.ticket_type.name.upper(),
            margin,
            top_y,
            content_width,
            subtitle_style,
        )
        top_y -= 12

        ticket_card_height = 166
        ticket_card_y = top_y - ticket_card_height
        pdf.setFillColor(HexColor("#f5f3ff"))
        pdf.setStrokeColor(HexColor("#c4b5fd"))
        pdf.setLineWidth(0.8)
        pdf.roundRect(
            margin,
            ticket_card_y,
            content_width,
            ticket_card_height,
            12,
            stroke=1,
            fill=1,
        )

        qr_size = 112
        qr_x = margin + 18
        qr_y = ticket_card_y + 16
        qr_png = generate_qr_png_bytes(ticket.qr_token)
        pdf.setFillColor(colors.white)
        pdf.roundRect(
            qr_x - 8,
            qr_y - 8,
            qr_size + 16,
            qr_size + 16,
            10,
            stroke=0,
            fill=1,
        )
        pdf.drawImage(
            ImageReader(BytesIO(qr_png)),
            qr_x,
            qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        _draw_pdf_centered_text(
            pdf,
            f"Ticket {index} de {len(tickets)}",
            qr_x + qr_size // 2,
            ticket_card_y + ticket_card_height - 17,
            font_bold,
            8,
            "#3f3f46",
        )

        info_x = qr_x + qr_size + 22
        info_width = margin + content_width - info_x - 18
        pdf.setFont(font_bold, 7)
        pdf.setFillColor(HexColor("#71717a"))
        pdf.drawString(info_x, ticket_card_y + ticket_card_height - 34, "LOCALIZADOR")
        code_box_y = ticket_card_y + ticket_card_height - 68
        pdf.setFillColor(HexColor("#7c3aed"))
        pdf.roundRect(
            info_x,
            code_box_y,
            info_width,
            28,
            7,
            stroke=0,
            fill=1,
        )
        _draw_pdf_centered_text(
            pdf,
            ticket.ticket_code.replace("TKT-", ""),
            info_x + info_width // 2,
            code_box_y + 9,
            font_bold,
            12,
            "#ffffff",
        )
        detail_top = code_box_y - 18
        pdf.setFont(font_bold, 7)
        pdf.setFillColor(HexColor("#71717a"))
        pdf.drawString(info_x, detail_top, "ASISTENTE")
        detail_top = _draw_pdf_paragraph(
            pdf,
            buyer_name,
            info_x,
            detail_top - 8,
            info_width,
            body_bold_style,
        )
        detail_top -= 8
        pdf.setFont(font_bold, 7)
        pdf.setFillColor(HexColor("#71717a"))
        pdf.drawString(info_x, detail_top, "TIPO DE ENTRADA")
        _draw_pdf_paragraph(
            pdf,
            ticket.ticket_type.name,
            info_x,
            detail_top - 8,
            info_width,
            body_bold_style,
        )

        top_y = ticket_card_y - 18
        order_box_height = 76
        order_box_y = top_y - order_box_height
        pdf.setFillColor(HexColor("#fafafa"))
        pdf.setStrokeColor(HexColor("#e4e4e7"))
        pdf.roundRect(
            margin,
            order_box_y,
            content_width,
            order_box_height,
            10,
            stroke=1,
            fill=1,
        )
        row_x = margin + 16
        row_width = content_width - 32
        draw_order_row(pdf, "Pedido", order_reference, row_x, order_box_y + 51, row_width)
        draw_order_row(pdf, "Compra", purchase_date, row_x, order_box_y + 31, row_width)
        draw_order_row(pdf, "Importe", order_total, row_x, order_box_y + 11, row_width)

        top_y = order_box_y - 20
        top_y = draw_section(
            pdf,
            "Sitio",
            session.location_name,
            margin,
            top_y,
            content_width,
            secondary=session.location_address,
        )
        _draw_pdf_paragraph(
            pdf,
            "Presenta este documento en el acceso al evento. Cada QR es único y solo puede validarse una vez.",
            margin,
            max(top_y, 42),
            content_width,
            footer_style,
        )

        pdf.showPage()

    pdf.save()
    return pdf_buffer.getvalue()


def get_ticket_delivery_history(db: Session, ticket_id: str, user: User) -> list[dict]:
    ticket = get_ticket_model_by_id_for_owner(db, ticket_id, user)

    deliveries = (
        db.query(TicketDelivery)
        .filter(TicketDelivery.ticket_id == ticket.id)
        .order_by(TicketDelivery.created_at.desc())
        .all()
    )

    return [_serialize_delivery(delivery) for delivery in deliveries]


def send_ticket_email(db: Session, ticket_id: str, user: User, force_resend: bool = False) -> dict:
    ticket = get_ticket_model_by_id_for_owner(db, ticket_id, user)

    recipient_email = user.email
    subject = f"Tu entrada para {ticket.event.title}"
    html_body = _build_ticket_email_html(ticket, user.full_name)
    pdf_bytes = _generate_order_tickets_pdf([ticket])

    if not force_resend:
        existing_success = (
            db.query(TicketDelivery)
            .filter(
                TicketDelivery.ticket_id == ticket.id,
                TicketDelivery.delivery_channel == "email",
                TicketDelivery.delivery_status == "sent",
            )
            .first()
        )
        if existing_success:
            return {
                "success": False,
                "message": "Este ticket ya fue enviado por email. Usa resend si quieres reenviarlo.",
                "delivery": _serialize_delivery(existing_success),
            }

    delivery = TicketDelivery(
        ticket_id=ticket.id,
        delivery_channel="email",
        delivery_status="pending",
        recipient_email=recipient_email,
        subject=subject,
        error_message=None,
        sent_at=None,
    )
    db.add(delivery)
    db.flush()

    try:
        send_email_with_attachment(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"{ticket.ticket_code}.pdf",
            attachment_mime_type="application/pdf",
        )

        delivery.delivery_status = "sent"
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.error_message = None

        db.commit()
        db.refresh(delivery)

        return {
            "success": True,
            "message": "Ticket enviado por email correctamente",
            "delivery": _serialize_delivery(delivery),
        }

    except Exception as exc:
        delivery.delivery_status = "failed"
        delivery.error_message = str(exc)

        db.commit()
        db.refresh(delivery)

        return {
            "success": False,
            "message": "Error al enviar el ticket por email",
            "delivery": _serialize_delivery(delivery),
        }


def send_order_tickets_email(
    db: Session,
    order_id: str,
    user: User | None = None,
    force_resend: bool = False,
) -> dict:
    order = db.query(Order).filter(Order.id == order_id).with_for_update().first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido no encontrado",
        )

    order = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.ticket_type),
            joinedload(Order.customer),
            joinedload(Order.buyer),
        )
        .filter(Order.id == order.id)
        .first()
    )

    if user and order.buyer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes enviar entradas de un pedido que no es tuyo",
        )

    if not user and not order.customer and not order.buyer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pedido no tiene datos de contacto para enviar las entradas",
        )

    account_user = user or order.buyer
    recipient_email = account_user.email if account_user else order.customer.email
    recipient_name = account_user.full_name if account_user else order.customer.full_name

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.session),
            joinedload(Ticket.ticket_type),
        )
        .filter(
            Ticket.order_id == order.id,
        )
        .order_by(Ticket.created_at.asc())
        .all()
    )

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay entradas generadas para este pedido",
        )

    ticket_ids = [ticket.id for ticket in tickets]
    if not force_resend:
        existing_in_progress_or_sent = (
            db.query(TicketDelivery)
            .filter(
                TicketDelivery.ticket_id.in_(ticket_ids),
                TicketDelivery.delivery_channel == "email",
                TicketDelivery.delivery_status.in_(("pending", "sent")),
            )
            .first()
        )
        if existing_in_progress_or_sent:
            return {
                "success": False,
                "message": "Las entradas de este pedido ya se estan enviando o ya fueron enviadas.",
                "delivery": _serialize_delivery(existing_in_progress_or_sent),
            }

    event_title = tickets[0].event.title
    subject = f"Tus entradas para {event_title}"
    html_body = _build_order_tickets_email_html(order, tickets, recipient_name)
    pdf_bytes = _generate_order_tickets_pdf(tickets)

    deliveries = []
    for ticket in tickets:
        delivery = TicketDelivery(
            ticket_id=ticket.id,
            delivery_channel="email",
            delivery_status="pending",
            recipient_email=recipient_email,
            subject=subject,
            error_message=None,
            sent_at=None,
        )
        db.add(delivery)
        deliveries.append(delivery)

    db.commit()

    try:
        send_email_with_attachment(
            to_email=recipient_email,
            subject=subject,
            html_body=html_body,
            attachment_bytes=pdf_bytes,
            attachment_filename=f"entradas-{str(order.id).split('-')[0]}.pdf",
            attachment_mime_type="application/pdf",
        )

        sent_at = datetime.now(timezone.utc)
        for delivery in deliveries:
            delivery.delivery_status = "sent"
            delivery.sent_at = sent_at
            delivery.error_message = None

        db.commit()
        db.refresh(deliveries[0])

        return {
            "success": True,
            "message": "Entradas enviadas por email correctamente",
            "delivery": _serialize_delivery(deliveries[0]),
        }

    except Exception as exc:
        for delivery in deliveries:
            delivery.delivery_status = "failed"
            delivery.error_message = str(exc)

        db.commit()
        db.refresh(deliveries[0])

        return {
            "success": False,
            "message": "Error al enviar las entradas por email",
            "delivery": _serialize_delivery(deliveries[0]),
        }


def get_order_tickets_pdf_for_owner(
    db: Session,
    order_id: str,
    user: User | None,
    guest_access_token: str | None = None,
) -> tuple[bytes, str]:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(
            Order.id == order_id,
            Order.status == "paid",
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pedido pagado no encontrado",
        )

    has_user_access = user is not None and order.buyer_id == user.id
    has_guest_access = has_valid_guest_checkout_access(order, guest_access_token)

    if not has_user_access and not has_guest_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes descargar entradas de este pedido",
        )

    ticket_filters = [Ticket.order_id == order.id, Ticket.status == "active"]
    if has_user_access:
        ticket_filters.append(Ticket.owner_user_id == user.id)

    tickets = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.event),
            joinedload(Ticket.session),
            joinedload(Ticket.ticket_type),
        )
        .filter(*ticket_filters)
        .order_by(Ticket.created_at.asc())
        .all()
    )

    if not tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay entradas disponibles para descargar en este pedido",
        )

    pdf_bytes = _generate_order_tickets_pdf(tickets)
    filename = f"entradas-{str(order.id).split('-')[0]}.pdf"
    return pdf_bytes, filename
