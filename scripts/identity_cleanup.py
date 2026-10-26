"""Target-checked Identity retention CLI; dry-run default, never schedules itself.

DSN comes only from CLIP_IDENTITY_DATABASE_URL, never an argument or output.
--apply is a write: review its exact target/dry-run and obtain the required
operator approval before real execution. Tests use only a new disposable DB.
"""

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from app.domains.identity.cleanup import IdentityCleanup


def main() -> int:
    """Require explicit expected database and emit only safe per-table counts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.expected_database in {"postgres", "template0", "template1"}:
            raise ValueError
        dsn = os.environ["CLIP_IDENTITY_DATABASE_URL"]

        def connect() -> psycopg.Connection[tuple[Any, ...]]:
            connection = psycopg.connect(dsn, autocommit=True, connect_timeout=3)
            try:
                row = connection.execute("SELECT current_database()").fetchone()
                if row is None or row[0] != args.expected_database:
                    raise ValueError
                return connection
            except Exception:
                connection.close()
                raise

        result = IdentityCleanup(connect, lambda: datetime.now(UTC)).run(
            apply=args.apply, batch_size=args.batch_size
        )
        print(
            json.dumps(
                {"dry_run": result.dry_run, "counts": result.counts}, sort_keys=True
            )
        )
        return 0
    except Exception:
        print(
            "Identity cleanup failed; target/configuration/checks require review",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
