from html import escape

from app.core.config import settings
from app.schemas.contact import OrganizerContactRequest
from app.services.email_service import send_email_with_attachment


def send_organizer_contact_email(data: OrganizerContactRequest) -> None:
    recipient = settings.organizer_contact_email or settings.smtp_from_email
    name = " ".join(data.name.split())
    phone = escape(data.phone.strip()) if data.phone else "No indicado"
    description = escape(data.description.strip()).replace("\n", "<br>")

    send_email_with_attachment(
        to_email=recipient,
        subject=f"Nueva solicitud para organizar un evento: {name}",
        html_body=(
            "<h1>Nueva solicitud para organizar un evento</h1>"
            f"<p><strong>Nombre:</strong> {escape(name)}</p>"
            f"<p><strong>Email:</strong> {escape(str(data.email))}</p>"
            f"<p><strong>Teléfono:</strong> {phone}</p>"
            f"<p><strong>Descripción:</strong><br>{description}</p>"
        ),
        reply_to=str(data.email),
    )
