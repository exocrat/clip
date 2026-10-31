"""CLI-login bridge expiry, redaction and lazy-selection checks; no real credentials."""

from datetime import UTC, datetime, timedelta
import json
import subprocess
from types import SimpleNamespace

import pytest

from data.generators import reference_login as login


def response(seconds=3600):
    return {
        "Version": 1,
        "AccessKeyId": "synthetic-access-id",
        "SecretAccessKey": "synthetic-secret-value",
        "SessionToken": "synthetic-session-value",
        "Expiration": (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(),
    }


def stub_export(monkeypatch, value=None, code=0):
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(
            returncode=code,
            stdout=json.dumps(response() if value is None else value).encode(),
            stderr=b"synthetic-sensitive-stderr",
        )

    monkeypatch.setattr(login.subprocess, "run", run)
    return calls


def test_export_arguments_and_secret_transport_are_bounded(monkeypatch, capsys):
    calls = stub_export(monkeypatch)
    provider = login.CliLoginProvider("mohitmahapa1", "/approved/aws")
    credentials = provider.load().get_frozen_credentials()
    assert credentials.access_key == "synthetic-access-id"
    args, kwargs = calls[0]
    assert args == [
        "/approved/aws",
        "--profile",
        "mohitmahapa1",
        "--no-cli-pager",
        "--cli-connect-timeout",
        "5",
        "--cli-read-timeout",
        "10",
        "configure",
        "export-credentials",
        "--format",
        "process",
    ]
    assert kwargs["timeout"] == 20 and kwargs["capture_output"]
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["env"]["AWS_MAX_ATTEMPTS"] == "1"
    assert "synthetic-secret-value" not in str(args)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "kind", ["exit", "version", "token", "expired", "naive", "oversize"]
)
def test_bad_exports_are_refused_without_echoing_values(monkeypatch, kind):
    value = response()
    if kind == "version":
        value["Version"] = 9
    if kind == "token":
        value.pop("SessionToken")
    if kind == "expired":
        value = response(-60)
    if kind == "naive":
        value["Expiration"] = "2030-01-01T00:00:00"
    if kind == "oversize":
        value["padding"] = "x" * 66000
    stub_export(monkeypatch, value, code=1 if kind == "exit" else 0)
    with pytest.raises(login.CliLoginUnavailable) as caught:
        login.CliLoginProvider("project", "/approved/aws").load()
    assert str(caught.value) == "cli_login_export_unavailable"
    assert caught.value.__suppress_context__


def test_export_timeout_is_redacted(monkeypatch):
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired("aws", 20, output=b"synthetic-sensitive-output")

    monkeypatch.setattr(login.subprocess, "run", timed_out)
    with pytest.raises(
        login.CliLoginUnavailable, match="^cli_login_export_unavailable$"
    ):
        login.CliLoginProvider("project", "/approved/aws").load()


def test_short_expiry_refreshes_using_the_same_named_source(monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(response(45 if len(calls) == 1 else 3600)).encode(),
            stderr=b"",
        )

    monkeypatch.setattr(login.subprocess, "run", run)
    credentials = login.CliLoginProvider("project", "/approved/aws").load()
    credentials.get_frozen_credentials()
    assert len(calls) == 2 and calls[0] == calls[1]


@pytest.mark.parametrize("is_login", [False, True])
def test_session_selection_is_lazy_and_scoped(monkeypatch, is_login):
    registered = []
    session = SimpleNamespace(
        get_scoped_config=lambda: (
            {"login_session": "synthetic-session-arn"} if is_login else {}
        ),
        register_component=lambda name, resolver: registered.append((name, resolver)),
    )
    monkeypatch.setattr(login.botocore.session, "Session", lambda **kwargs: session)
    monkeypatch.setattr(login.boto3, "Session", lambda **kwargs: kwargs)
    monkeypatch.setattr(login.shutil, "which", lambda name: "/approved/aws")

    def forbidden(*args, **kwargs):
        pytest.fail("Session construction exported credentials")

    monkeypatch.setattr(login.subprocess, "run", forbidden)
    result = login.sdk_session("project", "ap-south-1")
    assert result["botocore_session"] is session
    assert bool(registered) is is_login
    if is_login:
        assert registered[0][0] == "credential_provider"
        assert registered[0][1].providers[0].METHOD == "clip-cli-login"


def test_login_without_cli_fails_before_export(monkeypatch):
    monkeypatch.setattr(
        login.botocore.session,
        "Session",
        lambda **kwargs: SimpleNamespace(
            get_scoped_config=lambda: {"login_session": "synthetic"}
        ),
    )
    monkeypatch.setattr(login.shutil, "which", lambda name: None)
    with pytest.raises(login.CliLoginUnavailable, match="aws_cli_required"):
        login.sdk_session("project", "ap-south-1")
