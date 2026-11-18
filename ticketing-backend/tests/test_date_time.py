from datetime import datetime, timezone

from app.utils.date_time import format_display_datetime, to_display_datetime


def test_formats_utc_datetimes_in_canary_summer_time():
    value = datetime(2026, 9, 20, 19, 0, tzinfo=timezone.utc)

    assert format_display_datetime(value) == "20/09/2026 20:00"
    assert to_display_datetime(value).hour == 20


def test_formats_naive_database_datetimes_as_utc():
    value = datetime(2026, 1, 20, 19, 0)

    assert format_display_datetime(value) == "20/01/2026 19:00"
