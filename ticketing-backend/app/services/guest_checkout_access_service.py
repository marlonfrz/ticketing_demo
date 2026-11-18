import secrets
from datetime import datetime, timezone

from app.models.order import Order


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def has_valid_guest_checkout_access(
    order: Order,
    guest_access_token: str | None,
    *,
    now: datetime | None = None,
) -> bool:
    if order.buyer_id is not None or order.customer is None or not guest_access_token:
        return False

    expires_at = order.customer.guest_access_expires_at
    if expires_at is None:
        return False

    current_time = now or datetime.now(timezone.utc)
    if _as_utc(expires_at) <= _as_utc(current_time):
        return False

    return secrets.compare_digest(order.customer.guest_access_token, guest_access_token)
