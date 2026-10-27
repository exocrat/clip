"""Run approved Conversations retention on an explicitly checked target.

Dry-run by default. DSN comes from CLIP_CONVERSATIONS_DATABASE_URL, never argv
or output. Actual apply to persistent/shared targets needs its own operator run
approval. This command creates no schedule and accepts no client cutoff.
"""

import argparse
import asyncio
from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import sys

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps/api"))
from app.domains.conversations.cleanup import ConversationCleanup


async def execute(args: argparse.Namespace) -> None:
    """Validate database, host and port on every connection; print counts only."""
    if args.expected_database in {"postgres", "template0", "template1"}:
        raise ValueError("Application database required")

    async def check_target(connection: AsyncConnection) -> None:
        """Reject a mismatched DSN before the cleanup receives a connection."""
        info = connection.info
        if (
            info.dbname != args.expected_database
            or info.host != args.expected_host
            or info.port != args.expected_port
        ):
            raise ValueError("Target mismatch")

    async with AsyncConnectionPool(
        os.environ["CLIP_CONVERSATIONS_DATABASE_URL"],
        min_size=0,
        max_size=1,
        timeout=5,
        kwargs={"autocommit": True, "connect_timeout": 3},
        check=check_target,
        open=False,
    ) as pool:
        cleanup = ConversationCleanup(pool)
        if args.scope == "history":
            result = await cleanup.run(apply=args.apply, batch_size=args.batch_size)
        elif args.scope == "contact-shares":
            result = await cleanup.run_contact_shares(
                apply=args.apply, batch_size=args.batch_size
            )
        else:
            result = {
                "history": asdict(
                    await cleanup.run(apply=args.apply, batch_size=args.batch_size)
                ),
                "contact_shares": asdict(
                    await cleanup.run_contact_shares(
                        apply=args.apply, batch_size=args.batch_size
                    )
                ),
            }
    print(
        json.dumps(
            asdict(result) if not isinstance(result, dict) else result, sort_keys=True
        )
    )


def main() -> int:
    """Parse target assertions and mode; suppress private driver/config details."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--expected-host", required=True)
    parser.add_argument("--expected-port", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument(
        "--scope", choices=("history", "contact-shares", "all"), default="history"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    # Pool retries otherwise emit private connection/driver diagnostics before
    # the CLI can replace them with its reviewed generic failure message.
    logging.getLogger("psycopg.pool").disabled = True
    try:
        if not 1 <= args.expected_port <= 65535:
            raise ValueError("Invalid target port")
        asyncio.run(execute(args))
        return 0
    except Exception:
        print(
            "Conversation cleanup failed; review target/configuration/state",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
