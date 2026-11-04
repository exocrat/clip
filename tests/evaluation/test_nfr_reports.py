"""Synthetic accounting checks for the NFR-01/02 and NFR-03 previews."""

import hashlib
import json
import pytest
from uuid import uuid4

from scripts.evaluation.k6.nfr03_report import summarize as summarize_nfr03
from scripts.evaluation.k6.nfr_report import summarize as summarize_nfr01_02


def _point(metric, value, tags):
    return {"type": "Point", "metric": metric, "data": {"value": value, "tags": tags}}


def _nfr_profile(nfr_id):
    cases = []
    rate = 20 if nfr_id == "nfr-01" else 10
    return {
        "purpose": "nfr-local-preparation",
        "nfr_id": nfr_id,
        "configuration": "A",
        "run_id": "synthetic-report-test",
        "dataset_fingerprint": "synthetic",
        "cases": cases,
        "case_bundle_sha256": hashlib.sha256(b"[]").hexdigest(),
        "rate_rps": rate,
        "warmup_seconds": 60,
        "measured_seconds": 300,
        "drain_seconds": 5,
    }


def test_nfr02_counts_timeouts_in_the_issued_request_denominator():
    profile = _nfr_profile("nfr-02")
    points = []
    for phase, total in (("nfr_warmup", 600), ("nfr_measured", 3000)):
        base = {
            "nfr_id": "nfr-02",
            "configuration": "A",
            "run_id": profile["run_id"],
            "phase": phase,
        }
        for metric in ("clip_nfr_issued", "http_reqs"):
            points.append(_point(metric, total, base))
        successes = total if phase == "nfr_warmup" else 2800
        timeouts = total - successes
        for outcome, count in (("completed", successes), ("timeout", timeouts)):
            outcome_tags = {**base, "outcome": outcome}
            points.append(_point("clip_nfr_outcomes", count, outcome_tags))
            points.extend(
                _point("clip_nfr_elapsed_ms", 500, outcome_tags) for _ in range(count)
            )

    report = summarize_nfr01_02(points, profile)
    assert report["accounting_complete"] is True
    assert report["delivery_complete"] is True
    assert report["denominator"] == 3000
    assert report["successful_responses_within_1000ms"] == 2800
    assert report["fraction_within_1000ms"] == 2800 / 3000
    assert report["threshold_met_in_preview"] is False
    assert report["nfr_accepted"] is False


def _nfr03_inputs(*, short=False):
    cases = {"synthetic": True}
    case_hash = hashlib.sha256(
        json.dumps(
            cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    profile = {
        "purpose": "nfr-local-preparation",
        "nfr_id": "nfr-03",
        "configuration": "A",
        "run_id": "synthetic-nfr03-report",
        "dataset_fingerprint": "synthetic",
        "fixture_binding_sha256": "a" * 64,
        "cases": cases,
        "case_bundle_sha256": case_hash,
        "rate_rps": 50,
        "warmup_seconds": 10 if short else 60,
        "measured_seconds": 60 if short else 300,
    }
    points = [
        _point(
            "http_reqs",
            1,
            {
                "nfr_id": "nfr-03",
                "configuration": "A",
                "run_id": profile["run_id"],
                "phase": "nfr_preflight",
                "route": "wanted_fixture",
            },
        )
    ]
    operations = []
    for phase, phase_total in (
        ("nfr_warmup", 50 * profile["warmup_seconds"]),
        ("nfr_measured", 50 * profile["measured_seconds"]),
    ):
        identity = {
            "nfr_id": "nfr-03",
            "configuration": "A",
            "run_id": profile["run_id"],
            "phase": phase,
        }
        for route, percent in (
            ("browse", 30),
            ("search", 25),
            ("detail", 15),
            ("wanted", 10),
            ("conversations", 10),
            ("saved", 9),
            ("wanted_create", 1),
        ):
            count = phase_total * percent // 100
            route_tags = {**identity, "route": route}
            if route == "wanted_create":
                for _ in range(count):
                    operation_id = str(uuid4())
                    request_id = str(uuid4())
                    operations.append((operation_id, request_id))
                    op_tags = {**route_tags, "operation_id": operation_id}
                    points.append(_point("clip_nfr03_issued", 1, op_tags))
                    points.append(
                        _point(
                            "clip_nfr03_outcomes", 1, {**op_tags, "outcome": "correct"}
                        )
                    )
                    points.append(
                        _point(
                            "clip_nfr03_created_rows",
                            1,
                            {**op_tags, "created_request_id": request_id},
                        )
                    )
                points.append(_point("http_reqs", count, route_tags))
            else:
                points.extend(
                    (
                        _point("clip_nfr03_issued", count, route_tags),
                        _point("http_reqs", count, route_tags),
                        _point(
                            "clip_nfr03_outcomes",
                            count,
                            {**route_tags, "outcome": "correct"},
                        ),
                    )
                )
            if route != "wanted_create":
                latency_tags = {**route_tags, "outcome": "correct"}
                points.extend(
                    _point("clip_nfr03_elapsed_ms", 100, latency_tags)
                    for _ in range(count)
                )
            else:
                points.extend(
                    _point(
                        "clip_nfr03_elapsed_ms",
                        100,
                        {
                            **route_tags,
                            "outcome": "correct",
                            "operation_id": operation_id,
                        },
                    )
                    for operation_id, _ in operations[-count:]
                )

    points.append(
        _point(
            "http_reqs",
            1,
            {
                "nfr_id": "nfr-03",
                "configuration": "A",
                "run_id": profile["run_id"],
                "phase": "nfr_reconciliation",
                "route": "wanted_reconcile",
            },
        )
    )
    points.append(
        _point(
            "clip_nfr03_reconciliation_status",
            1,
            {
                "nfr_id": "nfr-03",
                "configuration": "A",
                "run_id": profile["run_id"],
                "status": "complete",
            },
        )
    )
    for operation_id, request_id in operations:
        points.append(
            _point(
                "clip_nfr03_reconciled_rows",
                1,
                {
                    "nfr_id": "nfr-03",
                    "configuration": "A",
                    "run_id": profile["run_id"],
                    "operation_id": operation_id,
                    "created_request_id": request_id,
                },
            )
        )
    return points, profile


def test_nfr03_checks_all_routes_and_reconciles_every_write():
    points, profile = _nfr03_inputs()
    report = summarize_nfr03(points, profile)
    assert report["accounting_complete"] is True
    assert report["delivery_complete"] is True
    assert report["write_reconciliation_complete"] is True
    assert report["denominator_all_issued_measured_operations"] == 15000
    assert report["success_fraction"] == 1
    assert report["nfr_accepted"] is False

    points.append(
        _point(
            "dropped_iterations",
            1,
            {"scenario": "nfr_measured"},
        )
    )
    incomplete = summarize_nfr03(points, profile)
    assert incomplete["delivery_complete"] is False
    assert incomplete["threshold_met_in_preview"] is False


def test_short_local_window_cannot_be_reported_with_formal_defaults():
    """Short runs keep exact write accounting and cannot become formal passes."""
    points, profile = _nfr03_inputs(short=True)
    with pytest.raises(ValueError, match="invalid_nfr03_profile"):
        summarize_nfr03(points, profile)
    report = summarize_nfr03(points, profile, local_short=True)
    assert report["accounting_complete"] is True
    assert report["delivery_complete"] is True
    assert report["write_reconciliation_complete"] is True
    assert report["denominator_all_issued_measured_operations"] == 3000
    assert report["nfr_accepted"] is False
    profile = _nfr_profile("nfr-02") | {"warmup_seconds": 10, "measured_seconds": 60}
    with pytest.raises(ValueError, match="NFR schedule mismatch"):
        summarize_nfr01_02([], profile)
    incomplete = summarize_nfr01_02([], profile, local_short=True)
    assert incomplete["delivery_complete"] is False
    assert incomplete["threshold_met_in_preview"] is False
