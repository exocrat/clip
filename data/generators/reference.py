"""NEXT-06 reference recipe generation: local files only, never a loader or sign-in.

Reuse PD-09 IDs/canonical JSON and named-run guards. Source photos stay external
and unmodified; no object, credential, session, query judgment or vector is
created. Generated records need actual schema/media/model checks before freeze.
"""

import argparse
from collections import Counter
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any
from uuid import UUID

from . import files
from .manifest import _utc_timestamp, canonical_json
from .preview import stable_id

ROOT = Path(__file__).resolve().parents[2]
RECIPE = ROOT / "data/evaluation/reference-recipe.json"
IMAGE_INVENTORY = ROOT / "data/evaluation/reference-image-inputs.json"
VERSION = "reference-recipe-v2"
MAX_IMAGE_BYTES = 10_485_760


def digest(value: object) -> str:
    """Hash logical JSON, retaining list order and excluding no fields implicitly."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def logical_clock(value: str) -> datetime:
    """Require explicit canonical UTC midnight; wall time never assigns records."""
    try:
        instant = datetime.fromisoformat(value)
        if _utc_timestamp(instant) != value or instant.time().isoformat() != "00:00:00":
            raise ValueError
        return instant
    except ValueError, TypeError, AttributeError:
        raise ValueError(
            "Logical time must be midnight UTC with six fractional digits"
        ) from None


def permutation(ids: list[str], name: str) -> list[str]:
    """Use the approved independent SHA256(seed:assignment:id) order, then ID ties."""
    return sorted(
        ids,
        key=lambda value: (
            hashlib.sha256(f"42:{name}:{value}".encode()).digest(),
            value,
        ),
    )


def partition(
    ids: list[str], name: str, groups: list[tuple[Any, int]]
) -> dict[str, Any]:
    """Assign exact consecutive group sizes in an independently permuted ID order."""
    if sum(count for _, count in groups) != len(ids) or any(
        count < 0 for _, count in groups
    ):
        raise ValueError("Recipe group counts do not match the reference corpus")
    ordered = permutation(ids, name)
    result = {}
    offset = 0
    for value, count in groups:
        result.update(
            (identifier, value) for identifier in ordered[offset : offset + count]
        )
        offset += count
    return result


def derived_id(kind: str, identifier: str) -> str:
    """Namespace image/upload/operation UUIDv4-shaped IDs separately from entity IDs."""
    return str(
        UUID(
            bytes=hashlib.sha256(
                f"clip-reference-v1:{kind}:{identifier}".encode()
            ).digest()[:16],
            version=4,
        )
    )


def source_binding() -> dict[str, Any]:
    """Bind schema/contracts/model/vocabulary and generator bytes without absolute paths.

    The Git revision is the base; content hashes also bind uncommitted generator
    files. Image inventory audit timestamps are intentionally excluded: its
    semantic records are bound separately, not by its file's serialization.
    """
    migrations = sorted((ROOT / "database/migrations").glob("*.sql"))
    paths = migrations + [
        RECIPE,
        Path(__file__),
        ROOT / "data/generators/preview.py",
        ROOT / "data/generators/manifest.py",
        ROOT / "data/generators/files.py",
        ROOT / "contracts/source/types.py",
        ROOT / "contracts/listings.md",
        ROOT / "contracts/search.md",
        ROOT / "apps/api/app/domains/listings/embedding_pipeline.json",
        ROOT / "apps/api/app/domains/listings/search_vocabulary.json",
    ]
    entries = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in paths
    ]
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return {
        "base_revision": revision,
        "source_digest": digest(entries),
        "files": entries,
        "migration_versions": [path.name.split("_", 1)[0] for path in migrations],
        "schema_version": f"reference-v2@{migrations[-1].name.split('_', 1)[0]}",
        "revision_scope": "base revision plus exact file digests; accepted freeze revision pending",
    }


def source_images(root: Path, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    """Revalidate all approved topic files, actual byte hashes/types and safe paths.

    File magic is not a full image decode/visual judgment. Reject substitutions,
    links, traversal and oversized input before any output directory is created.
    No conversion, renaming, EXIF processing or source-file write occurs here.
    """
    if (
        not root.is_absolute()
        or not root.is_dir()
        or root.is_symlink()
        or any(p.is_symlink() for p in root.parents)
    ):
        raise ValueError("Use an ordinary absolute image-root directory")
    document = files._read_json(IMAGE_INVENTORY)
    images = document.get("images")
    expected = {
        (category["code"], topic["slug"])
        for category in recipe["categories"]
        for topic in category["topics"]
    }
    if not isinstance(images, list) or len(images) != 45 or len(expected) != 45:
        raise ValueError("Expected45approved source images/topics")
    seen = set()
    for image in images:
        if not isinstance(image, dict) or set(image) != {
            "category_code",
            "topic_slug",
            "source_relative_path",
            "media_type",
            "size_bytes",
            "width",
            "height",
            "sha256",
        }:
            raise ValueError("Unexpected source-image inventory fields")
        key = (image["category_code"], image["topic_slug"])
        if key not in expected or key in seen:
            raise ValueError("Source-image topic is missing, duplicated or unexpected")
        seen.add(key)
        relative = PurePosixPath(image["source_relative_path"])
        if (
            relative.is_absolute()
            or len(relative.parts) != 2
            or any(part in (".", "..") for part in relative.parts)
            or relative.parts[0] != image["category_code"]
        ):
            raise ValueError("Unsafe relative source-image path")
        path = root.joinpath(*relative.parts)
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
            raise ValueError("Source image must be an ordinary file")
        size = path.stat().st_size
        if (
            type(image["size_bytes"]) is not int
            or size != image["size_bytes"]
            or not 0 < size <= MAX_IMAGE_BYTES
        ):
            raise ValueError("Source-image size differs or exceeds the limit")
        data = path.read_bytes()
        mime = (
            "image/jpeg"
            if data.startswith(b"\xff\xd8\xff")
            else (
                "image/png"
                if data.startswith(b"\x89PNG\r\n\x1a\n")
                else (
                    "image/webp"
                    if data[:4] == b"RIFF" and data[8:12] == b"WEBP"
                    else None
                )
            )
        )
        if (
            mime is None
            or mime != image["media_type"]
            or hashlib.sha256(data).hexdigest() != image["sha256"]
        ):
            raise ValueError(
                "Source-image content/type differs from its approved digest"
            )
        if any(type(image[k]) is not int or image[k] <= 0 for k in ("width", "height")):
            raise ValueError("Source-image dimensions are invalid")
    return sorted(
        images, key=lambda image: (image["category_code"], image["topic_slug"])
    )


def observed_counts(
    users: list[dict], listings: list[dict], images: list[dict]
) -> dict:
    """Report actual distributions and aggregate planned storage volume, not uploads."""
    return {
        "users": len(users),
        "listings": len(listings),
        "planned_images": len(images),
        "user_classes": dict(
            sorted(Counter(u["account_class"] for u in users).items())
        ),
        "categories": dict(
            sorted(Counter(row["category_code"] for row in listings).items())
        ),
        "conditions": dict(
            sorted(Counter(row["condition_code"] for row in listings).items())
        ),
        "prices_paise": dict(
            sorted(Counter(str(row["asking_price_paise"]) for row in listings).items())
        ),
        "negotiable": dict(Counter(str(row["negotiable"]).lower() for row in listings)),
        "proof": dict(
            Counter(
                (
                    "omitted"
                    if "proof_available" not in row
                    else str(row["proof_available"]).lower()
                )
                for row in listings
            )
        ),
        "availability_scenarios": dict(
            Counter(row["availability_scenario"] for row in listings)
        ),
        "pickup_areas": dict(Counter(row["pickup_area"] for row in listings)),
        "topics": dict(sorted(Counter(row["topic_slug"] for row in listings).items())),
        "distinct_regular_owners": len({row["owner_id"] for row in listings}),
        "planned_image_bytes": sum(row["size_bytes"] for row in images),
    }


def build_reference(
    *,
    logical_time: str,
    image_root: Path,
    sensitive_threshold_paise: int,
    generated_at: datetime | None = None,
    source_base_revision: str | None = None,
) -> dict[str, Any]:
    """Build the full approved5000/1000reference input without external side effects.

    Every assignment uses its own hash permutation. No authentication state,
    contacts, encrypted/private thread data, labels, vectors or fake confirmations
    are generated. The returned image plan becomes actual media only in Step3.
    """
    moment = logical_clock(logical_time)
    if (
        type(sensitive_threshold_paise) is not int
        or not 0 <= sensitive_threshold_paise <= 2**63 - 1
        or sensitive_threshold_paise % 100
    ):
        raise ValueError("Sensitive threshold must be nonnegative whole-rupee paise")
    recipe = files._read_json(RECIPE)
    if (
        recipe["format_version"] != "2"
        or recipe["seed"] != 42
        or recipe["users"] != {"regular": 5000, "temporary": 0}
    ):
        raise ValueError("Unsupported approved reference recipe")
    cutoff = logical_clock(recipe["measurement_before"])
    if cutoff <= moment + timedelta(hours=1):
        raise ValueError("Reference generation day must precede the evaluation cutoff")
    image_sources = source_images(image_root, recipe)
    sources = source_binding()
    if source_base_revision is not None:
        # Publishing an unchanged input must not invalidate it merely by adding
        # a descendant commit. All current file/schema/config digests still bind.
        if (
            not isinstance(source_base_revision, str)
            or len(source_base_revision) != 40
            or any(c not in "0123456789abcdef" for c in source_base_revision)
            or subprocess.run(
                ["git", "merge-base", "--is-ancestor", source_base_revision, "HEAD"],
                cwd=ROOT,
                capture_output=True,
                timeout=5,
            ).returncode
            != 0
        ):
            raise ValueError("Recorded source base is not a known ancestor")
        sources = sources | {"base_revision": source_base_revision}
    users = [
        {
            "id": stable_id(42, "user_placeholder", n),
            "account_class": "regular",
            "status": "active",
            "display_name": f"synthetic_{n:06d}",
            "handle_ready": True,
            "created_at": _utc_timestamp(moment - timedelta(days=1)),
            "activated_at": None,
            "expires_at": None,
        }
        for n in range(1, 5001)
    ]
    ids = [stable_id(42, "listing_placeholder", n) for n in range(1, 1001)]
    categories = partition(
        ids, "category", [(c["code"], c["count"]) for c in recipe["categories"]]
    )
    conditions = partition(
        ids, "condition", [(c["code"], c["count"]) for c in recipe["conditions"]]
    )
    labels = {c["code"]: c["label"] for c in recipe["conditions"]}
    prices = partition(
        ids, "price", [(price * 100, 100) for price in recipe["prices_rupees"]]
    )
    negotiable = partition(
        ids, "negotiable", list(zip([True, False], recipe["negotiable_counts"]))
    )
    proof = partition(
        ids, "proof", list(zip([None, True, False], recipe["proof_counts"]))
    )
    availability = partition(
        ids,
        "availability",
        list(
            zip(
                ["available", "unavailable", "future", "expired"],
                recipe["availability_counts"],
            )
        ),
    )
    pickup = partition(ids, "pickup", [(area, 250) for area in recipe["pickup_areas"]])
    owner_ids = permutation(
        [u["id"] for u in users if u["account_class"] == "regular"], "owner"
    )[:1000]
    owners = dict(zip(permutation(ids, "listing-owner"), owner_ids, strict=True))
    topics = {}
    for category in recipe["categories"]:
        group = permutation(
            [i for i in ids if categories[i] == category["code"]],
            f"topic:{category['code']}",
        )
        topics.update(
            (identifier, category["topics"][index % 5])
            for index, identifier in enumerate(group)
        )
    by_topic = {(i["category_code"], i["topic_slug"]): i for i in image_sources}
    listings = []
    image_plan = []
    for ordinal, identifier in enumerate(ids, 1):
        category = categories[identifier]
        topic = topics[identifier]
        scenario = availability[identifier]
        source = by_topic[(category, topic["slug"])]
        image_id = derived_id("image", identifier)
        row = {
            "id": identifier,
            "owner_id": owners[identifier],
            "title": f"Synthetic {topic['item']} {ordinal:04d}",
            "description": f"Synthetic {topic['item']}. {topic['synonym']}. Condition: {labels[conditions[identifier]]}. For campus use.",
            "category_code": category,
            "condition_code": conditions[identifier],
            "asking_price_paise": prices[identifier],
            "negotiable": negotiable[identifier],
            "pickup_area": pickup[identifier],
            "availability": "unavailable" if scenario == "unavailable" else "available",
            "available_from": _utc_timestamp(
                cutoff + timedelta(days=1)
                if scenario == "future"
                else (
                    moment - timedelta(days=30)
                    if scenario == "expired"
                    else moment - timedelta(days=1)
                )
            ),
            "available_until": _utc_timestamp(
                moment - timedelta(days=1)
                if scenario == "expired"
                else cutoff + timedelta(days=30)
            ),
            "created_at": _utc_timestamp(moment - timedelta(days=2)),
            "updated_at": _utc_timestamp(moment - timedelta(days=2)),
            "topic_slug": topic["slug"],
            "availability_scenario": scenario,
            "image_id": image_id,
            "expected_sensitive_purchase": category
            in recipe["sensitive_category_codes"]
            or prices[identifier] > sensitive_threshold_paise,
        }
        if proof[identifier] is not None:
            row["proof_available"] = proof[identifier]
        listings.append(row)
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[
            source["media_type"]
        ]
        image_plan.append(
            {
                "image_id": image_id,
                "upload_id": derived_id("upload", identifier),
                "operation_id": derived_id("image-operation", identifier),
                "listing_id": identifier,
                "owner_id": owners[identifier],
                "source_relative_path": source["source_relative_path"],
                "relative_object_key": f"images/{image_id}.{extension}",
                "media_type": source["media_type"],
                "size_bytes": source["size_bytes"],
                "sha256": source["sha256"],
            }
        )
    config = {
        "generator_version": VERSION,
        "requested_counts": {"users": 5000, "listings": 1000, "planned_images": 1000},
        "source_revision": sources["base_revision"],
        "seed": 42,
        "logical_time": logical_time,
        "schema_version": sources["schema_version"],
        "source_binding": sources,
        "recipe_digest": digest(recipe),
        "image_source_digest": digest(image_sources),
        "sensitive_purchase_threshold_paise": sensitive_threshold_paise,
    }
    logical = {
        "config": config,
        "users": users,
        "listings": listings,
        "image_plan": image_plan,
    }
    counts = observed_counts(users, listings, image_plan)
    return {
        "manifest": {
            **config,
            "phase": "generated-unloaded",
            "observed_counts": counts,
            "logical_data_fingerprint": digest(logical),
            "generated_at": _utc_timestamp(
                datetime.now(UTC) if generated_at is None else generated_at
            ),
            "measurement_window": {
                "from": _utc_timestamp(moment + timedelta(hours=1)),
                "before": _utc_timestamp(cutoff),
            },
            "acceptance": {
                "sql_loaded": False,
                "image_objects_uploaded": False,
                "image_objects_verified": False,
                "current_vectors_verified": False,
                "human_labels_reviewed": False,
                "data_ready": False,
            },
            "media_scope": "relative planned keys only; actual approved bucket/prefix/upload confirmation pending Step3",
            "credentials_sessions_provider_sends": "none",
        },
        "users": users,
        "listings": listings,
        "image_plan": image_plan,
    }


def validate_reference(bundle: dict, *, image_root: Path) -> dict:
    """Reconstruct against current approved inputs; reject tampering/stale files or claims."""
    manifest = bundle["manifest"]
    expected = build_reference(
        logical_time=manifest["logical_time"],
        image_root=image_root,
        sensitive_threshold_paise=manifest["sensitive_purchase_threshold_paise"],
        generated_at=datetime.fromisoformat(manifest["generated_at"]),
        source_base_revision=manifest["source_revision"],
    )
    if canonical_json(bundle) != canonical_json(expected):
        raise ValueError(
            "Reference input is altered, stale or claims unperformed checks"
        )
    return manifest


def write_reference(
    *, name: str, logical_time: str, image_root: Path, sensitive_threshold_paise: int
) -> dict:
    """Exclusively create one0700named run; manifest completion marker is written last."""
    target = files._run_path(name)
    if target.exists():
        raise ValueError("Reference run already exists; choose a fresh name")
    bundle = build_reference(
        logical_time=logical_time,
        image_root=image_root,
        sensitive_threshold_paise=sensitive_threshold_paise,
    )
    files.RUNS_ROOT.mkdir(mode=0o700, exist_ok=True)
    target.mkdir(mode=0o700, exist_ok=False)
    for filename, payload in (
        ("dataset.json", bundle),
        ("manifest.json", bundle["manifest"]),
    ):
        with (target / filename).open("xb") as stream:
            # Keep retained manifests legible; logical hashes still use canonical JSON.
            content = (
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode()
                if filename == "manifest.json"
                else canonical_json(payload)
            )
            stream.write(content + b"\n")
    return bundle["manifest"]


def read_reference(name: str, *, image_root: Path) -> dict:
    """Validate bounded nonsymlink run files and exact paired manifest; read-only."""
    target = files._run_path(name)
    bundle = files._read_json(target / "dataset.json")
    manifest = validate_reference(bundle, image_root=image_root)
    if canonical_json(manifest) != canonical_json(
        files._read_json(target / "manifest.json")
    ):
        raise ValueError("Reference manifest differs from its dataset")
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Generate today's corpus or validate retained runs; expose no cloud/load/reset action."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("generate", "validate"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--logical-time")
    parser.add_argument("--sensitive-threshold-paise", type=int)
    args = parser.parse_args(argv)
    try:
        if args.action == "generate":
            if not args.logical_time or args.sensitive_threshold_paise is None:
                raise ValueError(
                    "Generation requires explicit logical time and sensitive threshold"
                )
            if logical_clock(args.logical_time).date() != datetime.now(UTC).date():
                raise ValueError(
                    "Generate at midnight UTC on the current UTC day; validate preserves historical runs"
                )
            manifest = write_reference(
                name=args.name,
                logical_time=args.logical_time,
                image_root=args.image_root,
                sensitive_threshold_paise=args.sensitive_threshold_paise,
            )
        else:
            manifest = read_reference(args.name, image_root=args.image_root)
        print(
            f"PASS {manifest['logical_data_fingerprint']} users=5000 listings=1000 phase=generated-unloaded"
        )
        return 0
    except ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError:
        print(
            "Reference generation/validation refused; check reviewed inputs, source photos and fresh run name."
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
