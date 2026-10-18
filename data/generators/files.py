"""Local preview run files with fixed targets and no overwrite/database route.

Only the repository's data/runs/<name> directory is used by the CLI. Dataset
files are regenerable; separate manifests remain eligible for Git retention.
This unprivileged tool assumes one writer and no hostile concurrent filesystem
changes by the repository owner. Existing/symlinked targets fail closed.
"""

import argparse
import json
from pathlib import Path
import re

from .manifest import build_bundle, canonical_json, validate_bundle
from .preview import _cli_integer

RUNS_ROOT = Path(__file__).resolve().parents[1] / "runs"
MAX_FILE_BYTES = 128 * 1024 * 1024


def _run_path(name: str) -> Path:
    """Validate a simple run name and reject redirected roots/run directories."""
    if (
        not isinstance(name, str)
        or re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) is None
    ):
        raise ValueError("Run name must be 1–64 lowercase ASCII letters/digits/_/-")
    if RUNS_ROOT.is_symlink() or (RUNS_ROOT.exists() and not RUNS_ROOT.is_dir()):
        raise ValueError("Run root must be an ordinary local directory")
    target = RUNS_ROOT / name
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ValueError("Run target must be an ordinary local directory")
    return target


def write_run(*, name: str, seed: int, user_count: int, listing_count: int) -> dict:
    """Create one new run exclusively; never replace, delete or reset any output.

    Validate inputs/build first, reserve the directory atomically, write dataset
    exclusively, then write the manifest as completion marker. IO interruption
    can leave a partial run for inspection; it is never overwritten or treated
    as valid. Both files must validate before a consumer uses the run.
    """
    target = _run_path(name)
    bundle = build_bundle(seed=seed, user_count=user_count, listing_count=listing_count)
    RUNS_ROOT.mkdir(mode=0o700, parents=False, exist_ok=True)
    target.mkdir(mode=0o700, exist_ok=False)
    with (target / "dataset.json").open("xb") as stream:
        stream.write(canonical_json(bundle) + b"\n")
    with (target / "manifest.json").open("xb") as stream:
        stream.write(canonical_json(bundle["manifest"]) + b"\n")
    return bundle["manifest"]


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    """Reject duplicate JSON keys so malformed files cannot hide earlier values."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are unsupported")
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    """Read a bounded regular nonsymlink JSON file without exposing its contents."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Expected a regular preview JSON file no larger than 128 MiB")
    try:
        value = json.loads(
            path.read_bytes().decode("utf-8"), object_pairs_hook=_unique_object
        )
    except ValueError, UnicodeError, RecursionError:
        raise ValueError("Invalid preview JSON") from None
    if not isinstance(value, dict):
        raise ValueError("Expected a preview JSON object")
    return value


def validate_run(name: str) -> dict:
    """Verify the complete bundle and matching retained manifest; no DB access."""
    target = _run_path(name)
    bundle = _read_json(target / "dataset.json")
    manifest = _read_json(target / "manifest.json")
    validate_bundle(bundle)
    if canonical_json(manifest) != canonical_json(bundle["manifest"]):
        raise ValueError("Retained manifest does not match the preview dataset")
    return manifest


def _action(value: str) -> str:
    """Reject unknown CLI operations without echoing supplied values."""
    if value not in {"generate", "validate", "load"}:
        raise argparse.ArgumentTypeError("Expected generate, validate or load")
    return value


def main(argv: list[str] | None = None) -> int:
    """Expose fixed local file commands; load always reports real prerequisites.

    No path, database URL, overwrite, reset or provider argument is accepted.
    Exit 2 reports configuration/IO/integrity failures without private content.
    """
    parser = argparse.ArgumentParser(
        description="Manage local synthetic preview runs", allow_abbrev=False
    )
    parser.add_argument("action", type=_action)
    parser.add_argument("--name")
    parser.add_argument("--seed", type=_cli_integer)
    parser.add_argument("--users", type=_cli_integer)
    parser.add_argument("--listings", type=_cli_integer)
    args, unexpected = parser.parse_known_args(argv)
    if unexpected:
        parser.error(
            "Unexpected arguments; custom targets/overwrite/reset are unsupported"
        )
    counts = (args.seed, args.users, args.listings)
    if args.action == "load":
        parser.error(
            "Database loading unavailable: requires DL-00 contracts, accepted "
            "ID-READY/LI-CORE schemas and SE-01 adapters/loader validation"
        )
    if args.name is None:
        parser.error("An explicit --name is required")
    if args.action == "generate" and any(value is None for value in counts):
        parser.error("Generation requires explicit --seed, --users and --listings")
    if args.action == "validate" and any(value is not None for value in counts):
        parser.error("Validation accepts only the saved run name")
    try:
        if args.action == "generate":
            manifest = write_run(
                name=args.name,
                seed=args.seed,
                user_count=args.users,
                listing_count=args.listings,
            )
        else:
            manifest = validate_run(args.name)
    except FileExistsError:
        parser.error(
            "Run already exists; choose a new name. Overwrite/reset unsupported"
        )
    except ValueError as error:
        parser.error(str(error))
    except OSError:
        parser.error(
            "Local preview IO failed; inspect permissions/partial run before retry"
        )
    print(manifest["logical_data_fingerprint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
