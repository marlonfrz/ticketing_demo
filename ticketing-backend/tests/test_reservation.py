from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.order import Order
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_type import TicketType
from app.services.ticket_reservation_service import sync_sale_group_unlocks
from conftest import TestingSessionLocal, approve_event_for_test


def create_event(client, promoter_token, admin_token, title="Evento Reserva", capacity=500, publish=True):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    response = client.post(
        "/events",
        json={
            "title": title,
            "description": "Evento para reservas",
            "initial_session": {
                "location_name": "Sala Reservas",
                "location_address": "Calle Reservas 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": (starts_at + timedelta(hours=5)).isoformat(),
                "capacity": capacity,
            },
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert response.status_code == 200, response.text
    event = response.json()

    approve_event_for_test(event["id"])

    return event


def create_ticket_type(client, promoter_token, event_id, name, stock, price, max_per_purchase=10):
    response = client.post(
        f"/events/{event_id}/ticket-types",
        json={
            "name": name,
            "description": f"Entrada {name}",
            "price": price,
            "currency": "EUR",
            "stock": stock,
            "max_per_purchase": max_per_purchase,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_sale_group(client, promoter_token, event_id):
    response = client.post(
        f"/events/{event_id}/sale-groups",
        json={"name": "General Admission", "strategy": "stock_cascade", "is_active": True},
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def assign_ticket_type(client, promoter_token, event_id, ticket_type_id, group_id, order):
    response = client.post(
        f"/events/{event_id}/sale-groups/ticket-types/{ticket_type_id}/assign",
        json={"sale_group_id": group_id, "sale_order": order},
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert response.status_code == 200, response.text


def publish_session(client, admin_token, event):
    session_id = event["sessions"][0]["id"]
    event_response = client.post(
        f"/events/{event['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert event_response.status_code == 200, event_response.text

    response = client.post(
        f"/event-sessions/{session_id}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text


def test_sale_group_sync_does_not_commit_caller_transaction(
    client,
    db,
    promoter_token,
    admin_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type(client, promoter_token, event["id"], ticket["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    ticket_type = db.query(TicketType).filter(TicketType.id == ticket["id"]).first()
    ticket_type.sale_unlocked_at = None
    db.commit()

    with TestingSessionLocal() as transaction_db:
        changed = sync_sale_group_unlocks(transaction_db, group["id"])
        assert changed is True

        with TestingSessionLocal() as observer_db:
            observed = observer_db.query(TicketType).filter(TicketType.id == ticket["id"]).first()
            assert observed.sale_unlocked_at is None

        transaction_db.rollback()


def reserve(client, event_id, items, token=None, customer=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(
        f"/events/{event_id}/reservations/with-order",
        json={"items": items, "customer": customer},
        headers=headers,
    )


def guest_customer(email):
    return {
        "full_name": "Invitado Test",
        "email": email,
        "email_confirm": email,
        "phone": "+34600111222",
        "country_code": "ES",
        "accept_terms": True,
        "accept_privacy": True,
    }


def test_can_create_simple_reservation_with_order(client, db, promoter_token, admin_token, buyer_token):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", 10, 20)
    assign_ticket_type(client, promoter_token, event["id"], ticket["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    response = reserve(client, event["id"], [{"ticket_type_id": ticket["id"], "quantity": 2}], buyer_token)
    assert response.status_code == 200, response.text
    data = response.json()
    assert Decimal(data["total_amount"]) == Decimal("40.00")
    assert data["items"][0]["quantity"] == 2
    assert db.query(Order).filter(Order.id == data["order_id"]).first().status == "pending"
    assert db.query(Payment).filter(Payment.id == data["payment_id"]).first().status == "pending"


def test_stock_cascade_splits_reservation_and_issues_exact_requested_quantity(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    early = create_ticket_type(client, promoter_token, event["id"], "Early", 1, 15)
    general = create_ticket_type(client, promoter_token, event["id"], "General", 5, 20)
    assign_ticket_type(client, promoter_token, event["id"], early["id"], group["id"], 1)
    assign_ticket_type(client, promoter_token, event["id"], general["id"], group["id"], 2)
    publish_session(client, admin_token, event)

    options_response = client.get(
        f"/events/{event['id']}/sales-options",
        params={"session_id": event["sessions"][0]["id"]},
    )
    assert options_response.status_code == 200, options_response.text
    group_option = next(
        item
        for item in options_response.json()["items"]
        if item["type"] == "sale_group"
    )
    early_option, general_option = group_option["ticket_types"]
    assert early_option["max_selectable_quantity"] == 6
    assert early_option["available_quantity"] == 1
    assert general_option["max_selectable_quantity"] == 0
    assert general_option["available_quantity"] == 5

    reservation_response = reserve(
        client,
        event["id"],
        [{"ticket_type_id": early["id"], "quantity": 3}],
        buyer_token,
    )
    assert reservation_response.status_code == 200, reservation_response.text
    reservation = reservation_response.json()
    assert Decimal(reservation["tickets_subtotal"]) == Decimal("55.00")
    assert [
        (item["ticket_type_name"], item["quantity"])
        for item in reservation["items"]
    ] == [("Early", 1), ("General", 2)]

    checkout_response = client.post(
        f"/payments/demo/checkout/{reservation['order_id']}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert checkout_response.status_code == 200, checkout_response.text
    session_id = checkout_response.json()["checkout_session_id"]

    confirmation_response = client.post(
        f"/payments/demo/confirm-session/{session_id}",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert confirmation_response.status_code == 200, confirmation_response.text

    issued_tickets = db.query(Ticket).filter(Ticket.order_id == reservation["order_id"]).all()
    assert len(issued_tickets) == 3
    assert sum(str(ticket.ticket_type_id) == early["id"] for ticket in issued_tickets) == 1
    assert sum(str(ticket.ticket_type_id) == general["id"] for ticket in issued_tickets) == 2


def test_guest_reservation_requires_customer_data(client, promoter_token, admin_token):
    event = create_event(client, promoter_token, admin_token)
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", 10, 20)
    publish_session(client, admin_token, event)

    response = reserve(client, event["id"], [{"ticket_type_id": ticket["id"], "quantity": 1}])

    assert response.status_code == 400, response.text
    assert "datos de contacto" in response.json()["detail"].lower()


def test_cannot_buy_two_tramos_from_same_group(client, promoter_token, admin_token, buyer_token):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    early = create_ticket_type(client, promoter_token, event["id"], "Early", 2, 15)
    general = create_ticket_type(client, promoter_token, event["id"], "General", 10, 20)
    assign_ticket_type(client, promoter_token, event["id"], early["id"], group["id"], 1)
    assign_ticket_type(client, promoter_token, event["id"], general["id"], group["id"], 2)
    publish_session(client, admin_token, event)

    response = reserve(
        client,
        event["id"],
        [
            {"ticket_type_id": early["id"], "quantity": 1},
            {"ticket_type_id": general["id"], "quantity": 1},
        ],
        buyer_token,
    )
    assert response.status_code == 400, response.text
    detail = response.json()["detail"].lower()
    assert "disponible" in detail or "un tipo de entrada por cada grupo" in detail


def test_reservation_fails_if_ticket_has_not_enough_stock(client, promoter_token, admin_token, buyer_token):
    event = create_event(client, promoter_token, admin_token)
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", 3, 20)
    publish_session(client, admin_token, event)

    response = reserve(client, event["id"], [{"ticket_type_id": ticket["id"], "quantity": 5}], buyer_token)
    assert response.status_code == 400, response.text
    assert "disponibles" in response.json()["detail"].lower()


def test_active_reservations_reduce_real_available_stock(client, db, promoter_token, admin_token):
    event = create_event(client, promoter_token, admin_token)
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", 2, 20)
    publish_session(client, admin_token, event)

    first = reserve(
        client,
        event["id"],
        [{"ticket_type_id": ticket["id"], "quantity": 2}],
        customer=guest_customer("guest-one@test.com"),
    )
    assert first.status_code == 200, first.text

    second = reserve(
        client,
        event["id"],
        [{"ticket_type_id": ticket["id"], "quantity": 1}],
        customer=guest_customer("guest-two@test.com"),
    )
    assert second.status_code == 400, second.text
    assert db.query(TicketReservation).filter(TicketReservation.status == "active").count() == 1


def test_reservation_fails_if_event_is_not_published(client, promoter_token, admin_token, buyer_token):
    event = create_event(client, promoter_token, admin_token, publish=False)
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", 10, 20)

    response = reserve(client, event["id"], [{"ticket_type_id": ticket["id"], "quantity": 1}], buyer_token)
    assert response.status_code == 400, response.text
    assert "eventos publicados" in response.json()["detail"].lower()


def test_reservation_enforces_max_per_purchase(client, promoter_token, admin_token, buyer_token):
    event = create_event(client, promoter_token, admin_token)
    ticket = create_ticket_type(client, promoter_token, event["id"], "General", 10, 20, max_per_purchase=3)
    publish_session(client, admin_token, event)

    response = reserve(client, event["id"], [{"ticket_type_id": ticket["id"], "quantity": 4}], buyer_token)
    assert response.status_code == 400, response.text
    assert "hasta 3" in response.json()["detail"].lower()
