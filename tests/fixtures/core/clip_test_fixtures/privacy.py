"""Bounded, allowlisted test diagnostics; never serialize arbitrary fixture values."""

from itertools import islice
import re
from types import MappingProxyType

from app.core.errors import ERRORS
from clip_test_fixtures.providers import Fail, Return, ScriptedTestProvider

REDACTED = "[REDACTED]"
_PRIVATE_FIELDS = {
    name.replace("_", ""): name
    for name in (
        "email",
        "phone",
        "upi_id",
        "contact",
        "contacts",
        "token",
        "secret",
        "otp",
        "private_key",
        "credentials",
        "authorization",
        "message",
        "plaintext",
        "ciphertext",
        "message_plaintext",
        "message_ciphertext",
        "body",
        "payload",
        "headers",
        "value",
    )
}
_CONTAINERS = {
    "data",
    "items",
    "details",
    "error",
    "result",
    "results",
    "metadata",
    "primary",
    "downstream",
}
_COUNTS = {"callcount": "call_count", "remaining": "remaining", "page": "page"}
_CODES = frozenset(spec.code for spec in ERRORS.values())


def redact_snapshot(value: object) -> object:
    """Return JSON-safe diagnostics with payloads/unknown keys masked.

    Preserve only reviewed status/codes, bounded counts, flags and container
    structure. Never call str/repr or inspect arbitrary object attributes. Use the
    result for diagnostic snapshots/messages, not as a substitute for behavioral
    assertions. Raw print/assert-local output remains the consuming test's concern.
    """
    return _redact(value, 0)


def _redact(value: object, depth: int) -> object:
    """Bound recursive containers and omit raw scalar values, including contact-like keys."""
    if depth >= 6:
        return REDACTED
    if type(value) is Return:
        return {"outcome": "return", "value": REDACTED}
    if type(value) is Fail:
        return {"outcome": "failure", "reason": value.reason}
    if type(value) is ScriptedTestProvider:
        return {
            "provider": "scripted",
            "call_count": value.call_count,
            "remaining": value.remaining,
        }
    if value is None:
        return None
    if type(value) in (list, tuple):
        result = [_redact(item, depth + 1) for item in value[:32]]
        if len(value) > 32:
            result.append(REDACTED)
        return result
    if type(value) not in (dict, MappingProxyType):
        return REDACTED

    result = {}
    for key, item in islice(value.items(), 32):
        if type(key) is not str or len(key) > 64:
            result[REDACTED] = REDACTED
            continue
        name = re.sub("[^a-z0-9]", "", key.lower())
        if name in _PRIVATE_FIELDS:
            result[_PRIVATE_FIELDS[name]] = REDACTED
        elif name in _CONTAINERS:
            result[name] = _redact(item, depth + 1)
        elif name == "status":
            result["status"] = (
                item if type(item) is int and 100 <= item <= 599 else REDACTED
            )
        elif name in _COUNTS:
            result[_COUNTS[name]] = (
                item if type(item) is int and 0 <= item <= 1_000_000 else REDACTED
            )
        elif name == "pagesize":
            result["page_size"] = (
                item if type(item) is int and item in (20, 50, 100) else REDACTED
            )
        elif name in ("valid", "hasnext"):
            result["has_next" if name == "hasnext" else "valid"] = (
                item if type(item) is bool else REDACTED
            )
        elif name == "code":
            result["code"] = item if type(item) is str and item in _CODES else REDACTED
        else:
            # Even unknown map keys can be private contacts or user-entered text.
            result[REDACTED] = REDACTED
    if len(value) > 32:
        result[REDACTED] = REDACTED
    return result
