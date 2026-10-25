"""Explicit bounded pipeline operator CLI; target approval remains a human gate.

Read CLIP_DATABASE_URL only as a process secret, never a CLI argument/dotenv.
Require exact declared connection/server identity and pinned pipeline binding.
Status is read-only; each mutation separately requires --execute. This flag is
an execution guard, not evidence of approval for any shared/cloud target.
"""

import argparse
import asyncio
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from psycopg import AsyncConnection, Error as DatabaseError  # noqa: E402
from psycopg.conninfo import conninfo_to_dict  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app.domains.listings.embedding_bootstrap import (
    EmbeddingBootstrap,
    BootstrapBlocked,
)  # noqa: E402
from app.domains.listings.embedding_types import default_pipeline_spec  # noqa: E402


class TargetRejected(ValueError):
    """A declared binding is absent/mismatched; never include submitted values."""


def validate_target(args: argparse.Namespace, secret: str) -> None:
    """Bind URL host/port/database/login and pipeline before making a connection.

    Forbid ambient libpq/service/options target indirection. SSL inputs may remain
    in the approved secret; none are printed or copied into evidence. No target
    or credential discovery occurs, and mutations require explicit execution.
    """
    if any(key.startswith("PG") for key in os.environ):
        raise TargetRejected("Ambient libpq configuration forbidden")
    if args.pipeline_id != default_pipeline_spec().pipeline_id.hex():
        raise TargetRejected("Unsupported pipeline")
    if args.action != "status" and not args.execute:
        raise TargetRejected("Mutation requires explicit execution")
    if args.action != "queue" and args.batch_size is not None:
        raise TargetRejected("Batch size is only valid for queue")
    if args.action == "queue" and (
        type(args.batch_size) is not int or not 1 <= args.batch_size <= 1000
    ):
        raise TargetRejected("Queue requires bounded batch size")
    if not secret:
        raise TargetRejected("Database secret is required")
    params = conninfo_to_dict(secret)
    if set(params) - {
        "host",
        "port",
        "dbname",
        "user",
        "password",
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "connect_timeout",
        "application_name",
    }:
        raise TargetRejected("Unsupported connection indirection")
    expected = {
        "host": args.expected_host,
        "port": str(args.expected_port),
        "dbname": args.expected_database,
        "user": args.expected_role,
    }
    if any(params.get(key) != value for key, value in expected.items()):
        raise TargetRejected("Connection target mismatch")
    if any(not value or "," in value for value in expected.values()):
        raise TargetRejected("A single explicit target is required")


async def operate(args: argparse.Namespace, secret: str) -> dict:
    """Check actual server identity before one bounded explicit operator action."""
    validate_target(args, secret)
    async with asyncio.timeout(10):
        async with await AsyncConnection.connect(
            secret,
            autocommit=True,
            row_factory=dict_row,
            connect_timeout=5,
            options="-c statement_timeout=5000 -c lock_timeout=1000",
        ) as connection:
            identity = await (
                await connection.execute(
                    "SELECT current_database() AS db,current_user AS role,session_user AS login"
                )
            ).fetchone()
            if (
                identity
                != {
                    "db": args.expected_database,
                    "role": args.expected_role,
                    "login": args.expected_role,
                }
                or connection.info.host != args.expected_host
                or connection.info.port != args.expected_port
            ):
                raise TargetRejected("Actual server target mismatch")
            bootstrap = EmbeddingBootstrap(connection)
            if args.action == "queue":
                queued = await bootstrap.queue(args.batch_size)
                report = await bootstrap.status()
                return {
                    "queued": queued,
                    "status": {**asdict(report), "complete": report.complete},
                }
            report = await {
                "status": bootstrap.status,
                "prepare": bootstrap.prepare,
                "activate": bootstrap.activate,
            }[args.action]()
            return {**asdict(report), "complete": report.complete}


def parser() -> argparse.ArgumentParser:
    """Expose only fixed actions and non-secret exact binding/limit arguments."""
    result = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument("action", choices=("status", "prepare", "queue", "activate"))
    result.add_argument("--expected-host", required=True)
    result.add_argument("--expected-port", type=int, required=True)
    result.add_argument("--expected-database", required=True)
    result.add_argument("--expected-role", required=True)
    result.add_argument("--pipeline-id", required=True)
    result.add_argument("--batch-size", type=int)
    result.add_argument("--execute", action="store_true")
    return result


def main() -> None:
    """Emit aggregate safe output/errors only; never print connection/source traces."""
    args = parser().parse_args()
    try:
        report = asyncio.run(operate(args, os.environ.get("CLIP_DATABASE_URL", "")))
    except BootstrapBlocked as error:
        print(json.dumps({"error": error.code}), file=sys.stderr)
        raise SystemExit(2) from None
    except TargetRejected, DatabaseError, OSError, ValueError, TimeoutError:
        print(json.dumps({"error": "pipeline_operation_refused"}), file=sys.stderr)
        raise SystemExit(2) from None
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
