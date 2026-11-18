from app.core.config import settings
from app.services import email_service


def test_local_smtp_does_not_require_authentication(monkeypatch):
    calls: list[tuple[str, object]] = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            calls.append(("connect", (host, port, timeout)))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def starttls(self):
            calls.append(("starttls", None))

        def login(self, username, password):
            calls.append(("login", (username, password)))

        def send_message(self, message):
            calls.append(("send", message["To"]))

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSmtp)
    monkeypatch.setattr(settings, "email_delivery_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "mailpit")
    monkeypatch.setattr(settings, "smtp_port", 1025)
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_use_tls", False)

    email_service.send_email_with_attachment(
        "buyer@ticketing-demo.com",
        "Test message",
        "<p>Test</p>",
    )

    assert ("send", "buyer@ticketing-demo.com") in calls
    assert not any(name == "login" for name, _ in calls)
