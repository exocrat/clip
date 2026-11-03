"""Parse an untrusted Lambda ALB-shaped response without logging its contents.

This is a local protocol component, not an installed HTTP handler. The caller
must perform product correctness and real Lambda Web Adapter checks separately.
"""

import base64
import binascii
import json
import re
from dataclasses import dataclass, field

_HEADER = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_FORBIDDEN = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_MAX_BODY = 1048576


@dataclass(frozen=True)
class ReadResponse:
    """Store a bounded status and private response bytes for an eventual handler."""

    status: int
    headers: tuple[tuple[bytes, bytes], ...] = field(repr=False)
    body: bytes = field(repr=False)


def parse_read_response(payload: bytes) -> ReadResponse:
    """Validate an ALB multi-value envelope; preserve repeated safe headers."""
    try:
        if not isinstance(payload, bytes) or len(payload) > _MAX_BODY:
            raise ValueError
        event = json.loads(payload)
        if not isinstance(event, dict):
            raise ValueError
        status = event.get("statusCode")
        header_map = event.get("multiValueHeaders")
        body = event.get("body")
        encoded = event.get("isBase64Encoded")
        if (
            type(status) is not int
            or not 200 <= status <= 599
            or not isinstance(header_map, dict)
            or not isinstance(body, str)
            or type(encoded) is not bool
        ):
            raise ValueError
        result_headers = []
        total = 0
        for name, values in header_map.items():
            if not isinstance(name, str) or not _HEADER.fullmatch(name):
                raise ValueError
            lower = name.lower()
            if lower in _FORBIDDEN or not isinstance(values, list):
                raise ValueError
            for value in values:
                if not isinstance(value, str) or "\r" in value or "\n" in value:
                    raise ValueError
                # A future HTTP handler must calculate length from decoded bytes.
                if lower == "content-length":
                    continue
                pair = (lower.encode("ascii"), value.encode("latin-1"))
                total += len(pair[0]) + len(pair[1])
                result_headers.append(pair)
        if total > 16384:
            raise ValueError
        result_body = (
            base64.b64decode(body, validate=True) if encoded else body.encode("utf-8")
        )
        if len(result_body) > _MAX_BODY:
            raise ValueError
        return ReadResponse(status, tuple(result_headers), result_body)
    except ValueError, TypeError, UnicodeError, binascii.Error:
        raise ValueError("Invalid Lambda read response") from None
