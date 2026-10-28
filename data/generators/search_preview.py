"""Schema-shaped SE-01 fixtures, never final data or a production seed.

Reuse PD-09 stable IDs, canonical hashing and private run files. This module
does not rank results, authenticate users, contact storage or create labels.
The explicit logical clock freezes availability scenarios independently of
the audit timestamp. Local PostgreSQL loading lives in search_loader.
"""

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from . import files
from .manifest import _utc_timestamp, canonical_json
from .preview import _cli_integer, generate_preview

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "search-preview-1"
# Catalogue codes follow the approved catalogue and its NEXT-03 migration.
# Text is controlled fixture content, not a relevance judgment or imported data.
TOPICS = (
    ("mobile_phone", "mobile phone", "Android handset charger"),
    ("laptop", "laptop computer", "Portable computer keyboard"),
    ("electronics", "desk monitor", "Computer display HDMI cable"),
    ("furniture", "study desk", "Wooden desk adjustable chair"),
    ("books", "linear algebra textbook", "Mathematics vectors matrices"),
    ("bicycles", "campus bicycle", "Cycle pedals wheels helmet"),
    ("appliances", "electric kettle", "Kitchen water boiler"),
    ("sports_fitness", "sports racket", "Badminton sports equipment"),
    ("other", "backpack", "Student carrying bag umbrella water bottle"),
)
CONDITIONS = ("new", "like_new", "good", "fair")


def source_fingerprint() -> str:
    """Bind fixtures to current migrations and reviewed wire/boundary sources.

    Hash relative names and bytes so moving the clone does not change the hash.
    Revalidation refuses a corpus after any of these inputs changes.
    """
    paths = sorted((ROOT / "database/migrations").glob("*.sql")) + [
        ROOT / "contracts/source/types.py",
        ROOT / "contracts/listings.md",
        ROOT / "contracts/search.md",
    ]
    payload = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }
    return "sha256:" + hashlib.sha256(canonical_json(payload)).hexdigest()


def _clock(value: str) -> datetime:
    """Accept only canonical aware UTC instants; reject clock ambiguity safely."""
    try:
        moment = datetime.fromisoformat(value)
        if _utc_timestamp(moment) != value:
            raise ValueError
        return moment
    except ValueError, TypeError, AttributeError, OverflowError:
        raise ValueError(
            "Expected a six-fractional-digit UTC logical time ending in Z"
        ) from None


def _image_id(listing_id: str) -> str:
    """Derive a separate deterministic UUIDv4-shaped image fixture identifier."""
    return str(
        UUID(
            bytes=hashlib.sha256(
                f"search-preview-image:{listing_id}".encode()
            ).digest()[:16],
            version=4,
        )
    )


def build_corpus(
    *,
    seed: int,
    user_count: int,
    listing_count: int,
    logical_time: str,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Adapt PD-09 scaffolds to active regular users and varied listing rows.

    Listings cycle over categories, conditions, prices/ties, negotiability and
    available/unavailable/future/ended windows. A listing requires a generated
    owner. Image IDs/keys are metadata fixtures only; no image object exists.
    No credentials, contacts, selected buyer, or conversation data is produced.
    """
    moment = _clock(logical_time)
    scaffolds = list(
        generate_preview(seed=seed, user_count=user_count, listing_count=listing_count)
    )
    if listing_count and not user_count:
        raise ValueError("Listing fixtures require at least one generated owner")
    users = [
        {
            "id": row.id,
            "account_class": "regular",
            "status": "active",
            "display_name": row.label,
            "created_at": _utc_timestamp(moment - timedelta(days=30)),
        }
        for row in scaffolds
        if row.kind == "user_placeholder"
    ]
    listings = []
    for row in scaffolds[user_count:]:
        index = row.ordinal - 1
        category, title, description = TOPICS[(index + seed) % len(TOPICS)]
        scenario = index % 10
        start = (
            moment + timedelta(days=1) if scenario == 8 else moment - timedelta(days=2)
        )
        end = moment - timedelta(days=1) if scenario == 9 else None
        listings.append(
            {
                "id": row.id,
                "owner_id": users[index % user_count]["id"],
                "title": f"Synthetic {title} {row.ordinal:06d}",
                "description": f"Synthetic fixture only. {description}.",
                "category_code": category,
                "condition_code": CONDITIONS[(index // 8) % 4],
                "asking_price_paise": (index // 2 % 101) * 10000,
                "negotiable": bool((index // 32) % 2),
                "pickup_area": None,
                "proof_available": bool(index % 2),
                "availability": "unavailable" if scenario == 7 else "available",
                "available_from": _utc_timestamp(start),
                "available_until": _utc_timestamp(end) if end else None,
                "created_at": _utc_timestamp(
                    moment - timedelta(days=3, seconds=index // 2)
                ),
                "updated_at": _utc_timestamp(
                    moment - timedelta(days=3, seconds=index // 2)
                ),
                "image_id": _image_id(row.id),
            }
        )
    config = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "requested_counts": {"users": user_count, "listings": listing_count},
        "logical_time": logical_time,
        "source_fingerprint": source_fingerprint(),
    }
    logical = {**config, "users": users, "listings": listings}
    fingerprint = "sha256:" + hashlib.sha256(canonical_json(logical)).hexdigest()
    return {
        "manifest": {
            **config,
            "preview_only": True,
            "image_objects_verified": False,
            "observed_counts": {"users": len(users), "listings": len(listings)},
            "generated_at": _utc_timestamp(
                datetime.now(UTC) if generated_at is None else generated_at
            ),
            "logical_data_fingerprint": fingerprint,
        },
        "users": users,
        "listings": listings,
    }


def validate_corpus(bundle: dict[str, Any]) -> None:
    """Reconstruct the closed fixture schema to reject tampering and stale inputs.

    Equality is canonical-byte equality, so booleans cannot masquerade as money,
    and extra/private fields or externally supplied content cannot pass.
    """
    try:
        manifest = bundle["manifest"]
        counts = manifest["requested_counts"]
        expected = build_corpus(
            seed=manifest["seed"],
            user_count=counts["users"],
            listing_count=counts["listings"],
            logical_time=manifest["logical_time"],
            generated_at=_clock(manifest["generated_at"]),
        )
        if canonical_json(bundle) != canonical_json(expected):
            raise ValueError
    except KeyError, TypeError, ValueError, OverflowError, AttributeError:
        raise ValueError("Invalid, altered or stale Search preview corpus") from None


def write_corpus(
    *,
    name: str,
    seed: int,
    user_count: int,
    listing_count: int,
    logical_time: str,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Write a fresh owner-private named run; refuse overwrite and redirected IO."""
    target = files._run_path(name)
    bundle = build_corpus(
        seed=seed,
        user_count=user_count,
        listing_count=listing_count,
        logical_time=logical_time,
        generated_at=generated_at,
    )
    files.RUNS_ROOT.mkdir(mode=0o700, parents=False, exist_ok=True)
    target.mkdir(mode=0o700, exist_ok=False)
    for filename, payload in (
        ("dataset.json", bundle),
        ("manifest.json", bundle["manifest"]),
    ):
        with (target / filename).open("xb") as stream:
            stream.write(canonical_json(payload) + b"\n")
    return cast(dict[str, Any], bundle["manifest"])


def read_corpus(name: str) -> dict[str, Any]:
    """Load and verify a named bounded local file plus its matching manifest."""
    target = files._run_path(name)
    bundle = files._read_json(target / "dataset.json")
    validate_corpus(bundle)
    if canonical_json(files._read_json(target / "manifest.json")) != canonical_json(
        bundle["manifest"]
    ):
        raise ValueError("Search preview manifest does not match its corpus")
    return bundle


def main(argv: list[str] | None = None) -> int:
    """Generate/validate fixed local runs, with safe errors and no database target."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("generate", "validate"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--seed", type=_cli_integer)
    parser.add_argument("--users", type=_cli_integer)
    parser.add_argument("--listings", type=_cli_integer)
    parser.add_argument("--logical-time")
    args, unexpected = parser.parse_known_args(argv)
    if unexpected:
        parser.error("Unexpected arguments; custom targets/reset/overwrite unsupported")
    config = (args.seed, args.users, args.listings, args.logical_time)
    if args.action == "generate" and any(value is None for value in config):
        parser.error("Generation requires explicit seed, counts and logical time")
    if args.action == "validate" and any(value is not None for value in config):
        parser.error("Validation accepts only the run name")
    try:
        manifest = (
            write_corpus(
                name=args.name,
                seed=args.seed,
                user_count=args.users,
                listing_count=args.listings,
                logical_time=args.logical_time,
            )
            if args.action == "generate"
            else read_corpus(args.name)["manifest"]
        )
    except ValueError, OSError:
        parser.error(
            "Search preview refused; check inputs, source revision and fresh run name"
        )
    print(manifest["logical_data_fingerprint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
