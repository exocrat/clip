"""Offline Identity migration-review consistency check; never a live apply gate.

Reads this worktree and local Git objects only. Does not fetch refs, load settings,
retrieve credentials, connect to SQL, run Docker or contact a provider. Success
means the review package matches local source; human/cloud approvals stay separate.
"""

import argparse
from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.domains.identity.migration_runner import MigrationTarget, validate_manifest

EVIDENCE = Path("docs/evaluation/identity/id-01-step-12")
# Changes in these implementations invalidate the candidate's source review even
# when the SQL bytes themselves stay unchanged. Documentation-only commits do not.
REVIEWED_SOURCE = (
    "database/migrations",
    "database/roles/identity-runtime.sql.proposed",
    "apps/api/app/domains/identity/migration_runner.py",
    "apps/api/app/domains/identity/database_setup.py",
    "apps/api/app/domains/identity/runtime_database.py",
)


def git(root: Path, *arguments: str) -> bytes:
    """Read bounded local Git metadata, with no shell or credential/helper action."""
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        check=True,
        timeout=10,
    ).stdout


def audit(root: Path, upstream: str) -> dict[str, Any]:
    """Return safe check names; a consistent local candidate never authorizes DDL.

    Require a full immutable upstream SHA supplied by the operator. It must be an
    ancestor of HEAD and match the candidate base; a newly integrated main needs
    refreshed evidence. Never print exceptions or arbitrary file contents.
    """
    checks: dict[str, bool] = {}

    def check(name: str, operation: Callable[[], object]) -> None:
        """Keep independent findings visible without exposing underlying output."""
        try:
            checks[name] = bool(operation())
        except Exception:
            checks[name] = False

    result: dict[str, Any] = {
        "mode": "offline_review_consistency",
        "ready_for_live": False,
        "checks": checks,
    }
    if not re.fullmatch(r"[0-9a-f]{40}", upstream):
        checks["immutable_upstream"] = False
        result["consistent"] = False
        return result
    check(
        "upstream_integrated",
        lambda: git(root, "merge-base", "--is-ancestor", upstream, "HEAD") == b"",
    )
    try:
        candidate_path = root / EVIDENCE / "shared-migration-apply-review.json"
        manifest_path = root / EVIDENCE / "shared-migration-manifest.json"
        if candidate_path.is_symlink() or manifest_path.is_symlink():
            raise ValueError
        candidate = json.loads(candidate_path.read_text())
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        checks["review_documents"] = False
        result["consistent"] = False
        return result
    check("candidate_base", lambda: candidate["upstream_base"] == upstream)
    check("manifest_base", lambda: manifest["recorded_upstream_revision"] == upstream)
    check(
        "manifest_reference",
        lambda: candidate["manifest_path"]
        == str(EVIDENCE / "shared-migration-manifest.json"),
    )
    check(
        "manifest_digest",
        lambda: hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        == candidate["manifest_sha256"],
    )

    def migration_chain() -> bool:
        """Use the actual runner's strict byte/count/head checks without SQL I/O."""
        versions = validate_manifest(
            root / "database/migrations",
            manifest_path,
            candidate["image_to_review"],
            MigrationTarget(15432, isolated=True),
        )
        return bool(
            len(versions) == candidate["migration_count"]
            and versions[-1] == candidate["head"]
        )

    check("runner_manifest_compatibility", migration_chain)
    check(
        "locally_tested_image",
        lambda: candidate["image_to_review"] == manifest["locally_tested_image_digest"],
    )

    def upstream_bytes() -> bool:
        """Compare every upstream SQL file, not just the historical eleven names."""
        names = (
            git(root, "ls-tree", "-r", "--name-only", upstream, "database/migrations")
            .decode()
            .splitlines()
        )
        sql = [name for name in names if name.endswith(".sql")]
        return bool(sql) and all(
            not (root / name).is_symlink()
            and (root / name).read_bytes() == git(root, "show", f"{upstream}:{name}")
            for name in sql
        )

    check("upstream_sql_preserved", upstream_bytes)

    def reviewed_source() -> bool:
        """Catch changed runner/setup SQL even with unchanged manifest hashes."""
        source = candidate["source_head"]
        if not re.fullmatch(r"[0-9a-f]{40}", source):
            return False
        git(root, "merge-base", "--is-ancestor", source, "HEAD")
        return not git(
            root,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            source,
            "--",
            *REVIEWED_SOURCE,
        )

    check("reviewed_source_unchanged", reviewed_source)
    result["consistent"] = all(checks.values())
    return result


def main() -> int:
    """Print only structured local findings; exit one on stale/invalid evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upstream",
        required=True,
        help="Exact accepted main commit already integrated locally",
    )
    args = parser.parse_args()
    result = audit(ROOT, args.upstream)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
