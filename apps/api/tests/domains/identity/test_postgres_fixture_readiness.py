"""Deterministic bootstrap/TCP race and diagnostic privacy checks; no Docker target.

Real PostgreSQL/Docker migration acceptance still requires the hosted fixture run.
These tests assert migrations wait for TCP, failed probes are bounded, isolation
is retained and diagnostics never reflect secrets from subprocess output.
"""

import json
import subprocess
from types import SimpleNamespace

import pytest

from apps.api.tests.domains.identity import postgres_fixtures as fixture


@pytest.mark.parametrize(
    "output,category",
    [
        ("connection refused", "connection-refused"),
        ("password authentication failed", "authentication"),
        ("Permission denied", "permission"),
        ("Could not resolve host", "name-resolution"),
        ("manifest unknown", "image-unavailable"),
        ("private unknown exception", "command-failed"),
    ],
)
def test_diagnostic_categories_never_include_private_output(output, category):
    """Only fixed categories survive, including when provider text embeds a URL."""
    assert (
        fixture.failure_category(output + " postgres://user:private@host/db")
        == category
    )


def scripted_runtime(monkeypatch, *, fail_migration=False):
    """Simulate Docker's early socket-ready phase followed by final TCP readiness."""
    calls = []
    probes = []
    secret = "synthetic-fixture-only-password"
    monkeypatch.setattr(fixture.secrets, "token_hex", lambda _: secret)
    monkeypatch.setattr(fixture.time, "sleep", lambda _: None)

    def run(args, **kwargs):
        calls.append((args, kwargs))
        result = SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[-2:] == ["context", "show"]:
            result.stdout = "default"
        elif "inspect" in args:
            result.stdout = json.dumps(
                [{"Endpoints": {"docker": {"Host": "unix:///var/run/docker.sock"}}}]
            )
        elif "--detach" in args:
            result.stdout = "owned-container"
        elif "exec" in args:
            probes.append(args)
            assert kwargs["env"]["PGPASSWORD"] == secret
            assert secret not in repr(args)
            assert args[args.index("-h") + 1] == "127.0.0.1"
            assert kwargs["timeout"] <= 5
            if len(probes) == 1:
                # Unix bootstrap could already serve SQL here; TCP cannot yet.
                result.returncode = 1
                result.stderr = "connection refused " + secret
            else:
                result.stdout = "180006\n"
        elif "--rm" in args:
            assert (
                len(probes) == 2
            ), "migrations must not race the bootstrap-only server"
            assert "container:owned-container" in args
            assert "--read-only" in args and "--cap-drop" in args
            assert secret not in repr(args)
            if fail_migration:
                result.returncode = 1
                result.stderr = (
                    "password authentication failed postgres://user:"
                    + secret
                    + "@host/db"
                )
        elif "rm" in args:
            assert args[-1] == "owned-container"
        return result

    monkeypatch.setattr(fixture.subprocess, "run", run)
    return calls, probes, secret


def test_early_unix_readiness_does_not_start_migrations(tmp_path, monkeypatch):
    """Exercise the real fixture control flow across refusal/success and cleanup."""
    calls, probes, _ = scripted_runtime(monkeypatch)
    with fixture.disposable_identity_database(tmp_path) as connect:
        assert callable(connect)
        assert len(probes) == 2
    assert sum("rm" in args and "--force" in args for args, _ in calls) == 1
    start = next(args for args, _ in calls if "--detach" in args)
    assert start[start.index("--network") + 1] == "none"
    assert "--publish" not in start and "-p" not in start


def test_migration_failure_is_safe_and_owned_container_is_removed(
    tmp_path, monkeypatch
):
    """The migration stage/category is useful without revealing a password or URL."""
    calls, _, secret = scripted_runtime(monkeypatch, fail_migration=True)
    with pytest.raises(RuntimeError) as error:
        with fixture.disposable_identity_database(tmp_path):
            pytest.fail("failed migrations must not yield a database")
    message = str(error.value)
    assert "migration failed" in message and "category=authentication" in message
    assert secret not in message and "postgres://" not in message
    assert sum("rm" in args and "--force" in args for args, _ in calls) == 1


def test_tcp_probe_has_deadline_and_never_calls_migrations(monkeypatch):
    """A permanently unavailable TCP endpoint cannot hang or become synthetic success."""
    clock = iter([0, 0, 31, 31])
    monkeypatch.setattr(fixture.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(fixture.time, "sleep", lambda _: None)
    calls = []

    def refused(*args, **kwargs):
        calls.append((args, kwargs))
        raise RuntimeError("controlled refusal")

    with pytest.raises(RuntimeError, match="TCP readiness failed"):
        fixture.wait_for_migration_tcp(
            refused, ["docker"], "owned-container", "synthetic-only"
        )
    assert len(calls) == 1


def test_wrong_postgres_version_is_not_accepted():
    """A different server is a failure, not a successful readiness probe."""
    with pytest.raises(RuntimeError, match="version mismatch"):
        fixture.wait_for_migration_tcp(
            lambda *a, **kw: "170000", ["docker"], "owned", "synthetic-only"
        )


def test_command_timeout_has_safe_diagnostics_and_cleanup(tmp_path, monkeypatch):
    """A migration timeout remains a failure and removes only the owned container."""
    calls, _, secret = scripted_runtime(monkeypatch)
    original = fixture.subprocess.run

    def timeout(args, **kwargs):
        if "--rm" in args:
            raise subprocess.TimeoutExpired(args, 90, output=secret, stderr=secret)
        return original(args, **kwargs)

    monkeypatch.setattr(fixture.subprocess, "run", timeout)
    with pytest.raises(RuntimeError, match="migration timed out") as error:
        with fixture.disposable_identity_database(tmp_path):
            pytest.fail("timeout must not yield a database")
    assert secret not in str(error.value)
    assert sum("rm" in args and "--force" in args for args, _ in calls) == 1
