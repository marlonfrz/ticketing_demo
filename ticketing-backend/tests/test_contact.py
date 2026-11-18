from app.services import contact_service


def test_organizer_contact_schedules_email(client, monkeypatch):
    sent_messages = []

    monkeypatch.setattr(
        contact_service,
        "send_email_with_attachment",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    response = client.post(
        "/contact/organizer",
        json={
            "name": "María Pérez",
            "email": "maria@example.com",
            "phone": "+34 600 000 000",
            "description": "Quiero organizar un festival para quinientas personas.",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert len(sent_messages) == 1
    assert "María Pérez" in sent_messages[0]["subject"]
    assert "maria@example.com" in sent_messages[0]["html_body"]
    assert sent_messages[0]["reply_to"] == "maria@example.com"


def test_organizer_contact_rejects_invalid_payload(client):
    response = client.post(
        "/contact/organizer",
        json={
            "name": "A",
            "email": "not-an-email",
            "description": "Short",
        },
    )

    assert response.status_code == 422


def test_organizer_contact_ignores_honeypot(client, monkeypatch):
    sent_messages = []
    monkeypatch.setattr(
        contact_service,
        "send_email_with_attachment",
        lambda **kwargs: sent_messages.append(kwargs),
    )

    response = client.post(
        "/contact/organizer",
        json={
            "name": "Automated Sender",
            "email": "bot@example.com",
            "description": "This message is long enough to pass validation.",
            "website": "https://spam.example.com",
        },
    )

    assert response.status_code == 200
    assert sent_messages == []
