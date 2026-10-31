"""Explicit NEXT-06 local byte materialization and transactional schema adapter.

Never a production/cloud loader. Its caller must own a new private cluster and
media directory. Actual S3/session/vector acceptance remains separate; no model,
credential, provider send, production startup or existing-target reset lives here.
"""

from datetime import UTC, datetime
import hashlib
import os
from pathlib import Path
from uuid import UUID

from .manifest import _utc_timestamp
from .reference import digest, validate_reference

DATABASE = "clip_test_next06_reference"
ROLE = "clip_next06_loader"


def canonical_id(value) -> str:
    """Accept only canonical UUIDv4 object names, never arbitrary file paths."""
    parsed = UUID(str(value))
    if parsed.version != 4 or str(parsed) != str(value):
        raise ValueError("Expected a canonical object identifier")
    return str(parsed)


class LocalObjects:
    """Real owned immutable photo bytes; explicit local storage, not an S3 emulator."""

    def __init__(self, root: Path):
        """Reserve a new private directory; never adopt existing/symlinked storage."""
        if (
            not root.is_absolute()
            or root.exists()
            or root.is_symlink()
            or any(p.is_symlink() for p in root.parents)
        ):
            raise ValueError("Local media target must be fresh and canonical")
        root.mkdir(mode=0o700)
        self.root = root
        (root / "blobs").mkdir(mode=0o700)
        (root / "objects").mkdir(mode=0o700)
        self.types = {}

    def object_key_for(self, upload_id):
        """Use a fixed private prefix and validated upload UUID, like the storage boundary."""
        return f"reference-local/{canonical_id(upload_id)}"

    def path(self, key):
        """Confine provider reads to this run's object namespace."""
        prefix, identifier = key.split("/", 1)
        if prefix != "reference-local":
            raise ValueError("Unexpected local object prefix")
        return self.root / "objects" / canonical_id(identifier)

    def put(self, key, content, media_type):
        """Create an immutable object backed by a copied content blob; never overwrite."""
        if (
            media_type not in {"image/jpeg", "image/png", "image/webp"}
            or not 0 < len(content) <= 10485760
        ):
            raise ValueError("Invalid local object")
        sha = hashlib.sha256(content).hexdigest()
        blob = self.root / "blobs" / sha
        if not blob.exists():
            with blob.open("xb") as output:
                output.write(content)
            blob.chmod(0o400)
        elif hashlib.sha256(blob.read_bytes()).hexdigest() != sha:
            raise ValueError("Owned content blob changed")
        os.link(blob, self.path(key))
        self.types[key] = media_type
        return sha

    def read(self, key):
        """Read actual bytes from an ordinary owned object; no metadata-only success."""
        path = self.path(key)
        if path.is_symlink():
            raise ValueError("Local objects cannot be symlinks")
        return path.read_bytes()

    def materialize(self, bundle, image_root):
        """Copy45verified sources and materialize1000distinct backed references."""
        validate_reference(bundle, image_root=image_root)
        cached = {}
        for image in bundle["image_plan"]:
            relative = image["source_relative_path"]
            if relative not in cached:
                cached[relative] = (image_root / relative).read_bytes()
            content = cached[relative]
            if (
                len(content) != image["size_bytes"]
                or hashlib.sha256(content).hexdigest() != image["sha256"]
            ):
                raise ValueError("Source changed before materialization")
            self.put(
                self.object_key_for(image["upload_id"]), content, image["media_type"]
            )
        return self.verify(bundle)

    def verify(self, bundle):
        """Rehash each of the1000backed object paths, counting logical provider bytes."""
        total = 0
        mapping = []
        for image in bundle["image_plan"]:
            key = self.object_key_for(image["upload_id"])
            content = self.read(key)
            if (
                len(content) != image["size_bytes"]
                or hashlib.sha256(content).hexdigest() != image["sha256"]
            ):
                raise ValueError("Materialized image content mismatch")
            total += len(content)
            mapping.append(
                {
                    "image_id": image["image_id"],
                    "object_key": key,
                    "sha256": image["sha256"],
                }
            )
        return {
            "verified_local_objects": len(mapping),
            "logical_object_bytes": total,
            "mapping_digest": digest(mapping),
            "scope": "owned local files only; actual S3 pending",
        }


def guard_target(connection, objects, bundle):
    """Bind real DB/login/Unix path/version/migrations before any DML."""
    target = connection.execute(
        "SELECT current_database(),current_user,inet_server_addr(),current_setting('server_version_num')"
    ).fetchone()
    expected_socket = str(objects.root.parent / "pgsocket")
    if (
        target != (DATABASE, ROLE, None, "180006")
        or connection.info.host != expected_socket
        or connection.info.port != 55438
    ):
        raise ValueError("Refusing unowned or incompatible reference target")
    versions = {
        r[0] for r in connection.execute("SELECT version FROM public.schema_migrations")
    }
    if versions != set(bundle["manifest"]["source_binding"]["migration_versions"]):
        raise ValueError("Reference migrations do not match the generated input")


def load_local(connection, bundle, objects: LocalObjects, image_root: Path):
    """Insert one complete batch after real media validation; refuse any nonempty target.

    All writes share an exclusive guarded transaction. Confirmation timestamps are
    load-audit times, preserving the real24hour image attachment rule. Logical
    user/listing timestamps stay unchanged. No SQL trigger or auth rule is disabled.
    """
    validate_reference(bundle, image_root=image_root)
    guard_target(connection, objects, bundle)
    media = objects.verify(bundle)
    audit = datetime.now(UTC)
    from .reference_rows import insert_rows

    validation = insert_rows(
        connection, bundle, object_key_for=objects.object_key_for, audit=audit
    )
    return {
        "phase": "local-sql-and-byte-rehearsal",
        "input_fingerprint": bundle["manifest"]["logical_data_fingerprint"],
        "load_audit_utc": _utc_timestamp(audit),
        **media,
        **validation,
        "cloud_media_verified": False,
        "real_session_auth_verified": False,
        "new_listing_vectors_verified": False,
    }


def validate_rows(connection, bundle):
    """Preserve the local-only projection binding used by the native rehearsal."""
    from .reference_rows import validate_rows as verify

    return verify(
        connection,
        bundle,
        object_key_for=lambda upload: f"reference-local/{canonical_id(upload)}",
    )
