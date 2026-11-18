from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

from app.models.order import Order
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.ticket_reservation import TicketReservation
from app.models.ticket_type import TicketType
from app.services.payment_service import confirm_demo_payment
from conftest import TestingSessionLocal, approve_event_for_test


def create_event(client, promoter_token, admin_token, title="Evento Pago Reserva", capacity=500, publish=True):
    starts_at = datetime.now(timezone.utc) + timedelta(days=10)
    ends_at = starts_at + timedelta(hours=5)

    response = client.post(
        "/events",
        json={
            "title": title,
            "description": "Evento para pago desde reserva",
            "initial_session": {
                "location_name": "Sala Pago Reserva",
                "location_address": "Calle Pago Reserva 123",
                "starts_at": starts_at.isoformat(),
                "ends_at": ends_at.isoformat(),
                "capacity": capacity,
            },
            "status": "draft",
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    event = response.json()

    approve_event_for_test(event["id"])

    return event


def create_ticket_type(client, promoter_token, event_id, name, stock, price):
    response = client.post(
        f"/events/{event_id}/ticket-types",
        json={
            "name": name,
            "description": f"Entrada {name}",
            "price": price,
            "currency": "EUR",
            "stock": stock,
            "max_per_purchase": 10,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    return response.json()


def create_sale_group(client, promoter_token, event_id):
    response = client.post(
        f"/events/{event_id}/sale-groups",
        json={
            "name": "General Admission",
            "strategy": "stock_cascade",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    return response.json()


def assign_ticket_type_to_group(client, promoter_token, event_id, ticket_type_id, sale_group_id, sale_order):
    response = client.post(
        f"/events/{event_id}/sale-groups/ticket-types/{ticket_type_id}/assign",
        json={
            "sale_group_id": sale_group_id,
            "sale_order": sale_order,
        },
        headers={"Authorization": f"Bearer {promoter_token}"},
    )

    assert response.status_code == 200, response.text
    return response.json()


def publish_session(client, admin_token, event):
    event_response = client.post(
        f"/events/{event['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert event_response.status_code == 200, event_response.text

    response = client.post(
        f"/event-sessions/{event['sessions'][0]['id']}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, response.text


def create_reservation_with_order(client, buyer_token, event_id, ticket_type_id, quantity):
    response = client.post(
        f"/events/{event_id}/reservations/with-order",
        json={"items": [{"ticket_type_id": ticket_type_id, "quantity": quantity}]},
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert response.status_code == 200, response.text
    return response.json()


def test_confirm_payment_from_reservations_creates_tickets_and_marks_order_paid(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])

    general = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)

    assign_ticket_type_to_group(client, promoter_token, event["id"], general["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    reservation_data = create_reservation_with_order(
        client=client,
        buyer_token=buyer_token,
        event_id=event["id"],
        ticket_type_id=general["id"],
        quantity=5,
    )

    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    assert payment is not None

    payment.provider_order_id = f"prov_order_{payment.id}"
    db.commit()
    db.refresh(payment)

    result = confirm_demo_payment(
        db=db,
        provider_order_id=payment.provider_order_id,
    )

    assert result["status"] == "succeeded"

    db.refresh(payment)
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    assert order is not None
    assert order.status == "paid"

    reservations = db.query(TicketReservation).filter(TicketReservation.order_id == order.id).all()
    assert len(reservations) == 1
    assert all(r.status == "converted" for r in reservations)

    tickets = db.query(Ticket).filter(Ticket.order_id == order.id).all()
    assert len(tickets) == 5

    general_model = db.query(TicketType).filter(TicketType.id == general["id"]).first()

    assert general_model.sold_count == 5


def test_confirm_demo_payment_fulfills_expired_reservation(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])

    tt1 = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], tt1["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    reservation_data = create_reservation_with_order(
        client=client,
        buyer_token=buyer_token,
        event_id=event["id"],
        ticket_type_id=tt1["id"],
        quantity=2,
    )

    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    assert payment is not None

    payment.provider_order_id = f"prov_order_{payment.id}"
    db.commit()
    db.refresh(payment)

    reservations = db.query(TicketReservation).filter(TicketReservation.order_id == payment.order_id).all()
    assert len(reservations) >= 1

    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    for reservation in reservations:
        reservation.expires_at = expired_time
    db.commit()

    result = confirm_demo_payment(
        db=db,
        provider_order_id=payment.provider_order_id,
    )

    db.refresh(payment)
    order = db.query(Order).filter(Order.id == payment.order_id).first()

    assert result["status"] == "succeeded"
    assert payment.status == "succeeded"
    assert order.status == "paid"

    refreshed_reservations = db.query(TicketReservation).filter(TicketReservation.order_id == order.id).all()
    assert all(r.status == "converted" for r in refreshed_reservations)

    tickets = db.query(Ticket).filter(Ticket.order_id == order.id).all()
    assert len(tickets) == 2

    tt1_model = db.query(TicketType).filter(TicketType.id == tt1["id"]).first()
    assert tt1_model.sold_count == 2


def test_unknown_demo_payment_session_does_not_issue_tickets(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(
        client,
        promoter_token,
        event["id"],
        "General",
        stock=10,
        price=19.50,
    )
    assign_ticket_type_to_group(
        client,
        promoter_token,
        event["id"],
        ticket_type["id"],
        group["id"],
        1,
    )
    publish_session(client, admin_token, event)
    reservation_data = create_reservation_with_order(
        client,
        buyer_token,
        event["id"],
        ticket_type["id"],
        1,
    )

    confirmation_response = client.post(
        "/payments/demo/confirm-session/demo_unknown",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )

    assert confirmation_response.status_code == 404, confirmation_response.text
    assert db.query(Ticket).filter(Ticket.order_id == reservation_data["order_id"]).count() == 0


def test_concurrent_payment_confirmation_is_idempotent_for_expired_reservations(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], ticket_type["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    reservation_data = create_reservation_with_order(
        client=client,
        buyer_token=buyer_token,
        event_id=event["id"],
        ticket_type_id=ticket_type["id"],
        quantity=2,
    )
    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    payment.provider_order_id = f"prov_concurrent_{payment.id}"
    provider_order_id = payment.provider_order_id
    order_id = payment.order_id
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    for reservation in db.query(TicketReservation).filter(TicketReservation.order_id == order_id):
        reservation.expires_at = expired_at
    db.commit()

    barrier = Barrier(2)

    def confirm(index: int):
        with TestingSessionLocal() as worker_db:
            barrier.wait()
            return confirm_demo_payment(
                db=worker_db,
                provider_order_id=provider_order_id,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(confirm, range(2)))

    db.expire_all()
    assert [result["status"] for result in results] == ["succeeded", "succeeded"]
    assert db.query(Ticket).filter(Ticket.order_id == order_id).count() == 2
    refreshed_ticket_type = db.query(TicketType).filter(TicketType.id == ticket_type["id"]).first()
    assert refreshed_ticket_type.sold_count == 2


def test_checkout_reuses_open_demo_session(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], ticket_type["id"], group["id"], 1)
    publish_session(client, admin_token, event)
    reservation_data = create_reservation_with_order(
        client=client,
        buyer_token=buyer_token,
        event_id=event["id"],
        ticket_type_id=ticket_type["id"],
        quantity=1,
    )

    headers = {"Authorization": f"Bearer {buyer_token}"}
    first = client.post(
        f"/payments/demo/checkout/{reservation_data['order_id']}",
        headers=headers,
    )
    second = client.post(
        f"/payments/demo/checkout/{reservation_data['order_id']}",
        headers=headers,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["checkout_session_id"].startswith("demo_")
    assert second.json()["checkout_session_id"] == first.json()["checkout_session_id"]
    assert "/payment/demo?session_id=" in first.json()["checkout_url"]


def test_confirm_demo_session_requires_logged_buyer_access(
    client,
    db,
    promoter_token,
    admin_token,
    buyer_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], ticket_type["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    reservation_data = create_reservation_with_order(
        client=client,
        buyer_token=buyer_token,
        event_id=event["id"],
        ticket_type_id=ticket_type["id"],
        quantity=1,
    )

    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    payment.provider_order_id = "demo_test_owner"
    db.commit()

    denied = client.post("/payments/demo/confirm-session/demo_test_owner")
    assert denied.status_code == 403

    confirmed = client.post(
        "/payments/demo/confirm-session/demo_test_owner",
        headers={"Authorization": f"Bearer {buyer_token}"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "succeeded"
    assert confirmed.json()["raw_response"] is None


def test_confirm_demo_session_accepts_guest_access_token(
    client,
    db,
    promoter_token,
    admin_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], ticket_type["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    response = client.post(
        f"/events/{event['id']}/reservations/with-order",
        json={
            "items": [{"ticket_type_id": ticket_type["id"], "quantity": 1}],
            "customer": {
                "full_name": "Invitado Test",
                "email": "guest@example.com",
                "email_confirm": "guest@example.com",
                "phone": "+34600111222",
                "country_code": "ES",
                "accept_terms": True,
                "accept_privacy": True,
            },
        },
    )
    assert response.status_code == 200, response.text
    reservation_data = response.json()

    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    payment.provider_order_id = "demo_test_guest"
    db.commit()

    denied = client.post(
        "/payments/demo/confirm-session/demo_test_guest",
        headers={"X-Guest-Token": "guest_wrong"},
    )
    assert denied.status_code == 403

    confirmed = client.post(
        "/payments/demo/confirm-session/demo_test_guest",
        headers={"X-Guest-Token": reservation_data["guest_access_token"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "succeeded"


def test_confirm_demo_session_rejects_guest_without_access_token(
    client,
    db,
    promoter_token,
    admin_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], ticket_type["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    response = client.post(
        f"/events/{event['id']}/reservations/with-order",
        json={
            "items": [{"ticket_type_id": ticket_type["id"], "quantity": 1}],
            "customer": {
                "full_name": "Invitado Sin Token",
                "email": "guest-no-token@example.com",
                "email_confirm": "guest-no-token@example.com",
                "phone": "+34600111223",
                "country_code": "ES",
                "accept_terms": True,
                "accept_privacy": True,
            },
        },
    )
    assert response.status_code == 200, response.text
    reservation_data = response.json()

    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    payment.provider_order_id = "demo_test_guest_without_token"
    db.commit()

    denied = client.post(
        "/payments/demo/confirm-session/demo_test_guest_without_token"
    )
    assert denied.status_code == 403


def test_guest_can_download_pdf_and_admin_can_search_by_ticket_code(
    client,
    db,
    promoter_token,
    admin_token,
):
    event = create_event(client, promoter_token, admin_token)
    group = create_sale_group(client, promoter_token, event["id"])
    ticket_type = create_ticket_type(client, promoter_token, event["id"], "General", stock=10, price=20)
    assign_ticket_type_to_group(client, promoter_token, event["id"], ticket_type["id"], group["id"], 1)
    publish_session(client, admin_token, event)

    response = client.post(
        f"/events/{event['id']}/reservations/with-order",
        json={
            "items": [{"ticket_type_id": ticket_type["id"], "quantity": 1}],
            "customer": {
                "full_name": "Invitado PDF",
                "email": "guest-pdf@example.com",
                "email_confirm": "guest-pdf@example.com",
                "phone": "+34600111224",
                "country_code": "ES",
                "accept_terms": True,
                "accept_privacy": True,
            },
        },
    )
    assert response.status_code == 200, response.text
    reservation_data = response.json()

    payment = db.query(Payment).filter(Payment.id == reservation_data["payment_id"]).first()
    payment.provider_order_id = "demo_test_guest_pdf"
    db.commit()

    result = confirm_demo_payment(
        db=db,
        provider_order_id="demo_test_guest_pdf",
    )
    assert result["status"] == "succeeded"

    pdf_response = client.get(
        f"/tickets/order/{reservation_data['order_id']}/pdf",
        headers={"X-Guest-Token": reservation_data["guest_access_token"]},
    )
    assert pdf_response.status_code == 200, pdf_response.text
    assert pdf_response.headers["content-type"] == "application/pdf"

    checkout_session_pdf_response = client.get(
        f"/tickets/order/{reservation_data['order_id']}/pdf",
        headers={"X-Checkout-Session-Id": "demo_test_guest_pdf"},
    )
    assert checkout_session_pdf_response.status_code == 403

    ticket = db.query(Ticket).filter(Ticket.order_id == reservation_data["order_id"]).first()
    promoter_tickets_response = client.get(
        f"/tickets/event/{event['id']}",
        headers={"Authorization": f"Bearer {promoter_token}"},
    )
    assert promoter_tickets_response.status_code == 200, promoter_tickets_response.text
    assert "qr_token" not in promoter_tickets_response.json()[0]

    support_response = client.get(
        "/admin/orders/support",
        params={"q": ticket.ticket_code},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert support_response.status_code == 200, support_response.text
    data = support_response.json()
    assert data[0]["id"] == reservation_data["order_id"]
    assert data[0]["tickets"][0]["ticket_code"] == ticket.ticket_code
