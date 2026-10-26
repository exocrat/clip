"""Populated category migration proof in the existing disposable native target.

This fixture-only test may seed upstream tables. Search application code never
resolves private Listings UUIDs. No real target or cleanup implementation is used.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

from apps.api.tests.domains.listings.test_embedding_postgres import connect, target

ROOT = Path(__file__).resolve().parents[5]
MIGRATION = (
    ROOT / "database/migrations/20261025012200_wanted_category_code_reference.sql"
)


def test_native_wanted_category_populated_rollback_and_reapply():
    """Preserve content/metadata for open, unavailable, pending and retired rows."""
    asyncio.run(exercise(target()))


async def exercise(value):
    """Round-trip only inside a rollback transaction on the verified test server."""
    up, down = MIGRATION.read_text().split("-- migrate:down\n")
    async with await connect(value) as connection:
        async with connection.transaction(force_rollback=True):
            author = uuid4()
            await connection.execute(
                "INSERT INTO identity.users(id,account_class,status,display_name) "
                "VALUES(%s,'regular','active','Synthetic category migration author')",
                (author,),
            )
            identifiers = [uuid4() for _ in range(4)]
            for index, identifier in enumerate(identifiers):
                await connection.execute(
                    """INSERT INTO search.wanted_requests
                    (id,author_id,title,description,category_code,budget_paise,status,created_at,closed_at)
                    VALUES(%s,%s,'Synthetic request','Synthetic migration fixture','books',%s,%s,
                    statement_timestamp()-interval '200 days',
                    CASE WHEN %s THEN statement_timestamp()-interval '190 days' ELSE NULL END)""",
                    (
                        identifier,
                        author,
                        None if index == 0 else 0,
                        "open" if index == 0 else "unavailable",
                        index != 0,
                    ),
                )
            await connection.execute(
                """UPDATE search.wanted_requests SET
                retirement_pending_operation_id=%s,
                retirement_pending_cutoff_utc=statement_timestamp()-interval '90 days'
                WHERE id=%s""",
                (uuid4(), identifiers[2]),
            )
            # Only a controlled constraint fixture, not a production retirement
            # path: the request is old, unavailable, and has no conversations.
            await connection.execute(
                """UPDATE search.wanted_requests SET retired_at=statement_timestamp(),
                title=NULL,description=NULL,category_code=NULL,budget_paise=NULL WHERE id=%s""",
                (identifiers[3],),
            )
            # Historical assignment must survive category deactivation too.
            await connection.execute(
                "UPDATE listings.categories SET active=false WHERE code='books'"
            )

            async def snapshot(column):
                """Compare every retained field, excluding the renamed reference."""
                assert column in {"category_id", "category_code"}
                rows = await (
                    await connection.execute(
                        "SELECT id,to_jsonb(request)-%s AS content FROM search.wanted_requests AS request "
                        "WHERE author_id=%s ORDER BY id",
                        (column, author),
                    )
                ).fetchall()
                return rows

            original = await snapshot("category_code")
            await connection.execute(down)
            assert await snapshot("category_id") == original
            old_rows = await (
                await connection.execute(
                    "SELECT category_id FROM search.wanted_requests WHERE author_id=%s AND retired_at IS NULL",
                    (author,),
                )
            ).fetchall()
            category = await (
                await connection.execute(
                    "SELECT id FROM listings.categories WHERE code='books'"
                )
            ).fetchone()
            assert category is not None and all(
                row["category_id"] == category["id"] for row in old_rows
            )
            await connection.execute(up)
            assert await snapshot("category_code") == original
            rows = await (
                await connection.execute(
                    "SELECT category_code,retired_at FROM search.wanted_requests WHERE author_id=%s",
                    (author,),
                )
            ).fetchall()
            assert len(rows) == 4
            assert all(
                row["category_code"] == (None if row["retired_at"] else "books")
                for row in rows
            )
            functions = await (
                await connection.execute(
                    "SELECT count(*) AS total FROM pg_proc JOIN pg_namespace ON pg_namespace.oid=pronamespace "
                    "WHERE nspname='search' AND proname LIKE '_migrate_wanted_category_to_%'"
                )
            ).fetchone()
            assert functions == {"total": 0}
