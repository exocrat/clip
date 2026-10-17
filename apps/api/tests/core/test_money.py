"""Whole-rupee marketplace prices retain exact integer-paise units."""

from decimal import Decimal

import pytest

from app.core.money import format_rupees, rupees_to_paise, validate_paise


@pytest.mark.parametrize(
    ("rupees", "paise", "display"),
    [
        ("0", 0, "₹0"),
        ("125", 12500, "₹125"),
        ("-1", -100, "₹-1"),
        ("9007199254740993", 900719925474099300, "₹9007199254740993"),
    ],
)
def test_exact_conversion_and_display(rupees, paise, display):
    """Conversion is exact beyond float precision; domain ranges are separate."""
    assert rupees_to_paise(rupees) == paise
    assert validate_paise(paise) == paise
    assert format_rupees(paise) == display


@pytest.mark.parametrize(
    "value", [True, False, 12500.0, Decimal("12500"), "12500", None, 1, 12550, -1]
)
def test_invalid_paise_are_not_coerced_or_rounded(value):
    """Reject booleans, floats, nonintegers and fractional-rupee paise amounts."""
    with pytest.raises(ValueError):
        validate_paise(value)
    with pytest.raises(ValueError):
        format_rupees(value)


@pytest.mark.parametrize(
    "value",
    [
        None,
        125,
        True,
        "",
        "125.50",
        "125.00",
        "1e3",
        "₹125",
        "1,000",
        " 125",
        "125\n",
        "١٢٥",
    ],
)
def test_rupee_text_requires_plain_whole_digits(value):
    """User text must not invoke floating point, rounding or locale guessing."""
    with pytest.raises(ValueError):
        rupees_to_paise(value)
