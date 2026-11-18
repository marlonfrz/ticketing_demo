import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_email_with_attachment(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_bytes: bytes | None = None,
    attachment_filename: str | None = None,
    attachment_mime_type: str = "image/png",
    reply_to: str | None = None,
) -> None:
    if not settings.email_delivery_enabled:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content("Este correo contiene una versión HTML. Abre el mensaje desde un cliente compatible.")
    msg.add_alternative(html_body, subtype="html")

    if attachment_bytes and attachment_filename:
        maintype, subtype = attachment_mime_type.split("/", 1)
        msg.add_attachment(
            attachment_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_filename,
        )

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=settings.smtp_timeout_seconds,
    ) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
