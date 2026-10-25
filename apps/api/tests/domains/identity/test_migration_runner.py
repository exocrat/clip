"""Real dbmate/TLS transport and rollback probes on explicitly owned local SQL."""

import json
from pathlib import Path
import shutil
import subprocess
import time

from psycopg import sql
from pydantic import SecretStr
import pytest

from app.core.config import ConfigurationError
from app.domains.identity import migration_runner as runner
from apps.api.tests.domains.identity.migration_fixtures import (
    migration_case,
    tls_database,
)

ROOT = Path(__file__).resolve().parents[5]
MANIFEST = (
    ROOT / "docs/evaluation/identity/id-01-step-12/shared-migration-manifest.json"
)
DIRECTORY = ROOT / "database/migrations"


def migrate(case, **overrides):
    args = dict(directory=DIRECTORY, manifest=MANIFEST, ca=case.ca, image=case.image)
    args.update(overrides)
    runner.run_migrations(case.connect, case.password, case.target, **args)


def test_real_clean_repeat_and_private_docker_config(migration_case, monkeypatch):
    original = subprocess.run
    inspected = []

    def observed(args, **kwargs):
        if args[0] == "docker" and "run" in args and "--interactive" in args:
            password = migration_case.password.get_secret_value()
            assert password not in json.dumps(args)
            assert password not in json.dumps(kwargs["env"])
            assert "PGPASSWORD" not in kwargs["env"]
            name = args[args.index("--name") + 1]
            with subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=kwargs["env"],
            ) as process:
                for _ in range(100):
                    check = original(
                        migration_case.docker + ["inspect", name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if check.returncode == 0:
                        break
                    time.sleep(0.05)
                assert check.returncode == 0
                config = json.loads(check.stdout)[0]["Config"]
                assert password not in json.dumps(config)
                assert not any(
                    value.startswith("PGPASSWORD=") for value in config["Env"]
                )
                inspected.append(True)
                stdout, stderr = process.communicate(
                    kwargs["input"], timeout=kwargs["timeout"]
                )
                if process.returncode:
                    pytest.fail(
                        "Synthetic dbmate error: "
                        + stderr.replace(password, "REDACTED")
                    )
                return subprocess.CompletedProcess(
                    args, process.returncode, stdout, stderr
                )
        return original(args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", observed)
    migrate(migration_case)
    migrate(migration_case)
    assert len(inspected) == 2
    with migration_case.connect() as c:
        assert c.execute(
            "SELECT count(*) FROM public.schema_migrations"
        ).fetchone() == (17,)
        assert c.execute("SELECT count(*) FROM identity.users").fetchone() == (0,)
        assert c.execute("SELECT count(*) FROM listings.categories").fetchone() == (8,)


@pytest.mark.parametrize("tls_database", ["wrong-hostname.invalid"], indirect=True)
def test_real_hostname_mismatch_rejected(migration_case):
    # Python's inspection connection verifies the fixture certificate's actual
    # hostname; the migration container verifies the required different hostname.
    with pytest.raises(ConfigurationError, match="Identity migration run failed"):
        migrate(migration_case)
    with migration_case.connect() as c:
        assert c.execute(
            "SELECT to_regclass('public.schema_migrations')"
        ).fetchone() == (None,)


@pytest.mark.parametrize("state", ["manual-schema", "partial-tracker"])
def test_no_namespace_adoption_or_prefix_replay(migration_case, state):
    with migration_case.connect() as c:
        if state == "manual-schema":
            c.execute("CREATE SCHEMA identity")
        else:
            c.execute(
                "CREATE TABLE public.schema_migrations(version varchar(255) PRIMARY KEY)"
            )
            c.execute("INSERT INTO public.schema_migrations VALUES ('20261018094330')")
    with pytest.raises(ConfigurationError):
        migrate(migration_case)
    with migration_case.connect() as c:
        if state == "manual-schema":
            assert c.execute(
                "SELECT to_regnamespace('identity') IS NOT NULL"
            ).fetchone() == (True,)
        else:
            assert c.execute(
                "SELECT count(*) FROM public.schema_migrations"
            ).fetchone() == (1,)


@pytest.mark.parametrize(
    "change", ["edit", "extra", "mutable-image", "live-unreviewed"]
)
def test_manifest_image_and_live_review_guards(migration_case, tmp_path, change):
    directory = tmp_path / "migrations"
    shutil.copytree(DIRECTORY, directory)
    image = migration_case.image
    target = migration_case.target
    if change == "edit":
        first = sorted(directory.glob("*.sql"))[0]
        first.write_text(first.read_text() + "\n-- synthetic modification\n")
    if change == "extra":
        (directory / "20990101000000_extra.sql").write_text("-- synthetic extra")
    if change == "mutable-image":
        image = "ghcr.io/amacneil/dbmate:2.36.0"
    if change == "live-unreviewed":
        target = runner.MigrationTarget(15432)
    with pytest.raises(ValueError):
        runner.validate_manifest(directory, MANIFEST, image, target)


def test_newline_credential_rejected_before_connection(migration_case):
    def forbidden():
        raise AssertionError("Credential validation must run before SQL")

    with pytest.raises(ConfigurationError):
        runner.run_migrations(
            forbidden,
            SecretStr("synthetic\ncredential"),
            migration_case.target,
            directory=DIRECTORY,
            manifest=MANIFEST,
            ca=migration_case.ca,
            image=migration_case.image,
        )


def test_logging_probe_is_rolled_back(disposable_database):
    result = runner.probe_logging(
        disposable_database, runner.MigrationTarget(1, isolated=True)
    )
    assert result.completed and result.rollback_verified and result.failed_phase is None
    with disposable_database() as c:
        assert (
            c.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (runner.PROBE,)
            ).fetchone()
            is None
        )


def test_logging_probe_collision_is_preserved(disposable_database):
    with disposable_database() as c:
        c.execute(
            sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(runner.PROBE))
        )
    try:
        result = runner.probe_logging(
            disposable_database, runner.MigrationTarget(1, isolated=True)
        )
        assert (
            not result.completed
            and not result.rollback_verified
            and result.failed_phase == "collision"
        )
        with disposable_database() as c:
            assert c.execute(
                "SELECT rolcanlogin FROM pg_roles WHERE rolname=%s", (runner.PROBE,)
            ).fetchone() == (False,)
    finally:
        with disposable_database() as c:
            c.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(runner.PROBE)))


def test_probe_late_sql_failure_is_rolled_back(disposable_database):
    class FailingConnection:
        def __init__(self, c):
            self.c = c

        def __enter__(self):
            self.c.__enter__()
            return self

        def __exit__(self, *args):
            return self.c.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.c, name)

        def execute(self, query, params=None):
            if isinstance(query, sql.Composed) and query.as_string(self.c).startswith(
                "ALTER ROLE"
            ):
                return self.c.execute("SELECT 1/0")
            return self.c.execute(query, params)

    result = runner.probe_logging(
        lambda: FailingConnection(disposable_database()),
        runner.MigrationTarget(1, isolated=True),
    )
    assert (
        not result.completed
        and result.rollback_verified
        and result.failed_phase == "role defaults"
    )


def test_partial_real_migration_is_preserved_without_replay(migration_case):
    # The first migration creates tables; the next creates functions. Fail at
    # that real DDL boundary to prove per-file commit and prefix preservation.
    with migration_case.connect() as c:
        c.execute(
            "CREATE FUNCTION public.synthetic_ddl_failure() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic DDL failure'; END $$"
        )
        c.execute(
            "CREATE EVENT TRIGGER synthetic_fail_functions ON ddl_command_start WHEN TAG IN ('CREATE FUNCTION') EXECUTE FUNCTION public.synthetic_ddl_failure()"
        )
    with pytest.raises(ConfigurationError):
        migrate(migration_case)
    with migration_case.connect() as c:
        assert c.execute("SELECT version FROM public.schema_migrations").fetchall() == [
            ("20261018094330",)
        ]
    with pytest.raises(ConfigurationError):
        migrate(migration_case)
    with migration_case.connect() as c:
        assert c.execute("SELECT version FROM public.schema_migrations").fetchall() == [
            ("20261018094330",)
        ]


def test_zero_exit_without_schema_is_not_success(migration_case, monkeypatch):
    original = subprocess.run

    def empty_client(args, **kwargs):
        if args[0] == "docker" and "run" in args and "--interactive" in args:
            return subprocess.CompletedProcess(args, 0, "", "")
        return original(args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", empty_client)
    with pytest.raises(ConfigurationError):
        migrate(migration_case)
    with migration_case.connect() as c:
        assert c.execute(
            "SELECT to_regclass('public.schema_migrations')"
        ).fetchone() == (None,)


def test_timed_out_version_client_is_removed(migration_case, monkeypatch):
    original = subprocess.run
    owned = []

    def delayed_version(args, **kwargs):
        if args[0] == "docker" and "run" in args and "--version" in args:
            name = args[args.index("--name") + 1]
            owned.append(name)
            # Real long-running owned container; kill only its CLI by timeout.
            # The runner must then remove the container rather than leak it.
            delayed = args[:-2] + [
                "--entrypoint",
                "/bin/sh",
                args[-2],
                "-c",
                "sleep 30",
            ]
            return original(
                delayed,
                capture_output=True,
                text=True,
                env=kwargs["env"],
                timeout=1,
                check=True,
            )
        return original(args, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", delayed_version)
    with pytest.raises(ConfigurationError):
        migrate(migration_case)
    assert len(owned) == 1
    check = original(
        migration_case.docker + ["inspect", owned[0]],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert check.returncode != 0 and "No such" in check.stderr


@pytest.mark.parametrize("operation", ["migration", "probe"])
def test_actual_wrong_database_is_untouched(migration_case, operation):
    def other_database():
        return migration_case.connect("postgres")

    if operation == "migration":
        with pytest.raises(ConfigurationError):
            runner.run_migrations(
                other_database,
                migration_case.password,
                migration_case.target,
                directory=DIRECTORY,
                manifest=MANIFEST,
                ca=migration_case.ca,
                image=migration_case.image,
            )
    else:
        result = runner.probe_logging(other_database, migration_case.target)
        assert (
            not result.completed
            and not result.rollback_verified
            and result.failed_phase == "target"
        )
    with other_database() as c:
        assert c.execute(
            "SELECT to_regclass('public.schema_migrations')"
        ).fetchone() == (None,)
        assert (
            c.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (runner.PROBE,)
            ).fetchone()
            is None
        )
