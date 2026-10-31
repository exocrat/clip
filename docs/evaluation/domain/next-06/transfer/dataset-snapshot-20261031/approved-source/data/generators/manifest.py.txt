"""Versioned in-memory preview bundles and reproducible logical fingerprints.

There is no filesystem/database/provider access. Run time is audit metadata,
excluded from the logical fingerprint; final domain schemas remain SE-01 inputs.
"""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime

from .preview import GENERATOR_VERSION, PREVIEW_SCHEMA_VERSION, generate_preview

MANIFEST_VERSION = "1"
CONFIG_VERSION = "1"


def canonical_json(value: object) -> bytes:
    """Serialize finite JSON with stable keys/spacing and UTF-8 bytes for hashing.

    Array order is preserved; no Unicode normalization or floating-point money
    conversion is performed. Non-JSON values and NaN/infinity are rejected.
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _utc_timestamp(value: datetime) -> str:
    """Require an aware instant and emit the shared six-digit UTC wire format."""
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Generation time must be a timezone-aware instant")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def build_bundle(
    *,
    seed: int,
    user_count: int,
    listing_count: int,
    generated_at: datetime | None = None,
) -> dict:
    """Build a preview manifest/records bundle with observed counts and SHA-256.

    Explicit seed/counts inherit the generator's bounds. Generation time defaults
    to aware UTC now but never affects records or the fingerprint. This returns
    an in-memory object only; callers must not mistake it for a loaded dataset.
    """
    records = [
        asdict(record)
        for record in generate_preview(
            seed=seed, user_count=user_count, listing_count=listing_count
        )
    ]
    identity = {
        "generator_version": GENERATOR_VERSION,
        "config_version": CONFIG_VERSION,
        "schema_version": f"preview-{PREVIEW_SCHEMA_VERSION}",
        "seed": seed,
        "requested_counts": {"users": user_count, "listings": listing_count},
    }
    logical = {**identity, "records": records}
    fingerprint = "sha256:" + hashlib.sha256(canonical_json(logical)).hexdigest()
    observed = {
        "users": sum(record["kind"] == "user_placeholder" for record in records),
        "listings": sum(record["kind"] == "listing_placeholder" for record in records),
    }
    return {
        "manifest": {
            "manifest_version": MANIFEST_VERSION,
            "preview_only": True,
            **identity,
            "observed_counts": observed,
            "generated_at": _utc_timestamp(
                datetime.now(UTC) if generated_at is None else generated_at
            ),
            "logical_data_fingerprint": fingerprint,
        },
        "records": records,
    }


def validate_bundle(bundle: dict) -> None:
    """Reject unsupported versions, altered records/counts/fingerprints or time.

    Reconstructing the closed preview format checks fake-data safety, exact
    types and record ordering as well as the hash. It is not a final-schema or
    database integrity validator. Failures do not echo supplied data.
    """
    try:
        manifest = bundle["manifest"]
        counts = manifest["requested_counts"]
        timestamp = datetime.fromisoformat(manifest["generated_at"])
        expected = build_bundle(
            seed=manifest["seed"],
            user_count=counts["users"],
            listing_count=counts["listings"],
            generated_at=timestamp,
        )
        if canonical_json(bundle) != canonical_json(expected):
            raise ValueError(
                "Preview bundle does not match its versioned configuration"
            )
    except KeyError, TypeError, ValueError, OverflowError, AttributeError:
        raise ValueError("Invalid or unsupported preview bundle") from None
