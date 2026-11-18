from app.core.config import settings
from app.models.event import Event
from app.models.event_session import EventSession
from app.models.ticket_sale_group import TicketSaleGroup
from app.models.ticket_type import TicketType
from app.scripts.seed_demo import seed_demo_data


def test_demo_seed_requires_explicit_opt_in(db, admin_user, monkeypatch):
    admin_user.is_superadmin = True
    db.commit()
    monkeypatch.setattr(settings, "demo_data_enabled", False)

    assert seed_demo_data(db) == 0
    assert db.query(Event).count() == 0


def test_demo_seed_is_idempotent_and_creates_varied_sessions(db, admin_user, monkeypatch):
    admin_user.is_superadmin = True
    db.commit()
    monkeypatch.setattr(settings, "demo_data_enabled", True)

    assert seed_demo_data(db) == 6
    assert db.query(Event).count() == 6
    assert db.query(EventSession).count() == 21
    assert db.query(TicketSaleGroup).count() == 42
    assert db.query(TicketType).count() == 105
    assert sorted(len(event.sessions) for event in db.query(Event).all()) == [1, 2, 3, 4, 5, 6]
    assert all(event.status == "published" for event in db.query(Event).all())
    assert all(event.image_url.startswith("/demo-media/events/") for event in db.query(Event).all())

    for group in db.query(TicketSaleGroup).all():
        ticket_types = sorted(group.ticket_types, key=lambda ticket: ticket.sale_order)
        assert group.strategy == "stock_cascade"
        assert len(ticket_types) >= 2
        assert ticket_types[0].sale_unlocked_at is not None
        assert ticket_types[0].stock <= 2
        assert all(ticket.sale_unlocked_at is None for ticket in ticket_types[1:])
        assert [ticket.price for ticket in ticket_types] == sorted(
            ticket.price for ticket in ticket_types
        )

    assert seed_demo_data(db) == 0
    assert db.query(Event).count() == 6
    assert db.query(EventSession).count() == 21
    assert db.query(TicketSaleGroup).count() == 42
    assert db.query(TicketType).count() == 105
