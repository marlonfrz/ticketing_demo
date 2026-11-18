from datetime import datetime, timedelta, timezone

from conftest import create_event_with_session, create_user_with_roles


def test_admin_search_users_by_text_and_role(client, db, admin_token):
    create_user_with_roles(
        db=db,
        email="promoter-search@test.com",
        password="Password!1234",
        full_name="Promotor Search",
        roles=["promoter"],
    )

    response = client.get(
        "/admin/users/search",
        params={"q": "promoter-search", "role": "promoter"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 10
    assert data["total"] >= 1
    assert any(item["email"] == "promoter-search@test.com" for item in data["items"])


def test_admin_search_events_by_title_and_status(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento Admin Search",
        description="Evento no publicado",
        location_name="Madrid",
        location_address="Calle Test",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=3),
        capacity=100,
        status="not_reviewed",
    )

    response = client.get(
        "/admin/events/search",
        params={"q": "Admin Search", "event_status": "not_reviewed"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 10
    assert any(item["id"] == str(event.id) for item in data["items"])
    matched = next(item for item in data["items"] if item["id"] == str(event.id))
    assert matched["promoter"]["email"] == promoter_user.email


def test_admin_can_list_promoter_events(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento De Promotor",
        description="Evento para admin",
        location_name="Valencia",
        location_address="Calle Test",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=3),
        capacity=100,
        status="draft",
    )

    response = client.get(
        f"/admin/promoters/{promoter_user.id}/events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["promoter"]["id"] == str(promoter_user.id)
    assert any(item["id"] == str(event.id) for item in data["events"])


def test_admin_can_list_events_owned_by_an_admin(
    client,
    db,
    admin_token,
    admin_user,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        admin_user.id,
        title="Evento De Admin",
        description="Evento creado por administracion",
        location_name="Madrid",
        location_address="Calle Test",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=3),
        capacity=100,
        status="draft",
    )

    response = client.get(
        f"/admin/promoters/{admin_user.id}/events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["promoter"]["id"] == str(admin_user.id)
    assert any(item["id"] == str(event.id) for item in data["events"])


def test_admin_delete_redirect_target_remains_accessible(
    client,
    db,
    admin_token,
    admin_user,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        admin_user.id,
        title="Evento Admin Para Borrar",
        description="Evento borrable creado por administracion",
        location_name="Madrid",
        location_address="Calle Test",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=3),
        capacity=100,
        status="not_reviewed",
    )

    delete_response = client.delete(
        f"/events/{event.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    list_response = client.get(
        f"/admin/promoters/{admin_user.id}/events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert delete_response.status_code == 200, delete_response.text
    assert list_response.status_code == 200, list_response.text
    assert all(
        listed_event["id"] != str(event.id)
        for listed_event in list_response.json()["events"]
    )
