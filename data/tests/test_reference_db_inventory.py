"""Prepared host probe activation/privacy/cleanup guards; never remote/SQL acceptance."""

import io
import json
import sys
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_db_inventory as probe


def setup_host(monkeypatch, failure=None):
    calls = []
    label = [None]
    removed = [False]

    def run(args, **kwargs):
        calls.append((args, kwargs))
        if "--version" in args:
            data = b"aws-cli/1.2.3" if failure == "cli" else b"aws-cli/2.36.39"
        elif "get-caller-identity" in args:
            value = {
                "Account": probe.ACCOUNT,
                "Arn": f"arn:aws:sts::{probe.ACCOUNT}:assumed-role/clip-shared-test-ecs-instance/{probe.INSTANCE}",
            }
            if failure == "role":
                value["Arn"] = f"arn:aws:iam::{probe.ACCOUNT}:root"
            data = json.dumps(value).encode()
        elif "image" in args:
            if failure == "image":
                return SimpleNamespace(
                    returncode=1, stdout=b"", stderr=b"sensitive-error"
                )
            data = b"sha256:cached"
        elif "ps" in args:
            data = (
                b"present"
                if failure == "collision" or (label[0] and not removed[0])
                else b""
            )
        elif "get-parameter" in args:
            if failure == "parameter":
                return SimpleNamespace(
                    returncode=1,
                    stdout=b"",
                    stderr=b"An error occurred (AccessDeniedException) private-value",
                )
            if failure == "parameter_json":
                return SimpleNamespace(
                    returncode=0, stdout=b"private-value", stderr=b""
                )
            data = json.dumps(
                {"Parameter": {"Value": "synthetic-connection-text"}}
            ).encode()
        elif "run" in args:
            label[0] = args[args.index("--label") + 1].split("=", 1)[1]
            assert kwargs["input"] == b"synthetic-connection-text"
            assert "synthetic-connection-text" not in " ".join(args)
            assert "--pull=never" in args
            value = {
                "format_version": 2,
                "state": "readonly_metadata_passed",
                "stage": "complete",
                "metadata": metadata(),
            }
            if failure == "child":
                value = {
                    "format_version": 2,
                    "state": "refused_or_failed",
                    "stage": "connect",
                    "reason": "unexpected_error",
                    "failure_type": "OperationalError",
                    "sqlstate": "28000",
                }
                return SimpleNamespace(
                    returncode=1,
                    stdout=json.dumps(value).encode(),
                    stderr=b"sensitive-error",
                )
            data = json.dumps(value).encode()
        elif "inspect" in args:
            data = (
                "a" * 64
                + " "
                + ("someone-else" if failure == "foreign_cleanup" else label[0])
            ).encode()
        else:
            removed[0] = True
            data = b"removed"
        return SimpleNamespace(returncode=0, stdout=data, stderr=b"")

    monkeypatch.setattr(probe.shutil, "which", lambda name: "/approved/" + name)
    monkeypatch.setattr(probe.subprocess, "run", run)
    return calls


def test_inert_without_explicit_mode(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Inert probe executed a process")

    monkeypatch.setattr(probe.subprocess, "run", forbidden)
    assert probe.main([]) == 2
    assert "explicit_approval_required" in capsys.readouterr().out


def test_secret_only_in_stdin_and_owned_container_cleanup(monkeypatch, capsys):
    calls = setup_host(monkeypatch)
    assert probe.main(["--approved-readonly-inventory"]) == 0
    assert "synthetic-connection-text" not in capsys.readouterr().out
    cleanup = [args for args, _ in calls if "rm" in args]
    assert cleanup == [["/approved/docker", "rm", "--force", "a" * 64]]
    for args, kwargs in calls:
        assert "AWS_ACCESS_KEY_ID" not in kwargs["env"]
        assert kwargs["env"]["AWS_SHARED_CREDENTIALS_FILE"] == "/dev/null"


@pytest.mark.parametrize("failure", ["cli", "role", "image", "collision"])
def test_identity_cache_collision_fail_before_secret_read(monkeypatch, failure, capsys):
    calls = setup_host(monkeypatch, failure)
    assert probe.main(["--approved-readonly-inventory"]) == 1
    assert not any("get-parameter" in args for args, _ in calls)
    assert "sensitive-error" not in capsys.readouterr().out


def test_foreign_container_is_never_removed(monkeypatch, capsys):
    calls = setup_host(monkeypatch, "foreign_cleanup")
    assert probe.main(["--approved-readonly-inventory"]) == 1
    assert json.loads(capsys.readouterr().out)["cleanup"] == "foreign_refused"
    assert not any("rm" in args for args, _ in calls)


def test_actual_child_receives_input_only_through_pipe():
    """Exercise subprocess stdin wiring with synthetic bytes, no tools/network/SQL."""
    output = probe.run(
        [sys.executable, "-c", "import sys; print(len(sys.stdin.buffer.read()))"],
        env={},
        timeout=5,
        content=b"synthetic-pipe-value",
    )
    assert output == b"20\n"


@pytest.mark.parametrize(
    "changes",
    [
        {"host": "other.invalid"},
        {"sslmode": "disable"},
        {"user": "postgres"},
        {"options": "unsafe"},
    ],
)
def test_sql_child_refuses_unbound_secret_before_connect(monkeypatch, capsys, changes):
    import psycopg
    from psycopg.conninfo import make_conninfo

    fields = dict(
        host=probe.HOST,
        port=5432,
        user="clip_runtime",
        dbname="clip_app",
        sslmode="verify-full",
        sslrootcert="system",
    )
    fields.update(changes)
    monkeypatch.setattr(
        sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(make_conninfo(**fields).encode())),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe DSN reached SQL")

    monkeypatch.setattr(psycopg, "connect", forbidden)
    with pytest.raises(SystemExit) as caught:
        exec(compile(probe.SQL_PROBE, "approved_sql_probe", "exec"), {})
    assert caught.value.code == 1
    assert json.loads(capsys.readouterr().out)["state"] == "refused_or_failed"


@pytest.mark.parametrize("privilege", ["createdb", "rds_superuser"])
def test_sql_child_keeps_readonly_and_refuses_privileged_runtime(
    monkeypatch, capsys, privilege
):
    """Negative scripted metadata only; never emulate accepted database inventory."""
    import psycopg
    from psycopg.conninfo import make_conninfo

    secret = make_conninfo(
        host=probe.HOST,
        port=5432,
        user="clip_runtime",
        dbname="clip_app",
        sslmode="verify-full",
        sslrootcert="system",
    )
    monkeypatch.setattr(
        sys, "stdin", SimpleNamespace(buffer=io.BytesIO(secret.encode()))
    )
    statements = []

    def execute(sql):
        statements.append(sql)
        if sql == "SET TRANSACTION READ ONLY":
            return None
        if "current_database()" in sql:
            return SimpleNamespace(
                fetchone=lambda: (
                    "clip_app",
                    "clip_runtime",
                    "clip_runtime",
                    "180006",
                    "on",
                )
            )
        if "rolsuper,rolcreatedb" in sql:
            return SimpleNamespace(
                fetchall=lambda: [
                    ("clip_runtime", False, privilege == "createdb", False)
                ]
            )
        if "pg_has_role" in sql:
            return SimpleNamespace(fetchone=lambda: (123,))
        pytest.fail("Privileged role reached further database inspection")

    c = SimpleNamespace(
        execute=execute,
        transaction=lambda: nullcontext(),
        pgconn=SimpleNamespace(ssl_in_use=True),
    )

    def connect(*args, **kwargs):
        assert "default_transaction_read_only=on" in kwargs["options"]
        return nullcontext(c)

    monkeypatch.setattr(psycopg, "connect", connect)
    with pytest.raises(SystemExit):
        exec(compile(probe.SQL_PROBE, "approved_sql_probe", "exec"), {})
    assert statements[0] == "SET TRANSACTION READ ONLY"
    assert json.loads(capsys.readouterr().out)["state"] == "refused_or_failed"


def metadata():
    return {
        "identity": ["clip_app", "clip_runtime", "clip_runtime", "180006", "on"],
        "roles": [["clip_runtime", False, False, False]],
        "migration_versions": ["20261001"],
        "schemas": ["identity", "listings"],
        "proposed_database_already_exists": False,
    }


def test_child_failure_is_retained_without_raw_errors(monkeypatch, capsys):
    setup_host(monkeypatch, "child")
    assert probe.main(["--approved-readonly-inventory"]) == 1
    raw = capsys.readouterr().out
    value = probe.validate_host_report(raw)
    assert (value["stage"], value["child_stage"], value["sqlstate"]) == (
        "sql_child",
        "connect",
        "28000",
    )
    assert "sensitive-error" not in raw
    assert "synthetic-connection-text" not in raw


@pytest.mark.parametrize(
    "extra",
    [
        {"secret": "private"},
        {"stage": []},
        {"failure_type": "private"},
        {"sqlstate": "private"},
    ],
)
def test_untrusted_child_failure_rejected(extra):
    value = {
        "format_version": 2,
        "state": "refused_or_failed",
        "stage": "connect",
        "reason": "unexpected_error",
        "failure_type": "OperationalError",
        "sqlstate": "28000",
    }
    value.update(extra)
    with pytest.raises(probe.ProbeError):
        probe.validate_child_report(json.dumps(value), 1)


@pytest.mark.parametrize(
    "stopped,status,expected",
    [
        (True, "Failed", "probe_failed_resources_stopped"),
        (False, "Failed", "cleanup_pending_operator_attention"),
        (True, "Success", "phase_a_passed_and_stopped"),
    ],
)
def test_window_outcome_uses_verified_stops(stopped, status, expected):
    report = {
        "resource_start_attempts": {"rds": True, "ec2": True},
        "cleanup": {"rds_stopped": stopped, "host_stopped": True},
        "remote_status": {"status": status},
        "probe_report": {"state": "readonly_metadata_passed"},
    }
    assert probe.window_outcome(report) == expected


def test_process_timeout_does_not_print_error(monkeypatch):
    def timeout(*args, **kwargs):
        raise probe.subprocess.TimeoutExpired(
            "private", 1, output=b"private", stderr=b"private"
        )

    monkeypatch.setattr(probe.subprocess, "run", timeout)
    with pytest.raises(probe.ProbeError) as caught:
        probe.run(["aws"], env={}, timeout=1)
    assert caught.value.reason == "command_timeout"
    assert "private" not in str(caught.value)


def test_host_source_supports_existing_python39_syntax():
    import ast
    from pathlib import Path

    ast.parse(Path(probe.__file__).read_text(), feature_version=(3, 9))


@pytest.mark.parametrize(
    "failure,reason,provider",
    [
        ("parameter", "command_failed", "AccessDeniedException"),
        ("parameter_json", "invalid_json", None),
    ],
)
def test_parameter_failures_are_safe_and_classified(
    monkeypatch, capsys, failure, reason, provider
):
    calls = setup_host(monkeypatch, failure)
    assert probe.main(["--approved-readonly-inventory"]) == 1
    raw = capsys.readouterr().out
    value = probe.validate_host_report(raw)
    assert (value["stage"], value["reason"], value["provider_error"]) == (
        "connection_secret",
        reason,
        provider,
    )
    assert "private-value" not in raw
    assert not any("run" in args for args, _ in calls)
