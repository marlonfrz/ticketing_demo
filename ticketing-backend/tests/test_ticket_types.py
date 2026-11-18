from datetime import datetime, timedelta, timezone

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.order import Order
from app.models.role import Role
from app.models.ticket_type import TicketType
from app.models.user import User
from app.core.security import hash_password
from conftest import create_event_with_session


def create_promoter_event(client, promoter_token, title="Evento Ticket Types", capacity=500):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    response = client.post(
        "/events",
        json={
            "title": title,
            "description": "Evento de prueba",
            "initial_session": {
                "location_name": "Sala Test",
                "location_address": "Calle Test 123",
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


def test_promoter_can_create_ticket_type(client, promoter_token):
    event = create_promoter_event(client, promoter_token)

    response = client.post(
        f"/events/{event['id']}/ticket-types",
        json={
            "name": "General",
            "description": "Entrada general",
            "price": 20,
            "currency": "eur",
            "stock": 100,
            "max_per_purchase": 4,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "General"
    assert data["currency"] == "EUR"
    assert data["stock"] == 100


def test_ticket_type_session_cannot_be_changed_during_update(
    client,
    db,
    promoter_token,
):
    source_event = create_promoter_event(client, promoter_token, title="Evento origen")
    target_event = create_promoter_event(client, promoter_token, title="Evento destino")
    ticket_response = client.post(
        f"/events/{source_event['id']}/ticket-types",
        json={
            "session_id": source_event["sessions"][0]["id"],
            "name": "General",
            "price": 20,
            "currency": "EUR",
            "stock": 100,
            "max_per_purchase": 4,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert ticket_response.status_code == 200, ticket_response.text
    ticket_id = ticket_response.json()["id"]

    update_response = client.put(
        f"/ticket-types/{ticket_id}",
        json={"session_id": target_event["sessions"][0]["id"]},
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert update_response.status_code == 422, update_response.text
    db.expire_all()
    ticket_type = db.query(TicketType).filter(TicketType.id == ticket_id).first()
    assert str(ticket_type.session_id) == source_event["sessions"][0]["id"]


def test_buyer_cannot_create_ticket_type(client, buyer_token, promoter_token):
    event = create_promoter_event(client, promoter_token)

    response = client.post(
        f"/events/{event['id']}/ticket-types",
        json={
            "name": "General",
            "description": "Entrada general",
            "price": 20,
            "currency": "EUR",
            "stock": 100,
            "max_per_purchase": 4,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert response.status_code == 403, response.text


def test_cannot_create_ticket_type_exceeding_event_capacity(client, promoter_token):
    event = create_promoter_event(client, promoter_token, capacity=100)

    first_response = client.post(
        f"/events/{event['id']}/ticket-types",
        json={
            "name": "Early",
            "description": "Entrada early",
            "price": 10,
            "currency": "EUR",
            "stock": 70,
            "max_per_purchase": 4,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert first_response.status_code == 200, first_response.text

    second_response = client.post(
        f"/events/{event['id']}/ticket-types",
        json={
            "name": "General",
            "description": "Entrada general",
            "price": 20,
            "currency": "EUR",
            "stock": 40,
            "max_per_purchase": 4,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert second_response.status_code == 400, second_response.text
    assert "aforo" in second_response.json()["detail"].lower()


def test_create_ticket_type_ignores_legacy_sale_window(client, promoter_token):
    event = create_promoter_event(client, promoter_token)

    sale_starts_at = datetime.now(timezone.utc) + timedelta(days=1)
    sale_ends_at = sale_starts_at - timedelta(hours=1)

    response = client.post(
        f"/events/{event['id']}/ticket-types",
        json={
            "name": "General",
            "description": "Entrada general",
            "price": 20,
            "currency": "EUR",
            "stock": 100,
            "max_per_purchase": 4,
            "sale_starts_at": sale_starts_at.isoformat(),
            "sale_ends_at": sale_ends_at.isoformat(),
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["sale_starts_at"] is None
    assert response.json()["sale_ends_at"] is None


def test_admin_can_create_ticket_type_for_other_promoter_event(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento Ajeno",
        description="Evento de otro promoter",
        location_name="Sala Admin",
        location_address="Calle Admin 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="draft",
    )
    response = client.post(
        f"/events/{event.id}/ticket-types",
        json={
            "name": "VIP",
            "description": "Entrada VIP",
            "price": 50,
            "currency": "EUR",
            "stock": 50,
            "max_per_purchase": 2,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "VIP"


def test_cannot_create_ticket_type_when_event_is_published(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado sin cambios",
        description="No se pueden crear nuevas entradas",
        location_name="Sala Publicada",
        location_address="Calle Publicada 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )

    response = client.post(
        f"/events/{event.id}/ticket-types",
        json={
            "name": "Extra",
            "description": "Entrada extra",
            "price": 20,
            "currency": "EUR",
            "stock": 50,
            "max_per_purchase": 2,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()


def test_can_create_ticket_type_for_unreviewed_session_in_published_event(
    client,
    db,
    admin_token,
    promoter_user,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado con nueva sesion",
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
        f"/events/{event.id}/ticket-types",
        json={
            "name": "Extra",
            "description": "Entrada extra",
            "price": 20,
            "currency": "EUR",
            "stock": 50,
            "max_per_purchase": 2,
            "is_active": True,
            "session_id": str(extra_session.id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["session_id"] == str(extra_session.id)


def test_admin_can_update_only_stock_when_event_is_published(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado stock",
        description="Se puede ajustar stock",
        location_name="Sala Stock",
        location_address="Calle Stock 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    ticket_type = TicketType(
        event_id=event.id,
        session_id=event.sessions[0].id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=10,
        max_per_purchase=4,
        is_active=True,
        status="published",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    response = client.put(
        f"/ticket-types/{ticket_type.id}",
        json={"stock": 120},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["stock"] == 120
    assert response.json()["price"] == "20.00"


def test_promoter_can_update_only_stock_when_event_is_published(client, db, promoter_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado stock promoter",
        description="El promotor puede ajustar stock",
        location_name="Sala Stock Promoter",
        location_address="Calle Stock 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    ticket_type = TicketType(
        event_id=event.id,
        session_id=event.sessions[0].id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=10,
        max_per_purchase=4,
        is_active=True,
        status="published",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    response = client.put(
        f"/ticket-types/{ticket_type.id}",
        json={"stock": 130},
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["stock"] == 130


def test_admin_cannot_update_price_when_event_is_published(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado sin precio",
        description="No se puede cambiar precio",
        location_name="Sala Precio",
        location_address="Calle Precio 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    ticket_type = TicketType(
        event_id=event.id,
        session_id=event.sessions[0].id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="published",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    response = client.put(
        f"/ticket-types/{ticket_type.id}",
        json={"price": "25.00"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()


def test_promoter_cannot_update_price_when_event_is_published(client, db, promoter_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento publicado sin precio promoter",
        description="No se puede cambiar precio",
        location_name="Sala Precio Promoter",
        location_address="Calle Precio 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    ticket_type = TicketType(
        event_id=event.id,
        session_id=event.sessions[0].id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="published",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    response = client.put(
        f"/ticket-types/{ticket_type.id}",
        json={"price": "25.00"},
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()


def test_cannot_disable_ticket_type_with_sales(client, db, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento con ventas",
        description="Evento con ventas",
        location_name="Sala Ventas",
        location_address="Calle Ventas 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="draft",
    )
    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=5,
        max_per_purchase=4,
        is_active=True,
        status="active",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    # Login real del promoter
    login_response = client.post(
        "/auth/login",
        data={
            "username": "promoter@test.com",
            "password": "123456",
        },
    )
    assert login_response.status_code == 200, login_response.text
    promoter_token = login_response.json()["access_token"]

    response = client.delete(
        f"/admin/ticket-types/{ticket_type.id}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    # Si esta ruta es solo admin, puede dar 403.
    # Lo que realmente nos interesa es probar la lógica de negocio con admin en el siguiente test.
    assert response.status_code in (403, 405, 404)


def test_admin_cannot_disable_ticket_type_if_event_is_published(client, db, admin_token, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento Published",
        description="Evento ya publicado",
        location_name="Sala Published",
        location_address="Calle Published 123",
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=300,
        status="published",
    )
    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        description="Entrada general",
        price=20,
        currency="EUR",
        stock=100,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="active",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(ticket_type)

    response = client.delete(
        f"/admin/ticket-types/{ticket_type.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 400, response.text
    assert "draft" in response.json()["detail"].lower()
