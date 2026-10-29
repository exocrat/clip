"""Real PostgreSQL snapshot/coverage/ranking plus opted-in actual-model reads.

Coordinate vectors test SQL math only. The actual-model case has its own flag,
resource limits and evidence; no synthetic score proves inference quality/auth.
All targets use the existing private runner guard. No public application binding.
"""

import asyncio
from datetime import datetime, UTC, timedelta
import json
import math
import os
import time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.contracts.domain_types import ListingQuery, ListingSummary
from app.core.errors import ERRORS, PublicError
from app.domains.listings.browse_store import read_browse_page
from app.domains.listings.embedding_client import SemanticHelper
from app.domains.listings.embedding_store import EmbeddingStore
from app.domains.listings.embedding_types import (
    EmbeddingPart,
    default_pipeline_spec,
    pipeline_spec,
)
from app.domains.listings.embedding_worker import EmbeddingWorker
from app.domains.listings.hybrid_read import (
    bind_query,
    hybrid_statement,
    read_hybrid_page,
    search_hybrid_page,
)
from app.domains.listings.lexical_expansion import compile_expansion
from apps.api.tests.domains.listings.test_embedding_postgres import (
    connect,
    target,
    seed_listing,
    retire,
    wait_for_lock,
    ROOT,
)

VECTOR = (1.0,) + (0.0,) * 383


def parts(title_score, *description_scores):
    """Unit coordinate vectors have exact prescribed cosine against VECTOR."""

    def vector(score):
        return (score, math.sqrt(1 - score**2)) + (0.0,) * 382

    return (
        EmbeddingPart("title", 0, vector(title_score)),
        *(
            EmbeddingPart("description", index, vector(score))
            for index, score in enumerate(description_scores)
        ),
    )


async def live_listing(
    connection, seed, now, title, description, price=0, status="available"
):
    """One owned image-backed fixture; all relevance sources remain synthetic."""
    listing = await seed_listing(connection, seed, now=now)
    old = now - timedelta(days=200)
    await connection.execute(
        """UPDATE listings.sale_listings SET title=%s,description=%s,
        asking_price_paise=%s,availability=%s,available_from=%s,available_until=%s,
        retirement_pending_operation_id=%s,retirement_pending_cutoff_utc=%s WHERE id=%s""",
        (
            title,
            description,
            price,
            "unavailable" if status == "unavailable" else "available",
            now + timedelta(hours=1) if status == "future" else old,
            (
                now
                if status == "ended"
                else old + timedelta(days=1) if status == "unavailable" else None
            ),
            uuid4() if status == "pending" else None,
            now - timedelta(days=90) if status == "pending" else None,
            listing,
        ),
    )
    return listing


async def math_drain(store, spec, outputs, limit=150):
    """Explicit bounded mathematical publication; never starts an inference worker."""
    for index in range(limit):
        job = await store.claim(spec)
        if job is None:
            return index
        output = outputs.get(job.listing_id, parts(0.0, 0.0))
        assert await store.complete(job, output, len(output) - 1)
    raise AssertionError("Mathematical fixture job limit exceeded")


async def activate_math(connection, outputs):
    """Temporarily control only this runner's pipelines; caller rolls back/restores."""
    store = EmbeddingStore(connection)
    existing = await (
        await connection.execute(
            "SELECT encoding,state FROM listings.embedding_pipelines ORDER BY pipeline_id"
        )
    ).fetchall()
    for row in existing:
        await store.set_state(pipeline_spec(row["encoding"]), "retired")
    spec = default_pipeline_spec()
    await store.register(spec)
    await store.set_state(spec, "building")
    assert await store.queue_missing(spec, 150) < 150
    await math_drain(store, spec, outputs)
    return store, spec, existing


async def expect503(connection, request, now, bound):
    """A controlled error must replace the entire page, never expose partial rows."""
    with pytest.raises(PublicError) as raised:
        await read_hybrid_page(connection, request, now, 500000, bound, relevance=True)
    assert raised.value.spec == ERRORS[503]


def test_native_hybrid_math_coverage_filters_and_pages():
    asyncio.run(exercise_math(target()))


async def exercise_math(value):
    """Real native math/guards: no missing eligible source can hide behind text."""
    async with await connect(value) as connection:
        async with connection.transaction(force_rollback=True):
            now = datetime.now(UTC)
            outputs = {}
            store, spec, _ = await activate_math(connection, outputs)
            rows = []
            fixtures = [
                (
                    "Vehicle handbook",
                    "Original term regardless of score",
                    100,
                    "available",
                    parts(-1.0, -1.0),
                ),
                (
                    "Blue bicycle",
                    "Expanded keyword regardless of score",
                    200,
                    "available",
                    parts(-0.5, -0.5),
                ),
                (
                    "Study table",
                    "Semantic-only high score",
                    300,
                    "available",
                    parts(0.9, 0.9),
                ),
                (
                    "Plain item",
                    "Best of two complete description chunks",
                    400,
                    "available",
                    parts(0.0, -0.5, 0.6),
                ),
                (
                    "Unrelated object",
                    "Title alone must not bypass blend",
                    500,
                    "available",
                    parts(0.9, 0.0),
                ),
                (
                    "Hidden bicycle",
                    "Unavailable missing coverage is irrelevant",
                    600,
                    "unavailable",
                    parts(1.0, 1.0),
                ),
                ("Future bicycle", "Future source", 700, "future", parts(1.0, 1.0)),
                ("Ended bicycle", "Ended source", 800, "ended", parts(1.0, 1.0)),
                (
                    "Pending bicycle",
                    "Pending retirement source",
                    900,
                    "pending",
                    parts(1.0, 1.0),
                ),
            ]
            for index, (title, description, price, status, output) in enumerate(
                fixtures
            ):
                listing = await live_listing(
                    connection, 94100 + index, now, title, description, price, status
                )
                rows.append(listing)
                outputs[listing] = output
            # Retired content is scrubbed and has no generation; it must neither
            # appear nor make eligible coverage fail.
            retired = await seed_listing(connection, 94120, now=now)
            await retire(connection, retired)
            await math_drain(store, spec, outputs)
            await store.set_state(spec, "serving")
            request = ListingQuery(q="vehicle")
            bound = bind_query("vehicle", spec, VECTOR)

            async def read(query=request, relevance=True):
                return await read_hybrid_page(
                    connection,
                    query,
                    now,
                    500000,
                    bind_query(query.q, spec, VECTOR),
                    relevance=relevance,
                )

            # Accepted thresholds beyond bigint preserve public sensitivity
            # semantics and execute successfully in both real SQL paths.
            huge_page = await read_hybrid_page(
                connection, request, now, 10**30, bound, relevance=True
            )
            from app.domains.listings.browse_store import browse_statement

            keyword_sql, keyword_params = browse_statement(request, now, 10**30)
            keyword_rows = await (
                await connection.execute(keyword_sql, keyword_params)
            ).fetchall()
            assert huge_page.items and keyword_rows
            assert all(not item.sensitive_purchase for item in huge_page.items)
            assert all(not row["sensitive_purchase"] for row in keyword_rows)

            page = await read()
            assert [item.listing_id for item in page.items] == rows[:4]
            # Original -1 and expanded -.5 stay ahead of semantic .9; a title .9
            # with description0 gives .315 and is excluded. Two chunks use max.
            assert set(page.items[0].model_dump()) == set(ListingSummary.model_fields)
            assert [
                item.listing_id
                for item in (await read(ListingQuery(q="vehicel"))).items
            ] == [rows[1], rows[0], rows[2], rows[3]]
            for sort in ["created_desc", "price_asc", "price_desc"]:
                ordered = await read(ListingQuery(q="vehicle", sort=sort), False)
                expected = (
                    sorted(rows[:4], reverse=True)
                    if sort == "created_desc"
                    else rows[:4] if sort == "price_asc" else list(reversed(rows[:4]))
                )
                assert [item.listing_id for item in ordered.items] == expected
            assert (
                await read(ListingQuery(q="vehicle", category_code="books"))
            ).items == ()
            assert (
                len(
                    (
                        await read(
                            ListingQuery(
                                q="vehicle",
                                condition_code="good",
                                negotiable=False,
                                max_price_paise=300,
                            )
                        )
                    ).items
                )
                == 3
            )
            assert (await read(ListingQuery(q="vehicle", negotiable=True))).items == ()
            with pytest.raises(PublicError) as raised:
                await read(ListingQuery(q="vehicle", category_code="invalid"))
            assert raised.value.spec == ERRORS[422]
            maximum = 1_000_000_000
            await connection.execute(
                "UPDATE listings.sale_listings SET asking_price_paise=%s WHERE id=%s",
                (maximum, rows[0]),
            )
            large = await read(ListingQuery(q="vehicle", sort="price_desc"), False)
            assert (
                large.items[0].asking_price_paise == maximum
                and type(large.items[0].asking_price_paise) is int
            )
            assert (
                len(
                    (
                        await read(ListingQuery(q="vehicle", min_price_paise=maximum))
                    ).items
                )
                == 1
            )
            assert (
                len(
                    (
                        await read(ListingQuery(q="vehicle", max_price_paise=maximum))
                    ).items
                )
                == 4
            )
            with pytest.raises(ValidationError):
                ListingQuery(q="vehicle", max_price_paise=10**100)
            await connection.execute(
                "UPDATE listings.sale_listings SET asking_price_paise=100 WHERE id=%s",
                (rows[0],),
            )
            # This missing source does not match words or semantic cutoff; it
            # must nevertheless fail coverage until excluded by a real filter.
            await connection.execute(
                "DELETE FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s",
                (rows[4], spec.pipeline_id),
            )
            await expect503(connection, request, now, bound)
            assert (
                len((await read(ListingQuery(q="vehicle", max_price_paise=400))).items)
                == 4
            )
            assert await store.queue_missing(spec, 150) == 1
            await math_drain(store, spec, outputs)
            await connection.execute(
                "UPDATE listings.sale_listings SET description='Changed current source' WHERE id=%s",
                (rows[4],),
            )
            await expect503(connection, request, now, bound)  # pending
            job = await store.claim(spec)
            assert job is not None and job.listing_id == rows[4]
            await expect503(connection, request, now, bound)  # leased
            assert await store.fail(job, "helper_unavailable")
            await connection.execute(
                "UPDATE listings.embedding_generations SET state='failed',attempts=5 WHERE generation_id=%s",
                (job.generation_id,),
            )
            await expect503(connection, request, now, bound)
            assert await store.retry_failed(spec, rows[4])
            await math_drain(store, spec, outputs)
            async with connection.transaction(force_rollback=True):
                await connection.execute(
                    "UPDATE listings.embedding_generations SET source_fingerprint=%s WHERE listing_id=%s AND pipeline_id=%s",
                    (b"x" * 32, rows[4], spec.pipeline_id),
                )
                await expect503(connection, request, now, bound)
            assert len((await read()).items) == 4
            async with connection.transaction(force_rollback=True):
                await connection.execute(
                    """DELETE FROM listings.embedding_chunks WHERE generation_id=(
                    SELECT generation_id FROM listings.embedding_generations WHERE listing_id=%s AND pipeline_id=%s)
                    AND part_kind='description' AND ordinal=1""",
                    (rows[3], spec.pipeline_id),
                )
                await expect503(connection, request, now, bound)
            assert len((await read()).items) == 4
            with pytest.raises(PublicError) as raised:
                await read(ListingQuery(q="vehicle", condition_code="invalid"))
            assert raised.value.spec == ERRORS[422]
            # Ineligible unavailable/future/ended/pending gaps do not block.
            await connection.execute(
                "DELETE FROM listings.embedding_generations WHERE listing_id=ANY(%s)",
                (rows[5:],),
            )
            assert len((await read()).items) == 4
            await store.set_state(spec, "building")
            await expect503(
                connection, ListingQuery(q="vehicle", category_code="books"), now, bound
            )
            await store.queue_missing(spec, 150)
            await math_drain(store, spec, outputs)
            await store.set_state(spec, "serving")
            # A different serving vector space is never accepted as this model.
            encoding = spec.encoding
            encoding["numpy"] = "0.0.94100"
            other = pipeline_spec(encoding)
            await store.register(other)
            await store.set_state(other, "building")
            await store.queue_missing(other, 150)
            await math_drain(store, other, {})
            await store.set_state(spec, "retired")
            await store.set_state(other, "serving")
            await expect503(connection, request, now, bound)
            await store.set_state(other, "retired")
            await store.set_state(spec, "serving")
            # Same-source mathematical clones test whole-corpus paging, not new
            # inference evidence. Every clone still gets its own fenced receipt.
            clones = []
            for index in range(65):
                item = await live_listing(
                    connection,
                    94200 + index,
                    now,
                    "Blue bicycle",
                    "Expanded keyword regardless of score",
                    200,
                )
                clones.append(item)
                outputs[item] = parts(-0.5, -0.5)
            await expect503(connection, request, now, bound)
            await math_drain(store, spec, outputs)
            expected_relevance = [
                rows[0],
                *sorted([rows[1], *clones]),
                rows[2],
                rows[3],
            ]
            for size in [20, 50, 100]:
                for sort, relevance in [
                    ("created_desc", True),
                    ("created_desc", False),
                    ("price_asc", False),
                    ("price_desc", False),
                ]:
                    actual = []
                    for number in range(
                        1, math.ceil(len(expected_relevance) / size) + 1
                    ):
                        page = await read(
                            ListingQuery(
                                q="vehicle", page=number, page_size=size, sort=sort
                            ),
                            relevance,
                        )
                        actual.extend(item.listing_id for item in page.items)
                        assert page.has_next is (
                            number * size < len(expected_relevance)
                        )
                    if relevance:
                        expected = expected_relevance
                    elif sort == "created_desc":
                        expected = sorted(expected_relevance, reverse=True)
                    elif sort == "price_asc":
                        expected = [
                            rows[0],
                            *sorted([rows[1], *clones]),
                            rows[2],
                            rows[3],
                        ]
                    else:
                        expected = [
                            rows[3],
                            rows[2],
                            *sorted([rows[1], *clones], reverse=True),
                            rows[0],
                        ]
                    assert actual == expected and len(set(actual)) == len(actual)
            assert (await read(ListingQuery(q="vehicle", page=10))).items == ()


async def finish_fixture(connection, listing):
    """Retire only our committed synthetic source; no real Conversations claim."""
    await connection.execute(
        "UPDATE listings.sale_listings SET availability='unavailable',available_until=available_from+interval '1 day' WHERE id=%s",
        (listing,),
    )
    await retire(connection, listing)


def test_native_hybrid_single_statement_snapshot_during_commit():
    asyncio.run(exercise_snapshot(target()))


async def exercise_snapshot(value):
    """An observed gate pauses a real statement while another connection commits.

    Wrapping owned SQL in a test-only advisory-lock CTE adds no runtime flag or
    production branch. One statement snapshot must retain old coverage/content,
    while the next request sees pending new source and returns503.
    """
    async with await connect(value) as writer, await connect(value) as reader:
        now = datetime.now(UTC)
        outputs = {}
        listing = None
        task = None
        store, spec, existing = await activate_math(writer, outputs)
        try:
            async with writer.transaction():
                listing = await live_listing(
                    writer, 94300, now, "Vehicle snapshot", "Controlled before snapshot"
                )
            outputs[listing] = parts(1.0, 1.0)
            await math_drain(store, spec, outputs)
            await store.set_state(spec, "serving")
            request = ListingQuery(q="vehicle")
            bound = bind_query("vehicle", spec, VECTOR)
            compiled = await compile_expansion(reader, "vehicle")
            statement, parameters = hybrid_statement(
                request, now, 500000, bound, compiled, relevance=True
            )
            wrapped = (
                "WITH test_gate AS MATERIALIZED (SELECT pg_advisory_xact_lock(1129072976,31)) SELECT result.* FROM test_gate CROSS JOIN LATERAL ("
                + statement
                + ") AS result"
            )
            await reader.execute("SET statement_timeout='5s'")
            async with writer.transaction():
                await writer.execute("SELECT pg_advisory_xact_lock(1129072976,31)")
                task = asyncio.create_task(reader.execute(wrapped, parameters))
                await wait_for_lock(writer, reader)
                await writer.execute(
                    "UPDATE listings.sale_listings SET description='Controlled after snapshot' WHERE id=%s",
                    (listing,),
                )
            result = await (await asyncio.wait_for(task, 5)).fetchone()
            assert result["ready"] is True and len(result["items"]) == 1
            assert result["items"][0]["description"] == "Controlled before snapshot"
            await expect503(reader, request, now, bound)
            await math_drain(store, spec, outputs)
            recovered = await read_hybrid_page(
                reader, request, now, 500000, bound, relevance=True
            )
            assert (
                len(recovered.items) == 1
                and recovered.items[0].description == "Controlled after snapshot"
            )
        finally:
            if task is not None:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            if listing is not None:
                async with writer.transaction():
                    await finish_fixture(writer, listing)
            for row in existing:
                await store.set_state(pipeline_spec(row["encoding"]), row["state"])


def test_native_hybrid_actual_model():
    value = target()
    if os.environ.get("LISTINGS_TEST_HYBRID_MODEL") != "1":
        pytest.skip(
            "Use native-checks.sh --hybrid-read for actual helper/read integration"
        )
    asyncio.run(asyncio.wait_for(exercise_actual(value), 600))


async def exercise_actual(value):
    """One real helper/<=30windows/10min/512MiB; fail closed, recover by filtering."""
    from scripts.evaluation.semantic.ipc_probe import rss

    helper = SemanticHelper(
        ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
    )
    parent = os.getpid()
    owned = set()
    peak = 0
    simultaneous = 0
    faults = []
    stop = asyncio.Event()
    started = time.monotonic()

    async def monitor():
        nonlocal peak, simultaneous
        while not stop.is_set():
            if helper.pid is not None:
                owned.add(helper.pid)
            processes = await asyncio.to_thread(rss, {parent, *owned})
            if parent not in processes:
                faults.append("host_missing")
                await helper.close()
                return
            live = [
                pid for pid in owned if pid in processes and processes[pid][0] == parent
            ]
            total = processes[parent][1] + sum(processes[pid][1] for pid in live)
            peak = max(peak, total)
            simultaneous = max(simultaneous, len(live))
            if (
                total >= 512 * 1024 * 1024
                or len(live) > 1
                or helper.windows_started > 30
                or time.monotonic() - started > 600
            ):
                faults.append("resource_bound")
                await helper.close()
                return
            await asyncio.sleep(0.05)

    watchdog = asyncio.create_task(monitor())
    try:
        async with await connect(value) as connection:
            now = datetime.now(UTC)
            store = EmbeddingStore(connection)
            spec = default_pipeline_spec()
            ids = []
            existing = await (
                await connection.execute(
                    "SELECT encoding,state FROM listings.embedding_pipelines ORDER BY pipeline_id"
                )
            ).fetchall()
            for row in existing:
                await store.set_state(pipeline_spec(row["encoding"]), "retired")
            await store.register(spec)
            await store.set_state(spec, "building")
            try:
                fixtures = [
                    (
                        "Campus bicycle",
                        "A pedal powered bicycle for commuting around campus. Includes working brakes and lights.",
                    ),
                    (
                        "Calculus textbook",
                        "University mathematics textbook with worked exercises and solutions for calculus students.",
                    ),
                    (
                        "Compact refrigerator",
                        "Small kitchen appliance for storing milk, vegetables and groceries at a low temperature.",
                    ),
                ]
                for index, (title, description) in enumerate(fixtures):
                    async with connection.transaction():
                        ids.append(
                            await live_listing(
                                connection, 94400 + index, now, title, description
                            )
                        )
                # No accidental backfill of other fixtures through a real model.
                due = await (
                    await connection.execute(
                        "SELECT listing_id FROM listings.embedding_generations WHERE pipeline_id=%s AND state='pending'",
                        (spec.pipeline_id,),
                    )
                ).fetchall()
                assert {row["listing_id"] for row in due} == set(ids)
                for _ in ids:
                    assert await EmbeddingWorker(store, helper).run_one() == "published"
                await store.set_state(spec, "serving")
                cases = []
                for text, expected in [
                    ("bycicle", ids[0]),
                    ("study material for calculus", ids[1]),
                    ("keep food cold", ids[2]),
                ]:
                    page = await search_hybrid_page(
                        connection,
                        helper,
                        ListingQuery(q=text),
                        now,
                        500000,
                        relevance=True,
                    )
                    assert page.items and page.items[0].listing_id == expected
                    assert all(
                        set(item.model_dump()) == set(ListingSummary.model_fields)
                        for item in page.items
                    )
                    cases.append(
                        {
                            "scenario": text.replace(" ", "_"),
                            "expected_first": True,
                            "returned": len(page.items),
                        }
                    )
                async with connection.transaction():
                    ids.append(
                        await live_listing(
                            connection,
                            94410,
                            now,
                            "New chair",
                            "New source awaiting embeddings",
                            10000,
                        )
                    )
                with pytest.raises(PublicError) as raised:
                    await search_hybrid_page(
                        connection,
                        helper,
                        ListingQuery(q="keep food cold"),
                        now,
                        500000,
                        relevance=True,
                    )
                assert raised.value.spec == ERRORS[503]
                # The controlled failure leaves the process/helper usable. A
                # genuine filter excludes the unembedded source and restores read.
                page = await search_hybrid_page(
                    connection,
                    helper,
                    ListingQuery(q="keep food cold", max_price_paise=0),
                    now,
                    500000,
                    relevance=True,
                )
                assert page.items[0].listing_id == ids[2]
                keyword = await read_browse_page(
                    connection, ListingQuery(q="refrigerator"), now, 500000
                )
                assert [item.listing_id for item in keyword.items] == [ids[2]]
                await helper.close()
                with pytest.raises(PublicError) as raised:
                    await search_hybrid_page(
                        connection,
                        helper,
                        ListingQuery(q="keep food cold"),
                        now,
                        500000,
                        relevance=True,
                    )
                assert raised.value.spec == ERRORS[503]
                assert (
                    await read_browse_page(
                        connection, ListingQuery(q="refrigerator"), now, 500000
                    )
                ).items
            finally:
                for item in ids:
                    async with connection.transaction():
                        await finish_fixture(connection, item)
                for row in existing:
                    await store.set_state(pipeline_spec(row["encoding"]), row["state"])
    finally:
        await helper.close()
        stop.set()
        await watchdog
    assert not faults and helper.windows_started <= 30 and helper.starts == 1
    remaining = rss({parent, *owned})
    assert owned and all(pid not in remaining for pid in owned)
    result = {
        "captured_at": datetime.now(UTC).isoformat(),
        "isolated_only": True,
        "public_activation": False,
        "nfr_accepted": False,
        "actual_model": True,
        "cases": cases,
        "missing_coverage_503": True,
        "filtered_recovery_after_503": True,
        "closed_helper_503": True,
        "keyword_independent": True,
        "summary_whitelist_only": True,
        "model_windows": helper.windows_started,
        "helper_starts": helper.starts,
        "max_simultaneous_owned_helpers": simultaneous,
        "sampled_peak_host_helper_rss_bytes": peak,
        "all_owned_helpers_reaped": True,
        "elapsed_seconds": time.monotonic() - started,
    }
    folder = (
        ROOT
        / ".tools/semantic/hybrid-read-probes"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
