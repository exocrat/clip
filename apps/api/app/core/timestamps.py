"""Lossless microsecond UTC instant parsing and serialization."""

import re
from datetime import UTC, datetime

_WIRE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})",
    re.ASCII,
)


def as_utc(value: datetime) -> datetime:
    """Normalize an aware instant; never guess a timezone for naive values."""
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("Expected a timezone-aware instant")
    try:
        return value.astimezone(UTC)
    except ValueError, OverflowError:
        raise ValueError("Instant is outside the supported UTC range") from None


def parse_timestamp(value: str) -> datetime:
    """Accept explicit RFC 3339 offsets with at most microsecond precision."""
    if not isinstance(value, str) or not _WIRE.fullmatch(value):
        raise ValueError("Expected an offset timestamp with microsecond precision")
    # datetime accepts some non-RFC offsets; constrain offset hours/minutes here.
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError("Invalid timestamp offset")
    try:
        return as_utc(datetime.fromisoformat(value))
    except ValueError, OverflowError:
        raise ValueError("Invalid timestamp") from None


def format_timestamp(value: datetime) -> str:
    """Emit exactly six fractional digits and Z, preserving the instant."""
    return as_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")
