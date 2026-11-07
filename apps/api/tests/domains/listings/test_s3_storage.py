"""Check the S3 adapter with an in-process client double and no AWS calls."""

from __future__ import annotations

import asyncio
from io import BytesIO

from PIL import Image
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from app.domains.listings.s3_storage import (
    MAX_IMAGE_SIZE_BYTES,
    S3ListingsImageStorage,
)
from app.domains.listings.service import InvalidImageContent, StoredImageMetadata


def _png() -> bytes:
    """Build a real small image for successful structure validation."""
    output = BytesIO()
    Image.new("RGB", (2, 2)).save(output, format="PNG")
    return output.getvalue()


PNG = _png()


class _Body:
    """Record that object reads are bounded and the response is always closed."""

    def __init__(self, content: bytes) -> None:
        self.content = content
        self.read_limits: list[int] = []
        self.closed = False

    def read(self, size: int) -> bytes:
        self.read_limits.append(size)
        return self.content[:size]

    def close(self) -> None:
        self.closed = True


class _S3Client:
    def __init__(self) -> None:
        self.signed: list[tuple[str, dict, int, str]] = []
        self.get_response: dict | Exception | None = None
        self.deleted: list[dict] = []

    def generate_presigned_url(self, operation, *, Params, ExpiresIn, HttpMethod):
        self.signed.append((operation, Params, ExpiresIn, HttpMethod))
        return "https://signed.invalid/private-token"

    def get_object(self, **kwargs):
        if isinstance(self.get_response, Exception):
            raise self.get_response
        return self.get_response

    def delete_object(self, **kwargs):
        self.deleted.append(kwargs)


def _storage(monkeypatch):
    client = _S3Client()
    calls: list[tuple[str, str, object]] = []

    def make_client(service, *, region_name, config):
        calls.append((service, region_name, config))
        return client

    monkeypatch.setattr("app.domains.listings.s3_storage.boto3.client", make_client)
    storage = S3ListingsImageStorage("private-bucket", "ap-south-1", "test/run-1")
    return storage, client, calls


def test_s3_adapter_uses_only_the_configured_private_bucket_and_prefix(monkeypatch):
    storage, _, calls = _storage(monkeypatch)
    upload_id = uuid4()

    assert storage.object_key_for(upload_id) == f"test/run-1/{upload_id}"
    assert calls[0][0:2] == ("s3", "ap-south-1")


def test_upload_url_is_create_only_and_never_lives_over_five_minutes(monkeypatch):
    storage, client, _ = _storage(monkeypatch)
    expires = datetime.now(UTC) + timedelta(minutes=20)

    url = asyncio.run(
        storage.create_upload_url("test/run-1/key", "image/png", expires, 123)
    )

    assert url == "https://signed.invalid/private-token"
    operation, params, seconds, method = client.signed[-1]
    assert operation == "put_object"
    assert params == {
        "Bucket": "private-bucket",
        "Key": "test/run-1/key",
        "ContentType": "image/png",
        "ContentLength": 123,
        "IfNoneMatch": "*",
    }
    assert seconds == 300
    assert method == "PUT"


def test_download_url_is_private_cache_controlled_and_short_lived(monkeypatch):
    storage, client, _ = _storage(monkeypatch)
    expires = datetime.now(UTC) + timedelta(minutes=5)

    asyncio.run(storage.create_download_url("test/run-1/key", expires))

    operation, params, seconds, method = client.signed[-1]
    assert operation == "get_object"
    assert params == {
        "Bucket": "private-bucket",
        "Key": "test/run-1/key",
        "ResponseCacheControl": "private, no-store",
    }
    assert 1 <= seconds <= 300
    assert method == "GET"


def test_inspection_reads_only_the_bounded_body_and_closes_it(monkeypatch):
    storage, client, _ = _storage(monkeypatch)
    body = _Body(PNG)
    client.get_response = {
        "Body": body,
        "ContentLength": len(PNG),
        "ContentType": "image/png",
    }

    metadata = asyncio.run(storage.inspect_object("test/run-1/key"))

    assert metadata == StoredImageMetadata(media_type="image/png", size_bytes=len(PNG))
    assert body.read_limits == [MAX_IMAGE_SIZE_BYTES + 1]
    assert body.closed


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        ({"Body": None, "ContentLength": 1, "ContentType": "image/png"}, "no-body"),
        ({"Body": _Body(PNG), "ContentLength": 0, "ContentType": "image/png"}, "empty"),
        (
            {
                "Body": _Body(PNG),
                "ContentLength": MAX_IMAGE_SIZE_BYTES + 1,
                "ContentType": "image/png",
            },
            "too-large",
        ),
        (
            {
                "Body": _Body(b"not-an-image"),
                "ContentLength": 12,
                "ContentType": "image/png",
            },
            "invalid-signature",
        ),
        (
            {
                "Body": _Body(PNG),
                "ContentLength": len(PNG),
                "ContentType": "image/jpeg",
            },
            "declared-type-mismatch",
        ),
        (
            {
                "Body": _Body(PNG[:-1]),
                "ContentLength": len(PNG),
                "ContentType": "image/png",
            },
            "truncated-body",
        ),
    ],
    ids=[
        "no-body",
        "empty",
        "too-large",
        "invalid-signature",
        "declared-type-mismatch",
        "truncated-body",
    ],
)
def test_invalid_s3_objects_are_rejected_and_response_bodies_are_closed(
    monkeypatch, response, reason
):
    del reason
    storage, client, _ = _storage(monkeypatch)
    client.get_response = response

    with pytest.raises(InvalidImageContent):
        asyncio.run(storage.inspect_object("test/run-1/key"))

    body = response.get("Body")
    if body is not None:
        assert body.closed


def test_missing_s3_object_is_reported_as_absent(monkeypatch):
    storage, client, _ = _storage(monkeypatch)
    client.get_response = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "private detail"}}, "GetObject"
    )

    assert asyncio.run(storage.inspect_object("test/run-1/key")) is None


def test_other_s3_inspection_errors_propagate_for_safe_service_mapping(monkeypatch):
    storage, client, _ = _storage(monkeypatch)
    client.get_response = ClientError(
        {"Error": {"Code": "SlowDown", "Message": "private detail"}}, "GetObject"
    )

    with pytest.raises(ClientError):
        asyncio.run(storage.inspect_object("test/run-1/key"))


def test_delete_targets_only_the_configured_bucket_key(monkeypatch):
    storage, client, _ = _storage(monkeypatch)

    asyncio.run(storage.delete_object("test/run-1/key"))

    assert client.deleted == [{"Bucket": "private-bucket", "Key": "test/run-1/key"}]


@pytest.mark.parametrize("bad_prefix", ["", "../unsafe", "nested/../unsafe"])
def test_adapter_rejects_missing_or_traversing_key_prefix(monkeypatch, bad_prefix):
    with pytest.raises(ValueError, match="configuration is invalid"):
        S3ListingsImageStorage("private-bucket", "ap-south-1", bad_prefix)


@pytest.mark.parametrize("content", [b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n0000IHDR"])
def test_inspection_rejects_fake_image_headers(monkeypatch, content):
    storage, client, _ = _storage(monkeypatch)
    client.get_response = {
        "Body": _Body(content),
        "ContentLength": len(content),
        "ContentType": "image/jpeg" if content.startswith(b"\xff") else "image/png",
    }
    with pytest.raises(InvalidImageContent):
        asyncio.run(storage.inspect_object("test/run-1/key"))


def test_inspection_rejects_excessive_dimensions(monkeypatch):
    import app.domains.listings.s3_storage as storage_module

    monkeypatch.setattr(storage_module, "MAX_IMAGE_PIXELS", 3)
    storage, client, _ = _storage(monkeypatch)
    client.get_response = {
        "Body": _Body(PNG),
        "ContentLength": len(PNG),
        "ContentType": "image/png",
    }
    with pytest.raises(InvalidImageContent):
        asyncio.run(storage.inspect_object("test/run-1/key"))
