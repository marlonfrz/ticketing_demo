from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.guest_checkout_access_service import has_valid_guest_checkout_access


def guest_order(*, token: str = "guest_secret", expires_at: datetime | None = None):
    return SimpleNamespace(
        buyer_id=None,
        customer=SimpleNamespace(
            guest_access_token=token,
            guest_access_expires_at=expires_at
            or datetime.now(timezone.utc) + timedelta(hours=1),
        ),
    )


def test_guest_checkout_access_accepts_only_matching_unexpired_token():
    now = datetime.now(timezone.utc)

    assert has_valid_guest_checkout_access(
        guest_order(expires_at=now + timedelta(minutes=1)),
        "guest_secret",
        now=now,
    )
    assert not has_valid_guest_checkout_access(
        guest_order(expires_at=now + timedelta(minutes=1)),
        "guest_wrong",
        now=now,
    )
    assert not has_valid_guest_checkout_access(
        guest_order(expires_at=now - timedelta(seconds=1)),
        "guest_secret",
        now=now,
    )


def test_guest_checkout_access_rejects_registered_orders_and_missing_expiry():
    registered_order = guest_order()
    registered_order.buyer_id = "buyer-id"
    missing_expiry_order = guest_order()
    missing_expiry_order.customer.guest_access_expires_at = None

    assert not has_valid_guest_checkout_access(registered_order, "guest_secret")
    assert not has_valid_guest_checkout_access(missing_expiry_order, "guest_secret")
    assert not has_valid_guest_checkout_access(guest_order(), None)
