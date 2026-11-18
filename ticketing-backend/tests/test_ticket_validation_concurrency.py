from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier

from app.models.event import Event
from app.models.event_session import EventSession
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_type import TicketType
from app.models.ticket_validation import TicketValidation
from app.models.user import User
from app.services.ticket_service import validate_ticket_by_qr
from conftest import TestingSessionLocal


def test_concurrent_ticket_redemption_only_accepts_one_scan(db, admin_user):
    now = datetime.now(timezone.utc)
    event = Event(
        promoter_id=admin_user.id,
        title="Evento con acceso concurrente",
        description="Prueba de doble escaneo",
        status="published",
    )
    db.add(event)
    db.flush()

    session = EventSession(
        event_id=event.id,
        location_name="Sala Acceso",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
        capacity=100,
        status="published",
        display_order=1,
    )
    db.add(session)
    db.flush()

    ticket_type = TicketType(
        event_id=event.id,
        session_id=session.id,
        name="General",
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
        ticket_code="TKT-CONCURRENT-001",
        qr_token="qr_concurrent_001",
        status="active",
        is_valid=True,
    )
    db.add(ticket)
    db.commit()
    ticket_id = ticket.id
    qr_token = ticket.qr_token
    admin_user_id = admin_user.id

    barrier = Barrier(2)

    def redeem():
        with TestingSessionLocal() as worker_db:
            validator = worker_db.query(User).filter(User.id == admin_user_id).first()
            barrier.wait()
            return validate_ticket_by_qr(worker_db, qr_token, validator)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: redeem(), range(2)))

    assert sorted(result["valid"] for result in results) == [False, True]
    validations = db.query(TicketValidation).filter(TicketValidation.ticket_id == ticket_id).all()
    assert sorted(validation.result for validation in validations) == ["already_used", "success"]
