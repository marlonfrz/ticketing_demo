from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_type import TicketType
from app.models.ticket_validation import TicketValidation


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_published_session(db, event_id, location_name):
    now = datetime.now(timezone.utc)
    session = EventSession(
        event_id=event_id,
        location_name=location_name,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        capacity=100,
        status="published",
        display_order=1,
    )
    db.add(session)
    db.flush()
    return session


def _create_ticket(db, event, session, suffix):
    ticket_type = TicketType(
        event_id=event.id,
        session_id=session.id,
        name=f"General {suffix}",
        price=Decimal("20.00"),
        currency="EUR",
        stock=100,
        sold_count=1,
        max_per_purchase=4,
        is_active=True,
        status="published",
    )
    db.add(ticket_type)
    db.flush()
    order = Order(
        buyer_id=None,
        event_id=event.id,
        session_id=session.id,
        status="paid",
        total_amount=Decimal("20.00"),
        currency="EUR",
    )
    db.add(order)
    db.flush()
    ticket = Ticket(
        order_id=order.id,
        event_id=event.id,
        session_id=session.id,
        ticket_type_id=ticket_type.id,
        owner_user_id=None,
        ticket_code=f"TKT-STATION-{suffix}",
        qr_token=f"qr_station_{suffix}",
        status="active",
        is_valid=True,
    )
    db.add(ticket)
    db.flush()
    return ticket


def test_station_activation_and_scan_are_limited_to_one_session(
    client,
    db,
    promoter_user,
    admin_user,
    promoter_token,
    admin_token,
):
    event = Event(
        promoter_id=promoter_user.id,
        title="Evento con puestos temporales",
        description="Prueba de validadores por sesion",
        status="published",
    )
    db.add(event)
    db.flush()
    allowed_session = _create_published_session(db, event.id, "Puerta principal")
    other_session = _create_published_session(db, event.id, "Segunda fecha")
    allowed_ticket = _create_ticket(db, event, allowed_session, "ALLOWED")
    other_ticket = _create_ticket(db, event, other_session, "OTHER")
    db.commit()

    quota_response = client.post(
        f"/promoter/event-sessions/{allowed_session.id}/validation-quota-requests",
        headers=_auth(promoter_token),
        json={"requested_count": 2, "promoter_note": "Dos accesos"},
    )
    assert quota_response.status_code == 200, quota_response.text
    quota_request = quota_response.json()

    review_response = client.post(
        f"/admin/validation-quota-requests/{quota_request['id']}/review",
        headers=_auth(admin_token),
        json={"status": "approved", "approved_count": 1},
    )
    assert review_response.status_code == 200, review_response.text

    station_response = client.post(
        f"/promoter/event-sessions/{allowed_session.id}/validation-stations",
        headers=_auth(promoter_token),
        json={"name": "Puerta 1", "responsible_name": "Responsable prueba"},
    )
    assert station_response.status_code == 200, station_response.text
    station_link = station_response.json()
    station_id = station_link["station"]["id"]
    activation_token = parse_qs(urlparse(station_link["activation_url"]).query)["token"][0]

    activate_response = client.post(
        "/validator-stations/activate",
        json={"token": activation_token},
    )
    assert activate_response.status_code == 200, activate_response.text
    assert activate_response.json()["station"]["name"] == "Puerta 1"

    current_station_response = client.get("/validator-stations/me")
    assert current_station_response.status_code == 200, current_station_response.text

    wrong_session_response = client.post(
        "/validator-stations/validate",
        json={"qr_token": other_ticket.qr_token},
    )
    assert wrong_session_response.status_code == 200, wrong_session_response.text
    wrong_session_data = wrong_session_response.json()
    assert wrong_session_data["valid"] is False
    assert "no es de esta sesion" in wrong_session_data["message"].lower()
    assert wrong_session_data["ticket"]["ticket_code"] == other_ticket.ticket_code

    valid_response = client.post(
        "/validator-stations/validate",
        json={"qr_token": allowed_ticket.qr_token},
    )
    assert valid_response.status_code == 200, valid_response.text
    assert valid_response.json()["valid"] is True

    incident_response = client.post(
        "/validator-stations/incidents",
        json={"message": "El lector auxiliar ha tardado en enfocar"},
    )
    assert incident_response.status_code == 200, incident_response.text
    assert incident_response.json()["validation_type"] == "incident"

    management_response = client.get(
        f"/promoter/event-sessions/{allowed_session.id}/validation-stations",
        headers=_auth(promoter_token),
    )
    assert management_response.status_code == 200, management_response.text
    management_data = management_response.json()
    assert management_data["validated_count"] == 1
    assert management_data["stations"][0]["validated_count"] == 1

    activity_response = client.get(
        f"/promoter/validation-stations/{station_id}/activity",
        headers=_auth(promoter_token),
    )
    assert activity_response.status_code == 200, activity_response.text
    activity_data = activity_response.json()
    assert activity_data["total"] == 3
    assert len(activity_data["items"]) == 3
    assert activity_data["station"]["validated_count"] == 1

    db.expire_all()
    validations = db.query(TicketValidation).order_by(TicketValidation.validated_at.asc()).all()
    assert [validation.result for validation in validations] == ["wrong_session", "success", "reported"]
    assert all(validation.validation_station_id for validation in validations)


def test_admin_can_enable_session_validation_quota_directly(
    client,
    db,
    promoter_user,
    admin_token,
):
    event = Event(
        promoter_id=promoter_user.id,
        title="Evento con cupo admin",
        description="Prueba de cupo directo",
        status="published",
    )
    db.add(event)
    db.flush()
    session = _create_published_session(db, event.id, "Acceso admin")
    db.commit()

    quota_response = client.post(
        f"/admin/event-sessions/{session.id}/validation-quota-requests",
        headers=_auth(admin_token),
        json={"requested_count": 5, "promoter_note": "Cupo habilitado por admin"},
    )
    assert quota_response.status_code == 200, quota_response.text
    assert quota_response.json()["status"] == "approved"
    assert quota_response.json()["approved_count"] == 5

    station_response = client.post(
        f"/admin/event-sessions/{session.id}/validation-stations",
        headers=_auth(admin_token),
        json={"name": "Puerta admin", "responsible_name": "Equipo acceso"},
    )
    assert station_response.status_code == 200, station_response.text
    assert station_response.json()["station"]["session_id"] == str(session.id)

    management_response = client.get(
        f"/admin/event-sessions/{session.id}/validation-stations",
        headers=_auth(admin_token),
    )
    assert management_response.status_code == 200, management_response.text
    assert management_response.json()["approved_quota"] == 5
    assert management_response.json()["occupied_slots"] == 1
    assert management_response.json()["validated_count"] == 0
