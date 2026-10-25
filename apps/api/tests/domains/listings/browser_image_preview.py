"""Test-only local image storage and built UI for the Listings browser checkpoint.

This adapter implements the reviewed storage boundary without AWS. The ordinary
API never imports it; only the explicit loopback browser launcher installs it.
Image bytes are temporary and disappear when the preview server stops.
"""

from datetime import UTC, datetime
from pathlib import Path
import secrets
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings
from app.domains.listings.s3_storage import MAX_IMAGE_SIZE_BYTES, _sniff_image_type
from app.domains.listings.service import InvalidImageContent, StoredImageMetadata

ORIGIN = "http://127.0.0.1:5174"


class LocalPreviewStorage:
    """Keep bounded test objects locally and issue expiring, create-only links."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.links: dict[str, tuple[str, str, datetime, str | None]] = {}

    def object_key_for(self, upload_id: UUID) -> str:
        return f"synthetic/browser/{upload_id}"

    def _link(
        self, action: str, object_key: str, expires_at: datetime, media_type: str | None
    ) -> str:
        token = secrets.token_urlsafe(32)
        self.links[token] = (action, object_key, expires_at, media_type)
        return f"{ORIGIN}/__listings_demo/storage/{token}"

    async def create_upload_url(
        self, object_key: str, media_type: str, expires_at: datetime
    ) -> str:
        return self._link("put", object_key, expires_at, media_type)

    async def create_download_url(self, object_key: str, expires_at: datetime) -> str:
        return self._link("get", object_key, expires_at, None)

    async def inspect_object(self, object_key: str) -> StoredImageMetadata | None:
        stored = self.objects.get(object_key)
        if stored is None:
            return None
        content, declared_type = stored
        detected_type = _sniff_image_type(content)
        if detected_type is None or detected_type != declared_type:
            raise InvalidImageContent
        return StoredImageMetadata(media_type=detected_type, size_bytes=len(content))

    async def delete_object(self, object_key: str) -> None:
        self.objects.pop(object_key, None)

    def resolve(self, token: str, action: str) -> tuple[str, str | None]:
        """Reject unknown, expired, or wrong-operation test links."""
        link = self.links.get(token)
        if link is None or link[0] != action or link[2] <= datetime.now(UTC):
            raise HTTPException(status_code=403)
        return link[1], link[3]


def install_image_preview(
    application: FastAPI, settings: Settings, web_root: Path
) -> None:
    """Serve the built app with a conspicuous local-only storage/identity label."""
    if settings.environment != "test" or not settings.development_auth:
        raise RuntimeError(
            "Local image preview requires explicit isolated test settings"
        )
    index = web_root / "index.html"
    if not index.is_file():
        raise RuntimeError("Build the web app before starting the image UI preview")
    storage = LocalPreviewStorage()
    application.state.listings_image_storage = storage

    @application.put("/__listings_demo/storage/{token}", status_code=204)
    async def upload_bytes(token: str, request: Request) -> Response:
        """Model the signed create-only PUT, bounded independently of browser claims."""
        key, expected_type = storage.resolve(token, "put")
        if (
            request.headers.get("if-none-match") != "*"
            or request.headers.get("content-type") != expected_type
        ):
            raise HTTPException(status_code=403)
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_IMAGE_SIZE_BYTES:
                raise HTTPException(status_code=413)
        if not content:
            raise HTTPException(status_code=422)
        if key in storage.objects:
            raise HTTPException(status_code=412)
        storage.objects[key] = (bytes(content), expected_type or "")
        return Response(status_code=204)

    @application.get("/__listings_demo/storage/{token}")
    async def download_bytes(token: str) -> Response:
        key, _ = storage.resolve(token, "get")
        stored = storage.objects.get(key)
        if stored is None:
            raise HTTPException(status_code=404)
        return Response(
            stored[0],
            media_type=stored[1],
            headers={"Cache-Control": "private, no-store"},
        )

    application.mount("/assets", StaticFiles(directory=web_root / "assets"))

    async def preview_page() -> HTMLResponse:
        """Return the built SPA for its approved Listings UI entry paths."""
        banner = (
            '<aside role="note" style="padding:12px;background:#fef3c7;color:#422006">'
            "Local Listings image preview: synthetic seller, isolated PostgreSQL, "
            "temporary local image storage. No AWS. Files disappear when this server stops."
            "</aside>"
        )
        return HTMLResponse(
            index.read_text().replace("<body>", f"<body>{banner}"),
            headers={"Cache-Control": "no-store"},
        )

    application.add_api_route("/", preview_page, methods=["GET"])
    application.add_api_route("/listings/new", preview_page, methods=["GET"])
    application.add_api_route(
        "/listings/{listing_id}/edit", preview_page, methods=["GET"]
    )
    application.add_api_route("/listings/{listing_id}", preview_page, methods=["GET"])
    application.add_api_route("/my/listings", preview_page, methods=["GET"])
    application.add_api_route("/saved", preview_page, methods=["GET"])
    application.add_api_route("/wanted/{request_id}", preview_page, methods=["GET"])
