from datetime import datetime, timedelta, timezone

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket_type import TicketType
from app.models.ticket_sale_group import TicketSaleGroup
from conftest import create_event_with_session


def create_draft_event(client, promoter_token, title="Evento Sale Group", capacity=500):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    response = client.post(
        "/events",
        json={
            "title": title,
            "description": "Evento de prueba para sale groups",
            "initial_session": {
                "location_name": "Sala Sale Groups",
                "location_address": "Calle Sale Groups 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "capacity": capacity,
            },
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    return response.json()


def create_ticket_type(client, promoter_token, event_id, name="General", stock=100, price=20):
    response = client.post(
        f"/events/{event_id}/ticket-types",
        json={
            "name": name,
            "description": f"Entrada {name}",
            "price": price,
            "currency": "EUR",
            "stock": stock,
            "max_per_purchase": 4,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    return response.json()


def test_promoter_can_create_sale_group(client, promoter_token):
    event = create_draft_event(client, promoter_token)

    response = client.post(
        f"/events/{event['id']}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "General Admission"
    assert data["strategy"] == "stock_cascade"
    assert data["event_id"] == event["id"]


def test_buyer_cannot_create_sale_group(client, buyer_token, promoter_token):
    event = create_draft_event(client, promoter_token)

    response = client.post(
        f"/events/{event['id']}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert response.status_code == 403, response.text


def test_cannot_create_sale_group_when_event_is_published(client, db, promoter_user, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado sin grupos nuevos",
        description="No se pueden crear grupos nuevos",
        location_name="Sala Publicada",
        location_address="Calle Publicada 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )

    response = client.post(
        f"/events/{event.id}/sale-groups",
        json={
            "name": "Grupo tardio",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()


def test_can_create_sale_group_for_unreviewed_session_in_published_event(
    client,
    db,
    promoter_user,
    promoter_token,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado con grupo en sesion nueva",
        description="Se prepara una sesion nueva",
        location_name="Sala Publicada",
        location_address="Calle Publicada 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    extra_session = EventSession(
        event_id=event.id,
        title="Sesion extra",
        location_name="Sala Extra",
        location_address="Calle Extra 123",
        starts_at=starts_at + timedelta(days=2),
        ends_at=starts_at + timedelta(days=2, hours=5),
        capacity=200,
        status="not_reviewed",
        display_order=2,
    )
    db.add(extra_session)
    db.commit()
    db.refresh(extra_session)

    response = client.post(
        f"/events/{event.id}/sale-groups",
        json={
            "name": "Grupo extra",
            "strategy": "stock_cascade",
            "is_active": True,
            "session_id": str(extra_session.id),
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["session_id"] == str(extra_session.id)


def test_list_sale_groups_by_event(client, promoter_token):
    event = create_draft_event(client, promoter_token)

    create_response = client.post(
        f"/events/{event['id']}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert create_response.status_code == 200, create_response.text

    list_response = client.get(
        f"/events/{event['id']}/sale-groups",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert list_response.status_code == 200, list_response.text

    data = list_response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "General Admission"


def test_cannot_delete_sale_group_when_event_is_published(client, db, promoter_user, promoter_token):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado con grupo",
        description="No se puede borrar grupo",
        location_name="Sala Publicada",
        location_address="Calle Publicada 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    group = TicketSaleGroup(
        event_id=event.id,
        session_id=event.sessions[0].id,
        name="Grupo existente",
        strategy="stock_cascade",
        status="draft",
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    response = client.delete(
        f"/events/{event.id}/sale-groups/{group.id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()


def test_promoter_can_assign_ticket_type_to_sale_group(client, promoter_token):
    event = create_draft_event(client, promoter_token)
    ticket_type = create_ticket_type(client, promoter_token, event["id"], name="Early Bird")
    group_response = client.post(
        f"/events/{event['id']}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert group_response.status_code == 200, group_response.text
    group = group_response.json()

    assign_response = client.post(
        f"/events/{event['id']}/sale-groups/ticket-types/{ticket_type['id']}/assign",
        json={
            "sale_group_id": group["id"],
            "sale_order": 1,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert assign_response.status_code == 200, assign_response.text
    data = assign_response.json()
    assert data["sale_group_id"] == group["id"]
    assert data["sale_order"] == 1
    assert data["name"] == "Early Bird"


def test_cannot_assign_ticket_type_to_group_from_other_event(client, promoter_token):
    event1 = create_draft_event(client, promoter_token, title="Evento 1")
    event2 = create_draft_event(client, promoter_token, title="Evento 2")

    ticket_type = create_ticket_type(client, promoter_token, event1["id"], name="Early Bird")

    group_response = client.post(
        f"/events/{event2['id']}/sale-groups",
        json={
            "name": "Grupo Evento 2",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert group_response.status_code == 200, group_response.text
    group = group_response.json()

    assign_response = client.post(
        f"/events/{event2['id']}/sale-groups/ticket-types/{ticket_type['id']}/assign",
        json={
            "sale_group_id": group["id"],
            "sale_order": 1,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert assign_response.status_code == 400, assign_response.text
    assert "mismo evento" in assign_response.json()["detail"].lower()


def test_cannot_repeat_sale_order_within_same_group(client, promoter_token):
    event = create_draft_event(client, promoter_token)

    ticket_type_1 = create_ticket_type(client, promoter_token, event["id"], name="Early Bird")
    ticket_type_2 = create_ticket_type(client, promoter_token, event["id"], name="General")

    group_response = client.post(
        f"/events/{event['id']}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert group_response.status_code == 200, group_response.text
    group = group_response.json()

    first_assign = client.post(
        f"/events/{event['id']}/sale-groups/ticket-types/{ticket_type_1['id']}/assign",
        json={
            "sale_group_id": group["id"],
            "sale_order": 1,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert first_assign.status_code == 200, first_assign.text

    second_assign = client.post(
        f"/events/{event['id']}/sale-groups/ticket-types/{ticket_type_2['id']}/assign",
        json={
            "sale_group_id": group["id"],
            "sale_order": 1,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert second_assign.status_code == 400, second_assign.text
    assert "orden" in second_assign.json()["detail"].lower()


def test_can_remove_ticket_type_from_sale_group(client, promoter_token):
    event = create_draft_event(client, promoter_token)
    ticket_type = create_ticket_type(client, promoter_token, event["id"], name="Early Bird")

    group_response = client.post(
        f"/events/{event['id']}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert group_response.status_code == 200, group_response.text
    group = group_response.json()

    assign_response = client.post(
        f"/events/{event['id']}/sale-groups/ticket-types/{ticket_type['id']}/assign",
        json={
            "sale_group_id": group["id"],
            "sale_order": 1,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert assign_response.status_code == 200, assign_response.text

    remove_response = client.post(
        f"/events/{event['id']}/sale-groups/ticket-types/{ticket_type['id']}/remove",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert remove_response.status_code == 200, remove_response.text
    data = remove_response.json()
    assert data["success"] is True
    assert data["ticket_type_id"] == ticket_type["id"]
    assert data["sale_order"] is None
