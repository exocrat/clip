"""Run-only policy boundaries; no real credentials, browser or AWS operations."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_workflow_local as subject


def test_wrong_identity_stops_before_bucket_access():
    calls = []

    def client(service, **kwargs):
        calls.append(service)
        return SimpleNamespace(
            get_caller_identity=lambda: {"Account": "wrong"}, close=lambda: None
        )

    with pytest.raises(ValueError, match="wrong_project_identity"):
        subject.live_preflight(SimpleNamespace(client=client))
    assert calls == ["sts", "s3"]  # Clients constructed; only STS operation invoked.


@pytest.mark.parametrize(
    "path,method",
    [
        ("/auth/temporary/registration-challenges", "POST"),
        ("/conversations", "POST"),
        ("/listings/synthetic", "DELETE"),
    ],
)
def test_unselected_mutations_do_not_reach_application(path, method):
    async def app(*args):
        raise AssertionError("Unselected operation reached application")

    messages = []

    async def send(value):
        messages.append(value)

    scope = {"type": "http", "path": path, "method": method, "client": ("127.0.0.1", 1)}
    asyncio.run(subject.WorkflowBoundary(app, {"http_counts": {}})(scope, None, send))
    assert messages[0]["status"] == 403


def test_one_create_attempt_even_if_application_fails():
    received = []

    async def app(scope, receive, send):
        received.append(1)
        await send({"type": "http.response.start", "status": 503})
        await send({"type": "http.response.body", "body": b""})

    async def send(value):
        pass

    policy = subject.WorkflowBoundary(app, {"http_counts": {}})
    scope = {
        "type": "http",
        "path": "/listings",
        "method": "POST",
        "client": ("127.0.0.1", 1),
    }
    asyncio.run(policy(scope, None, send))
    asyncio.run(policy(scope, None, send))
    assert received == [1]


def test_live_mode_needs_explicit_flag_and_bounded_duration(monkeypatch):
    def forbidden(*args):
        raise AssertionError("Constructed SDK before guard")

    monkeypatch.setattr(subject, "sdk_session", forbidden)
    with pytest.raises(SystemExit):
        subject.main([])
    with pytest.raises(SystemExit):
        subject.main(["--approved-live-local", "--seconds", "3600"])


def test_storage_session_restored_and_scope_enforced():
    import boto3

    original = boto3.DEFAULT_SESSION
    callbacks = {}
    events = SimpleNamespace(
        register=lambda name, callback: callbacks.update({name: callback}),
        unregister=lambda name, callback: callbacks.pop(name),
    )
    sdk = SimpleNamespace(
        events=events,
        _session=SimpleNamespace(set_default_client_config=lambda config: None),
    )
    report = {}
    prefix = "id01/next06-step3-test"
    with subject.bounded_storage_session(sdk, prefix, report):
        assert boto3.DEFAULT_SESSION is sdk
        guard = callbacks["before-parameter-build.s3"]
        for key in ("a",):
            guard(
                {
                    "Bucket": subject.BUCKET,
                    "Key": prefix + "/" + key,
                    "IfNoneMatch": "*",
                },
                SimpleNamespace(name="PutObject"),
            )
        with pytest.raises(ValueError, match="upload_limit"):
            guard(
                {"Bucket": subject.BUCKET, "Key": prefix + "/c", "IfNoneMatch": "*"},
                SimpleNamespace(name="PutObject"),
            )
        for params, operation in (
            (
                {"Bucket": subject.BUCKET, "Key": "id01/next06-reference-42-v1/a"},
                "GetObject",
            ),
            ({"Bucket": subject.BUCKET, "Key": prefix + "/a"}, "DeleteObject"),
            ({"Bucket": "another-bucket", "Key": prefix + "/a"}, "GetObject"),
        ):
            with pytest.raises(ValueError, match="scope_or_budget"):
                guard(params, SimpleNamespace(name=operation))
    assert boto3.DEFAULT_SESSION is original
    assert callbacks == {}


@pytest.mark.parametrize("status", [200, 503])
def test_only_successful_hybrid_query_records_current_source_witness(status):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": status})
        await send({"type": "http.response.body", "body": b""})

    async def send(value):
        pass

    report = {"http_counts": {}}
    policy = subject.WorkflowBoundary(
        app, report, lambda: {"sources": [{"sha256": "synthetic"}]}
    )
    asyncio.run(
        policy(
            {
                "type": "http",
                "path": "/listings",
                "method": "GET",
                "client": ("127.0.0.1", 1),
                "query_string": b"q=controlled&search_mode=hybrid",
            },
            None,
            send,
        )
    )
    assert bool(report.get("source_observations")) is (status == 200)
    assert "controlled" not in str(report)


def test_unapproved_live_review_never_constructs_sdk(monkeypatch, tmp_path):
    directory = tmp_path / "docs/evaluation/domain/next-06/transfer"
    directory.mkdir(parents=True)
    (directory / "step-03-workflow-live-review.json").write_text(
        json.dumps({"approved": False, "files": []})
    )
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")

    calls = []

    def forbidden(*args):
        calls.append("sdk")
        raise AssertionError("SDK must not be constructed before review approval")

    monkeypatch.setattr(subject, "sdk_session", forbidden)
    assert subject.main(["--approved-live-local", "--seconds", "60"]) == 2
    assert calls == []


def test_reviewed_duration_bound_precedes_native_or_sdk(monkeypatch, tmp_path):
    directory = tmp_path / "docs/evaluation/domain/next-06/transfer"
    directory.mkdir(parents=True)
    (directory / "step-03-workflow-live-review.json").write_text(
        json.dumps(
            {"approved": True, "consumed": False, "max_live_seconds": 60, "files": []}
        )
    )
    monkeypatch.setattr(subject, "ROOT", tmp_path)

    calls = []

    def forbidden(*args):
        calls.append("native_or_sdk")
        raise AssertionError("Native/SDK work started before duration guard")

    monkeypatch.setattr(subject, "require_local", forbidden)
    monkeypatch.setattr(subject, "sdk_session", forbidden)
    assert subject.main(["--approved-live-local", "--seconds", "300"]) == 2
    assert calls == []
