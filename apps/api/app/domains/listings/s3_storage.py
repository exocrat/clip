"""Private S3 adapter for owner-authorized Listings image storage."""

from __future__ import annotations

import asyncio
import struct
from io import BytesIO
from datetime import UTC, datetime
from math import floor
from typing import Any, Literal, cast

import boto3  # type: ignore[import-untyped]
from botocore.config import Config as BotoConfig  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from PIL import Image, UnidentifiedImageError

from app.contracts.domain_types import ImageId
from app.domains.listings.service import InvalidImageContent, StoredImageMetadata

MAX_IMAGE_SIZE_BYTES = 10_485_760
MAX_NEW_IMAGE_SIZE_BYTES = 5_242_880
MAX_IMAGE_PIXELS = 40_000_000
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
        self, object_key: str, media_type: str, expires_at: datetime, size_bytes: int
    ) -> str:
        """Bind the create-only PUT to its declared content type and exact length."""
        if not 1 <= size_bytes <= MAX_NEW_IMAGE_SIZE_BYTES:
            raise ValueError("Invalid upload size")
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
                    "ContentLength": size_bytes,
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
        media_type = await asyncio.to_thread(_validate_image, content)
        if media_type is None or response.get("ContentType") != media_type:
            raise InvalidImageContent
        # Strip uploader metadata (EXIF/GPS/device serial, XMP, thumbnail) and any
        # appended data before the image is ever delivered to another user, then
        # store the cleaned copy in place of the original. The returned size stays
        # the uploaded size so the caller's upload-integrity check (stored size ==
        # declared size) still holds; only the stored bytes shrink.
        cleaned = await asyncio.to_thread(_sanitize_image, content, media_type)
        if cleaned is None:
            raise InvalidImageContent
        if cleaned != content:
            await asyncio.to_thread(
                lambda: self._client.put_object(
                    Bucket=self._bucket,
                    Key=object_key,
                    Body=cleaned,
                    ContentType=media_type,
                    CacheControl="private, no-store",
                )
            )
        return StoredImageMetadata(media_type=media_type, size_bytes=len(content))

    async def delete_object(self, object_key: str) -> None:
        """Delete one private object idempotently; callers retain keys on errors."""
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self._bucket, Key=object_key
        )


def _validate_image(
    content: bytes,
) -> Literal["image/jpeg", "image/png", "image/webp"] | None:
    """Verify supported image structure and bound dimensions without decoding pixels."""
    formats = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    try:
        with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as image:
            width, height = image.size
            media_type = formats.get(image.format or "")
            if (
                media_type is None
                or width < 1
                or height < 1
                or width * height > MAX_IMAGE_PIXELS
            ):
                return None
            # Reject multi-frame/animated images (animated WEBP, APNG): a listing
            # photo is a single still frame, and animation is outside the contract.
            if getattr(image, "n_frames", 1) > 1:
                return None
        # verify() must run on a freshly opened image; re-open rather than reuse the
        # instance whose frame count was just inspected above.
        with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as image:
            image.verify()
        return cast(Literal["image/jpeg", "image/png", "image/webp"] | None, media_type)
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ):
        return None


def _strip_jpeg(content: bytes) -> bytes | None:
    """Drop every APPn/COM metadata segment and any bytes after the end marker.

    Returns the cleaned JPEG (equal to the input only when it carried no such
    segments and no trailing data), or None if the container does not parse as a
    well-formed JPEG marker stream, so the caller can fall back to a full re-encode.
    This removes EXIF/GPS/XMP/ICC/thumbnail and appended-polyglot data without
    decoding any pixels.
    """
    if content[:2] != b"\xff\xd8":
        return None
    out = bytearray(content[:2])
    i, n = 2, len(content)
    while True:
        if i + 1 >= n or content[i] != 0xFF:
            return None
        marker = content[i + 1]
        if marker == 0xDA:  # Start of Scan: copy entropy data up to and incl. EOI.
            eoi = content.find(b"\xff\xd9", i)
            if eoi < 0:
                return None
            out += content[i : eoi + 2]
            return bytes(out)
        if i + 4 > n:
            return None
        seg_len = struct.unpack(">H", content[i + 2 : i + 4])[0]
        if seg_len < 2 or i + 2 + seg_len > n:
            return None
        if not (0xE0 <= marker <= 0xEF or marker == 0xFE):
            out += content[i : i + 2 + seg_len]
        i += 2 + seg_len


def _strip_png(content: bytes) -> bytes | None:
    """Drop PNG text/EXIF/time metadata chunks and any bytes after IEND.

    Keeps the critical and rendering chunks (IHDR, PLTE, IDAT, colour/transparency,
    ICC) and removes only identifying metadata, without decoding pixels. Returns
    None on a malformed chunk stream so the caller can fall back to a re-encode.
    """
    signature = b"\x89PNG\r\n\x1a\n"
    if content[:8] != signature:
        return None
    drop = {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}
    out = bytearray(signature)
    i, n = 8, len(content)
    while i + 8 <= n:
        length = struct.unpack(">I", content[i : i + 4])[0]
        chunk_type = content[i + 4 : i + 8]
        chunk_end = i + 8 + length + 4  # length + type + data + CRC
        if length > n or chunk_end > n:
            return None
        if chunk_type not in drop:
            out += content[i:chunk_end]
        if chunk_type == b"IEND":
            return bytes(out)
        i = chunk_end
    return None


def _reencode_image(content: bytes, media_type: str) -> bytes | None:
    """Authoritatively strip all metadata by decoding pixels into a fresh image.

    Used as the fallback for WEBP and for any JPEG/PNG whose lightweight strip does
    not re-validate. Bounded by MAX_IMAGE_PIXELS; copies pixels into a new image
    with empty info so no EXIF/XMP/ICC is carried into the re-encoded output.
    """
    formats = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
    target = formats.get(media_type)
    if target is None:
        return None
    try:
        with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as image:
            if image.format != target:
                return None
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                return None
            image.load()
            clean = Image.new(image.mode, image.size)
            clean.paste(image)
        buffer = BytesIO()
        if target == "JPEG":
            clean.convert("RGB").save(buffer, "JPEG", quality=90)
        elif target == "PNG":
            clean.save(buffer, "PNG")
        else:
            clean.save(buffer, "WEBP", quality=90)
        return buffer.getvalue()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
        KeyError,
    ):
        return None


def _sanitize_image(content: bytes, media_type: str) -> bytes | None:
    """Return metadata-free bytes for an already-validated image, or None to reject.

    Prefers the fast no-decode strip for JPEG/PNG and re-validates its output;
    falls back to a full re-encode (always for WEBP) so a strip bug can never store
    a corrupt image, and rejects anything that still fails validation.
    """
    stripper = {"image/jpeg": _strip_jpeg, "image/png": _strip_png}.get(media_type)
    if stripper is not None:
        cleaned = stripper(content)
        if cleaned is not None and (
            cleaned == content or _validate_image(cleaned) == media_type
        ):
            return cleaned
    reencoded = _reencode_image(content, media_type)
    if reencoded is not None and _validate_image(reencoded) == media_type:
        return reencoded
    return None
