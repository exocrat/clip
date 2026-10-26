"""Private vector/output and SQL transport tests; native state/concurrency separate."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import math
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from app.domains.listings.embedding_types import (
    EmbeddingJob,
    EmbeddingPart,
    default_pipeline_spec,
    pipeline_spec,
    validate_parts,
)
from app.domains.listings.embedding_store import EmbeddingStore

ID = UUID("10000000-0000-4000-8000-000000000001")
GEN = UUID("20000000-0000-4000-8000-000000000001")
TOKEN = UUID("30000000-0000-4000-8000-000000000001")
VECTOR = (1.0,) + (0.0,) * 383


def job():
    """Synthetic internal receipt; no real corpus IDs or human judgments."""
    spec = default_pipeline_spec()
    return EmbeddingJob(
        ID,
        spec.pipeline_id,
        GEN,
        b"f" * 32,
        TOKEN,
        datetime.now(UTC) + timedelta(seconds=30),
        "Controlled private source title",
        "Controlled private source description",
        spec.encoding,
    )


def parts():
    """Coordinate vectors test schema/math only, never fake model relevance."""
    return (EmbeddingPart("title", 0, VECTOR), EmbeddingPart("description", 0, VECTOR))


def result(row=None, rows=None):
    """Script a psycopg transport cursor; it implements no SQL/state machine."""
    cursor = AsyncMock()
    cursor.fetchone.return_value = row
    cursor.fetchall.return_value = rows or []
    cursor.rowcount = 1
    return cursor


def connection(*responses):
    """Provide context-manager/execute transports for parameter and refusal checks."""
    subject = MagicMock()
    subject.execute = AsyncMock(side_effect=responses)
    cursor = AsyncMock()
    subject.cursor.return_value.__aenter__.return_value = cursor
    return subject


def test_candidate_configuration_is_frozen_and_bound():
    spec = default_pipeline_spec()
    assert len(spec.pipeline_id) == 32
    assert spec == pipeline_spec(spec.encoding)
    mutable = spec.encoding
    mutable["dimensions"] = 1
    assert spec.encoding["dimensions"] == 384
    changed = spec.encoding
    changed["encoder_version"] = "other"
    with pytest.raises(ValueError):
        pipeline_spec(changed)


@pytest.mark.parametrize(
    "mutation",
    [
        {"dimensions": True},
        {"window": 512},
        {"model_revision": "latest"},
        {"model_sha256": "bad"},
        {"tokenizers": "latest"},
        {"extra": True},
    ],
)
def test_invalid_encoding_rejected(mutation):
    encoding = default_pipeline_spec().encoding
    encoding.update(mutation)
    with pytest.raises(ValueError):
        pipeline_spec(encoding)


def test_parts_sorting_and_private_repr():
    assert validate_parts(tuple(reversed(parts())), 1) == parts()
    assert "Controlled private" not in repr(job())
    assert str(VECTOR) not in repr(parts()[0])


@pytest.mark.parametrize(
    "vector",
    [
        (),
        VECTOR[:-1],
        (0.0,) * 384,
        (math.nan,) + VECTOR[1:],
        (math.inf,) + VECTOR[1:],
        (-math.inf,) + VECTOR[1:],
        (1e308,) + VECTOR[1:],
        (True,) + VECTOR[1:],
        (None,) + VECTOR[1:],
    ],
)
def test_bad_vectors_rejected_before_sql(vector):
    malformed = (replace(parts()[0], vector=vector), parts()[1])
    subject = connection()
    with pytest.raises(ValueError):
        asyncio.run(EmbeddingStore(subject).complete(job(), malformed, 1))
    subject.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "bad, count",
    [
        ((parts()[0],), 1),
        ((parts()[0], parts()[0]), 1),
        ((parts()[0], replace(parts()[1], ordinal=1)), 1),
        ((replace(parts()[0], ordinal=True), parts()[1]), 1),
        (parts(), True),
        (parts(), 97),
        (parts(), 0),
    ],
)
def test_missing_duplicate_and_out_of_range_parts_rejected(bad, count):
    with pytest.raises(ValueError):
        validate_parts(bad, count)


@pytest.mark.parametrize(
    "row",
    [
        None,
        {
            "retired_at": datetime.now(UTC),
            "retirement_pending_operation_id": None,
            "fingerprint": b"f" * 32,
        },
        {
            "retired_at": None,
            "retirement_pending_operation_id": TOKEN,
            "fingerprint": b"f" * 32,
        },
        {
            "retired_at": None,
            "retirement_pending_operation_id": None,
            "fingerprint": b"x" * 32,
        },
    ],
)
def test_source_retirement_or_pending_fence_prevents_publication(row):
    subject = connection(result(row))
    assert not asyncio.run(EmbeddingStore(subject).complete(job(), parts(), 1))
    subject.cursor.return_value.__aenter__.return_value.executemany.assert_not_awaited()
    assert subject.execute.await_count == 1


def current_row():
    return {
        "retired_at": None,
        "retirement_pending_operation_id": None,
        "fingerprint": b"f" * 32,
    }


def test_stale_lease_or_generation_prevents_chunk_writes():
    subject = connection(result(current_row()), result(None))
    assert not asyncio.run(EmbeddingStore(subject).complete(job(), parts(), 1))
    sql, values = subject.execute.await_args.args
    assert "FOR UPDATE OF generation" in sql and "lease_until>clock_timestamp()" in sql
    receipt = job()
    assert (
        receipt.generation_id in values
        and receipt.lease_token in values
        and receipt.source_fingerprint in values
    )
    subject.cursor.return_value.__aenter__.return_value.executemany.assert_not_awaited()


def test_publication_binds_vectors_and_ready_counts():
    subject = connection(
        result(current_row()), result({"attempts": 1}), result(), result()
    )
    assert asyncio.run(EmbeddingStore(subject).complete(job(), parts(), 1))
    sql, rows = (
        subject.cursor.return_value.__aenter__.return_value.executemany.await_args.args
    )
    assert sql.count("%s") == 4 and "Controlled private" not in sql
    assert rows[0] == (GEN, "title", 0, list(VECTOR))
    update, values = subject.execute.await_args.args
    assert "state='ready'" in update and values == (1, GEN)


@pytest.mark.parametrize(
    "attempt, state, delay",
    [
        (1, "pending", 5),
        (2, "pending", 30),
        (3, "pending", 120),
        (4, "pending", 300),
        (5, "failed", 300),
    ],
)
def test_failure_backoff_stops_at_fifth_attempt(attempt, state, delay):
    subject = connection(result(current_row()), result({"attempts": attempt}), result())
    assert asyncio.run(EmbeddingStore(subject).fail(job(), "timeout"))
    assert subject.execute.await_args.args[1] == (state, "timeout", delay, GEN)


def test_unknown_failure_text_never_persisted():
    subject = connection()
    with pytest.raises(ValueError):
        asyncio.run(EmbeddingStore(subject).fail(job(), "private input"))
    subject.execute.assert_not_awaited()


@pytest.mark.parametrize("limit", [0, True, 1001])
def test_queue_bounds_reject_before_sql(limit):
    subject = connection()
    with pytest.raises(ValueError):
        asyncio.run(
            EmbeddingStore(subject).queue_missing(default_pipeline_spec(), limit)
        )
    subject.execute.assert_not_awaited()


def test_ready_row_from_concurrent_completion_not_claimed_or_failed():
    receipt = job()
    candidate = {
        "id": ID,
        "title": receipt.title,
        "description": receipt.description,
        "pipeline_id": receipt.pipeline_id,
        "encoding": receipt.encoding,
        "fingerprint": receipt.source_fingerprint,
    }
    subject = connection(
        result(candidate),
        result(
            {
                "due": False,
                "attempts": 5,
                "source_fingerprint": receipt.source_fingerprint,
            }
        ),
    )
    assert asyncio.run(EmbeddingStore(subject).claim()) is None
    assert subject.execute.await_count == 2


def test_registration_does_not_enable_pipeline():
    spec = default_pipeline_spec()
    subject = connection(result(), result(), result({"encoding": spec.encoding}))
    asyncio.run(EmbeddingStore(subject).register(spec))
    sql, values = subject.execute.await_args_list[1].args
    assert "state" not in sql and values[0] == spec.pipeline_id
    assert "ON CONFLICT DO NOTHING" in sql


def test_explicit_failed_retry_uses_new_generation_and_current_fingerprint():
    subject = connection(
        result({"fingerprint": b"f" * 32}),
        result({"generation_id": GEN}),
        result(),
        result(),
    )
    spec = default_pipeline_spec()
    assert asyncio.run(EmbeddingStore(subject).retry_failed(spec, ID))
    sql, values = subject.execute.await_args.args
    assert values[0] == ID and values[1] == spec.pipeline_id
    assert values[2] != GEN and values[2].version == 4
    assert values[3] == b"f" * 32 and "VALUES (%s,%s,%s,%s)" in sql


def test_explicit_retry_refuses_retired_or_missing_listing():
    subject = connection(result(None))
    assert not asyncio.run(
        EmbeddingStore(subject).retry_failed(default_pipeline_spec(), ID)
    )
    assert subject.execute.await_count == 1


def test_math_pipeline_fixture_keys_never_alias_real_candidate():
    """Check fixture isolation without PostgreSQL/model calls, even when SQL skips."""
    from apps.api.tests.domains.listings.test_embedding_postgres import math_pipeline

    real = default_pipeline_spec()
    specs = [math_pipeline(index) for index in (94011, 94012, 94013)]
    assert len({spec.pipeline_id for spec in specs}) == 3
    assert real.pipeline_id not in {spec.pipeline_id for spec in specs}
    assert default_pipeline_spec() == real


def test_capacity_deferral_is_fenced_and_preserves_failure_budget():
    """Inspect bound SQL only; native tests prove actual state/lease behavior."""
    subject = connection(result(current_row()), result({"attempts": 2}), result())
    assert asyncio.run(EmbeddingStore(subject).defer(job()))
    sql, values = subject.execute.await_args.args
    assert "attempts=greatest(attempts-1,0)" in sql
    assert "interval '5 seconds'" in sql and values == (GEN,)
    cursor = subject.cursor.return_value.__aenter__.return_value
    assert [call.args[0] for call in cursor.execute.await_args_list] == [
        "SET LOCAL statement_timeout='3s'",
        "SET LOCAL lock_timeout='1s'",
    ]
    missing = connection(result(None))
    assert not asyncio.run(EmbeddingStore(missing).defer(job()))
    assert missing.execute.await_count == 1
