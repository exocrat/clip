from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest

from scripts.evaluation.k6.cloudwatch_capture import (
    build_queries,
    capture,
    validate_window,
)


def test_proxy_metrics_bind_name_and_aggregate_all_proxy_nodes():
    plan = _plan()
    plan["format_version"] = 2
    plan["resources"]["database_proxy"] = {
        "name": "clip-shared-test-pool",
        "arn": "arn:aws:rds:ap-south-1:335523638354:db-proxy:prx-example",
        "endpoint": "clip-shared-test-pool.proxy-example.ap-south-1.rds.amazonaws.com",
    }
    queries = build_queries(plan)["proxy"]
    assert len(queries) == 7
    for query in queries:
        metric = query["MetricStat"]
        assert metric["Metric"]["Dimensions"] == [
            {"Name": "ProxyName", "Value": "clip-shared-test-pool"}
        ]
        assert metric["Stat"] == (
            "Average"
            if metric["Metric"]["MetricName"] == "DatabaseConnectionsBorrowLatency"
            else "Sum"
        )


def _plan(configuration: str = "B") -> dict[str, object]:
    is_b = configuration == "B"
    account = "335523638354"
    region = "ap-south-1"
    digest = "a" * 64
    resources = {
        "load_balancer_arn": f"arn:aws:elasticloadbalancing:{region}:{account}:loadbalancer/app/clip-exp03-run/0123456789abcdef",
        "listener_arn": f"arn:aws:elasticloadbalancing:{region}:{account}:listener/app/clip-exp03-run/0123456789abcdef/1111111111111111",
        "listener_rule_arn": (
            f"arn:aws:elasticloadbalancing:{region}:{account}:listener-rule/app/clip-exp03-run/0123456789abcdef/1111111111111111/2222222222222222"
            if is_b
            else None
        ),
        "certificate_arn": f"arn:aws:acm:{region}:{account}:certificate/33333333-3333-4333-8333-333333333333",
        "ecs_cluster_arn": f"arn:aws:ecs:{region}:{account}:cluster/clip-shared-test",
        "ecs_service_arn": f"arn:aws:ecs:{region}:{account}:service/clip-shared-test/clip-api",
        "ecs_task_definition_arn": f"arn:aws:ecs:{region}:{account}:task-definition/clip-api:1",
        "ecs_target_group_arn": f"arn:aws:elasticloadbalancing:{region}:{account}:targetgroup/clip-ecs/4444444444444444",
        "lambda_function_arn": (
            f"arn:aws:lambda:{region}:{account}:function:clip-exp03-lambda"
            if is_b
            else None
        ),
        "lambda_target_group_arn": (
            f"arn:aws:elasticloadbalancing:{region}:{account}:targetgroup/clip-lambda/5555555555555555"
            if is_b
            else None
        ),
        "database_instance_id": "clip-shared-test-postgres",
        "database_name": "clip_test",
        "database_parameter_arn": f"arn:aws:ssm:{region}:{account}:parameter/clip/test/database-url",
    }
    return {
        "format_version": 1,
        "purpose": "clip-read-experiment-target",
        "run_id": "cw-run-001",
        "configuration": configuration,
        "aws_profile": "surajs2",
        "account_id": account,
        "region": region,
        "expected_caller_arn": f"arn:aws:iam::{account}:user/surajs2",
        "expected_user_id": "12345678-1234-4234-8234-123456789abc",
        "api_origin": "https://clip-iisc.site",
        "resources": resources,
        "routing": {
            "lambda_weight_percent": 50 if is_b else 0,
            "methods": ["GET"],
            "path_regexes": ["^/api/listings$", "^/api/listings/[0-9A-Fa-f-]{36}$"],
            "stickiness_enabled": False,
        },
        "revisions": {
            "ecs_image_uri": f"{account}.dkr.ecr.{region}.amazonaws.com/clip@sha256:{digest}",
            "lambda_image_uri": (
                f"{account}.dkr.ecr.{region}.amazonaws.com/lambda@sha256:{digest}"
                if is_b
                else None
            ),
            "application_revision": "1" * 40,
            "dataset_fingerprint": f"sha256:{digest}",
            "model_revision": "2" * 40,
        },
        "evidence_path": "docs/evaluation/experiment-runs/cw-run-001",
        "execution_permitted": False,
        "nfr_accepted": False,
    }


def _window() -> dict[str, object]:
    return {
        "format_version": 1,
        "run_id": "cw-run-001",
        "actual_start_utc": "2026-11-03T10:00:12Z",
        "actual_end_utc": "2026-11-03T10:02:35Z",
    }


class _FakeSts:
    def __init__(self, account: str = "335523638354") -> None:
        self.account = account

    def get_caller_identity(self) -> dict[str, str]:
        return {
            "Account": self.account,
            "Arn": f"arn:aws:iam::{self.account}:user/surajs2",
            "UserId": "AIDA-USER",
        }


class _FakeCloudWatch:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_metric_data(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        queries = kwargs["MetricDataQueries"]
        assert isinstance(queries, list)
        if len(self.calls) == 1:
            return {
                "MetricDataResults": [
                    {
                        "Id": queries[0]["Id"],
                        "Label": queries[0]["Label"],
                        "StatusCode": "Complete",
                        "Timestamps": [
                            datetime(2026, 11, 3, 10, 1, tzinfo=timezone.utc)
                        ],
                        "Values": [4.0],
                    }
                ],
                "NextToken": "next-page",
            }
        return {
            "MetricDataResults": [
                {
                    "Id": query["Id"],
                    "Label": query["Label"],
                    "StatusCode": "Complete",
                    "Timestamps": [],
                    "Values": [],
                }
                for query in queries
            ]
        }


def test_build_queries_captures_ecs_lambda_alb_and_database_metrics() -> None:
    groups = build_queries(_plan())

    assert {query["Id"] for query in groups["ecs"]} >= {
        "ecs_cpu",
        "ecs_memory",
        "alb_ecs_requests",
    }
    assert {query["Id"] for query in groups["lambda"]} >= {
        "lambda_invocations",
        "lambda_errors",
        "lambda_throttles",
        "lambda_duration_p95",
        "alb_lambda_requests",
        "alb_lambda_user_errors",
        "alb_lambda_internal_errors",
    }
    assert {query["Id"] for query in groups["postgres"]} >= {
        "rds_connections",
        "rds_cpu",
        "rds_free_memory",
    }
    assert all(
        query["MetricStat"]["Period"] == 60
        for group in groups.values()
        for query in group
    )


def test_configuration_a_records_lambda_as_not_applicable(tmp_path) -> None:
    cw = _FakeCloudWatch()
    result = capture(
        _plan("A"),
        _window(),
        _FakeSts(),
        cw,
        tmp_path / "capture",
        hashlib.sha256(b"exact target plan bytes").hexdigest(),
        now=datetime(2026, 11, 3, 10, 3, tzinfo=timezone.utc),
    )

    lambda_artifact = json.loads(
        (tmp_path / "capture/lambda-cloudwatch.json").read_text()
    )
    assert lambda_artifact["state"] == "not_applicable"
    assert lambda_artifact["not_applicable_reason"] == "configuration_a_ecs_only"
    assert result["measurement_authorized"] is False
    assert result["nfr_accepted"] is False


def test_capture_paginates_and_preserves_missing_metrics_and_exact_hash(
    tmp_path,
) -> None:
    cw = _FakeCloudWatch()
    exact_hash = hashlib.sha256(b"exact target plan bytes").hexdigest()
    result = capture(
        _plan(),
        _window(),
        _FakeSts(),
        cw,
        tmp_path / "capture",
        exact_hash,
        now=datetime(2026, 11, 3, 10, 3, tzinfo=timezone.utc),
    )

    assert len(cw.calls) == 4  # first component paginates; others complete directly
    assert cw.calls[1]["NextToken"] == "next-page"
    assert cw.calls[0]["StartTime"] == datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    assert cw.calls[0]["EndTime"] == datetime(2026, 11, 3, 10, 3, tzinfo=timezone.utc)
    ecs = json.loads((tmp_path / "capture/ecs-cloudwatch.json").read_text())
    assert ecs["target_plan_sha256"] == exact_hash
    assert ecs["series"][0]["values"] == [4.0]
    assert any(item["status_code"] == "NoData" for item in ecs["series"])
    assert (
        result["artifacts"]["ecs"]["sha256"]
        == hashlib.sha256(
            (tmp_path / "capture/ecs-cloudwatch.json").read_bytes()
        ).hexdigest()
    )


def test_wrong_caller_fails_before_cloudwatch_or_output(tmp_path) -> None:
    cw = _FakeCloudWatch()
    with pytest.raises(ValueError, match="aws_caller_target_mismatch"):
        capture(
            _plan(),
            _window(),
            _FakeSts("484394572488"),
            cw,
            tmp_path / "capture",
            "a" * 64,
        )

    assert cw.calls == []
    assert not (tmp_path / "capture").exists()


def test_bad_run_windows_rejected_before_provider_calls() -> None:
    with pytest.raises(ValueError, match="run_window_target_mismatch"):
        validate_window({**_window(), "run_id": "different-run"}, _plan())
    with pytest.raises(ValueError, match="run_window_out_of_bounds"):
        validate_window(
            {
                **_window(),
                "actual_end_utc": "2026-11-03T18:00:13Z",
            },
            _plan(),
        )


def test_existing_output_is_never_overwritten(tmp_path) -> None:
    output = tmp_path / "capture"
    output.mkdir()
    with pytest.raises(ValueError, match="output_directory_must_be_new"):
        capture(
            _plan(),
            _window(),
            _FakeSts(),
            _FakeCloudWatch(),
            output,
            "a" * 64,
        )
