"""Loopback operator page for the Search-owned vector integration checkpoint.

This is not an application feature, fake auth route or deployed page. It serves
only fixed tool HTML and one supplied public product photo; normal mutations
still go through the unchanged authenticated application APIs. Browser reports
are annotations, never proof of authorization or vector publication.
"""

import base64
import asyncio
import hashlib
import json
from pathlib import Path
import re
import ssl
from threading import Lock
from urllib.parse import urlsplit, parse_qs, unquote
from urllib.request import (
    Request,
    HTTPSHandler,
    HTTPRedirectHandler,
    ProxyHandler,
    build_opener,
)

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "/__next06_search_check__"
ORIGIN = "http://localhost:5173"
FIELDS = {"image_sha256_match", "image_decode_succeeded", "create_found", "edit_found"}
BUCKET_HOST = "clip-test-listings-images-ap-south-1-id01.s3.ap-south-1.amazonaws.com"
BUCKET_HOSTS = {
    BUCKET_HOST,
    "clip-test-listings-images-ap-south-1-id01.s3.amazonaws.com",
}


def signed_probe_key(url, prefix):
    """Validate the exact regional host/run key and short-lived v4S3 capability.

    Never resolve arbitrary hosts, follow redirects or accept another object's
    URL. Signature validity and authorization remain S3's responsibility.
    """
    if (
        not isinstance(url, str)
        or len(url) > 8192
        or not re.fullmatch(r"id01/next06-step3-[0-9a-f]{32}", prefix or "")
    ):
        raise ValueError("probe_transfer_scope")
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    key = unquote(parsed.path).lstrip("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname not in BUCKET_HOSTS
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.path != "/" + key
        or not re.fullmatch(
            re.escape(prefix)
            + r"/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            key,
        )
        or any(len(v) != 1 for v in query.values())
        or query.get("X-Amz-Algorithm") != ["AWS4-HMAC-SHA256"]
        or not re.fullmatch(r"[0-9a-f]{64}", query.get("X-Amz-Signature", [""])[0])
        or not query.get("X-Amz-Credential", [""])[0].endswith(
            "/ap-south-1/s3/aws4_request"
        )
    ):
        raise ValueError("probe_transfer_scope")
    try:
        if not 1 <= int(query.get("X-Amz-Expires", [""])[0]) <= 300:
            raise ValueError
    except ValueError, TypeError:
        raise ValueError("probe_transfer_expiry") from None
    return key


class NoRedirect(HTTPRedirectHandler):
    """Keep every byte transfer on the approved host; never replay elsewhere."""

    def redirect_request(self, *args, **kwargs):
        return None


def photo_input():
    """Read the exact existing source photo and verify approved inventory bytes."""
    inventory = json.loads(
        (ROOT / "data/evaluation/reference-image-inputs.json").read_text()
    )
    row = next(
        r
        for r in inventory["images"]
        if r["source_relative_path"] == "mobile_phone/android-smartphone.jpg"
    )
    content = (
        Path("/Users/mohitmahapatra/Desktop/clip-dataset-images")
        / row["source_relative_path"]
    ).read_bytes()
    if (
        len(content) != row["size_bytes"]
        or hashlib.sha256(content).hexdigest() != row["sha256"]
    ):
        raise ValueError("operator_photo_binding_changed")
    return content, row["sha256"]


class SearchOperatorPage:
    """Fixed static resources plus one bounded, same-origin observation report.

    The report cannot create accounts/listings, encode vectors, read DB rows or
    turn a failing SQL/HTTP witness into a passing result. It may request owned
    server shutdown so real worker/pool/native cleanup can finish promptly.
    """

    def __init__(self, app, report, photo, photo_sha256, stop, probe_prefix=None):
        if hashlib.sha256(photo).hexdigest() != photo_sha256:
            raise ValueError("operator_photo_hash_differs")
        self.app, self.report, self.photo, self.stop = app, report, photo, stop
        self.html = (
            (ROOT / "scripts/evaluation/reference_search_workflow.html")
            .read_text()
            .replace("__PHOTO_SHA256__", photo_sha256)
            .encode()
        )
        script = self.html.split(b"<script>", 1)[1].split(b"</script>", 1)[0]
        digest = base64.b64encode(hashlib.sha256(script).digest()).decode()
        self.csp = (
            "default-src 'none'; script-src 'sha256-" + digest + "'; "
            "style-src 'unsafe-inline'; connect-src 'self'; "
            "img-src blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        self.recorded = False
        self.probe_prefix, self.photo_sha256 = probe_prefix, photo_sha256
        self.transfer_attempts = {"upload": 0, "download": 0}
        self.upload_key = None
        self.transfer_lock = Lock()

    def transfer(self, kind, payload):
        """Send fixed photo/read identical bytes using a real API-issued URL.

        This test transport avoids new browser CORS permissions. No AWS secret
        or arbitrary request body enters it. OnePUT/twoGETs, no redirect/proxy/
        retry, bounded read; signed URLs stay memory-only.
        """
        with self.transfer_lock:
            return self._transfer_locked(kind, payload)

    def _transfer_locked(self, kind, payload):
        """Reserve one attempt and perform its bounded HTTPS operation serially."""
        if (
            kind not in self.transfer_attempts
            or not isinstance(payload, dict)
            or set(payload) != ({"url", "headers"} if kind == "upload" else {"url"})
        ):
            raise ValueError("probe_transfer_shape")
        key = signed_probe_key(payload.get("url"), self.probe_prefix)
        if self.transfer_attempts[kind] >= (1 if kind == "upload" else 2):
            raise ValueError("probe_transfer_limit")
        if kind == "upload":
            if payload["headers"] != {
                "Content-Type": "image/jpeg",
                "If-None-Match": "*",
            }:
                raise ValueError("probe_transfer_headers")
            self.upload_key = key
        elif key != self.upload_key:
            raise ValueError("probe_transfer_object")
        self.transfer_attempts[kind] += 1
        self.report["operator_s3_transfer_attempts"] = dict(self.transfer_attempts)
        opener = build_opener(
            ProxyHandler({}),
            HTTPSHandler(context=ssl.create_default_context()),
            NoRedirect(),
        )
        request = Request(
            payload["url"],
            data=self.photo if kind == "upload" else None,
            headers=payload.get("headers", {}),
            method="PUT" if kind == "upload" else "GET",
        )
        with opener.open(request, timeout=10) as response:
            if response.status not in {200, 204}:
                raise ValueError("probe_transfer_status")
            if kind == "upload":
                self.report["operator_s3_upload_verified"] = True
                return b""
            content = response.read(len(self.photo) + 1)
            if (
                len(content) != len(self.photo)
                or hashlib.sha256(content).hexdigest() != self.photo_sha256
            ):
                raise ValueError("probe_download_hash")
            self.report["operator_s3_downloads_byte_verified"] = (
                self.report.get("operator_s3_downloads_byte_verified", 0) + 1
            )
            return content

    async def __call__(self, scope, receive, send):
        """Never intercept normal API requests; no caller/session is supplied."""
        if scope["type"] != "http" or not scope["path"].startswith(PREFIX):
            return await self.app(scope, receive, send)

        async def respond(status, body=b"", media="text/plain"):
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [
                        (b"content-type", media.encode()),
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"content-security-policy", self.csp.encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        peer = scope.get("client")
        if not peer or peer[0] not in {"127.0.0.1", "::1"}:
            return await respond(403)
        self.report["operator_http_requests"] = (
            self.report.get("operator_http_requests", 0) + 1
        )
        if self.report["operator_http_requests"] > 20:
            return await respond(429)
        path, method = scope["path"], scope["method"]
        if method == "GET" and path == PREFIX:
            return await respond(200, self.html, "text/html; charset=utf-8")
        if method == "GET" and path == PREFIX + "/photo":
            return await respond(200, self.photo, "image/jpeg")
        kind = path.removeprefix(PREFIX + "/")
        if kind not in {"result", "upload", "download"} or method != "POST":
            return await respond(404)
        headers = dict(scope.get("headers", []))
        if (
            self.recorded
            or headers.get(b"origin") != ORIGIN.encode()
            or headers.get(b"x-clip-request") != b"1"
            or headers.get(b"content-type") != b"application/json"
        ):
            return await respond(403)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return await respond(400)
            body.extend(message.get("body", b""))
            if len(body) > (1024 if kind == "result" else 16384):
                return await respond(413)
            if not message.get("more_body"):
                break
        try:
            result = json.loads(body)
            if kind in {"upload", "download"}:
                if not self.probe_prefix:
                    return await respond(403)
                try:
                    content = await asyncio.to_thread(self.transfer, kind, result)
                except Exception:
                    return await respond(502)
                return await respond(
                    204 if kind == "upload" else 200,
                    content,
                    "image/jpeg" if kind == "download" else "text/plain",
                )
            if (
                not isinstance(result, dict)
                or set(result) != FIELDS
                or any(v is not True for v in result.values())
            ):
                raise ValueError
        except ValueError, TypeError:
            return await respond(400)
        self.recorded = True
        self.report["browser_observation"] = result
        self.report["browser_observation_is_annotation_only"] = True
        await respond(204)
        self.stop()
