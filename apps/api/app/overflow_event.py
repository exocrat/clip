"""Build an unwired ALB-shaped Lambda event for selected read requests.

The caller must establish trusted HTTPS/host and authorization separately.
Synthetic ALB-shaped events are not proof of Lambda Web Adapter compatibility.
"""

import json
import re
from collections import defaultdict
from collections.abc import Sequence

_HEADER = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_DETAIL = re.compile(r"/api/listings/[^/]+")
_TARGET_GROUP = re.compile(
    r"arn:aws:elasticloadbalancing:ap-south-1:335523638354:targetgroup/clip-exp03-[a-z0-9]{3,10}-lambda/[0-9a-f]{16}"
)
_HOP_HEADERS = {
    b"connection",
    b"keep-alive",
    b"proxy-authenticate",
    b"proxy-authorization",
    b"te",
    b"trailer",
    b"transfer-encoding",
    b"upgrade",
}


def build_read_event(
    method: str,
    path: str,
    raw_query: bytes,
    headers: Sequence[tuple[bytes, bytes]],
    target_group_arn: str,
) -> bytes:
    """Serialize one bodyless Listing GET; preserve repeated raw query values.

    Reject forwarded/hop-by-hop headers rather than trusting client metadata.
    The trusted caller must supply the correct ingress metadata in a future
    reviewed integration; this function never adds a claim of HTTPS itself.
    """
    if (
        method != "GET"
        or not isinstance(path, str)
        or not (path == "/api/listings" or _DETAIL.fullmatch(path))
        or not isinstance(raw_query, bytes)
        or len(raw_query) > 8192
        or not isinstance(target_group_arn, str)
        or _TARGET_GROUP.fullmatch(target_group_arn) is None
    ):
        raise ValueError("Invalid overflow read")
    query: dict[str, list[str]] = defaultdict(list)
    clean_headers: dict[str, list[str]] = defaultdict(list)
    try:
        if raw_query:
            last_key: bytes | None = None
            completed_keys: set[bytes] = set()
            for item in raw_query.split(b"&"):
                key, _, value = item.partition(b"=")
                # ALB groups values by key and cannot preserve interleaving.
                if key != last_key:
                    if key in completed_keys:
                        raise ValueError
                    if last_key is not None:
                        completed_keys.add(last_key)
                    last_key = key
                query[key.decode("ascii")].append(value.decode("ascii"))
        total = 0
        for key, value in headers:
            if not isinstance(key, bytes) or not isinstance(value, bytes):
                raise ValueError
            lower = key.lower()
            total += len(key) + len(value)
            if (
                _HEADER.fullmatch(key) is None
                or any(byte < 32 and byte != 9 or byte == 127 for byte in value)
                or lower in _HOP_HEADERS
                or lower.startswith(b"x-forwarded-")
                or lower == b"forwarded"
            ):
                raise ValueError
            clean_headers[lower.decode("ascii")].append(value.decode("latin-1"))
        if total > 16384:
            raise ValueError
        event = {
            "requestContext": {"elb": {"targetGroupArn": target_group_arn}},
            "httpMethod": "GET",
            "path": path,
            "multiValueHeaders": dict(clean_headers),
            "multiValueQueryStringParameters": dict(query),
            "body": None,
            "isBase64Encoded": False,
        }
        return json.dumps(event, ensure_ascii=True, separators=(",", ":")).encode()
    except TypeError, UnicodeError, ValueError:
        raise ValueError("Invalid overflow read") from None
