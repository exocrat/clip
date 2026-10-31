"""Private JSON-lines protocol v1, compatible with API Python3.14/helper3.13.

Only pipes between owned local processes carry these messages. No HTTP endpoint,
actor identity, DB target, raw error/trace or arbitrary model path is in a frame.
"""

import json
from typing import Any
from uuid import UUID

VERSION = 1
INPUT_BYTES = 64 * 1024
OUTPUT_BYTES = 2 * 1024 * 1024
WINDOW = 254
OVERLAP = 32
MAX_CHUNKS = 96


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys rather than letting later values replace bindings."""
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("Invalid helper frame")
        result[key] = value
    return result


def _constant(value: str) -> Any:
    """Reject JSON NaN/Infinity; no nonfinite model output is a valid frame."""
    raise ValueError("Invalid helper frame")


def decode_frame(raw: bytes, maximum: int) -> dict[str, Any]:
    """Require a bounded UTF-8 JSON object and one newline, with fixed diagnostics."""
    if not raw or len(raw) > maximum or not raw.endswith(b"\n"):
        raise ValueError("Invalid helper frame")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
    except Exception:
        raise ValueError("Invalid helper frame") from None
    if not isinstance(value, dict):
        raise ValueError("Invalid helper frame")
    return value


def encode_frame(value: dict[str, Any], maximum: int) -> bytes:
    """Serialize controlled fields without Unicode expansion or NaN coercion."""
    raw = (
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode()
        + b"\n"
    )
    if len(raw) > maximum:
        raise ValueError("Helper frame exceeds bound")
    return raw


def chunk_ranges(length: int) -> tuple[tuple[int, int], ...]:
    """Cover all content tokens with fixed overlap; overflow fails, never truncates."""
    if type(length) is not int or length < 0:
        raise ValueError("Invalid token count")
    if length == 0:
        return ((0, 0),)
    ranges = []
    start = 0
    while start < length:
        end = min(start + WINDOW, length)
        ranges.append((start, end))
        if len(ranges) > MAX_CHUNKS:
            raise ValueError("Token coverage exceeds bound")
        if end == length:
            break
        start += WINDOW - OVERLAP
    return tuple(ranges)


def validate_request(value: dict[str, Any], pipeline_id: str) -> None:
    """Check exact operation fields/IDs/text sizes before tokenization or inference."""
    texts: tuple[tuple[object, int], ...]
    operation = value.get("operation")
    fields = {"v", "request_id", "pipeline_id", "operation"}
    if operation == "query":
        fields.add("text")
        texts = ((value.get("text"), 120),)
    elif operation == "listing":
        fields.update(("title", "description"))
        texts = ((value.get("title"), 120), (value.get("description"), 5000))
    else:
        raise ValueError("Invalid helper request")
    if (
        set(value) != fields
        or type(value["v"]) is not int
        or value["v"] != VERSION
        or value["pipeline_id"] != pipeline_id
    ):
        raise ValueError("Invalid helper request")
    try:
        identifier = UUID(value["request_id"])
        valid = identifier.version == 4 and str(identifier) == value["request_id"]
    except Exception:
        valid = False
    if not valid or any(
        not isinstance(text, str) or not text.strip() or len(text) > bound
        for text, bound in texts
    ):
        raise ValueError("Invalid helper request")


def validate_ranges(value: object, expected: tuple[tuple[int, int], ...]) -> None:
    """Reject booleans/coercions as token offsets, not just numerically equal pairs."""
    if not isinstance(value, list) or len(value) != len(expected):
        raise ValueError("Invalid token coverage")
    for pair, correct in zip(value, expected):
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(type(item) is not int for item in pair)
            or tuple(pair) != correct
        ):
            raise ValueError("Invalid token coverage")
