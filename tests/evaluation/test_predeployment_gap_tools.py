"""Failure/accounting coverage for the three predeployment integration fixes."""

from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import pytest
from scripts.evaluation.k6.lambda_initialization import parse_event, collect
from scripts.evaluation.k6.live_parity import compare, bridge, capture
from scripts.evaluation.nfr07_restore_observer import _read_isolated_session


def test_platform_logs_preserve_initialization_without_claiming_every_other_request_warm():
    cold = parse_event(
        {
            "message": "REPORT RequestId: abc-123 Duration: 2.5 ms Billed Duration: 100 ms Init Duration: 90.1 ms",
            "timestamp": 1,
            "logStreamName": "private-stream",
        }
    )
    assert cold["initialization_observed"] and cold["init_duration_ms"] == 90.1
    assert "abc-123" not in json.dumps(cold) and "private-stream" not in json.dumps(
        cold
    )
    ordinary = parse_event(
        {
            "message": json.dumps(
                {
                    "type": "platform.report",
                    "record": {"requestId": "def-456", "metrics": {"durationMs": 3}},
                }
            ),
            "timestamp": 2,
        }
    )
    assert ordinary["initialization_observed"] is False
    assert ordinary["init_duration_ms"] is None
    assert (
        parse_event({"message": "private application content", "timestamp": 3}) is None
    )
    with pytest.raises(ValueError):
        parse_event(
            {
                "message": json.dumps(
                    {
                        "type": "platform.report",
                        "record": {
                            "requestId": "abc",
                            "metrics": {"durationMs": float("nan")},
                        },
                    }
                ),
                "timestamp": 4,
            }
        )


def test_log_pagination_retains_all_reports_and_refuses_repeating_token():
    class Logs:
        def __init__(self):
            self.calls = 0

        def filter_log_events(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {"events": [], "nextToken": "next"}
            assert kwargs["nextToken"] == "next"
            return {
                "events": [
                    {"timestamp": 10, "message": "REPORT RequestId: abc Duration: 1 ms"}
                ]
            }

    assert len(collect(Logs(), "group", 0, 20)) == 1

    class Broken:
        def filter_log_events(self, **kwargs):
            return {"events": [], "nextToken": "repeated"}

    with pytest.raises(ValueError, match="pagination"):
        collect(Broken(), "group", 0, 20)


def receipt(configuration):
    return {
        "configuration": configuration,
        "run_id": configuration + "-run",
        "smoke_passed": True,
        "corpus_sha256": "a" * 64,
        "revisions": {
            k: "same"
            for k in (
                "application_revision",
                "dataset_fingerprint",
                "model_revision",
                "ecs_image_uri",
            )
        },
        "cases": [
            {
                "case_id": f"case-{i}",
                "response_sha256": "b" * 64,
                "correct": True,
                "status": 200,
            }
            for i in range(10)
        ],
        "anonymous_status": 401,
        "hidden_status": 404,
        "hidden_listing_id_sha256": "c" * 64,
    }


def test_pair_refuses_wrong_responses_changed_corpus_and_nonpassing_captures():
    a, b = receipt("A"), receipt("B")
    assert compare(a, b)["response_parity_passed"]
    for field, value in [
        ("smoke_passed", False),
        ("corpus_sha256", "changed"),
        ("cases", []),
    ]:
        altered = deepcopy(b)
        altered[field] = value
        assert not compare(a, altered)["response_parity_passed"]
    altered = deepcopy(b)
    altered["revisions"]["dataset_fingerprint"] = "different"
    assert not compare(a, altered)["response_parity_passed"]


def test_capture_rejects_bad_approval_without_live_calls(monkeypatch):
    monkeypatch.setattr(
        "scripts.evaluation.k6.live_parity.inspect_target",
        lambda *_: pytest.fail("unexpected live call"),
    )
    manifest = {
        "format_version": 1,
        "run_id": "a-run",
        "configuration": "A",
        "target_plan_path": "unused",
        "target_plan_sha256": "a" * 64,
        "corpus_path": "unused",
        "corpus_sha256": "b" * 64,
        "hidden_listing_id": "a" * 8 + "-aaaa-4aaa-8aaa-" + "a" * 12,
    }
    with pytest.raises(ValueError, match="approval"):
        capture(manifest, {}, "c" * 64, "")


def test_isolated_session_requires_owner_only_regular_file(tmp_path):
    handoff = tmp_path / "session"
    handoff.write_text("__Host-clip_session=synthetic")
    handoff.chmod(0o644)
    with pytest.raises(ValueError, match="unsafe"):
        _read_isolated_session(str(handoff))
    handoff.chmod(0o600)
    assert _read_isolated_session(str(handoff)) == "__Host-clip_session=synthetic"
    link = tmp_path / "link"
    link.symlink_to(handoff)
    with pytest.raises(OSError):
        _read_isolated_session(str(link))


def test_bridge_rejects_incomplete_oracles_before_any_requests():
    row = {"case_id": "x", "request": {"kind": "browse", "query": {}}, "expected": None}
    cases = [{**row, "case_id": f"b{i}"} for i in range(5)]
    cases += [
        {
            "case_id": f"s{i}",
            "request": {
                "kind": "search",
                "query": {"q": "synthetic", "search_mode": "hybrid"},
            },
            "expected": None,
        }
        for i in range(3)
    ]
    cases += [
        {
            "case_id": f"d{i}",
            "request": {
                "kind": "detail",
                "listing_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            },
            "expected": None,
        }
        for i in range(2)
    ]
    with pytest.raises(ValueError, match="invalid"):
        bridge(cases)


def valid_corpus():
    listing_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    row = {
        "listing_id": listing_id,
        "title": "Synthetic bicycle",
        "description": "Synthetic item",
        "category_code": "bicycles",
        "category_label": "Bicycles",
        "condition_code": "good",
        "condition_label": "Good",
        "asking_price_paise": 10000,
        "original_price_paise": None,
        "negotiable": True,
        "pickup_area": None,
        "available_from": "2026-01-01T00:00:00Z",
        "available_until": None,
        "availability": "available",
        "sensitive_purchase": False,
        "image_ids": [listing_id],
    }
    page = {"items": [row], "page": 1, "page_size": 20, "has_next": False}
    cases = [
        {
            "case_id": f"b{i}",
            "request": {"kind": "browse", "query": {}},
            "expected": deepcopy(page),
        }
        for i in range(5)
    ]
    cases += [
        {
            "case_id": f"s{i}",
            "request": {
                "kind": "search",
                "query": {"q": "synthetic", "search_mode": "hybrid"},
            },
            "expected": None,
        }
        for i in range(3)
    ]
    cases += [
        {
            "case_id": f"d{i}",
            "request": {"kind": "detail", "listing_id": listing_id},
            "expected": {**row, "proof_available": None},
        }
        for i in range(2)
    ]
    responses = [{"status": 200, "body": deepcopy(page)} for _ in range(8)] + [
        {"status": 200, "body": deepcopy(c["expected"])} for c in cases[8:]
    ]
    return cases, responses


def test_real_contract_bridge_accepts_correct_cases_and_exposes_wrong_200():
    cases, responses = valid_corpus()
    assert len(bridge(cases)["paths"]) == 10
    assert all(c["correct"] for c in bridge(cases, responses)["cases"])
    responses[0]["body"]["items"][0]["title"] = "Incorrect but HTTP 200"
    responses[5] = {"status": 0, "body": None}
    checked = bridge(cases, responses)["cases"]
    assert checked[0]["correct"] is False and checked[5]["correct"] is False
    assert checked[1]["correct"] is True


def restore_settings(**changes):
    from app.core.config import Settings

    values = dict(
        environment="test",
        identity_provider="microsoft",
        email_provider="dual",
        identity_runtime_enabled=True,
        nfr07_restore_smoke_enabled=True,
        identity_browser_origins=("https://restore.clip-iisc.site",),
        database_url="postgresql://synthetic@localhost/fixture",
        ses_test_recipients=("synthetic@example.invalid",),
    )
    values.update(changes)
    return Settings(**values)


def test_restore_identity_profile_rejects_production_source_origin_and_writers():
    from pydantic import ValidationError

    assert restore_settings().nfr07_restore_smoke_enabled
    for changes in (
        {"environment": "production"},
        {"identity_runtime_enabled": False},
        {"identity_browser_origins": ("https://clip-iisc.site",)},
        {"notification_worker_enabled": True},
        {"hybrid_worker_enabled": True},
    ):
        with pytest.raises(ValidationError):
            restore_settings(**changes)


def test_restore_bootstrap_reads_isolated_identity_parameter(monkeypatch):
    from app.core.config import ConfigurationError
    from app.domains.identity import runtime_configuration as runtime
    from pydantic import SecretStr

    calls = []

    def read(_client, name):
        calls.append(name)
        return SecretStr("synthetic-in-memory-only")

    def stop_before_database(*_args):
        raise ValueError("offline boundary")

    monkeypatch.setattr(runtime, "read_secure_parameter", read)
    monkeypatch.setattr(runtime, "parse_authentication_keys", lambda _: object())
    monkeypatch.setattr(runtime, "connection_factory", stop_before_database)
    with pytest.raises(ConfigurationError):
        runtime.prepare_hosted_test_identity(restore_settings(), client=object())
    assert calls == [
        "/clip/test/identity/authentication-keys",
        "/clip/test/nfr07/identity-database-url",
    ]


def test_capture_executes_twelve_checks_and_retains_only_hashes(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from scripts.evaluation.k6 import live_parity as module

    cases, responses = valid_corpus()
    target = {
        "run_id": "a-run",
        "configuration": "A",
        "api_origin": "https://example.invalid",
        "revisions": receipt("A")["revisions"],
    }
    monkeypatch.setattr(module, "validate_plan", lambda p: p)
    monkeypatch.setattr(
        module,
        "read_bound",
        lambda path, _digest: target if path == "target" else {"cases": cases},
    )
    monkeypatch.setattr(module, "inspect_target", lambda _target: None)
    monkeypatch.setattr(module, "check_session_identity", lambda _target, _cookie: None)
    queue = iter(
        responses + [{"status": 401, "body": None}, {"status": 404, "body": None}]
    )
    calls = []

    def fetch(_origin, path, cookie):
        calls.append((path, cookie))
        return next(queue)

    monkeypatch.setattr(module, "fetch", fetch)
    manifest = {
        "format_version": 1,
        "run_id": "a-run",
        "configuration": "A",
        "target_plan_path": "target",
        "target_plan_sha256": "a" * 64,
        "corpus_path": "corpus",
        "corpus_sha256": "b" * 64,
        "hidden_listing_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    }
    now = datetime.now(timezone.utc)
    approval = {
        "action": "capture_live_parity",
        "manifest_sha256": "c" * 64,
        "authorized_at": (now - timedelta(seconds=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=1)).isoformat(),
        "review_record": "synthetic offline review",
    }
    result = module.capture(manifest, approval, "c" * 64, "synthetic-session")
    assert result["smoke_passed"] and len(calls) == 12
    assert calls[10][1] is None and len(result["request_timings_ms"]) == 10
    assert "Synthetic bicycle" not in json.dumps(result)
    assert "synthetic-session" not in json.dumps(result)


def test_every_smoke_domain_must_use_restored_endpoint_and_verified_tls():
    from scripts.evaluation.nfr07_restore_observer import _verify_restored_parameters

    smoke = {
        key: key
        for key in (
            "database_parameter_arn",
            "identity_database_parameter_arn",
            "conversations_database_parameter_arn",
        )
    }
    smoke.update(
        identity_database_name="identity", conversations_database_name="conversations"
    )
    names = {
        "database_parameter_arn": "listings",
        "identity_database_parameter_arn": "identity",
        "conversations_database_parameter_arn": "conversations",
    }
    values = {
        key: f"postgresql://synthetic@restored.internal:5432/{name}?sslmode=verify-full"
        for key, name in names.items()
    }

    class SSM:
        def get_parameter(self, Name, WithDecryption):
            return {"Parameter": {"ARN": Name, "Value": values[Name]}}

    instance = {"Endpoint": {"Address": "restored.internal", "Port": 5432}}
    _verify_restored_parameters(SSM(), smoke, instance, "listings")
    values["identity_database_parameter_arn"] = values[
        "identity_database_parameter_arn"
    ].replace("restored.internal", "source.internal")
    with pytest.raises(ValueError, match="target_mismatch"):
        _verify_restored_parameters(SSM(), smoke, instance, "listings")


def test_restore_session_preflight_requires_ecs_only_source_before_network(monkeypatch):
    from scripts.evaluation import nfr07_restore_observer as observer
    from scripts.evaluation.k6 import live_parity, real_target_preflight as target

    source = {
        "configuration": "A",
        "account_id": "335523638354",
        "region": "ap-south-1",
        "resources": {"database_instance_id": "source-db"},
        "expected_user_id": "synthetic-user",
        "revisions": {"application_revision": "a" * 40, "ecs_image_uri": "image"},
    }
    smoke = {
        "expected_user_id": "synthetic-user",
        "application_revision": "a" * 40,
        "container_image": "image",
    }
    plan = {
        "source_target_plan_path": "source",
        "target_manifest_sha256": "a" * 64,
        "application_smoke_plan": smoke,
        "account_id": source["account_id"],
        "region": source["region"],
        "snapshot_source_instance_id": "source-db",
    }
    calls = []
    monkeypatch.setattr(live_parity, "read_bound", lambda *_: source)
    monkeypatch.setattr(target, "validate_plan", lambda value: value)
    monkeypatch.setattr(
        target, "inspect_target", lambda value: calls.append(value["configuration"])
    )
    monkeypatch.setattr(target, "check_session_identity", lambda *_: None)
    assert observer._verify_smoke_session(plan, "synthetic-cookie") == source
    source["configuration"] = "B"
    with pytest.raises(ValueError, match="source_target_mismatch"):
        observer._verify_smoke_session(plan, "synthetic-cookie")
    assert calls == ["A"]
