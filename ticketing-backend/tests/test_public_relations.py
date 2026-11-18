from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.ticket_type import TicketType
from conftest import create_event_with_session


def _create_published_event_with_ticket(db, promoter_user):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento RRPP",
        description="Evento con RRPP",
        location_name="Sala RRPP",
        location_address="Calle RRPP 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="published",
    )
    session = event.sessions[0]
    session.status = "published"
    session.publish_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    session.tickets_publish_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    session.tickets_activated_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    ticket_type = TicketType(
        event_id=event.id,
        session_id=session.id,
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
    vip_ticket_type = TicketType(
        event_id=event.id,
        session_id=session.id,
        name="VIP",
        description="Entrada VIP",
        price=50,
        currency="EUR",
        stock=50,
        sold_count=0,
        max_per_purchase=4,
        is_active=True,
        status="published",
    )
    db.add_all([ticket_type, vip_ticket_type])
    db.commit()
    db.refresh(event)
    db.refresh(ticket_type)
    db.refresh(vip_ticket_type)
    return event, ticket_type, vip_ticket_type


def test_public_relations_registration_returns_sales_link(client, db, promoter_user):
    event, _, _ = _create_published_event_with_ticket(db, promoter_user)

    response = client.post(
        f"/events/{event.id}/public-relations/register",
        json={
            "full_name": "RRPP Test",
            "phone": "+34 600 111 222",
            "email": "rrpp@test.com",
            "social_handle": "@rrpp",
            "accept_privacy": True,
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["full_name"] == "RRPP Test"
    assert data["sales_code"]
    assert f"/events/{event.id}?rrpp=" in data["sales_url"]


def test_public_relations_are_unavailable_before_event_approval(
    client,
    db,
    promoter_user,
):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    event = create_event_with_session(
        db,
        promoter_user.id,
        title="Evento RRPP pendiente",
        description="Evento aun no aprobado",
        location_name="Sala pendiente",
        location_address="Calle pendiente 123",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=5),
        capacity=300,
        status="not_reviewed",
    )

    info_response = client.get(
        f"/events/{event.id}/public-relations/register-info",
    )
    register_response = client.post(
        f"/events/{event.id}/public-relations/register",
        json={
            "full_name": "RRPP demasiado pronto",
            "phone": "+34600111222",
            "email": None,
            "social_handle": None,
            "accept_privacy": True,
        },
    )

    assert info_response.status_code == 400, info_response.text
    assert register_response.status_code == 400, register_response.text
    assert "aprobado" in register_response.json()["detail"].lower()


def test_reservation_stores_public_relations_id(client, db, promoter_user):
    event, ticket_type, _ = _create_published_event_with_ticket(db, promoter_user)
    register_response = client.post(
        f"/events/{event.id}/public-relations/register",
        json={
            "full_name": "RRPP Venta",
            "phone": "+34600222333",
            "email": None,
            "social_handle": None,
            "accept_privacy": True,
        },
    )
    sales_code = register_response.json()["sales_code"]

    response = client.post(
        f"/events/{event.id}/reservations/with-order",
        json={
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
            "public_relations_code": sales_code,
            "customer": {
                "full_name": "Comprador Test",
                "email": "buyer-rrpp@test.com",
                "email_confirm": "buyer-rrpp@test.com",
                "phone": "+34600444555",
                "country_code": "ES",
                "accept_terms": True,
                "accept_privacy": True,
            },
        },
    )

    assert response.status_code == 200, response.text
    order = db.query(Order).filter(Order.id == response.json()["order_id"]).first()
    assert order.public_relations_id is not None


def test_promoter_can_see_public_relations_summary(client, db, promoter_user, promoter_token):
    event, general, vip = _create_published_event_with_ticket(db, promoter_user)
    register_response = client.post(
        f"/events/{event.id}/public-relations/register",
        json={
            "full_name": "RRPP Resumen",
            "phone": "+34600666777",
            "email": "resumen@test.com",
            "social_handle": "@resumen",
            "accept_privacy": True,
        },
    )
    rrpp_id = register_response.json()["id"]

    order = Order(
        event_id=event.id,
        session_id=event.sessions[0].id,
        public_relations_id=rrpp_id,
        status="paid",
        total_amount=Decimal("90.00"),
        currency="EUR",
    )
    db.add(order)
    db.flush()
    db.add_all(
        [
            OrderItem(
                order_id=order.id,
                ticket_type_id=general.id,
                session_id=event.sessions[0].id,
                quantity=2,
                unit_price=Decimal("20.00"),
                subtotal=Decimal("40.00"),
            ),
            OrderItem(
                order_id=order.id,
                ticket_type_id=vip.id,
                session_id=event.sessions[0].id,
                quantity=1,
                unit_price=Decimal("50.00"),
                subtotal=Decimal("50.00"),
            ),
        ]
    )
    db.commit()

    response = client.get(
        f"/events/{event.id}/public-relations",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data[0]["total_sold"] == 3
    assert {item["ticket_type_name"]: item["quantity"] for item in data[0]["by_ticket_type"]} == {
        "General": 2,
        "VIP": 1,
    }
    assert data[0]["by_session"][0]["quantity"] == 3
