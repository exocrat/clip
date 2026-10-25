"""Synthetic arithmetic/input checks only; no model/native SQL claims here."""

import copy
import json
import math
from pathlib import Path

import pytest

from scripts.evaluation.semantic.calibration import (
    FIXTURE,
    CalibrationError,
    analyze,
    development_set,
    fingerprint,
    ranked,
    read_json,
    semantic_score,
    validate_matrix,
)
from app.domains.listings.embedding_types import default_pipeline_spec
from app.domains.listings.vocabulary import load_vocabulary


def arithmetic_inputs():
    """Tiny scripted score matrix: misleading lexical hit versus useful semantic hit."""
    document = read_json(FIXTURE, 65536)
    document["listings"] = [
        row
        for row in document["listings"]
        if row["key"] in {"cycle", "poster", "plant"}
    ]
    document["queries"] = [
        row for row in document["queries"] if row["key"] in {"vehicle", "absent_guitar"}
    ]
    data = development_set(document)
    matrix = {
        "format_version": 1,
        "fixture_fingerprint": data.fingerprint,
        "pipeline_id": default_pipeline_spec().pipeline_id.hex(),
        "vocabulary_fingerprint": load_vocabulary().fingerprint,
        "queries": [],
    }
    for query in document["queries"]:
        rows = []
        for row in document["listings"]:
            key = row["key"]
            lexical = query["key"] == "vehicle" and key == "poster"
            title = (
                0.8
                if query["key"] == "vehicle" and key == "cycle"
                else 0.15 if lexical else 0.05
            )
            rows.append(
                {
                    "key": key,
                    "listing_id": data.listing_id(key),
                    "original": lexical,
                    "expanded": lexical,
                    "title_score": title,
                    "description_score": 0.1 if lexical else title,
                }
            )
        matrix["queries"].append({"key": query["key"], "rows": rows})
    return data, matrix


def test_fixture_separate_from_final_labels_and_bindings_exact():
    data = development_set(read_json(FIXTURE, 65536))
    assert len(data.document["listings"]) == 8 and len(data.document["queries"]) == 11
    assert data.document["human_review_verified"] is False
    assert data.fingerprint == fingerprint(json.loads(FIXTURE.read_text()))
    assert data.listing_id("cycle") != data.listing_id("poster")
    assert "development" in FIXTURE.parts


@pytest.mark.parametrize(
    "mutation",
    [
        "reviewed",
        "final",
        "unknown",
        "duplicate",
        "too_long",
        "bad_label",
        "duplicate_label",
        "bool_version",
    ],
)
def test_bad_development_fixture_refused(mutation):
    doc = read_json(FIXTURE, 65536)
    if mutation == "reviewed":
        doc["human_review_verified"] = True
    if mutation == "final":
        doc["purpose"] = "final_evaluation"
    if mutation == "unknown":
        doc["extra"] = True
    if mutation == "duplicate":
        doc["listings"][1]["key"] = doc["listings"][0]["key"]
    if mutation == "too_long":
        doc["listings"][0]["description"] = "a" * 5001
    if mutation == "bad_label":
        doc["queries"][0]["relevant_keys"] = ["unknown"]
    if mutation == "duplicate_label":
        doc["queries"][0]["relevant_keys"] *= 2
    if mutation == "bool_version":
        doc["format_version"] = True
    with pytest.raises(CalibrationError, match="invalid_development_fixture"):
        development_set(doc)


@pytest.mark.parametrize(
    "raw",
    [
        '{"a":1,"a":2}',
        '{"a":NaN}',
        '{"a":Infinity}',
        "[]",
        "{invalid",
        '{"secret":"' + "x" * 100 + '"}',
    ],
)
def test_json_refusal_hides_input(tmp_path, raw):
    path = tmp_path / "input.json"
    path.write_text(raw)
    with pytest.raises(CalibrationError) as raised:
        read_json(path, 100)
    assert str(raised.value) == "invalid_calibration_json"


@pytest.mark.parametrize(
    "mutation",
    [
        "fixture",
        "pipeline",
        "vocabulary",
        "missing_query",
        "duplicate_query",
        "missing_row",
        "duplicate_row",
        "bool_score",
        "nan",
        "score_range",
        "wrong_id",
        "lexical_regression",
        "extra",
    ],
)
def test_matrix_requires_full_bound_native_scores(mutation):
    data, matrix = arithmetic_inputs()
    row = matrix["queries"][0]["rows"][0]
    if mutation in {"fixture", "pipeline", "vocabulary"}:
        key = {
            "fixture": "fixture_fingerprint",
            "pipeline": "pipeline_id",
            "vocabulary": "vocabulary_fingerprint",
        }[mutation]
        matrix[key] = "0" * 64
    if mutation == "missing_query":
        matrix["queries"].pop()
    if mutation == "duplicate_query":
        matrix["queries"][1] = matrix["queries"][0]
    if mutation == "missing_row":
        matrix["queries"][0]["rows"].pop()
    if mutation == "duplicate_row":
        matrix["queries"][0]["rows"][1] = row
    if mutation == "bool_score":
        row["title_score"] = True
    if mutation == "nan":
        row["title_score"] = math.nan
    if mutation == "score_range":
        row["title_score"] = 1.1
    if mutation == "wrong_id":
        row["listing_id"] = data.listing_id("plant")
    if mutation == "lexical_regression":
        row["original"], row["expanded"] = True, False
    if mutation == "extra":
        row["private"] = "forbidden"
    with pytest.raises(CalibrationError, match="invalid_score_matrix"):
        validate_matrix(data, matrix)


def test_grid_arithmetic_and_explicit_empty_query_denominator():
    data, matrix = arithmetic_inputs()
    result = analyze(data, matrix)
    assert len(result["comparisons"]) == 90 and result["policy_frozen"] is False
    assert (
        result["human_review_verified"] is False
        and result["final_labels_used"] is False
    )
    baseline = result["keyword"]
    assert baseline["candidate_recall"] == 0 and baseline["candidate_precision"] == 0
    comparison = next(
        item
        for item in result["comparisons"]
        if item["settings"]
        == {
            "aggregation": "max",
            "threshold": 0.45,
            "fusion": "tiered",
            "cap": None,
            "mode": "hybrid",
        }
    )
    assert (
        comparison["candidate_recall"] == 1 and comparison["candidate_precision"] == 0.5
    )
    assert (
        comparison["development_hits_at5"] == 1 and comparison["all_query_count"] == 2
    )
    assert comparison["positive_query_count"] == 1 and comparison["positive_top1"] == 0
    assert comparison["empty_query_count"] == comparison["empty_queries_correct"] == 1


def test_lexical_preservation_tier_vs_boost_and_stable_uuid_ties():
    data, matrix = arithmetic_inputs()
    rows = matrix["queries"][0]["rows"]
    assert ranked(rows, "max", 0.65, "tiered", None) == ["poster", "cycle"]
    assert ranked(rows, "max", 0.65, "boosted", None) == ["cycle", "poster"]
    tied = copy.deepcopy(rows)
    for row in tied:
        row["title_score"] = row["description_score"] = 0.8
        row["original"] = row["expanded"] = False
    expected = [row["key"] for row in sorted(tied, key=lambda row: row["listing_id"])]
    assert ranked(list(reversed(tied)), "max", 0.45, "tiered", 3) == expected
    assert ranked(rows, "max", 0.65, "tiered", 3, mode="keyword") == ["poster"]


def test_blend_does_not_discard_title_and_is_not_max():
    row = {"title_score": 0.8, "description_score": 0.2}
    assert semantic_score(row, "blend") == pytest.approx(0.41)
    assert semantic_score(row, "max") == 0.8
    with pytest.raises(CalibrationError):
        semantic_score(row, "unknown")


@pytest.mark.parametrize(
    "settings",
    [
        ("max", 0.2, "tiered", None),
        ("max", 0.45, "unknown", None),
        ("max", 0.45, "tiered", True),
        ("max", 0.45, "tiered", 1),
    ],
)
def test_settings_cannot_silently_leave_declared_grid(settings):
    _, matrix = arithmetic_inputs()
    with pytest.raises(CalibrationError):
        ranked(matrix["queries"][0]["rows"], *settings)


@pytest.mark.parametrize(
    "bad", ["host", "user", "database", "port", "transaction", "autocommit", "pipeline"]
)
def test_measure_refuses_unsafe_target_before_sql_or_model(bad):
    """Prove rejection order, never emulate PostgreSQL or model behavior."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from psycopg.pq import TransactionStatus
    from scripts.evaluation.semantic.calibration import measure

    data, _ = arithmetic_inputs()
    info = SimpleNamespace(
        host="/tmp/clip-listings-test-controlled/pgsocket",
        user="clip_ci",
        dbname="clip_test_ci",
        port=55438,
        transaction_status=TransactionStatus.IDLE,
    )
    connection = SimpleNamespace(info=info, autocommit=True, execute=AsyncMock())
    helper = SimpleNamespace(
        spec=default_pipeline_spec(),
        encode_listing=AsyncMock(),
        encode_query=AsyncMock(),
    )
    if bad == "host":
        info.host = "/tmp/unapproved/pgsocket"
    if bad == "user":
        info.user = "other"
    if bad == "database":
        info.dbname = "existing"
    if bad == "port":
        info.port = 5433
    if bad == "transaction":
        info.transaction_status = TransactionStatus.INTRANS
    if bad == "autocommit":
        connection.autocommit = False
    if bad == "pipeline":
        helper.spec = None
    with pytest.raises(CalibrationError, match="disposable_idle_target_required"):
        asyncio.run(measure(connection, helper, data))
    connection.execute.assert_not_awaited()
    helper.encode_listing.assert_not_awaited()
    helper.encode_query.assert_not_awaited()
