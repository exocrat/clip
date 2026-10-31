"""Deterministic preview records, independent of domain schemas and providers.

Records are test scaffolding, not users/listings suitable for database loading.
IDs retain UUIDv4 wire shape but are predictable and must never create real
accounts, credentials or authorization. This module performs no file/network IO;
its CLI writes only controlled synthetic JSON Lines to stdout.
"""

import argparse
import hashlib
import json
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from uuid import UUID

GENERATOR_VERSION = "1"
PREVIEW_SCHEMA_VERSION = "1"
MAX_COUNT = 100_000
KINDS = ("user_placeholder", "listing_placeholder")


@dataclass(frozen=True)
class PreviewRecord:
    """Immutable generator scaffold; none of these fields is a domain contract.

    Ordinals are one-based within each kind. Only user placeholders carry an
    example.invalid address; listing placeholders contain no invented schema.
    """

    kind: str
    ordinal: int
    id: str
    label: str
    example_email: str | None


def _integer(value: int, name: str, minimum: int, maximum: int) -> None:
    """Reject booleans, non-integers and unsafe ranges without echoing input."""
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")


def stable_id(seed: int, kind: str, ordinal: int) -> str:
    """Derive a reproducible test-only UUIDv4 from version/seed/kind/ordinal.

    SHA-256 avoids process-randomized hash() and global RNG state. Setting UUID
    variant/version bits preserves the shared wire format, not unpredictability.
    A user's requested count does not change an existing record's identifier.
    """
    _integer(seed, "seed", -(2**63), 2**63 - 1)
    _integer(ordinal, "ordinal", 1, MAX_COUNT)
    if kind not in KINDS:
        raise ValueError("Unsupported preview record kind")
    encoded = json.dumps(
        [
            "clip-preview",
            GENERATOR_VERSION,
            PREVIEW_SCHEMA_VERSION,
            seed,
            kind,
            ordinal,
        ],
        separators=(",", ":"),
    ).encode("utf-8")
    return str(UUID(bytes=hashlib.sha256(encoded).digest()[:16], version=4))


def validate_record(record: PreviewRecord) -> None:
    """Validate closed preview shape and reserved-domain fake-data safety.

    This deliberately validates no domain eligibility, foreign key or feature
    behavior. Additional pure validation hooks can reject records after this
    baseline check; final schema adapters/loader validation remain SE-01 work.
    """
    if not isinstance(record, PreviewRecord) or record.kind not in KINDS:
        raise ValueError("Expected a supported preview record")
    _integer(record.ordinal, "ordinal", 1, MAX_COUNT)
    try:
        identifier = UUID(record.id)
    except ValueError, TypeError, AttributeError:
        raise ValueError("Expected a canonical synthetic UUIDv4") from None
    if identifier.version != 4 or str(identifier) != record.id:
        raise ValueError("Expected a canonical synthetic UUIDv4")
    noun = "user" if record.kind == "user_placeholder" else "listing"
    if record.label != f"Synthetic {noun} {record.ordinal:06d}":
        raise ValueError("Expected a controlled synthetic label")
    expected_email = (
        f"synthetic-{record.id}@example.invalid" if noun == "user" else None
    )
    if record.example_email != expected_email:
        raise ValueError("Expected a reserved-domain example or absent email")


def generate_preview(
    *,
    seed: int,
    user_count: int,
    listing_count: int,
    validator: Callable[[PreviewRecord], None] | None = None,
) -> Iterator[PreviewRecord]:
    """Yield users then listings in stable ordinal order without external IO.

    Both counts and seed are explicit and validated before the first record.
    Each count is bounded to 100,000, including zero. The optional hook runs
    after baseline validation and must be pure; exceptions propagate to callers.
    Wall-clock time and global random state never affect logical records.
    """
    _integer(seed, "seed", -(2**63), 2**63 - 1)
    _integer(user_count, "user_count", 0, MAX_COUNT)
    _integer(listing_count, "listing_count", 0, MAX_COUNT)
    for kind, count in zip(KINDS, (user_count, listing_count), strict=True):
        noun = "user" if kind == "user_placeholder" else "listing"
        for ordinal in range(1, count + 1):
            identifier = stable_id(seed, kind, ordinal)
            record = PreviewRecord(
                kind=kind,
                ordinal=ordinal,
                id=identifier,
                label=f"Synthetic {noun} {ordinal:06d}",
                example_email=(
                    f"synthetic-{identifier}@example.invalid"
                    if noun == "user"
                    else None
                ),
            )
            validate_record(record)
            if validator is not None:
                validator(record)
            yield record


def _cli_integer(value: str) -> int:
    """Reject malformed CLI integers without echoing potentially private input."""
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected an integer") from None


def main(argv: list[str] | None = None) -> int:
    """Parse explicit preview inputs and stream synthetic JSON Lines to stdout.

    There is no default seed/count, output path, loading target or provider.
    Invalid configuration exits 2 with a safe diagnostic before output begins.
    """
    parser = argparse.ArgumentParser(
        description="Generate preview-only synthetic records", allow_abbrev=False
    )
    parser.add_argument("--seed", type=_cli_integer, required=True)
    parser.add_argument("--users", type=_cli_integer, required=True)
    parser.add_argument("--listings", type=_cli_integer, required=True)
    args, unexpected = parser.parse_known_args(argv)
    if unexpected:
        parser.error("Unexpected arguments; only seed/user/listing counts are accepted")
    try:
        for record in generate_preview(
            seed=args.seed, user_count=args.users, listing_count=args.listings
        ):
            print(json.dumps(asdict(record), sort_keys=True, separators=(",", ":")))
    except ValueError as error:
        parser.error(str(error))
    return 0
