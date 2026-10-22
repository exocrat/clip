"""Run the shared foundation checks, individually or as the local CI aggregate.

Setup must already be complete (uv sync --locked and npm ci); Docker is needed
for database/secret checks. Each command is rooted at this clone, has a bounded
runtime, preserves its exit status and stops the aggregate on first failure.
"""

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
# One editable command list serves Make and each labelled CI step.
CHECKS = {
    "ci-parity": ("uv", "run", "--locked", "python", "scripts/check_ci_parity.py"),
    "python-format": ("uv", "run", "--locked", "black", "--check", "--diff", "."),
    "python-tests": ("uv", "run", "--locked", "pytest", "-q", "-W", "error"),
    "data-tests": (
        "uv",
        "run",
        "--locked",
        "pytest",
        "data/tests",
        "-q",
        "-W",
        "error",
    ),
    "boundaries": ("uv", "run", "--locked", "python", "scripts/check_boundaries.py"),
    "contracts": (
        "uv",
        "run",
        "--locked",
        "python",
        "scripts/generate_contracts.py",
        "check",
    ),
    "contract-types": (
        "uv",
        "run",
        "--locked",
        "mypy",
        "--no-incremental",
        "apps/api/tests/domains/search/doubles/listings.py",
        "tests/contracts/conversations_consumer_types.py",
    ),
    "web": ("npm", "run", "check"),
    "database-safety": ("bash", "database/tests/local-db-safety.sh"),
    "database": ("uv", "run", "--locked", "python", "scripts/check_database.py"),
    "conversations-retirement": (
        "uv",
        "run",
        "--locked",
        "python",
        "scripts/check_conversations_retirement.py",
    ),
    "secrets": ("uv", "run", "--locked", "python", "scripts/check_secrets.py"),
}


def main():
    """Validate the selected check and fail visibly without shell interpretation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", nargs="?", default="all", choices=["all", *CHECKS])
    args = parser.parse_args()
    selected = CHECKS if args.check == "all" else [args.check]
    for name in selected:
        print(f"Checking {name} in {ROOT}", flush=True)
        try:
            code = subprocess.run(CHECKS[name], cwd=ROOT, timeout=600).returncode
        except OSError, subprocess.TimeoutExpired:
            print(f"FAIL: {name}; tool missing or 600-second timeout", flush=True)
            return 1
        if code:
            print(f"FAIL: {name} (exit {code})", flush=True)
            return code if code > 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
