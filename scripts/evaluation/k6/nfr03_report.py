"""Report NFR-03 mixed-workload accounting without changing raw k6 output."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

MAX_RAW_BYTES = 200_000_000
ROUTES = {
    "browse",
    "search",
    "detail",
    "wanted",
    "conversations",
    "saved",
    "wanted_create",
}
OUTCOMES = {
    "correct",
    "incorrect",
    "timeout",
    "throttled",
    "unauthorized",
    "http_error",
    "transport_error",
}
ROUTE_FRACTIONS = {
    "browse": 30,
    "search": 25,
    "detail": 15,
    "wanted": 10,
    "conversations": 10,
    "saved": 9,
    "wanted_create": 1,
}
UUID4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def _value(point: dict[str, Any]) -> float:
    value = point.get("data", {}).get("value")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("invalid_metric_value")
    return float(value)


def _quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize(points: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    if (
        profile.get("nfr_id") != "nfr-03"
        or profile.get("purpose") != "nfr-local-preparation"
        or profile.get("rate_rps") != 50
        or profile.get("warmup_seconds") != 60
        or profile.get("measured_seconds") != 300
    ):
        raise ValueError("invalid_nfr03_profile")
    case_hash = hashlib.sha256(
        json.dumps(
            profile.get("cases"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    if case_hash != profile.get("case_bundle_sha256") or not re.fullmatch(
        r"[0-9a-f]{64}", profile.get("fixture_binding_sha256", "")
    ):
        raise ValueError("nfr03_profile_hash_mismatch")
    expected = {"nfr_warmup": 3000, "nfr_measured": 15000}
    # Keep the metric accumulator flexible at the ingestion boundary: points
    # carry different fields, while the report validates their relationships
    # before serializing any result.
    data: dict[str, dict[str, Any]] = {
        phase: {
            "issued": 0,
            "http": 0,
            "dropped": 0,
            "invalid_clock": 0,
            "outcomes": Counter(),
            "latencies": [],
            "routes": defaultdict(
                lambda: {"issued": 0, "http": 0, "outcomes": Counter(), "latencies": []}
            ),
        }
        for phase in expected
    }
    operation_outcomes: dict[str, str] = {}
    operation_ids: set[str] = set()
    created_rows: dict[str, str] = {}
    tracked = {
        "clip_nfr03_issued",
        "http_reqs",
        "dropped_iterations",
        "clip_nfr03_clock_invalid",
        "clip_nfr03_outcomes",
        "clip_nfr03_elapsed_ms",
        "clip_nfr03_created_rows",
        "clip_nfr03_reconciliation_status",
        "clip_nfr03_reconciled_rows",
    }
    reconciliation_statuses: Counter[str] = Counter()
    reconciled_rows: dict[str, str] = {}
    reconciliation_http_requests = 0
    for point in points:
        if point.get("type") != "Point" or point.get("metric") not in tracked:
            continue
        metric = point["metric"]
        tags = point.get("data", {}).get("tags") or {}
        if not isinstance(tags, dict):
            raise ValueError("invalid_metric_tags")
        if metric == "http_reqs" and tags.get("route") == "wanted_reconcile":
            if (
                tags.get("nfr_id") != "nfr-03"
                or tags.get("run_id") != profile.get("run_id")
                or tags.get("configuration") != profile.get("configuration")
                or tags.get("phase") != "nfr_reconciliation"
            ):
                raise ValueError("reconciliation_request_identity_mismatch")
            count = _value(point)
            if not count.is_integer():
                raise ValueError("reconciliation_request_count_must_be_integer")
            reconciliation_http_requests += int(count)
            continue
        if metric in {"clip_nfr03_reconciliation_status", "clip_nfr03_reconciled_rows"}:
            if (
                tags.get("nfr_id") != "nfr-03"
                or tags.get("run_id") != profile.get("run_id")
                or tags.get("configuration") != profile.get("configuration")
            ):
                raise ValueError("reconciliation_identity_mismatch")
            val = _value(point)
            if not val.is_integer():
                raise ValueError("reconciliation_count_must_be_integer")
            if metric == "clip_nfr03_reconciliation_status":
                status = tags.get("status")
                if status not in {"complete", "incomplete"}:
                    raise ValueError("invalid_reconciliation_status")
                reconciliation_statuses[status] += int(val)
            else:
                operation_id = tags.get("operation_id")
                request_id = tags.get("created_request_id")
                if (
                    not isinstance(operation_id, str)
                    or not UUID4.fullmatch(operation_id)
                    or not isinstance(request_id, str)
                    or not UUID4.fullmatch(request_id)
                    or operation_id in reconciled_rows
                ):
                    raise ValueError("invalid_reconciled_write_binding")
                reconciled_rows[operation_id] = request_id
            continue
        scenario = tags.get("scenario")
        phase = scenario if metric == "dropped_iterations" else tags.get("phase")
        if phase not in data or scenario is not None and scenario != phase:
            raise ValueError("invalid_phase")
        if metric != "dropped_iterations" and (
            tags.get("nfr_id") != "nfr-03"
            or tags.get("run_id") != profile.get("run_id")
            or tags.get("configuration") != profile.get("configuration")
        ):
            raise ValueError("run_identity_mismatch")
        route = tags.get("route")
        if metric not in {"dropped_iterations"} and route not in ROUTES:
            raise ValueError("invalid_route")
        val = _value(point)
        row = data[phase]
        route_data: dict[str, Any] | None = (
            row["routes"][route] if route in ROUTES else None
        )
        if (
            metric
            in {
                "clip_nfr03_issued",
                "http_reqs",
                "dropped_iterations",
                "clip_nfr03_clock_invalid",
                "clip_nfr03_outcomes",
                "clip_nfr03_created_rows",
            }
            and not val.is_integer()
        ):
            raise ValueError("counter_must_be_integer")
        if metric == "clip_nfr03_issued":
            row["issued"] += int(val)
            assert route_data is not None
            route_data["issued"] += int(val)
            if route == "wanted_create":
                operation_id = tags.get("operation_id")
                if (
                    not isinstance(operation_id, str)
                    or not UUID4.fullmatch(operation_id)
                    or operation_id in operation_ids
                ):
                    raise ValueError("duplicate_or_invalid_write_operation_id")
                operation_ids.add(operation_id)
        elif metric == "http_reqs":
            row["http"] += int(val)
            assert route_data is not None
            route_data["http"] += int(val)
        elif metric == "dropped_iterations":
            row["dropped"] += int(val)
        elif metric == "clip_nfr03_clock_invalid":
            row["invalid_clock"] += int(val)
        elif metric == "clip_nfr03_outcomes":
            outcome = tags.get("outcome")
            if outcome not in OUTCOMES:
                raise ValueError("invalid_outcome")
            row["outcomes"][outcome] += int(val)
            assert route_data is not None
            route_data["outcomes"][outcome] += int(val)
            if route == "wanted_create":
                operation_id = tags.get("operation_id")
                if (
                    operation_id not in operation_ids
                    or operation_id in operation_outcomes
                ):
                    raise ValueError("duplicate_write_operation_outcome")
                operation_outcomes[operation_id] = outcome
        elif metric == "clip_nfr03_elapsed_ms":
            outcome = tags.get("outcome")
            if outcome not in OUTCOMES:
                raise ValueError("invalid_latency_outcome")
            row["latencies"].append((val, outcome))
            assert route_data is not None
            route_data["latencies"].append((val, outcome))
        elif metric == "clip_nfr03_created_rows":
            operation_id = tags.get("operation_id")
            request_id = tags.get("created_request_id")
            if (
                operation_id not in operation_ids
                or not isinstance(request_id, str)
                or not UUID4.fullmatch(request_id)
                or operation_id in created_rows
            ):
                raise ValueError("invalid_created_row_binding")
            created_rows[operation_id] = request_id

    phases = {}
    accounting_complete = True
    delivery_complete = True
    for phase, row in data.items():
        outcome_total = sum(row["outcomes"].values())
        labels = Counter(outcome for _, outcome in row["latencies"])
        same_labels = Counter(row["outcomes"]) == labels
        issued, actual = row["issued"], row["http"]
        accounting = (
            issued == actual == outcome_total == len(row["latencies"])
            and row["invalid_clock"] == 0
            and same_labels
        )
        delivered = (
            issued + row["dropped"] == expected[phase]
            and issued == expected[phase]
            and row["dropped"] == 0
        )
        accounting_complete &= accounting
        delivery_complete &= delivered
        route_results = {}
        for route, route_row in sorted(row["routes"].items()):
            n = expected[phase] * ROUTE_FRACTIONS[route] // 100
            route_outcomes = dict(route_row["outcomes"])
            route_accounting = (
                route_row["issued"]
                == route_row["http"]
                == sum(route_outcomes.values())
                == len(route_row["latencies"])
                == n
            )
            route_results[route] = {
                "scheduled": n,
                "issued": route_row["issued"],
                "http_requests": route_row["http"],
                "outcomes": route_outcomes,
                "accounting_complete": route_accounting,
                "latency_ms": {
                    f"p{p}": _quantile([v for v, _ in route_row["latencies"]], p / 100)
                    for p in (50, 95, 99)
                },
            }
            accounting_complete &= route_accounting
        # A complete total can still describe the wrong route mix. Require all
        # seven operation classes to occur at their exact scheduled counts.
        accounting_complete &= set(row["routes"]) == ROUTES
        phases[phase] = {
            "scheduled": expected[phase],
            "issued": issued,
            "http_requests": actual,
            "dropped_iterations": row["dropped"],
            "invalid_clock_samples": row["invalid_clock"],
            "outcomes": dict(row["outcomes"]),
            "accounting_complete": accounting,
            "delivery_complete": delivered,
            "routes": route_results,
        }

    measured = data["nfr_measured"]
    denominator = measured["issued"]
    successes = sum(
        1
        for duration, label in measured["latencies"]
        if label == "correct" and duration <= 5000
    )
    ratio = successes / denominator if denominator else None
    missing_write_outcomes = sorted(operation_ids - set(operation_outcomes))
    extra_write_outcomes = sorted(set(operation_outcomes) - operation_ids)
    missing_reconciled_writes = sorted(operation_ids - set(reconciled_rows))
    unissued_reconciled_writes = sorted(set(reconciled_rows) - operation_ids)
    reconciliation_complete = (
        reconciliation_statuses == Counter({"complete": 1})
        and len(reconciled_rows) == 180
        and not missing_reconciled_writes
        and not unissued_reconciled_writes
    )
    unresolved_write_ids = sorted(
        operation_id
        for operation_id in operation_ids
        if operation_outcomes.get(operation_id) != "correct"
    )
    return {
        "preview_only": True,
        "nfr_id": "nfr-03",
        "configuration": profile["configuration"],
        "run_id": profile["run_id"],
        "dataset_fingerprint": profile["dataset_fingerprint"],
        "fixture_binding_sha256": profile["fixture_binding_sha256"],
        "case_bundle_sha256": profile["case_bundle_sha256"],
        "execution_permitted": False,
        "nfr_accepted": False,
        "accounting_complete": accounting_complete,
        "delivery_complete": delivery_complete,
        "write_reconciliation_complete": reconciliation_complete,
        "latency_timing_verified": False,
        "successes_within_5000ms": successes,
        "denominator_all_issued_measured_operations": denominator,
        "success_fraction": ratio,
        "threshold_met_in_preview": ratio is not None
        and ratio >= 0.95
        and accounting_complete
        and delivery_complete
        and reconciliation_complete,
        "phases": phases,
        "write_reconciliation": {
            "operation_ids_issued": len(operation_ids),
            "expected_total_including_warmup": 180,
            "operation_ids_with_outcome": len(operation_outcomes),
            "created_request_ids_by_operation_id": created_rows,
            "reconciled_request_ids_by_operation_id": reconciled_rows,
            "missing_outcome_operation_ids": missing_write_outcomes,
            "unissued_outcome_operation_ids": extra_write_outcomes,
            "missing_reconciled_operation_ids": missing_reconciled_writes,
            "unissued_reconciled_operation_ids": unissued_reconciled_writes,
            "post_run_status_counts": dict(reconciliation_statuses),
            "post_run_http_requests": reconciliation_http_requests,
            "operations_requiring_reconciliation": unresolved_write_ids,
            "cleanup_status": "not_executed_by_report",
        },
        "raw_data": "Read only; raw k6 JSONL is not rewritten.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("raw", type=Path)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-receipt", type=Path)
    parser.add_argument("--run-plan", type=Path)
    args = parser.parse_args()
    try:
        if (
            args.raw.stat().st_size > MAX_RAW_BYTES
            or args.profile.stat().st_size > 5_000_000
        ):
            raise ValueError("input_too_large")
        points = [
            json.loads(line)
            for line in args.raw.read_text().splitlines()
            if line.strip()
        ]
        profile = json.loads(args.profile.read_text())
        report = summarize(points, profile)
        if bool(args.execution_receipt) != bool(args.run_plan):
            raise ValueError("both execution receipt and run plan are required")
        if args.execution_receipt:
            try:
                from scripts.evaluation.k6.real_run_evidence import verify_execution

                binding = verify_execution(
                    args.execution_receipt,
                    args.run_plan,
                    args.raw,
                    args.profile,
                    workload_kind="nfr-03",
                    configuration=profile["configuration"],
                    run_id=profile["run_id"],
                )
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
                binding = {
                    "execution_artifact_binding_verified": False,
                    "failure_code": (
                        str(error)
                        if isinstance(error, ValueError)
                        else "execution_evidence_invalid"
                    ),
                    "nfr_accepted": False,
                }
            report["execution_provenance"] = binding
            report["latency_timing_verified"] = (
                binding.get("execution_artifact_binding_verified") is True
                and binding.get("latency_timing_binary_hash_bound") is True
            )
            if not report["latency_timing_verified"]:
                report["threshold_met_in_preview"] = False
        else:
            report["execution_provenance"] = None
        with args.output.open("x", encoding="utf-8") as output:
            output.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        if (
            not report["accounting_complete"]
            or not report["delivery_complete"]
            or not report["write_reconciliation_complete"]
        ):
            raise SystemExit(1)
    except OSError, ValueError, KeyError, json.JSONDecodeError:
        parser.exit(2, "Could not produce an NFR-03 accounting preview\n")


if __name__ == "__main__":
    main()
