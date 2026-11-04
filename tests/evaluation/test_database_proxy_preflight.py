"""Fail closed on unexpected endpoint overrides or a proxy bound to another DB."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from scripts.evaluation.k6.real_target_preflight import _verify_database_proxy
from scripts.evaluation.k6.exp05_pilot import (
    build_plan,
    _validate_plan,
    summarize_pilot,
)

PROXY = {
    "name": "clip-shared-test-pool",
    "arn": "arn:aws:rds:ap-south-1:335523638354:db-proxy:prx-example",
    "endpoint": "clip-shared-test-pool.proxy-example.ap-south-1.rds.amazonaws.com",
}
DATABASE = {
    "DbiResourceId": "db-example",
    "Endpoint": {"Address": "source.example", "Port": 5432},
}
ENVIRONMENT = {"CLIP_DATABASE_PROXY_ENDPOINT": PROXY["endpoint"]}


def client():
    """Return independently mutable AWS response fixtures, not a live transport."""
    proxy = {
        "DBProxyArn": PROXY["arn"],
        "Endpoint": PROXY["endpoint"],
        "Status": "available",
        "EngineFamily": "POSTGRESQL",
        "RequireTLS": True,
        "DebugLogging": False,
        "IdleClientTimeout": 300,
    }
    group = {
        "TargetGroupName": "default",
        "ConnectionPoolConfig": {
            "ConnectionBorrowTimeout": 1,
            "MaxConnectionsPercent": 75,
            "MaxIdleConnectionsPercent": 50,
            "InitQuery": "SET statement_timeout='5s'; SET lock_timeout='1s'; SET idle_in_transaction_session_timeout='5s'",
        },
    }
    target = {
        "Type": "RDS_INSTANCE",
        "RdsResourceId": "db-example",
        "Endpoint": "source.example",
        "Port": 5432,
        "TargetHealth": {"State": "AVAILABLE"},
    }
    return SimpleNamespace(
        proxy=proxy,
        group=group,
        target=target,
        describe_db_proxies=lambda **_: {"DBProxies": [proxy]},
        describe_db_proxy_target_groups=lambda **_: {"TargetGroups": [group]},
        describe_db_proxy_targets=lambda **_: {"Targets": [target]},
    )


def test_exact_proxy_target_and_both_runtimes_required():
    _verify_database_proxy(client(), PROXY, DATABASE, ENVIRONMENT, ENVIRONMENT)
    for a, b in (({}, ENVIRONMENT), (ENVIRONMENT, {})):
        with pytest.raises(ValueError, match="runtime_database_proxy"):
            _verify_database_proxy(client(), PROXY, DATABASE, a, b)


def test_direct_plan_refuses_unrecorded_proxy():
    _verify_database_proxy(None, None, DATABASE, {}, None)
    with pytest.raises(ValueError, match="runtime_database_proxy"):
        _verify_database_proxy(None, None, DATABASE, ENVIRONMENT, None)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("Endpoint", "another.example"),
        ("RdsResourceId", "db-other"),
        ("TargetHealth", {"State": "UNAVAILABLE"}),
        ("Type", "TRACKED_CLUSTER"),
        ("Port", 6432),
    ],
)
def test_proxy_to_wrong_or_unavailable_database_refused(field, bad):
    aws = client()
    aws.target[field] = bad
    with pytest.raises(ValueError, match="proxy_target"):
        _verify_database_proxy(aws, PROXY, DATABASE, ENVIRONMENT, ENVIRONMENT)


@pytest.mark.parametrize(
    "field,bad",
    [("RequireTLS", False), ("DebugLogging", True), ("IdleClientTimeout", 1800)],
)
def test_changed_proxy_safety_settings_refused(field, bad):
    aws = client()
    aws.proxy[field] = bad
    with pytest.raises(ValueError, match="proxy_state"):
        _verify_database_proxy(aws, PROXY, DATABASE, ENVIRONMENT, ENVIRONMENT)


def test_unbounded_backend_pool_refused():
    aws = client()
    aws.group["ConnectionPoolConfig"]["MaxConnectionsPercent"] = 100
    with pytest.raises(ValueError, match="proxy_pool"):
        _verify_database_proxy(aws, PROXY, DATABASE, ENVIRONMENT, ENVIRONMENT)


def test_new_pilot_contains_only_baseline_and_full_offload_but_keeps_repetitions():
    bindings = {
        f"pilot-{mode}-r{i}": "a" * 64 for mode in ("base", "l100") for i in (1, 2, 3)
    }
    plan = build_plan("pilot", "b" * 64, bindings)
    assert _validate_plan(plan) == plan
    assert len(plan["runs"]) == 6
    assert plan["candidate_weights_lambda_ecs_percent"] == [[100, 0]]
    with pytest.raises(ValueError, match="all_declared"):
        summarize_pilot(plan, [])
    changed = deepcopy(plan)
    changed["runs"].pop()
    with pytest.raises(ValueError, match="complete_run_matrix"):
        _validate_plan(changed)


def pilot_records(plan):
    """Bind synthetic complete reports to each declared repetition for scoring."""
    return [
        {
            **row,
            "workload_sha256": plan["workload"]["sha256"],
            "resource_checks": {
                key: True
                for key in (
                    "database_headroom",
                    "generator_headroom",
                    "telemetry_complete",
                    "cost_under_cap",
                    "routing_weight_verified",
                )
            },
            "report": {
                "preview_only": True,
                "accounting_complete": True,
                "delivery_complete": True,
                "execution_provenance": {
                    "execution_artifact_binding_verified": True,
                    "target_plan_sha256": row["target_plan_sha256"],
                },
                "client_metrics": {
                    "burst_measured": {
                        "accounting_complete": True,
                        "delivery_complete": True,
                        "issued": 6000,
                        "correct": 6000,
                        "dropped_iterations": 0,
                        "correct_latency_ms": {"p95_ms": 200},
                        "failed": 0,
                    }
                },
            },
        }
        for row in plan["runs"]
    ]


@pytest.mark.parametrize("historical", [False, True])
def test_current_and_historical_pilots_score_all_results_without_inventing_success(
    historical,
):
    import hashlib
    import json

    bindings = {
        f"pilot-{mode}-r{i}": "a" * 64 for mode in ("base", "l100") for i in (1, 2, 3)
    }
    plan = build_plan("pilot", "b" * 64, bindings)
    if historical:
        plan["schema_version"] = 1
        plan["candidate_weights_lambda_ecs_percent"] += [[75, 25], [50, 50], [25, 75]]
        for weight in (75, 50, 25):
            plan["run_order"].append(f"lambda_ecs_{weight}_{100-weight}")
            for repetition in (1, 2, 3):
                plan["runs"].append(
                    {
                        "run_id": f"pilot-l{weight}-r{repetition}",
                        "configuration": "B",
                        "lambda_weight_percent": weight,
                        "ecs_weight_percent": 100 - weight,
                        "repetition": repetition,
                        "target_plan_sha256": "a" * 64,
                    }
                )
        plan["target_binding_sha256"] = hashlib.sha256(
            json.dumps(
                {row["run_id"]: row["target_plan_sha256"] for row in plan["runs"]},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    records = pilot_records(plan)
    assert summarize_pilot(plan, records)["selected_lambda_weight_percent"] == 100
    records[3]["resource_checks"]["database_headroom"] = False
    result = summarize_pilot(plan, records)
    assert result["selected_lambda_weight_percent"] == (75 if historical else None)
    assert result["candidate_results"][0]["eligible"] is False
    assert result["nfr_accepted"] is False
    records[0]["report"]["client_metrics"]["burst_measured"]["correct"] = 6001
    result = summarize_pilot(plan, records)
    assert result["baseline_eligible"] is False
    assert result["selected_lambda_weight_percent"] is None
