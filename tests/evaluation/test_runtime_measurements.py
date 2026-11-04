"""Check privacy, phase separation, fresh-start gates and frozen coverage order."""

from datetime import UTC, datetime, timedelta
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts.evaluation import fresh_runtime as resetter
from scripts.evaluation.performance_campaign import build_campaign, verify_fresh_receipt
from scripts.evaluation.runtime_observations import collect, request_event, summarize
from scripts.evaluation.runtime_observations import stage_event

ID = "12345678-1234-4234-8234-123456789abc"


def test_stage_events_are_safe_and_keep_nested_measurements_separate(tmp_path):
    """Join stage totals by hashed request without adding overlapping spans."""
    event = {
        "timestamp": 1,
        "message": json.dumps(
            {
                "event": "request_stage",
                "request_id": ID,
                "duration_ms": 2,
                "stage": "identity.pool_acquire",
                "private": "PRIVATE",
            }
        ),
    }
    row = stage_event(event)
    assert row and "PRIVATE" not in json.dumps(row) and ID not in json.dumps(row)
    app = {
        "request_id_sha256": row["request_id_sha256"],
        "log_stream_sha256": "a" * 64,
        "timestamp_ms": 1,
        "server_duration_ms": 10,
        "status": 200,
    }
    raw = tmp_path / "raw.ndjson"
    raw.write_text(
        json.dumps(
            {
                "type": "Point",
                "metric": "clip_comparison_elapsed_ms",
                "data": {
                    "value": 10,
                    "tags": {
                        "phase": "measured",
                        "sample_index": "0",
                        "outcome": "correct",
                        "request_id_sha256": row["request_id_sha256"],
                    },
                },
            }
        )
        + "\n"
    )
    result = summarize(
        raw,
        {
            "requests": [app],
            "platform_reports": [],
            "stages": [row, {**row, "duration_ms": 3}],
            "collection_complete": True,
        },
    )
    assert result["stage_timings"][0]["p95_ms"] == 5
    assert result["nested_stages_must_not_be_summed"]


def test_safe_request_and_phase_join_preserves_raw(tmp_path):
    """Match actual IDs while retaining rejected requests and separate distributions."""
    event = {
        "timestamp": 100,
        "logStreamName": "api/task-id",
        "message": json.dumps(
            {
                "event": "request_completed",
                "request_id": ID,
                "duration_ms": 3,
                "status": 200,
                "cookie": "PRIVATE",
            }
        ),
    }
    app = request_event(event)
    assert "PRIVATE" not in json.dumps(app) and ID not in json.dumps(app)
    raw = tmp_path / "raw.ndjson"
    rows = []
    for phase, value, digest in (
        ("burst_warmup", 100, app["request_id_sha256"]),
        ("burst_measured", 10, ""),
    ):
        rows.append(
            {
                "type": "Point",
                "metric": "clip_comparison_elapsed_ms",
                "data": {
                    "value": value,
                    "tags": {
                        "phase": phase,
                        "sample_index": "0",
                        "outcome": "correct" if digest else "http_error",
                        "request_id_sha256": digest,
                    },
                },
            }
        )
    raw.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    before = raw.read_bytes()
    evidence = {"requests": [app], "platform_reports": [], "collection_complete": True}
    report = summarize(raw, evidence)
    assert report["phases"]["burst_warmup"]["p95_ms"] == 100
    assert report["phases"]["burst_measured"]["p95_ms"] == 10
    assert report["phases"]["burst_measured"]["unattributed"] == 1
    assert report["missing_initialization_means_warm"] is False
    assert raw.read_bytes() == before
    # The Lambda invocation ID and the application's UUID are different.
    # Only matching START/REPORT boundaries plus one completion can join them.
    evidence["invocation_starts"] = [
        {
            "request_id_sha256": "b" * 64,
            "log_stream_sha256": app["log_stream_sha256"],
            "timestamp_ms": 90,
        }
    ]
    evidence["platform_reports"] = [
        {
            "request_id_sha256": "b" * 64,
            "log_stream_sha256": app["log_stream_sha256"],
            "timestamp_ms": 110,
            "initialization_observed": True,
            "init_duration_ms": 50,
        }
    ]
    report = summarize(raw, evidence)
    assert (
        report["phases"]["burst_warmup"]["confirmed_initialization_client_samples"] == 1
    )
    assert report["cold_request_latency_attribution_verified"]
    evidence["requests"].append({**app, "request_id_sha256": "c" * 64})
    assert not summarize(raw, evidence)["cold_request_latency_attribution_verified"]
    raw.write_text(raw.read_text() + json.dumps(rows[0]) + "\n")
    with pytest.raises(ValueError, match="duplicate_runtime_sample"):
        summarize(raw, evidence)


def test_initialization_and_pagination():
    """Only explicit Init Duration counts; a repeated pagination token fails."""
    event = {
        "timestamp": 100,
        "logStreamName": "stream",
        "message": f"REPORT RequestId: {ID} Duration: 3.0 ms Init Duration: 1000.0 ms",
    }
    logs = SimpleNamespace(filter_log_events=lambda **_: {"events": [event]})
    evidence = collect(logs, "group", 0, 200)
    assert evidence["platform_reports"][0]["initialization_observed"]
    logs.filter_log_events = lambda **_: {"events": [], "nextToken": "same"}
    with pytest.raises(ValueError, match="pagination_invalid"):
        collect(logs, "group", 0, 200)


def test_campaign_is_coverage_first_and_keeps_all_performance_repetitions():
    """Formal/NFR timing remains five minutes; every comparison pair stays matched."""
    campaign = build_campaign("campaign-fixture")
    rows = campaign["entries"]
    assert len({row["run_id"] for row in rows}) == len(rows)
    first_repeat = next(i for i, row in enumerate(rows) if row["stage"] == "repeat")
    assert {row["kind"] for row in rows[:first_repeat]} == {
        f"nfr-0{i}" for i in range(1, 8)
    }
    for kind in ("nfr-01", "nfr-02", "nfr-03", "nfr-05"):
        for config in ("A", "B"):
            selected = [
                row
                for row in rows
                if row["kind"] == kind and row["configuration"] == config
            ]
            assert [row["repetition"] for row in selected] == [1, 2, 3]
            assert all(row["measured_seconds"] == 300 for row in selected)
    comparison = [row for row in rows if row["kind"] == "comparison"]
    assert len(comparison) == 18
    assert [row["configuration"] for row in comparison[6:8]] == ["B", "A"]
    assert campaign["hold_after_lambda_pilots"] and not campaign["execution_authorized"]


def fresh(now, config="A"):
    """Synthetic ready receipt, with no credential or live resource identifiers."""
    return {
        "run_id": "fixture-run",
        "configuration": config,
        "target_plan_sha256": "a" * 64,
        "state": "prepared_requires_log_confirmation",
        "old_ecs_tasks": ["old-a", "old-b"],
        "new_ecs_tasks": [{"task_arn": "new-a"}, {"task_arn": "new-b"}],
        "ended_at_utc": now.isoformat(),
        "lambda_revision": "new-revision",
        "lambda_reset_marker": "fixture-run",
    }


@pytest.mark.parametrize(
    "change", ["old_task", "wrong_run", "expired", "partial", "lambda_marker"]
)
def test_fresh_receipt_rejects_incomplete_or_wrong_runtime(change):
    """A reset command is not sufficient evidence that a fresh runtime is ready."""
    now = datetime.now(UTC)
    receipt = fresh(now, "B")
    target = {"run_id": "fixture-run", "configuration": "B"}
    verify_fresh_receipt(receipt, target, now)
    if change == "old_task":
        receipt["new_ecs_tasks"][0]["task_arn"] = "old-a"
    elif change == "wrong_run":
        receipt["run_id"] = "another-run"
    elif change == "expired":
        receipt["ended_at_utc"] = (now - timedelta(minutes=16)).isoformat()
    elif change == "partial":
        receipt["state"] = "restarting_ecs"
    else:
        receipt["lambda_reset_marker"] = "old-run"
    with pytest.raises(ValueError):
        verify_fresh_receipt(receipt, target, now)


def test_reset_requires_exact_and_unexpired_approval():
    """Preparation has a separate exact approval; load approval cannot replace it."""
    now = datetime.now(UTC)
    raw = b"frozen plan"
    approval = {
        "action": "prepare_fresh_application_runtimes",
        "approved": True,
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "review_record": "human fixture",
        "approved_at_utc": now.isoformat(),
        "expires_at_utc": (now + timedelta(minutes=15)).isoformat(),
    }
    resetter.validate_approval(raw, approval, now)
    with pytest.raises(ValueError):
        resetter.validate_approval(b"changed plan", approval, now)
    with pytest.raises(ValueError):
        resetter.validate_approval(raw, approval, now + timedelta(minutes=16))


@pytest.mark.parametrize("configuration", ["A", "B"])
def test_reset_replaces_only_api_tasks_and_preserves_lambda_settings(configuration):
    """Exercise real reset orchestration against local AWS doubles, never AWS."""
    now = datetime.now(UTC)
    resources = {
        "ecs_cluster_arn": "cluster",
        "ecs_service_arn": "service/api",
        "ecs_task_definition_arn": "api:14",
        "ecs_target_group_arn": "api-target",
        "lambda_function_arn": "function",
    }
    state = {
        "restart": False,
        "env": {"ORIGINAL_SETTING": "unchanged"},
        "revision": "old",
        "calls": [],
    }

    def update_service(**kwargs):
        state["calls"].append(kwargs)
        state["restart"] = True

    def describe_tasks(**kwargs):
        old = kwargs["tasks"] == ["old-a", "old-b"]
        return {
            "tasks": [
                {
                    "taskArn": name,
                    "lastStatus": "STOPPED" if old else "RUNNING",
                    "taskDefinitionArn": "api:14",
                    "createdAt": now,
                    "startedAt": now,
                    "attachments": [
                        {
                            "details": [
                                {
                                    "name": "privateIPv4Address",
                                    "value": f"10.0.0.{i + 1}",
                                }
                            ]
                        }
                    ],
                }
                for i, name in enumerate(kwargs["tasks"])
            ]
        }

    ecs = SimpleNamespace(
        list_tasks=lambda **_: {
            "taskArns": ["new-a", "new-b"] if state["restart"] else ["old-a", "old-b"]
        },
        update_service=update_service,
        describe_services=lambda **_: {
            "services": [
                {
                    "desiredCount": 2,
                    "runningCount": 2,
                    "pendingCount": 0,
                    "taskDefinition": "api:14",
                }
            ]
        },
        describe_tasks=describe_tasks,
    )
    elb = SimpleNamespace(
        describe_target_health=lambda **_: {
            "TargetHealthDescriptions": [
                {"Target": {"Id": f"10.0.0.{i}"}, "TargetHealth": {"State": "healthy"}}
                for i in (1, 2)
            ]
        }
    )

    def update_function(**kwargs):
        assert set(kwargs) == {"FunctionName", "RevisionId", "Environment"}
        state["env"] = kwargs["Environment"]["Variables"]
        state["revision"] = "new"

    lam = SimpleNamespace(
        get_function_configuration=lambda **_: {
            "LastUpdateStatus": "Successful",
            "RevisionId": state["revision"],
            "MemorySize": 2048,
            "Timeout": 5,
            "Environment": {"Variables": state["env"]},
        },
        update_function_configuration=update_function,
    )
    session = SimpleNamespace(
        client=lambda name: {"ecs": ecs, "elbv2": elb, "lambda": lam}[name]
    )
    plan = {
        "run_id": "fixture-run",
        "configuration": configuration,
        "target_plan_sha256": "a" * 64,
        "maximum_transition_seconds": 900,
        "poll_seconds": 5,
        "recycle_lambda": configuration == "B",
    }
    result = resetter.reset(
        plan,
        {"resources": resources},
        session,
        monotonic=lambda: 1,
        sleep=lambda _: None,
    )
    assert result["state"] == "prepared_requires_log_confirmation"
    assert result["cold_observations_confirmed"] is False
    assert len(state["calls"]) == 1 and state["calls"][0]["service"] == "service/api"
    assert state["env"]["ORIGINAL_SETTING"] == "unchanged"
    if configuration == "B":
        assert state["env"][resetter.MARKER] == "fixture-run"
    else:
        assert resetter.MARKER not in state["env"]
