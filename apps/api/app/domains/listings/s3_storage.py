"""Private S3 adapter for owner-authorized Listings image storage."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from math import floor
from typing import Any, Literal, cast

import boto3  # type: ignore[import-untyped]
from botocore.config import Config as BotoConfig  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.contracts.domain_types import ImageId
from app.domains.listings.service import InvalidImageContent, StoredImageMetadata

MAX_IMAGE_SIZE_BYTES = 10_485_760
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class S3ListingsImageStorage:
    """Sign uploads and inspect or delete objects in the private image bucket."""

    def __init__(self, bucket: str, region: str, key_prefix: str) -> None:
        """Bind an explicitly configured bucket and run-scoped key prefix."""
        prefix = key_prefix.strip("/")
        if not bucket or not region or not prefix or ".." in prefix.split("/"):
            raise ValueError("Listings S3 storage configuration is invalid")
        self._bucket = bucket
        self._prefix = prefix
        self._client: Any = boto3.client(
            "s3",
            region_name=region,
            config=BotoConfig(signature_version="s3v4"),
        )

    def object_key_for(self, upload_id: ImageId) -> str:
        """Keep object names private and deterministic from the server ID."""
        return f"{self._prefix}/{upload_id}"

    async def create_upload_url(
        self, object_key: str, media_type: str, expires_at: datetime
    ) -> str:
        """Presign a PUT requiring its declared type and an absent destination."""
        remaining = floor((expires_at - datetime.now(UTC)).total_seconds())
        if remaining < 1:
            raise ValueError("Upload intent has expired")
        return cast(
            str,
            self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": object_key,
                    "ContentType": media_type,
                    "IfNoneMatch": "*",
                },
                ExpiresIn=min(300, remaining),
                HttpMethod="PUT",
            ),
        )

    async def create_download_url(self, object_key: str, expires_at: datetime) -> str:
        """Sign a private GET for no longer than the requested five-minute window."""
        remaining = floor((expires_at - datetime.now(UTC)).total_seconds())
        if remaining < 1:
            raise ValueError("Image delivery has expired")
        return cast(
            str,
            self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": object_key,
                    "ResponseCacheControl": "private, no-store",
                },
                ExpiresIn=min(300, remaining),
                HttpMethod="GET",
            ),
        )

    async def inspect_object(self, object_key: str) -> StoredImageMetadata | None:
        """Read a bounded object body and verify type from its bytes, not its name."""
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=object_key
            )
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        body = response.get("Body")
        size_bytes = response.get("ContentLength")
        if body is None:
            raise InvalidImageContent
        if type(size_bytes) is not int or not 1 <= size_bytes <= MAX_IMAGE_SIZE_BYTES:
            body.close()
            raise InvalidImageContent

        def read_bounded_body() -> bytes:
            """Read at most the contract limit plus one byte and always close S3."""
            try:
                return cast(bytes, body.read(MAX_IMAGE_SIZE_BYTES + 1))
            finally:
                body.close()

        content = await asyncio.to_thread(read_bounded_body)
        if len(content) != size_bytes or len(content) > MAX_IMAGE_SIZE_BYTES:
            raise InvalidImageContent
        media_type = _sniff_image_type(content)
        if media_type is None or response.get("ContentType") != media_type:
            raise InvalidImageContent
        return StoredImageMetadata(media_type=media_type, size_bytes=len(content))

    async def delete_object(self, object_key: str) -> None:
        """Delete one private object idempotently; callers retain keys on errors."""
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self._bucket, Key=object_key
        )


def _sniff_image_type(
    content: bytes,
) -> Literal["image/jpeg", "image/png", "image/webp"] | None:
    """Recognize only the three contract formats from their file signatures."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n") and content[12:16] == b"IHDR":
        return "image/png"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None
