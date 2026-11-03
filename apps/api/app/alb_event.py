"""Parse a bounded ALB multi-value request without establishing caller trust.

This is a local preparation component, not a Lambda handler. The eventual
adapter must independently establish the trusted origin and session before
using a request to invoke the application.
"""

from dataclasses import dataclass, field
import re
from urllib.parse import unquote_plus, urlencode


@dataclass(frozen=True)
class AlbRequest:
    """Carry the request fields needed by a future reviewed ASGI adapter."""

    method: str
    path: str
    query_string: bytes
    headers: tuple[tuple[bytes, bytes], ...] = field(repr=False)


def parse_alb_read(event: object) -> AlbRequest:
    """Parse a bodyless GET in ALB multi-value format; reject malformed input.

    Values are not logged, authenticated, or treated as a trusted HTTPS origin.
    The caller must enforce route selection and authorization separately.
    """
    if not isinstance(event, dict) or event.get("httpMethod") != "GET":
        raise ValueError("Invalid ALB read request")
    path = event.get("path")
    headers = event.get("multiValueHeaders")
    query = event.get("multiValueQueryStringParameters")
    if query is None:
        query = {}
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or len(path) > 2048
        or not isinstance(headers, dict)
        or not isinstance(query, dict)
        or event.get("body") not in (None, "")
    ):
        raise ValueError("Invalid ALB read request")
    pairs: list[tuple[str, str]] = []
    clean_headers: list[tuple[bytes, bytes]] = []
    try:
        for key, values in query.items():
            if not isinstance(key, str) or not isinstance(values, list):
                raise ValueError
            for value in values:
                if not isinstance(value, str):
                    raise ValueError
                pairs.append((unquote_plus(key), unquote_plus(value)))
        for key, values in headers.items():
            if (
                not isinstance(key, str)
                or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", key)
                or not isinstance(values, list)
            ):
                raise ValueError
            for value in values:
                if not isinstance(value, str) or "\r" in value or "\n" in value:
                    raise ValueError
                clean_headers.append(
                    (key.lower().encode("ascii"), value.encode("latin-1"))
                )
        encoded_query = urlencode(pairs).encode("ascii")
    except ValueError, UnicodeError:
        raise ValueError("Invalid ALB read request") from None
    if (
        len(encoded_query) > 8192
        or sum(len(k) + len(v) for k, v in clean_headers) > 16384
    ):
        raise ValueError("Invalid ALB read request")
    return AlbRequest("GET", path, encoded_query, tuple(clean_headers))
