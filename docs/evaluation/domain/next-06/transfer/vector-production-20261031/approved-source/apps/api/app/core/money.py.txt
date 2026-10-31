"""Exact integer-paise helpers for whole-rupee marketplace amounts."""

import re

_RUPEES = re.compile(r"-?[0-9]+", re.ASCII)

# User-facing listing prices and Wanted Request budgets stop at ₹1 crore.
# This generous marketplace cap keeps every amount exact across browser JSON,
# API validation and bigint storage while rejecting implausibly large typos.
MAX_LISTING_PRICE_PAISE = 1_000_000_000


def validate_paise(value: int) -> int:
    """Require integral whole rupees; domains separately enforce allowed ranges."""
    if type(value) is not int or value % 100:
        raise ValueError("Expected integer paise in whole rupees")
    return value


def rupees_to_paise(value: str) -> int:
    """Convert plain signed whole-rupee text exactly, without rounding or floats."""
    if not isinstance(value, str) or not _RUPEES.fullmatch(value):
        raise ValueError("Expected whole-rupee text")
    return int(value) * 100


def format_rupees(value: int) -> str:
    """Display exact whole rupees; this performs no currency or range conversion."""
    return f"₹{validate_paise(value) // 100}"
