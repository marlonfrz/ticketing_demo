import logging
from html import escape

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event import Event
from app.models.event_session import EventSession
from app.models.user import User
from app.services.email_service import send_email_with_attachment
from app.utils.date_time import format_display_datetime


logger = logging.getLogger(__name__)


EVENT_STATUS_LABELS = {
    "not_reviewed": "No revisado",
    "in_review": "En revision",
    "draft": "Aprobado",
    "published": "Publicado",
    "unpublished": "Despublicado",
    "cancelled": "Cancelado",
    "finished": "Finalizado",
    "sold_out": "Agotado",
    "archived": "Borrado",
    "disabled": "Desactivado",
}

EVENT_STATUS_MESSAGES = {
    "in_review": (
        "Tu evento se ha enviado a revision. Nuestro equipo lo revisara y te "
        "avisaremos cuando haya una respuesta."
    ),
    "draft": (
        "Tu evento ha sido aprobado. Ya puedes continuar con la preparacion "
        "antes de publicarlo."
    ),
    "not_reviewed": (
        "Tu evento necesita algunos cambios antes de poder aprobarse. Revisa "
        "la informacion desde tu panel de promotor."
    ),
    "cancelled": (
        "Tu evento ha sido cancelado. Si crees que se trata de un error, "
        "ponte en contacto con nosotros."
    ),
    "published": "Tu evento ha sido publicado correctamente.",
    "unpublished": (
        "Tu evento ha sido despublicado y ya no se muestra en la web publica."
    ),
    "finished": "Tu evento ha sido marcado como finalizado.",
    "archived": "Tu evento ha sido borrado.",
}

SESSION_STATUS_MESSAGES = {
    "in_review": (
        "La sesion se ha enviado a revision. Nuestro equipo la revisara y te "
        "avisaremos cuando haya una respuesta."
    ),
    "draft": (
        "La sesion ha sido aprobada. Ya puedes continuar con la preparacion "
        "antes de publicarla."
    ),
    "not_reviewed": (
        "La sesion necesita algunos cambios antes de poder aprobarse. Revisa "
        "la informacion desde tu panel de promotor."
    ),
    "cancelled": (
        "La sesion ha sido cancelada. Si crees que se trata de un error, "
        "ponte en contacto con nosotros."
    ),
    "published": "La sesion ha sido publicada correctamente.",
    "unpublished": (
        "La sesion ha sido despublicada y ya no se muestra en la web publica."
    ),
    "finished": "La sesion ha sido marcada como finalizada.",
    "archived": "La sesion ha sido archivada.",
    "disabled": "La sesion ha sido desactivada.",
}


def get_event_status_label(status: str) -> str:
    return EVENT_STATUS_LABELS.get(status, status)


def build_event_status_email_html(event: Event, recipient_name: str) -> str:
    status_label = get_event_status_label(event.status)
    status_message = EVENT_STATUS_MESSAGES.get(
        event.status,
        "El estado de tu evento ha cambiado.",
    )
    event_url = f"{settings.frontend_base_url}/events/{event.id}/manage"
    safe_event_title = escape(event.title)
    safe_recipient_name = escape(recipient_name)
    safe_status_label = escape(status_label)

    if event.status == "archived":
        return f"""
        <div style="font-family: Arial, sans-serif; color: #111; line-height: 1.5;">
          <h2 style="margin: 0 0 16px;">Hola {safe_recipient_name},</h2>
          <p>El evento <strong>{safe_event_title}</strong> ha sido borrado.</p>
          <p>
            Si tienes alguna duda o crees que se trata de un error, ponte en
            contacto con nosotros y te ayudaremos.
          </p>
        </div>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #111; line-height: 1.5;">
      <h2 style="margin: 0 0 16px;">Hola {safe_recipient_name},</h2>
      <p>{status_message}</p>
      <div style="margin: 20px 0; padding: 16px; border: 1px solid #ddd; border-radius: 8px;">
        <p style="margin: 0 0 8px;"><strong>Evento:</strong> {safe_event_title}</p>
        <p style="margin: 0;"><strong>Estado actual:</strong> {safe_status_label}</p>
      </div>
      <p>
        Puedes revisar el evento desde tu panel:
        <a href="{event_url}">{event_url}</a>
      </p>
      <p>
        Si tienes alguna duda o necesitas aclarar algo, ponte en contacto con
        nosotros y te ayudaremos.
      </p>
    </div>
    """


def build_new_event_admin_email_html(event: Event, promoter: User, events_created_today: int) -> str:
    first_session = min(event.sessions, key=lambda session: session.starts_at) if event.sessions else None
    event_url = f"{settings.frontend_base_url}/events/{event.id}/manage"
    safe_event_title = escape(event.title)
    safe_promoter_name = escape(promoter.full_name or "Promotor")
    safe_promoter_email = escape(promoter.email)
    safe_promoter_id = escape(str(promoter.id))
    safe_status = escape(get_event_status_label(event.status))

    session_block = ""
    if first_session:
        safe_location = escape(first_session.location_name)
        starts_at = format_display_datetime(first_session.starts_at)
        session_block = f"""
        <p style="margin: 0 0 8px;"><strong>Primera sesion:</strong> {safe_location}</p>
        <p style="margin: 0;"><strong>Fecha:</strong> {starts_at}</p>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #111; line-height: 1.5;">
      <h2 style="margin: 0 0 16px;">Nuevo evento creado por promotor</h2>
      <p>Un promotor ha creado un nuevo evento en la plataforma.</p>
      <div style="margin: 20px 0; padding: 16px; border: 1px solid #ddd; border-radius: 8px;">
        <p style="margin: 0 0 8px;"><strong>Evento:</strong> {safe_event_title}</p>
        <p style="margin: 0 0 8px;"><strong>Estado:</strong> {safe_status}</p>
        <p style="margin: 0 0 8px;"><strong>Promotor:</strong> {safe_promoter_name}</p>
        <p style="margin: 0 0 8px;"><strong>Email:</strong> {safe_promoter_email}</p>
        <p style="margin: 0 0 8px;"><strong>ID promotor:</strong> {safe_promoter_id}</p>
        <p style="margin: 0 0 8px;"><strong>Eventos creados hoy por este promotor:</strong> {events_created_today}</p>
        {session_block}
      </div>
      <p>
        Puedes revisar el evento desde admin:
        <a href="{event_url}">{event_url}</a>
      </p>
    </div>
    """


def get_superadmin_notification_emails(db: Session) -> list[str]:
    emails: list[str] = []
    superadmins = (
        db.query(User)
        .filter(
            User.is_superadmin == True,
            User.is_active == True,
            User.status == "active",
        )
        .all()
    )

    for user in superadmins:
        if user.email and user.email not in emails:
            emails.append(user.email)

    if settings.superadmin_email and settings.superadmin_email not in emails:
        emails.append(settings.superadmin_email)

    return emails


def build_event_session_status_email_html(
    session: EventSession,
    recipient_name: str,
    reason: str | None = None,
) -> str:
    event = session.event
    status_label = get_event_status_label(session.status)
    status_message = SESSION_STATUS_MESSAGES.get(
        session.status,
        "El estado de una sesion de tu evento ha cambiado.",
    )
    event_url = f"{settings.frontend_base_url}/events/{event.id}/manage"
    safe_event_title = escape(event.title)
    safe_session_title = escape(session.title or session.location_name)
    safe_location = escape(session.location_name)
    safe_recipient_name = escape(recipient_name)
    safe_status_label = escape(status_label)
    safe_reason = escape(reason.strip()) if reason and reason.strip() else None
    starts_at = format_display_datetime(session.starts_at)

    reason_block = ""
    if safe_reason:
        reason_block = f"""
        <div style="margin-top: 12px; padding: 12px; background: #fff8e6; border: 1px solid #f0d58a; border-radius: 8px;">
          <p style="margin: 0 0 6px;"><strong>Motivo indicado por admin:</strong></p>
          <p style="margin: 0;">{safe_reason}</p>
        </div>
        """

    return f"""
    <div style="font-family: Arial, sans-serif; color: #111; line-height: 1.5;">
      <h2 style="margin: 0 0 16px;">Hola {safe_recipient_name},</h2>
      <p>{status_message}</p>
      <div style="margin: 20px 0; padding: 16px; border: 1px solid #ddd; border-radius: 8px;">
        <p style="margin: 0 0 8px;"><strong>Evento:</strong> {safe_event_title}</p>
        <p style="margin: 0 0 8px;"><strong>Sesion:</strong> {safe_session_title}</p>
        <p style="margin: 0 0 8px;"><strong>Lugar:</strong> {safe_location}</p>
        <p style="margin: 0 0 8px;"><strong>Fecha:</strong> {starts_at}</p>
        <p style="margin: 0;"><strong>Estado actual:</strong> {safe_status_label}</p>
        {reason_block}
      </div>
      <p>
        Puedes revisar la sesion desde tu panel:
        <a href="{event_url}">{event_url}</a>
      </p>
      <p>
        Si tienes alguna duda o necesitas aclarar algo, ponte en contacto con
        nosotros y te ayudaremos.
      </p>
    </div>
    """


def send_event_status_email(event: Event) -> None:
    promoter: User | None = event.promoter
    if not promoter or not promoter.email:
        return

    status_label = get_event_status_label(event.status)
    safe_subject_title = event.title.replace("\r", " ").replace("\n", " ")
    subject = f"Actualizacion de estado: {safe_subject_title} - {status_label}"
    recipient_name = promoter.full_name or "promotor"
    html_body = build_event_status_email_html(event, recipient_name)

    try:
        send_email_with_attachment(
            to_email=promoter.email,
            subject=subject,
            html_body=html_body,
        )
    except Exception:
        logger.exception(
            "No se pudo enviar el email de cambio de estado del evento %s",
            event.id,
        )


def send_new_event_admin_email(db: Session, event: Event, events_created_today: int) -> None:
    promoter: User | None = event.promoter
    if not promoter:
        return

    recipient_emails = get_superadmin_notification_emails(db)
    if not recipient_emails:
        return

    safe_subject_title = event.title.replace("\r", " ").replace("\n", " ")
    subject = f"Nuevo evento creado: {safe_subject_title}"
    html_body = build_new_event_admin_email_html(event, promoter, events_created_today)

    for recipient_email in recipient_emails:
        try:
            send_email_with_attachment(
                to_email=recipient_email,
                subject=subject,
                html_body=html_body,
            )
        except Exception:
            logger.exception(
                "No se pudo enviar el email de nuevo evento %s al superadmin %s",
                event.id,
                recipient_email,
            )


def send_event_session_status_email(session: EventSession, reason: str | None = None) -> None:
    event = session.event
    promoter: User | None = event.promoter
    if not promoter or not promoter.email:
        return

    status_label = get_event_status_label(session.status)
    event_title = event.title.replace("\r", " ").replace("\n", " ")
    session_title = (session.title or session.location_name).replace("\r", " ").replace("\n", " ")
    subject = f"Actualizacion de sesion: {event_title} - {session_title} - {status_label}"
    recipient_name = promoter.full_name or "promotor"
    html_body = build_event_session_status_email_html(session, recipient_name, reason)

    try:
        send_email_with_attachment(
            to_email=promoter.email,
            subject=subject,
            html_body=html_body,
        )
    except Exception:
        logger.exception(
            "No se pudo enviar el email de cambio de estado de la sesion %s",
            session.id,
        )
