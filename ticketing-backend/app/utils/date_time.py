from datetime import datetime, timezone
from zoneinfo import ZoneInfo


DISPLAY_TIME_ZONE = ZoneInfo("Atlantic/Canary")


def to_display_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(DISPLAY_TIME_ZONE)


def format_display_datetime(
    value: datetime,
    date_format: str = "%d/%m/%Y %H:%M",
) -> str:
    return to_display_datetime(value).strftime(date_format)
