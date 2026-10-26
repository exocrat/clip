"""Actual native embedding integrity/races in the disposable database only.

No SQL emulator or fake inference engine. Coordinate vectors test persistence and
math, not model quality. The first test rolls back all fixtures; concurrency
requires committed synthetic fixtures, retained until the runner destroys its
own disposable container. No reset/external target accepted or executed here.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import os
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
import pytest
from psycopg.types.json import Jsonb

from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_types import (
    EmbeddingPart,
    default_pipeline_spec,
    pipeline_spec,
)
from data.generators.preview import stable_id

VECTOR = (1.0,) + (0.0,) * 383
PARTS = (EmbeddingPart("title", 0, VECTOR), EmbeddingPart("description", 0, VECTOR))
ROOT = Path(__file__).resolve().parents[5]


def target():
    """Skip without the existing private runner URL; verify server identity below."""
    value = os.environ.get("LISTINGS_TEST_DATABASE_URL")
    if not value:
        pytest.skip(
            "Run scripts/check_database.py --listings-store for real PostgreSQL"
        )
    return value


async def connect(value):
    """Enforce the exact disposable DB and Unix socket before any fixture writes."""
    params = psycopg.conninfo.conninfo_to_dict(value)
    socket = Path(params.get("host", ""))
    if (
        set(params) - {"user", "password", "dbname", "host", "port", "sslmode"}
        or params.get("user") != "clip_ci"
        or params.get("dbname") != "clip_test_ci"
        or params.get("port", "5432") not in {"5432", "55438"}
        or socket.name != "pgsocket"
        or not socket.parent.name.startswith("clip-listings-test-")
        or str(socket.parent.parent) not in {"/tmp", "/private/tmp"}
        or any(name.startswith("PG") for name in os.environ)
    ):
        raise ValueError("Only the disposable runner target is allowed")
    connection = await psycopg.AsyncConnection.connect(
        value, row_factory=dict_row, autocommit=True
    )
    row = await (
        await connection.execute(
            "SELECT current_database() AS name,inet_server_addr() IS NULL AS local_socket"
        )
    ).fetchone()
    assert row == {"name": "clip_test_ci", "local_socket": True}
    return connection


async def seed_listing(connection, seed, *, now=None):
    """Insert one controlled old-unavailable listing with confirmed image metadata."""
    # Optional fixed server instant lets consumers create deterministic sort
    # ties at INSERT time; created_at is immutable and must never be rewritten.
    now = now if now is not None else datetime.now(UTC)
    old = now - timedelta(days=200)
    owner = UUID(stable_id(seed, "user_placeholder", 1))
    listing = UUID(stable_id(seed, "listing_placeholder", 1))
    upload = UUID(stable_id(seed, "listing_placeholder", 2))
    await connection.execute(
        "INSERT INTO identity.users(id,account_class,status,display_name) VALUES (%s,'regular','active','Synthetic embedding owner')",
        (owner,),
    )
    await connection.execute(
        """INSERT INTO listings.sale_listings
        (id,owner_id,title,description,category_id,condition_code,asking_price_paise,negotiable,
         availability,available_from,available_until,created_at,updated_at)
        SELECT %s,%s,'Synthetic embedding bicycle','Controlled embedding fixture',id,'good',0,false,
         'unavailable',%s,%s,%s,%s FROM listings.categories WHERE code='bicycles'""",
        (listing, owner, old, old + timedelta(days=1), old, old),
    )
    key = f"synthetic-embedding/{upload}"
    await connection.execute(
        """INSERT INTO listings.image_uploads
        (id,owner_id,operation_id,object_key,state,created_at,expires_at,confirmed_at,
         requested_media_type,requested_size_bytes,confirmed_media_type,confirmed_size_bytes)
        VALUES (%s,%s,%s,%s,'confirmed',%s,%s,%s,'image/png',1,'image/png',1)""",
        (upload, owner, upload, key, now, now + timedelta(days=1), now),
    )
    await connection.execute(
        "INSERT INTO listings.images(id,listing_id,upload_id,object_key,position,media_type,size_bytes) VALUES (%s,%s,%s,%s,0,'image/png',1)",
        (upload, listing, upload, key),
    )
    return listing


async def retire(connection, listing):
    """Exercise approved derived cleanup through real own-schema retirement writes.

    The old-unavailable fixture has no conversations. This verifies the database
    embedding mechanism, not real Conversations retirement-marker integration.
    """
    # Parent/image publication is an atomic multi-write transition. The test
    # earlier forces constraints immediate to inspect assertions, so restore
    # only these initially-deferred publication constraints for retirement.
    await connection.execute(
        "SET CONSTRAINTS listings.listing_publication,listings.image_publication DEFERRED"
    )
    now = datetime.now(UTC)
    operation = UUID(stable_id(94003, "listing_placeholder", 1))
    await connection.execute(
        "UPDATE listings.sale_listings SET retirement_pending_operation_id=%s,retirement_pending_cutoff_utc=%s WHERE id=%s",
        (operation, now - timedelta(days=90), listing),
    )
    await connection.execute(
        "UPDATE listings.images SET retired_at=%s WHERE listing_id=%s AND retired_at IS NULL",
        (now, listing),
    )
    await connection.execute(
        """UPDATE listings.sale_listings SET title=NULL,description=NULL,category_id=NULL,
        condition_code=NULL,asking_price_paise=NULL,negotiable=NULL,pickup_area=NULL,
        proof_available=NULL,selected_buyer_id=NULL,selected_conversation_id=NULL,
        available_until=NULL,availability='unavailable',retirement_eligible_since=NULL,
        retired_at=%s,retirement_pending_operation_id=NULL,retirement_pending_cutoff_utc=NULL,
        updated_at=%s WHERE id=%s""",
        (now, now, listing),
    )


def test_native_embedding_integrity_and_recovery():
    asyncio.run(exercise_integrity(target()))


async def exercise_integrity(value):
    """Check actual trigger, lease, publication, rollback, validation and cleanup paths."""
    async with await connect(value) as connection:
        async with connection.transaction(force_rollback=True):
            await connection.execute("SET LOCAL statement_timeout='10s'")
            await connection.execute("SET LOCAL lock_timeout='3s'")
            store = EmbeddingStore(connection)
            spec = default_pipeline_spec()
            await store.register(spec)
            await store.set_state(spec, "building")
            listing = await seed_listing(connection, 94001)
            await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            with pytest.raises(
                psycopg.errors.CheckViolation, match="coverage incomplete"
            ):
                async with connection.transaction():
                    await store.set_state(spec, "serving")
            with pytest.raises(psycopg.errors.CheckViolation, match="immutable"):
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE listings.embedding_pipelines SET encoding=%s WHERE pipeline_id=%s",
                        (Jsonb({"changed": True}), spec.pipeline_id),
                    )
            receipt = await store.claim()
            assert receipt is not None and receipt.listing_id == listing
            assert await store.claim() is None
            title = b"Synthetic embedding bicycle"
            description = b"Controlled embedding fixture"
            expected = hashlib.sha256(
                b"clip-listing-embedding-source-v1"
                + len(title).to_bytes(8, "big")
                + title
                + len(description).to_bytes(8, "big")
                + description
            ).digest()
            assert receipt.source_fingerprint == expected
            # Publication inside an aborted transaction leaves no ready vectors.
            async with connection.transaction(force_rollback=True):
                assert await store.complete(receipt, PARTS, 1)
                await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            assert await store.complete(receipt, PARTS, 1)
            await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            assert not await store.complete(receipt, PARTS, 1)
            row = await (
                await connection.execute(
                    "SELECT state,title_count,description_count FROM listings.embedding_generations WHERE listing_id=%s",
                    (listing,),
                )
            ).fetchone()
            assert row == {"state": "ready", "title_count": 1, "description_count": 1}
            cosine = await (
                await connection.execute(
                    "SELECT listings.embedding_cosine(%s::real[],%s::real[]) AS value",
                    (list(VECTOR), list(VECTOR)),
                )
            ).fetchone()
            assert cosine and cosine["value"] == pytest.approx(1)
            for vector in (
                [0.0] * 384,
                [float("nan")] + [0.0] * 383,
                [float("inf")] + [0.0] * 383,
                [None] + [0.0] * 383,
                [1.0],
            ):
                result = await (
                    await connection.execute(
                        "SELECT listings.embedding_vector_valid(%s::real[]) AS valid",
                        (vector,),
                    )
                ).fetchone()
                assert result and result["valid"] is False
            with pytest.raises(psycopg.errors.CheckViolation):
                async with connection.transaction():
                    await connection.execute(
                        "UPDATE listings.embedding_chunks SET vector=%s::real[] WHERE generation_id=%s AND part_kind='title'",
                        ([0.0] * 384, receipt.generation_id),
                    )
            # A ready marker cannot hide a removed ending vector.
            with pytest.raises(psycopg.errors.CheckViolation):
                async with connection.transaction():
                    await connection.execute(
                        "DELETE FROM listings.embedding_chunks WHERE generation_id=%s AND part_kind='description'",
                        (receipt.generation_id,),
                    )
                    await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            # The exact down section must refuse populated derived content.
            down = (
                (
                    ROOT
                    / "database/migrations/20261024153316_listing_embedding_generations.sql"
                )
                .read_text()
                .split("-- migrate:down", 1)[1]
            )
            with pytest.raises(
                psycopg.errors.CheckViolation, match="Populated embedding store"
            ):
                async with connection.transaction():
                    await connection.execute(down)
            await connection.execute(
                "UPDATE listings.sale_listings SET asking_price_paise=100,revision=revision+1 WHERE id=%s",
                (listing,),
            )
            kept = await (
                await connection.execute(
                    "SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s",
                    (listing,),
                )
            ).fetchone()
            assert kept and kept["generation_id"] == receipt.generation_id
            await connection.execute(
                "UPDATE listings.sale_listings SET title='Changed synthetic title' WHERE id=%s",
                (listing,),
            )
            assert not await store.complete(receipt, PARTS, 1)
            await connection.execute(
                "UPDATE listings.sale_listings SET title='Synthetic embedding bicycle' WHERE id=%s",
                (listing,),
            )
            assert not await store.complete(
                receipt, PARTS, 1
            )  # same hash, new generation
            fresh = await store.claim()
            assert fresh is not None and fresh.generation_id != receipt.generation_id
            assert await store.fail(fresh, "timeout")
            await connection.execute(
                "UPDATE listings.embedding_generations SET retry_after=clock_timestamp()-interval '1 second' WHERE listing_id=%s",
                (listing,),
            )
            second = await store.claim()
            assert second is not None
            await connection.execute(
                "UPDATE listings.embedding_generations SET lease_until=clock_timestamp()-interval '1 second' WHERE listing_id=%s",
                (listing,),
            )
            reclaimed = await store.claim()
            assert reclaimed is not None and reclaimed.lease_token != second.lease_token
            assert not await store.complete(second, PARTS, 1)
            assert not await store.fail(second, "timeout")
            assert await store.complete(reclaimed, PARTS, 1)
            await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            # Real retry exhaustion stops rather than spinning forever.
            await connection.execute(
                "UPDATE listings.sale_listings SET description='Retry controlled fixture' WHERE id=%s",
                (listing,),
            )
            for attempt in range(1, 6):
                candidate = await store.claim()
                assert candidate is not None
                assert await store.fail(candidate, "timeout")
                if attempt < 5:
                    await connection.execute(
                        "UPDATE listings.embedding_generations SET retry_after=clock_timestamp()-interval '1 second' WHERE listing_id=%s",
                        (listing,),
                    )
            failed = await (
                await connection.execute(
                    "SELECT state,attempts FROM listings.embedding_generations WHERE listing_id=%s",
                    (listing,),
                )
            ).fetchone()
            assert failed == {"state": "failed", "attempts": 5}
            assert await store.retry_failed(spec, listing)
            retried = await (
                await connection.execute(
                    "SELECT generation_id,state,attempts FROM listings.embedding_generations WHERE listing_id=%s",
                    (listing,),
                )
            ).fetchone()
            assert retried and retried["generation_id"] != candidate.generation_id
            assert retried["state"] == "pending" and retried["attempts"] == 0
            assert 0 <= await store.queue_missing(spec, 1) <= 1
            await retire(connection, listing)
            await connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
            count = await (
                await connection.execute(
                    "SELECT count(*) AS count FROM listings.embedding_generations WHERE listing_id=%s",
                    (listing,),
                )
            ).fetchone()
            assert count == {"count": 0}
            assert not await store.complete(reclaimed, PARTS, 1)


def test_native_two_connection_edit_and_retirement_fences():
    asyncio.run(exercise_concurrency(target()))


async def wait_for_lock(observer, waiting):
    """Use a server-observed lock barrier, never assume a scheduling sleep is proof."""
    for _ in range(200):
        row = await (
            await observer.execute(
                "SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s",
                (waiting.info.backend_pid,),
            )
        ).fetchone()
        if row and row["wait_event_type"] == "Lock":
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Native worker did not reach expected row-lock barrier")


async def blocked_publication(first, second, store, receipt, change):
    """Observe a blocked publisher, commit a conflicting change, drain owned task."""
    publishing = None
    try:
        async with first.transaction():
            await first.execute(
                "SELECT id FROM listings.sale_listings WHERE id=%s FOR UPDATE",
                (receipt.listing_id,),
            )
            publishing = asyncio.create_task(store.complete(receipt, PARTS, 1))
            await wait_for_lock(first, second)
            if change == "edit":
                await first.execute(
                    "UPDATE listings.sale_listings SET description='New controlled description' WHERE id=%s",
                    (receipt.listing_id,),
                )
            else:
                await retire(first, receipt.listing_id)
        assert not await asyncio.wait_for(publishing, timeout=5)
    finally:
        if publishing is not None:
            if not publishing.done():
                publishing.cancel()
            await asyncio.gather(publishing, return_exceptions=True)


async def exercise_concurrency(value):
    """Commit synthetic fixture solely for genuine two-connection lock races."""
    async with await connect(value) as first, await connect(value) as second:
        spec = default_pipeline_spec()
        left, right = EmbeddingStore(first), EmbeddingStore(second)
        async with first.transaction():
            await first.execute("SET LOCAL statement_timeout='10s'")
            await left.register(spec)
            await left.set_state(spec, "building")
            listing = await seed_listing(first, 94002)
        results = await asyncio.wait_for(
            asyncio.gather(left.claim(), right.claim()), timeout=5
        )
        receipts = [receipt for receipt in results if receipt is not None]
        assert len(receipts) == 1 and receipts[0].listing_id == listing
        receipt = receipts[0]
        await blocked_publication(first, second, right, receipt, "edit")
        fresh = await left.claim()
        assert fresh is not None
        await blocked_publication(first, second, right, fresh, "retire")
        row = await (
            await second.execute(
                "SELECT count(*) AS count FROM listings.embedding_generations WHERE listing_id=%s",
                (listing,),
            )
        ).fetchone()
        assert row == {"count": 0}


@pytest.mark.parametrize(
    "value",
    [
        "postgresql://clip_ci@remote.invalid/clip_test_ci",
        "postgresql://clip_ci@/other?host=/tmp/clip-listings-test-example/pgsocket",
        "postgresql://clip_ci@/clip_test_ci?host=/tmp/other/pgsocket",
    ],
)
def test_embedding_native_gate_refuses_other_targets_before_connect(value):
    """Pure guard test; rejected targets must cause no network/database access."""
    with pytest.raises(ValueError, match="disposable runner"):
        asyncio.run(connect(value))


def math_pipeline(index):
    """Allocate a synthetic registry space; this runtime version is never installed.

    Coordinate vectors exercise only SQL lifecycle. These deliberately synthetic
    pins must never be mistaken for a working helper/model/relevance result.
    """
    encoding = default_pipeline_spec().encoding
    encoding["numpy"] = f"0.0.{index}"
    return pipeline_spec(encoding)


async def drain_math_jobs(store):
    """Complete bounded native fixture jobs without simulating inference/ranking."""
    count = 0
    while count < 60:
        receipt = await store.claim()
        if receipt is None:
            return count
        assert await store.complete(receipt, PARTS, 1)
        count += 1
    raise AssertionError("Native fixture work exceeded its 60-job ceiling")


async def missing_coverage(connection, spec):
    """Measure actual retained-source coverage, independent of serving enum state."""
    row = await (
        await connection.execute(
            """SELECT count(*) AS missing FROM listings.sale_listings AS listing
        LEFT JOIN listings.embedding_generations AS generation
          ON generation.listing_id=listing.id AND generation.pipeline_id=%s
        WHERE listing.retired_at IS NULL AND listing.retirement_pending_operation_id IS NULL
          AND (generation.state IS DISTINCT FROM 'ready' OR generation.source_fingerprint IS DISTINCT FROM
              listings.embedding_source_fingerprint(listing.title,listing.description))""",
            (spec.pipeline_id,),
        )
    ).fetchone()
    return row["missing"]


async def serving_ids(connection):
    """Observe committed registry snapshots without importing a public search path."""
    rows = await (
        await connection.execute(
            "SELECT pipeline_id FROM listings.embedding_pipelines WHERE state='serving' ORDER BY pipeline_id"
        )
    ).fetchall()
    return [row["pipeline_id"] for row in rows]


def test_native_bootstrap_and_atomic_pipeline_switch_with_mutation():
    """Run the remaining registry/bootstrap races only inside the disposable runner."""
    asyncio.run(exercise_pipeline_switch(target()))


async def exercise_pipeline_switch(value):
    """Verify bounded resume, incomplete promotion, limits and concurrent source edits.

    This private corpus is wholly synthetic and exclusively owned by the runner.
    Temporarily retire prior fixture pipelines, restore their states afterward,
    and delete only this test's mathematical generations/pipeline configuration.
    Never starts an inference worker or enables application/API search.
    """
    async with await connect(value) as first, await connect(value) as second:
        await first.execute("SET statement_timeout='5s'")
        await second.execute("SET statement_timeout='5s'")
        left, right = EmbeddingStore(first), EmbeddingStore(second)
        existing = await (
            await first.execute(
                "SELECT encoding,state FROM listings.embedding_pipelines ORDER BY pipeline_id"
            )
        ).fetchall()
        specs = [math_pipeline(94011), math_pipeline(94012), math_pipeline(94013)]
        a, b, c = specs
        listing = None
        try:
            for row in existing:
                await left.set_state(pipeline_spec(row["encoding"]), "retired")
            for spec in specs:
                await left.register(spec)
            corpus = await (
                await first.execute(
                    "SELECT count(*) AS count FROM listings.sale_listings WHERE retired_at IS NULL"
                )
            ).fetchone()
            assert corpus["count"] < 30
            # The INSERT trigger observes A as planned. Enable/reconcile from a
            # different connection before the source INSERT commits: its row is
            # invisible to that first reconciliation and must be found on resume.
            async with first.transaction():
                listing = await seed_listing(first, 94011)
                await right.set_state(a, "building")
                assert 0 <= await right.queue_missing(a, 1) <= 1
            absent = await (
                await second.execute(
                    "SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s",
                    (listing, a.pipeline_id),
                )
            ).fetchone()
            assert absent is None
            with pytest.raises(
                psycopg.errors.CheckViolation, match="coverage incomplete"
            ):
                await right.set_state(a, "serving")
            queued = 0
            for _ in range(31):
                count = await right.queue_missing(a, 1)
                assert count in {0, 1}
                queued += count
                if count == 0:
                    break
            else:
                raise AssertionError("Bootstrap resume did not converge")
            assert queued >= 1
            assert await drain_math_jobs(right) >= 1
            assert await missing_coverage(second, a) == 0
            before = await (
                await second.execute(
                    "SELECT listing_id,generation_id FROM listings.embedding_generations WHERE pipeline_id=%s ORDER BY listing_id",
                    (a.pipeline_id,),
                )
            ).fetchall()
            assert await right.queue_missing(a, 1) == 0
            after = await (
                await second.execute(
                    "SELECT listing_id,generation_id FROM listings.embedding_generations WHERE pipeline_id=%s ORDER BY listing_id",
                    (a.pipeline_id,),
                )
            ).fetchall()
            assert before == after  # resumable/idempotent, no ready identity rewrite
            await right.set_state(a, "serving")
            assert await serving_ids(first) == [a.pipeline_id]
            await right.set_state(b, "building")
            with pytest.raises(psycopg.errors.CheckViolation, match="pipeline limit"):
                await right.set_state(c, "building")
            with pytest.raises(
                psycopg.errors.CheckViolation, match="coverage incomplete"
            ):
                await right.set_state(b, "serving")
            assert await serving_ids(first) == [a.pipeline_id]
            assert await right.queue_missing(b, 1000) >= 1
            assert await drain_math_jobs(right) >= 1
            assert await missing_coverage(second, b) == 0
            with pytest.raises(psycopg.errors.UniqueViolation):
                await right.set_state(b, "serving")
            assert await serving_ids(first) == [a.pipeline_id]
            old_ids = await (
                await first.execute(
                    "SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s ORDER BY pipeline_id",
                    (listing,),
                )
            ).fetchall()
            # Edit remains uncommitted while the switch sees the prior complete
            # source snapshot. A serving enum cannot promise perpetual coverage:
            # the reader must check actual current generations after this edit.
            async with first.transaction():
                await first.execute(
                    "UPDATE listings.sale_listings SET description='Concurrent pipeline source edit' WHERE id=%s",
                    (listing,),
                )
                async with second.transaction():
                    await right.set_state(a, "retired")
                    assert await serving_ids(first) == [a.pipeline_id]
                    await right.set_state(b, "serving")
                assert await serving_ids(first) == [b.pipeline_id]
            assert await serving_ids(second) == [b.pipeline_id]
            assert await missing_coverage(second, b) >= 1
            current_ids = await (
                await second.execute(
                    "SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s ORDER BY pipeline_id",
                    (listing,),
                )
            ).fetchall()
            assert not {row["generation_id"] for row in old_ids}.intersection(
                row["generation_id"] for row in current_ids
            )
            old_vectors = await (
                await second.execute(
                    "SELECT count(*) AS count FROM listings.embedding_chunks WHERE generation_id=ANY(%s::uuid[])",
                    ([row["generation_id"] for row in old_ids],),
                )
            ).fetchone()
            assert old_vectors == {"count": 0}
            assert await drain_math_jobs(right) >= 1
            assert await missing_coverage(second, b) == 0
        finally:
            # Owned mathematical fixtures only. Retire source before restoring
            # any old serving space, so its prior coverage is unchanged.
            if listing is not None:
                async with first.transaction():
                    await retire(first, listing)
            for spec in specs:
                await left.set_state(spec, "retired")
                async with first.transaction():
                    await first.execute(
                        "DELETE FROM listings.embedding_generations WHERE pipeline_id=%s",
                        (spec.pipeline_id,),
                    )
                    await first.execute(
                        "DELETE FROM listings.embedding_pipelines WHERE pipeline_id=%s",
                        (spec.pipeline_id,),
                    )
            for row in existing:
                await left.set_state(pipeline_spec(row["encoding"]), row["state"])
