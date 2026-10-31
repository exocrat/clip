"""The local operator serves fixed assets, never auth or application mutations."""

import asyncio
import hashlib
import json

import pytest
from urllib.parse import urlencode

from scripts.evaluation import reference_search_operator as subject

from scripts.evaluation.reference_search_operator import (
    FIELDS,
    ORIGIN,
    PREFIX,
    SearchOperatorPage,
)


def invoke(
    path, method="GET", *, peer="127.0.0.1", origin=ORIGIN, body=b"", headers=True
):
    """Drive ASGI in memory; the downstream sentinel represents real app auth."""
    delegated, stopped, messages, report = [], [], [], {}

    async def app(scope, receive, send):
        delegated.append(scope)

    operator = SearchOperatorPage(
        app,
        report,
        b"synthetic-public-photo",
        hashlib.sha256(b"synthetic-public-photo").hexdigest(),
        lambda: stopped.append(True),
    )
    scope = {
        "type": "http",
        "path": path,
        "method": method,
        "client": (peer, 1234),
        "headers": [],
    }
    if headers:
        scope["headers"] = [
            (b"origin", origin.encode()),
            (b"x-clip-request", b"1"),
            (b"content-type", b"application/json"),
        ]

    async def receive():
        return {"type": "http.request", "body": body}

    async def send(message):
        messages.append(message)

    asyncio.run(operator(scope, receive, send))
    return messages, delegated, stopped, report


def test_normal_authenticated_api_passes_through_unchanged():
    messages, delegated, stopped, report = invoke("/listings", "POST")
    assert len(delegated) == 1
    assert delegated[0]["path"] == "/listings"
    assert not messages and not stopped and not report


def test_fixed_page_has_hashed_script_policy_and_no_store():
    messages, delegated, _, _ = invoke(PREFIX)
    headers = dict(messages[0]["headers"])
    assert messages[0]["status"] == 200
    assert headers[b"cache-control"] == b"no-store"
    assert b"script-src 'sha256-" in headers[b"content-security-policy"]
    assert b"__PHOTO_SHA256__" not in messages[1]["body"]
    assert not delegated


@pytest.mark.parametrize(
    "overrides,status",
    [
        ({"peer": "192.0.2.1"}, 403),
        ({"origin": "https://foreign.invalid"}, 403),
        ({"headers": False}, 403),
        ({"body": b"x" * 1025}, 413),
        ({"body": b'{"passed":true}'}, 400),
    ],
)
def test_observation_refuses_untrusted_or_oversized_input(overrides, status):
    messages, delegated, stopped, report = invoke(
        PREFIX + "/result", "POST", **overrides
    )
    assert messages[0]["status"] == status
    assert not delegated and not stopped
    assert not report.get("browser_observation")


def test_browser_observation_cannot_mark_workflow_passed():
    messages, _, stopped, report = invoke(
        PREFIX + "/result",
        "POST",
        body=json.dumps(dict.fromkeys(FIELDS, True)).encode(),
    )
    assert messages[0]["status"] == 204 and stopped == [True]
    assert report["browser_observation_is_annotation_only"] is True
    assert "workflow_evidence_complete" not in report


def test_fixed_photo_hash_must_match_before_serving():
    with pytest.raises(ValueError, match="photo_hash_differs"):
        SearchOperatorPage(None, {}, b"changed", "0" * 64, lambda: None)


def capability():
    """Unsigned synthetic URL shape; never an AWS credential or callable fixture."""
    prefix = "id01/next06-step3-" + "a" * 32
    key = prefix + "/10000000-0000-4000-8000-000000000001"
    query = urlencode(
        {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Signature": "0" * 64,
            "X-Amz-Credential": "synthetic/20261031/ap-south-1/s3/aws4_request",
            "X-Amz-Expires": "300",
        }
    )
    return prefix, key, "https://" + subject.BUCKET_HOST + "/" + key + "?" + query


@pytest.mark.parametrize(
    "change",
    ["http", "host", "port", "userinfo", "path", "region", "expires", "double-slash"],
)
def test_transfer_destination_expiry_and_key_are_fixed(change):
    prefix, key, url = capability()
    bad = {
        "http": url.replace("https:", "http:"),
        "host": url.replace(subject.BUCKET_HOST, "example.invalid"),
        "port": url.replace(subject.BUCKET_HOST, subject.BUCKET_HOST + ":444"),
        "userinfo": url.replace("https://", "https://user@"),
        "path": url.replace(prefix, "id01/next06-reference-42-v1"),
        "region": url.replace("ap-south-1%2Fs3", "us-east-1%2Fs3"),
        "expires": url.replace("Expires=300", "Expires=301"),
        "double-slash": url.replace("/id01/", "//id01/"),
    }[change]
    assert subject.signed_probe_key(url, prefix) == key
    with pytest.raises(ValueError):
        subject.signed_probe_key(bad, prefix)


def test_transfer_has_one_put_two_gets_and_hash_checks(monkeypatch):
    prefix, _, url = capability()
    photo = b"synthetic-public-photo"
    calls = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return photo

    class Opener:
        def open(self, request, **kwargs):
            calls.append(request.get_method())
            return Response()

    monkeypatch.setattr(subject, "build_opener", lambda *args: Opener())
    report = {}
    operator = SearchOperatorPage(
        None,
        report,
        photo,
        hashlib.sha256(photo).hexdigest(),
        lambda: None,
        probe_prefix=prefix,
    )
    with pytest.raises(ValueError, match="headers"):
        operator.transfer(
            "upload", {"url": url, "headers": {"Cookie": "must-not-forward"}}
        )
    assert calls == []
    operator.transfer(
        "upload",
        {"url": url, "headers": {"Content-Type": "image/jpeg", "If-None-Match": "*"}},
    )
    assert operator.transfer("download", {"url": url}) == photo
    assert operator.transfer("download", {"url": url}) == photo
    with pytest.raises(ValueError, match="limit"):
        operator.transfer("download", {"url": url})
    assert calls == ["PUT", "GET", "GET"]
    assert report["operator_s3_downloads_byte_verified"] == 2
    assert url not in json.dumps(report)


@pytest.mark.parametrize("operation", ["put_object", "get_object"])
def test_real_sdk_presign_shape_accepted_without_network(operation):
    import boto3
    from botocore.config import Config

    prefix, key, _ = capability()
    client = boto3.Session(
        aws_access_key_id="synthetic",
        aws_secret_access_key="synthetic-not-a-credential",
        region_name="ap-south-1",
    ).client(
        "s3",
        config=Config(signature_version="s3v4", ignore_configured_endpoint_urls=True),
    )
    try:
        params = {"Bucket": "clip-test-listings-images-ap-south-1-id01", "Key": key}
        if operation == "put_object":
            params |= {"ContentType": "image/jpeg", "IfNoneMatch": "*"}
        url = client.generate_presigned_url(operation, Params=params, ExpiresIn=300)
        assert subject.signed_probe_key(url, prefix) == key
    finally:
        client.close()
