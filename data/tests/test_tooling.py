"""Reproducibility and refusal tests using only synthetic values/private temp IO."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from uuid import UUID

import pytest

from data.generators import files, preview
from data.generators.manifest import build_bundle, canonical_json, validate_bundle

REPOSITORY = Path(__file__).resolve().parents[2]
CONFIG = {"seed": 42, "user_count": 3, "listing_count": 2}
RUN_TIME = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def bundle():
    """Return fresh deterministic data so mutation tests cannot affect each other."""
    return build_bundle(**CONFIG, generated_at=RUN_TIME)


@pytest.fixture
def run_root(tmp_path, monkeypatch):
    """Redirect internal IO only for tests, never accepting a CLI target override."""
    root = tmp_path / "runs"
    monkeypatch.setattr(files, "RUNS_ROOT", root)
    return root


def test_reproducible_across_process_hash_seeds(tmp_path):
    """Fresh credential-free processes must emit byte-identical logical records."""
    command = [
        sys.executable,
        "-m",
        "data.generators",
        "--seed",
        "42",
        "--users",
        "3",
        "--listings",
        "2",
    ]
    outputs = []
    for hash_seed in ("1", "987"):
        environment = {
            "PATH": os.defpath,
            "HOME": str(tmp_path),
            "LC_ALL": "C",
            "PYTHONHASHSEED": hash_seed,
        }
        result = subprocess.run(
            command,
            cwd=REPOSITORY,
            env=environment,
            capture_output=True,
            check=True,
            timeout=10,
        )
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]
    assert len(outputs[0].splitlines()) == 5


def test_stable_ids_counts_order_and_rng():
    """Counts may grow without changing existing IDs or touching global RNG."""
    state = random.getstate()
    small = list(preview.generate_preview(**CONFIG))
    large = list(preview.generate_preview(seed=42, user_count=4, listing_count=3))
    lookup = {(row.kind, row.ordinal): row for row in large}
    assert all(lookup[(row.kind, row.ordinal)] == row for row in small)
    assert random.getstate() == state
    assert len({row.id for row in large}) == 7
    assert all(
        UUID(row.id).version == 4 and str(UUID(row.id)) == row.id for row in large
    )
    assert small != list(
        preview.generate_preview(seed=43, user_count=3, listing_count=2)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", True),
        ("seed", 2**63),
        ("seed", -(2**63) - 1),
        ("user_count", -1),
        ("user_count", 1.0),
        ("user_count", True),
        ("listing_count", 100001),
        ("listing_count", None),
    ],
)
def test_invalid_configuration_before_first_record(field, value):
    """Invalid seeds/counts must fail before producing any logical record."""
    config = {**CONFIG, field: value}
    with pytest.raises(ValueError):
        next(preview.generate_preview(**config))


def test_zero_counts_and_integer_boundaries():
    """Empty previews and documented inclusive bounds remain usable."""
    assert list(preview.generate_preview(seed=0, user_count=0, listing_count=0)) == []
    row = next(
        preview.generate_preview(seed=-(2**63), user_count=100000, listing_count=0)
    )
    assert row.ordinal == 1
    assert (
        UUID(preview.stable_id(2**63 - 1, "listing_placeholder", 100000)).version == 4
    )


def test_validation_hook_and_failure_propagation():
    """Pure hooks see each validated row and their failures are never swallowed."""
    seen = []
    rows = list(preview.generate_preview(**CONFIG, validator=seen.append))
    assert seen == rows

    def reject(_record):
        """Represent a later pure adapter validation failure without external IO."""
        raise RuntimeError("synthetic hook rejection")

    with pytest.raises(RuntimeError, match="synthetic hook rejection"):
        next(preview.generate_preview(**CONFIG, validator=reject))


@pytest.mark.parametrize(
    "field,value",
    [
        ("ordinal", True),
        ("ordinal", 0),
        ("kind", "actual_user"),
        ("id", "bad-id"),
        ("label", "uncontrolled-sentinel"),
        ("example_email", "uncontrolled-sentinel"),
    ],
)
def test_uncontrolled_record_rejected(field, value):
    """Validation refuses corrupted identity/shape and noncontrolled fake values."""
    row = next(preview.generate_preview(**CONFIG))
    with pytest.raises(ValueError) as error:
        preview.validate_record(replace(row, **{field: value}))
    assert "uncontrolled-sentinel" not in str(error.value)


def test_fingerprint_excludes_run_time_and_tracks_configuration(bundle):
    """Audit time changes without logical drift; seed/count changes affect the hash."""
    later = build_bundle(**CONFIG, generated_at=RUN_TIME + timedelta(days=1))
    assert bundle["records"] == later["records"]
    assert bundle["manifest"]["generated_at"] != later["manifest"]["generated_at"]
    fingerprint = bundle["manifest"]["logical_data_fingerprint"]
    assert fingerprint == later["manifest"]["logical_data_fingerprint"]
    for change in ({"seed": 43}, {"user_count": 4}, {"listing_count": 0}):
        changed = build_bundle(**{**CONFIG, **change}, generated_at=RUN_TIME)
        assert changed["manifest"]["logical_data_fingerprint"] != fingerprint
    validate_bundle(bundle)
    validate_bundle(later)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b["manifest"].update(logical_data_fingerprint="sha256:" + "0" * 64),
        lambda b: b["manifest"]["observed_counts"].update(users=2),
        lambda b: b["records"].pop(),
        lambda b: b["records"].reverse(),
        lambda b: b["manifest"].update(schema_version="final-unreviewed"),
        lambda b: b["manifest"].update(config_version="unreviewed"),
        lambda b: b["manifest"].update(extra=True),
        lambda b: b["records"][0].update(ordinal=True),
        lambda b: b["records"][0].update(example_email="private-sentinel"),
        lambda b: b["manifest"].update(generated_at="2026-01-01T00:00:00"),
        lambda b: b["manifest"].update(generated_at="2026-01-01T00:00:00Z"),
    ],
    ids=[
        "hash",
        "counts",
        "missing-row",
        "order",
        "schema",
        "config",
        "extra",
        "bool",
        "unsafe-value",
        "naive",
        "precision",
    ],
)
def test_bundle_tamper_rejected(bundle, mutate):
    """Closed manifests verify content/types/order as well as the claimed hash."""
    mutate(bundle)
    with pytest.raises(ValueError) as error:
        validate_bundle(bundle)
    assert "private-sentinel" not in str(error.value)


def test_aware_time_normalization_and_finite_json():
    """UTC format rejects naive instants and JSON cannot contain NaN/infinity."""
    offset = timezone(timedelta(hours=5, minutes=30))
    value = build_bundle(
        seed=0,
        user_count=0,
        listing_count=0,
        generated_at=datetime(2026, 1, 1, 5, 30, tzinfo=offset),
    )
    assert value["manifest"]["generated_at"] == "2026-01-01T00:00:00.000000Z"
    validate_bundle(value)
    with pytest.raises(ValueError):
        build_bundle(**CONFIG, generated_at=datetime(2026, 1, 1))
    for invalid in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            canonical_json({"value": invalid})


def test_run_round_trip_and_no_overwrite(run_root):
    """Repeated input reproduces hashes while an existing run remains untouched."""
    first = files.write_run(name="first", **CONFIG)
    second = files.write_run(name="second", **CONFIG)
    assert files.validate_run("first") == first
    assert files.validate_run("second") == second
    assert first["logical_data_fingerprint"] == second["logical_data_fingerprint"]
    original = (run_root / "first/dataset.json").read_bytes()
    with pytest.raises(FileExistsError):
        files.write_run(name="first", seed=0, user_count=0, listing_count=0)
    assert (run_root / "first/dataset.json").read_bytes() == original
    (run_root / "empty-existing").mkdir()
    with pytest.raises(FileExistsError):
        files.write_run(name="empty-existing", **CONFIG)


@pytest.mark.parametrize(
    "name", ["../escape", "/absolute", "bad/path", "Uppercase", "", ".", "a" * 65]
)
def test_unsafe_names_create_nothing(run_root, name):
    """Path-shaped/invalid names must fail without creating the output root."""
    with pytest.raises(ValueError):
        files.write_run(name=name, **CONFIG)
    assert not run_root.exists()


def test_invalid_counts_create_nothing(run_root):
    """Configuration validation precedes all run-directory creation."""
    with pytest.raises(ValueError):
        files.write_run(name="invalid", seed=1, user_count=-1, listing_count=0)
    assert not run_root.exists()


@pytest.mark.parametrize("location", ["root", "run", "file"])
def test_symlink_targets_rejected(run_root, tmp_path, location):
    """Root/run/file redirection cannot read or write an outside target."""
    outside = tmp_path / "outside"
    outside.mkdir()
    if location == "root":
        run_root.symlink_to(outside, target_is_directory=True)
        with pytest.raises(ValueError):
            files.write_run(name="linked", **CONFIG)
    elif location == "run":
        run_root.mkdir()
        (run_root / "linked").symlink_to(outside, target_is_directory=True)
        with pytest.raises(ValueError):
            files.validate_run("linked")
    else:
        files.write_run(name="linked", **CONFIG)
        target = run_root / "linked/dataset.json"
        target.unlink()
        target.symlink_to(outside)
        with pytest.raises(ValueError):
            files.validate_run("linked")
    assert not list(outside.iterdir())


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "invalid-json",
        "non-utf8",
        "mismatch",
        "directory",
        "oversized",
    ],
)
def test_partial_or_corrupt_runs_fail(run_root, monkeypatch, damage):
    """Incomplete/ambiguous/corrupt manifests and oversized files cannot validate."""
    files.write_run(name="damaged", **CONFIG)
    target = run_root / "damaged/manifest.json"
    if damage == "missing":
        target.unlink()
    elif damage == "duplicate":
        target.write_text('{"key":1,"key":2}', encoding="utf-8")
    elif damage == "invalid-json":
        target.write_text("private-sentinel", encoding="utf-8")
    elif damage == "non-utf8":
        target.write_bytes('{"value":1}'.encode("utf-16"))
    elif damage == "mismatch":
        value = json.loads(target.read_text())
        value["observed_counts"]["users"] = 99
        target.write_text(json.dumps(value), encoding="utf-8")
    elif damage == "directory":
        target.unlink()
        target.mkdir()
    else:
        monkeypatch.setattr(files, "MAX_FILE_BYTES", 1)
    with pytest.raises(ValueError) as error:
        files.validate_run("damaged")
    assert "private-sentinel" not in str(error.value)
    with pytest.raises(FileExistsError):
        files.write_run(name="damaged", **CONFIG)


def test_file_cli_success(run_root, capsys):
    """Public file-command arguments generate/validate the same run fingerprint."""
    assert (
        files.main(
            [
                "generate",
                "--name",
                "cli",
                "--seed",
                "42",
                "--users",
                "3",
                "--listings",
                "2",
            ]
        )
        == 0
    )
    first = capsys.readouterr()
    assert files.main(["validate", "--name", "cli"]) == 0
    second = capsys.readouterr()
    assert first.out == second.out and first.out.startswith("sha256:")
    assert first.err == second.err == ""


@pytest.mark.parametrize(
    "argv",
    [
        ["generate", "--name", "valid"],
        [
            "generate",
            "--name",
            "../private-sentinel",
            "--seed",
            "0",
            "--users",
            "0",
            "--listings",
            "0",
        ],
        [
            "generate",
            "--name",
            "valid",
            "--seed",
            "private-sentinel",
            "--users",
            "0",
            "--listings",
            "0",
        ],
        ["validate", "--name", "valid", "--seed", "0"],
        ["validate", "--name", "valid", "--database-url", "private-sentinel"],
        ["private-sentinel"],
    ],
)
def test_file_cli_refuses_unsafe_input(run_root, capsys, argv):
    """Unknown targets/operations and bad arguments fail without echo or writes."""
    with pytest.raises(SystemExit) as error:
        files.main(argv)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert not output.out and "private-sentinel" not in output.err
    assert not run_root.exists()


def test_loader_names_real_prerequisites_without_output(run_root, capsys):
    """The unavailable loader cannot silently succeed or create data files."""
    with pytest.raises(SystemExit) as error:
        files.main(["load"])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert all(name in output.err for name in ("DL-00", "ID-READY/LI-CORE", "SE-01"))
    assert not run_root.exists()


def test_template_claims_no_human_review_or_labels():
    """The retained starter must stay draft, never fabricated evaluation evidence."""
    path = REPOSITORY / "data/evaluation/query-labels.template.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert value["status"] == "draft" and value["queries"] == []
    assert all(item is None for item in value["dataset"].values())
    assert all(item is None for item in value["review"].values())
    assert value["search_contract_revision"] is None


@pytest.mark.parametrize(
    "path,ignored",
    [
        ("data/runs/example/dataset.json", True),
        ("data/runs/example/manifest.json", False),
        ("data/evaluation/query-labels.template.json", False),
        ("data/generators/preview.py", False),
    ],
)
def test_git_retains_reproduction_sources(path, ignored):
    """Ignore rules hide regenerable payload only, preserving inputs/manifests."""
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", path],
        cwd=REPOSITORY,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == (0 if ignored else 1)
