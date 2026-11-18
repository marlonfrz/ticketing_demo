from decimal import Decimal, ROUND_HALF_UP


def to_minor_units(value: Decimal | float | int | str) -> int:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(amount * 100)
