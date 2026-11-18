from datetime import datetime, timedelta, timezone

from conftest import create_event_with_session, create_user_with_roles


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client, email: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _management_paths(event_id: str) -> list[str]:
    return [
        f"/events/{event_id}/sessions",
        f"/events/{event_id}/ticket-types",
        f"/events/{event_id}/sale-groups",
        f"/events/{event_id}/ticket-capacity-summary",
    ]


def test_management_collections_require_role_and_event_access(
    client,
    db,
    promoter_user,
    promoter_token,
    buyer_token,
    admin_token,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento privado de gestion",
        description="Configuracion visible solo para sus gestores",
        location_name="Sala privada",
        location_address="Calle privada 1",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=4),
        capacity=300,
        status="not_reviewed",
    )
    other_promoter = create_user_with_roles(
        db,
        email="other-promoter@test.com",
        password="123456",
        full_name="Other Promoter",
        roles=["promoter"],
    )
    other_promoter_token = _login(client, other_promoter.email, "123456")

    for path in _management_paths(str(event.id)):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=_auth(buyer_token)).status_code == 403
        assert client.get(path, headers=_auth(other_promoter_token)).status_code == 403
        assert client.get(path, headers=_auth(promoter_token)).status_code == 200
        assert client.get(path, headers=_auth(admin_token)).status_code == 200


def test_public_event_and_sales_options_remain_anonymous(client, db, promoter_user):
    now = datetime.now(timezone.utc)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publico",
        description="Contrato publico sin datos de gestion",
        location_name="Sala publica",
        location_address="Calle publica 1",
        starts_at=now + timedelta(days=10),
        ends_at=now + timedelta(days=10, hours=4),
        capacity=300,
        status="published",
    )
    event.publish_at = now - timedelta(minutes=1)
    session = event.sessions[0]
    session.publish_at = now - timedelta(minutes=1)
    session.tickets_publish_at = now - timedelta(minutes=1)
    session.tickets_activated_at = now - timedelta(minutes=1)
    db.commit()

    event_response = client.get(f"/events/{event.id}")
    sales_response = client.get(
        f"/events/{event.id}/sales-options",
        params={"session_id": str(session.id)},
    )

    assert event_response.status_code == 200, event_response.text
    assert sales_response.status_code == 200, sales_response.text
