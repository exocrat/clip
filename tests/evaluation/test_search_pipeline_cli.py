"""Target/execute binding guards; these tests never connect to a database."""

from unittest.mock import AsyncMock
import pytest

from app.domains.listings.embedding_types import default_pipeline_spec
from scripts import search_pipeline as cli

URL = "postgres://clip_ci@localhost:55438/clip_test_ci?host=/tmp/synthetic-socket&sslmode=disable"


def arguments(action="status", extra=()):
    return cli.parser().parse_args(
        [
            action,
            "--expected-host",
            "/tmp/synthetic-socket",
            "--expected-port",
            "55438",
            "--expected-database",
            "clip_test_ci",
            "--expected-role",
            "clip_ci",
            "--pipeline-id",
            default_pipeline_spec().pipeline_id.hex(),
            *extra,
        ]
    )


def test_read_only_status_and_explicit_mutation_binding():
    cli.validate_target(arguments(), URL)
    for action in ("prepare", "activate"):
        with pytest.raises(cli.TargetRejected):
            cli.validate_target(arguments(action), URL)
        cli.validate_target(arguments(action, ["--execute"]), URL)
    cli.validate_target(arguments("queue", ["--execute", "--batch-size", "100"]), URL)


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_host", "/tmp/other"),
        ("expected_port", 5432),
        ("expected_database", "other"),
        ("expected_role", "other"),
        ("pipeline_id", "0" * 64),
    ],
)
def test_exact_target_and_space_mismatch_refused(field, value):
    args = arguments("prepare", ["--execute"])
    setattr(args, field, value)
    with pytest.raises(cli.TargetRejected):
        cli.validate_target(args, URL)


def test_ambient_libpq_and_connection_indirection_refused(monkeypatch):
    monkeypatch.setenv("PGHOST", "synthetic-other")
    with pytest.raises(cli.TargetRejected):
        cli.validate_target(arguments(), URL)
    monkeypatch.delenv("PGHOST")
    with pytest.raises(cli.TargetRejected):
        cli.validate_target(arguments(), URL + "&options=-c%20role%3Dother")


@pytest.mark.parametrize(
    "action,extra",
    [
        ("status", ["--batch-size", "1"]),
        ("queue", ["--execute"]),
        ("queue", ["--execute", "--batch-size", "0"]),
        ("queue", ["--execute", "--batch-size", "1001"]),
    ],
)
def test_action_specific_bounds_refused(action, extra):
    with pytest.raises(cli.TargetRejected):
        cli.validate_target(arguments(action, extra), URL)


def test_operator_errors_do_not_echo_private_details(monkeypatch, capsys):
    args = arguments()
    monkeypatch.setattr(
        cli, "parser", lambda: type("Parser", (), {"parse_args": lambda self: args})()
    )
    monkeypatch.setattr(
        cli,
        "operate",
        AsyncMock(side_effect=ValueError("synthetic-private-credential")),
    )
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 2
    captured = capsys.readouterr()
    assert "synthetic-private-credential" not in captured.err + captured.out
    assert "pipeline_operation_refused" in captured.err


@pytest.mark.parametrize(
    "changed",
    [
        {"db": "other"},
        {"role": "other"},
        {"login": "other"},
        {"host": "/tmp/other"},
        {"port": 5432},
    ],
)
def test_actual_server_binding_checked_before_bootstrap(changed):
    """A matching submitted URL is insufficient if the connected identity differs."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import MagicMock, patch

    async def exercise():
        connection = MagicMock()
        connection.__aenter__.return_value = connection
        connection.info = SimpleNamespace(
            host=changed.get("host", "/tmp/synthetic-socket"),
            port=changed.get("port", 55438),
        )
        identity = {"db": "clip_test_ci", "role": "clip_ci", "login": "clip_ci"}
        identity.update(
            {key: value for key, value in changed.items() if key in identity}
        )
        connection.execute = AsyncMock(
            return_value=SimpleNamespace(fetchone=AsyncMock(return_value=identity))
        )
        with (
            patch.object(
                cli.AsyncConnection, "connect", AsyncMock(return_value=connection)
            ),
            patch.object(cli, "EmbeddingBootstrap") as bootstrap,
        ):
            with pytest.raises(cli.TargetRejected):
                await cli.operate(arguments("prepare", ["--execute"]), URL)
            bootstrap.assert_not_called()

    asyncio.run(exercise())
