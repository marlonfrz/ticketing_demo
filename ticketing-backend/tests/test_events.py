from datetime import datetime, timedelta, timezone

from conftest import create_event_with_session


def test_promoter_can_create_event(client, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    response = client.post(
        "/events",
        json={
            "title": "Festival Test",
            "description": "Evento de prueba",
            "initial_session": {
                "location_name": "Madrid Arena",
                "location_address": "Calle Test 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "capacity": 500,
            },
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Festival Test"
    assert data["status"] == "not_reviewed"


def test_buyer_cannot_create_event(client, buyer_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    response = client.post(
        "/events",
        json={
            "title": "Festival Test",
            "description": "Evento de prueba",
            "initial_session": {
                "location_name": "Madrid Arena",
                "location_address": "Calle Test 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "capacity": 500,
            },
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert response.status_code == 403


def test_public_events_are_ordered_by_publish_date_desc(client, db, promoter_user):
    now = datetime.now(timezone.utc)
    old_event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento antiguo",
        description="Publicado antes",
        location_name="Sala Antigua",
        location_address="Calle Antigua 1",
        starts_at=now + timedelta(days=20),
        ends_at=now + timedelta(days=20, hours=5),
        capacity=300,
        status="finished",
    )
    old_event.publish_at = now - timedelta(days=10)

    new_event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento nuevo",
        description="Publicado despues",
        location_name="Sala Nueva",
        location_address="Calle Nueva 1",
        starts_at=now + timedelta(days=30),
        ends_at=now + timedelta(days=30, hours=5),
        capacity=300,
        status="published",
    )
    new_event.publish_at = now - timedelta(days=1)
    db.commit()

    response = client.get("/events")

    assert response.status_code == 200, response.text
    titles = [event["title"] for event in response.json()]
    assert titles[:2] == ["Evento nuevo", "Evento antiguo"]


def test_promoter_can_create_only_three_events_per_day(client, promoter_token):
    for index in range(3):
        starts_at = datetime.now(timezone.utc) + timedelta(days=10 + index)
        ends_at = starts_at + timedelta(hours=5)

        response = client.post(
            "/events",
            json={
                "title": f"Festival Diario {index}",
                "description": "Evento de prueba",
                "initial_session": {
                    "location_name": "Madrid Arena",
                    "location_address": "Calle Test 123",
                    "starts_at": starts_at.isoformat(),
                    "ends_at": ends_at.isoformat(),
                    "capacity": 500,
                },
            },
            headers={"Authorization": f"Bearer {promoter_token}"},
        )

        assert response.status_code == 200

    starts_at = datetime.now(timezone.utc) + timedelta(days=20)
    ends_at = starts_at + timedelta(hours=5)
    response = client.post(
        "/events",
        json={
            "title": "Festival Diario Bloqueado",
            "description": "Evento de prueba",
            "initial_session": {
                "location_name": "Madrid Arena",
                "location_address": "Calle Test 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "capacity": 500,
            },
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 429
    assert "limite de 3 eventos" in response.json()["detail"]


def test_new_promoter_event_requires_admin_review_before_publish(client, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    create_response = client.post(
        "/events",
        json={
            "title": "Festival Publish",
            "description": "Evento publicable",
            "initial_session": {
                "location_name": "Madrid Arena",
                "location_address": "Calle Test 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "capacity": 500,
            },
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert create_response.status_code == 200
    event_id = create_response.json()["id"]

    publish_response = client.post(
        f"/events/{event_id}/publish",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert publish_response.status_code == 403
    assert "administrador" in publish_response.json()["detail"].lower()
