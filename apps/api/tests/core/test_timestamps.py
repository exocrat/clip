"""UTC normalization, precision preservation, and timezone input boundaries."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.timestamps import as_utc, format_timestamp, parse_timestamp


@pytest.mark.parametrize(
    ("wire", "expected"),
    [
        ("2026-10-17T12:00:00+05:30", "2026-10-17T06:30:00.000000Z"),
        ("2026-10-16T23:30:00-07:00", "2026-10-17T06:30:00.000000Z"),
        ("2026-10-17T06:30:00.1Z", "2026-10-17T06:30:00.100000Z"),
        ("2024-02-29T23:59:59.123456Z", "2024-02-29T23:59:59.123456Z"),
        ("2026-10-17T06:30:00+00:00", "2026-10-17T06:30:00.000000Z"),
    ],
)
def test_offset_input_normalizes_and_round_trips(wire, expected):
    """Equivalent instants must share one lossless microsecond UTC output."""
    instant = parse_timestamp(wire)
    assert instant.tzinfo is UTC
    assert format_timestamp(instant) == expected
    assert parse_timestamp(expected) == instant


def test_internal_aware_datetime_normalizes_without_changing_instant():
    """Internal offset-aware values must use the same serialization boundary."""
    instant = datetime(
        2026, 10, 17, 12, 0, 0, 999999, tzinfo=timezone(timedelta(hours=5, minutes=30))
    )
    assert as_utc(instant) == instant
    assert format_timestamp(instant) == "2026-10-17T06:30:00.999999Z"


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        "",
        "2026-10-17",
        "2026-10-17T06:30:00",
        "2026-10-17 06:30:00Z",
        "2026-10-17T06:30:00.1234567Z",
        "2026-02-29T00:00:00Z",
        "2026-10-17T24:00:00Z",
        "2026-10-17T00:00:00+24:00",
        "2026-10-17T00:00:00+00:60",
        "0001-01-01T00:00:00+01:00",
        "9999-12-31T23:59:59-01:00",
    ],
)
def test_invalid_or_lossy_timestamp_inputs_fail(value):
    """Reject ambiguous, impossible, overprecision, and out-of-UTC-range inputs."""
    with pytest.raises(ValueError):
        parse_timestamp(value)


@pytest.mark.parametrize(
    "value", [datetime(2026, 10, 17), "2026-10-17T00:00:00Z", None]
)
def test_internal_boundary_never_assumes_timezone(value):
    """Internal callers must provide an aware datetime, not a naive/string value."""
    with pytest.raises(ValueError):
        format_timestamp(value)
