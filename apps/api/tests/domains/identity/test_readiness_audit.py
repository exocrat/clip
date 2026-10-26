"""Local Git/migration evidence checks; no SQL, Docker, AWS or provider calls."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts import identity_readiness as readiness

ROOT = Path(__file__).resolve().parents[5]


def git(root, *args):
    """Create/read only the test's disposable local Git history, without hooks."""
    return (
        subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=root,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        .decode()
        .strip()
    )


@pytest.fixture
def package(tmp_path):
    """Build genuine upstream/implementation commits and matching review evidence."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic Review")
    git(root, "config", "user.email", "review@example.invalid")
    manifest = json.loads(
        (ROOT / readiness.EVIDENCE / "shared-migration-manifest.json").read_text()
    )
    for record in manifest["migrations"]:
        if record["version"] in {"20261023173439", "20261023192856", "20261023202807"}:
            continue
        path = root / record["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / record["path"], path)
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic upstream")
    base = git(root, "rev-parse", "HEAD")
    for name in readiness.REVIEWED_SOURCE:
        source = ROOT / name
        target = root / name
        if source.is_dir():
            # This fixture represents the exact reviewed package. New forwards
            # belong to a different candidate; never silently bless them here.
            target.mkdir(parents=True, exist_ok=True)
            for record in manifest["migrations"]:
                shutil.copyfile(ROOT / record["path"], root / record["path"])
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic implementation")
    head = git(root, "rev-parse", "HEAD")
    evidence = root / readiness.EVIDENCE
    evidence.mkdir(parents=True)
    manifest["recorded_upstream_revision"] = base
    manifest_path = evidence / "shared-migration-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    candidate = json.loads(
        (ROOT / readiness.EVIDENCE / "shared-migration-apply-review.json").read_text()
    )
    candidate.update(
        upstream_base=base,
        source_head=head,
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    )
    (evidence / "shared-migration-apply-review.json").write_text(json.dumps(candidate))
    return root, base


def test_consistent_package_never_implies_live_approval(package):
    root, base = package
    result = readiness.audit(root, base)
    assert result["consistent"]
    assert not result["ready_for_live"]
    assert all(result["checks"].values())


@pytest.mark.parametrize("change", ["edit", "extra", "missing", "symlink"])
def test_changed_migration_chain_is_rejected(package, change):
    root, base = package
    migration = sorted((root / "database/migrations").glob("*.sql"))[-1]
    if change == "edit":
        migration.write_text(migration.read_text() + "\n-- changed after review\n")
    elif change == "extra":
        (migration.parent / "20990101000000_unreviewed.sql").write_text("SELECT 1;")
    elif change == "missing":
        migration.unlink()
    else:
        target = root / "copied.sql"
        shutil.copyfile(migration, target)
        migration.unlink()
        migration.symlink_to(target)
    result = readiness.audit(root, base)
    assert not result["consistent"]
    assert not result["checks"]["runner_manifest_compatibility"]


def test_uncommitted_runner_change_invalidates_source_review(package):
    root, base = package
    path = root / "apps/api/app/domains/identity/migration_runner.py"
    path.write_text(path.read_text() + "\n# unreviewed source change\n")
    result = readiness.audit(root, base)
    assert not result["consistent"]
    assert result["checks"]["runner_manifest_compatibility"]
    assert not result["checks"]["reviewed_source_unchanged"]


def test_advanced_main_requires_updated_candidate_and_manifest(package):
    root, _ = package
    (root / "database/migrations/20990101000000_new_upstream.sql").write_text(
        "SELECT 1;"
    )
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic upstream advance")
    new_base = git(root, "rev-parse", "HEAD")
    result = readiness.audit(root, new_base)
    assert not result["consistent"]
    assert result["checks"]["upstream_integrated"]
    assert not result["checks"]["candidate_base"]
    assert not result["checks"]["manifest_base"]
    assert not result["checks"]["runner_manifest_compatibility"]


def test_document_hash_corruption_is_reported_without_contents(package):
    root, base = package
    path = root / readiness.EVIDENCE / "shared-migration-manifest.json"
    path.write_text(path.read_text() + "\n")
    result = readiness.audit(root, base)
    assert not result["consistent"]
    assert not result["checks"]["manifest_digest"]
    assert "migrations" not in result


def test_invalid_upstream_never_invokes_git_or_echoes_input(monkeypatch):
    def forbidden(*args):
        raise AssertionError("No command may execute for invalid input")

    monkeypatch.setattr(readiness, "git", forbidden)
    value = "--output=private-synthetic-value"
    result = readiness.audit(ROOT, value)
    assert not result["consistent"]
    assert value not in json.dumps(result)


def test_unintegrated_upstream_is_rejected(package):
    root, base = package
    git(root, "checkout", "-qb", "unintegrated", base)
    (root / "upstream-marker").write_text("new upstream")
    git(root, "add", "upstream-marker")
    git(root, "commit", "-qm", "Unintegrated upstream")
    other = git(root, "rev-parse", "HEAD")
    git(root, "checkout", "-")
    assert not readiness.audit(root, other)["checks"]["upstream_integrated"]


def test_candidate_image_must_match_recorded_local_evidence(package):
    root, base = package
    path = root / readiness.EVIDENCE / "shared-migration-apply-review.json"
    candidate = json.loads(path.read_text())
    candidate["image_to_review"] = "ghcr.io/amacneil/dbmate@sha256:" + "0" * 64
    path.write_text(json.dumps(candidate))
    result = readiness.audit(root, base)
    assert not result["consistent"]
    assert not result["checks"]["locally_tested_image"]


def test_source_diff_does_not_execute_external_diff_driver(package):
    root, base = package
    marker = root / "external-diff-ran"
    driver = root / "external-diff.sh"
    driver.write_text("#!/bin/sh\ntouch external-diff-ran\n")
    driver.chmod(0o700)
    git(root, "config", "diff.external", str(driver))
    path = root / "apps/api/app/domains/identity/migration_runner.py"
    path.write_text(path.read_text() + "\n# unreviewed source change\n")
    result = readiness.audit(root, base)
    assert not result["checks"]["reviewed_source_unchanged"]
    assert not marker.exists()
