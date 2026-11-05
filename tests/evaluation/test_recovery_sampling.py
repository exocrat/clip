"""A slow response must not serialize a one-request-per-second recovery stream."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import json
from scripts.evaluation import nfr06_recovery as recovery


def harness(monkeypatch: Any, start: int = 0) -> list[int]:
    clock = [start]

    class Future:
        def __init__(self) -> None:
            self.issued = clock[0]

        def done(self) -> bool:
            return clock[0] >= self.issued + 2_000_000_000

        def result(self, timeout: int = 6) -> tuple[int, str, int]:
            clock[0] = max(clock[0], self.issued + 2_000_000_000)
            return 200, "success", self.issued + 2_000_000_000

    class Executor:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["max_workers"] == 6

        def submit(self, call: Any) -> Future:
            return Future()

        def shutdown(self, **kwargs: Any) -> None:
            pass

    monkeypatch.setattr(recovery, "ThreadPoolExecutor", Executor)
    monkeypatch.setattr(recovery.time, "monotonic_ns", lambda: clock[0])
    monkeypatch.setattr(
        recovery.time,
        "sleep",
        lambda seconds: clock.__setitem__(0, clock[0] + round(seconds * 1e9)),
    )
    return clock


def plan(tmp_path: Path) -> dict[str, Any]:
    return {
        "target_origin": "https://synthetic.example.invalid",
        "listing_read_path": "/api/listings",
        "ecs_read_path": "/api/me",
        "observation_path": str(tmp_path / "events.ndjson"),
    }


def test_two_second_reads_keep_one_per_second_and_preserve_all_outcomes(
    monkeypatch: Any, tmp_path: Path
) -> None:
    harness(monkeypatch)
    p = plan(tmp_path)
    rows, _ = recovery._load_window(p, "__Host-clip_session=synthetic", "baseline", 6)
    assert len(rows) == 6 and all(r["outcome"] == "success" for r in rows)
    assert [r["issued_monotonic_ns"] for r in rows] == [
        i * 1_000_000_000 for i in range(6)
    ]
    evidence = [
        json.loads(x) for x in Path(p["observation_path"]).read_text().splitlines()
    ]
    assert len(evidence) == 6 and all(x["event"] == "request_outcome" for x in evidence)
    assert "synthetic" not in Path(p["observation_path"]).read_text()


def test_stop_deadline_includes_time_already_spent_in_stop_api(
    monkeypatch: Any, tmp_path: Path
) -> None:
    harness(monkeypatch, 100_000_000_000)
    rows, restored = recovery._load_window(
        plan(tmp_path),
        "synthetic",
        "recovery",
        300,
        stop_at_deadline=True,
        deadline_ns=110_000_000_000,
        recovery_probe=lambda: {"serving_capacity_restored": False},
    )
    assert len(rows) == 10 and restored is None


def test_recovery_rejects_two_healthy_targets_for_different_tasks() -> None:
    """Counts alone cannot establish recovery when the ALB still sees old IPs."""
    from types import SimpleNamespace

    ecs = SimpleNamespace(
        describe_services=lambda **_: {
            "services": [{"desiredCount": 2, "runningCount": 2, "pendingCount": 0}]
        },
        list_tasks=lambda **_: {"taskArns": ["api-1", "api-2"]},
        describe_tasks=lambda **_: {
            "tasks": [
                {
                    "taskArn": f"api-{i}",
                    "lastStatus": "RUNNING",
                    "attachments": [
                        {
                            "details": [
                                {"name": "privateIPv4Address", "value": f"10.0.0.{i}"}
                            ]
                        }
                    ],
                }
                for i in (1, 2)
            ]
        },
    )
    targets = [
        {"Target": {"Id": f"10.0.0.{i}"}, "TargetHealth": {"State": "healthy"}}
        for i in (1, 2)
    ]
    elb = SimpleNamespace(
        describe_target_health=lambda **_: {"TargetHealthDescriptions": targets}
    )
    p = {
        "cluster_arn": "cluster",
        "service_arn": "arn/service/cluster/api",
        "desired_count": 2,
        "target_group_arn": "tg",
    }
    assert recovery._describe_capacity(ecs, elb, p)["serving_capacity_restored"]
    targets[1]["Target"]["Id"] = "10.0.0.99"
    observed = recovery._describe_capacity(ecs, elb, p)
    assert observed["healthy_alb_targets"] == 2
    assert not observed["healthy_targets_match_api_tasks"]
    assert not observed["serving_capacity_restored"]


def test_stop_acknowledgement_cannot_count_stale_original_tasks_as_recovered(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """AWS may briefly report the original healthy pair after StopTask returns."""
    from types import SimpleNamespace
    from data.generators import reference_login

    p = {
        **plan(tmp_path),
        "run_id": "synthetic-recovery",
        "configuration": "A",
        "account_id": "synthetic-account",
        "region": "synthetic-region",
        "cluster_arn": "synthetic-cluster",
        "service_arn": "synthetic-service",
        "task_arn": "original-task",
        "target_group_arn": "synthetic-target-group",
        "target_manifest_sha256": "0" * 64,
    }
    ecs = SimpleNamespace(stop_task=lambda **_: {"task": {"taskArn": p["task_arn"]}})
    clients = {
        "sts": SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": p["account_id"],
                "Arn": "synthetic-operator",
            }
        ),
        "ecs": ecs,
        "elbv2": object(),
    }
    monkeypatch.setattr(
        reference_login,
        "sdk_profile_session",
        lambda **_: SimpleNamespace(client=clients.__getitem__),
    )
    monkeypatch.setattr(
        recovery, "_load_target_plan", lambda _: {"aws_profile": "synthetic"}
    )
    monkeypatch.setattr(recovery, "inspect_target", lambda _: None)
    monkeypatch.setattr(recovery, "check_session_identity", lambda *_: None)
    state = {
        "serving_capacity_restored": True,
        "task_arns": ["original-task", "surviving-task"],
    }
    monkeypatch.setattr(recovery, "_describe_capacity", lambda *_: dict(state))

    def load_window(*args: Any, **kwargs: Any) -> Any:
        if args[2] == "baseline":
            return [{"outcome": "success"} for _ in range(60)], None
        stale = kwargs["recovery_probe"]()
        assert not stale["stopped_task_absent"]
        assert not stale["serving_capacity_restored"]
        state["task_arns"] = ["replacement-task", "surviving-task"]
        fresh = kwargs["recovery_probe"]()
        assert fresh["stopped_task_absent"] and fresh["serving_capacity_restored"]
        return [], {
            "elapsed_monotonic_ns": recovery.time.monotonic_ns(),
            "state": fresh,
        }

    monkeypatch.setattr(recovery, "_load_window", load_window)
    result = recovery.run(p, {"approval_id": "synthetic-approval"})
    assert result["restored_capacity_state"]["stopped_task_absent"]
