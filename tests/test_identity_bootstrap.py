"""Destructive rehearsals ONLY in the fixture-owned local TLS PostgreSQL server."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from apps.api.tests.domains.identity.migration_fixtures import (
    migration_case,
    reviewed_migration_directory,
    tls_database,
)
from app.domains.identity.database_setup import LOGGING
from scripts import identity_bootstrap as boot

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT / "docs/evaluation/identity/id-01-step-12/shared-migration-manifest.json"
)


@dataclass
class Case:
    database: object
    connect: object
    plan: dict
    passwords: dict
    migration_directory: Path

    def run(self):
        return boot.bootstrap(
            self.connect,
            self.database.password,
            self.database.target,
            plan=self.plan,
            directory=self.migration_directory,
            manifest=MANIFEST,
            ca=self.database.ca,
            image=self.database.image,
        )


@pytest.fixture
def case(migration_case, reviewed_migration_directory):
    """Build old17 baseline and real retained logins in this disposable server."""

    def connect():
        c = migration_case.connect()
        for name, value in LOGGING.items():
            c.execute(
                sql.SQL("SET {} = {}").format(sql.Identifier(name), sql.Literal(value))
            )
        return c

    passwords = {role: secrets.token_hex(32) for role in boot.proposed_grants()}
    try:
        with connect() as c:
            c.execute(
                "CREATE TABLE public.schema_migrations(version varchar(128) PRIMARY KEY)"
            )
            for record in json.loads(MANIFEST.read_text())["migrations"][:17]:
                original = (ROOT / record["path"]).read_text()
                with c.transaction():
                    c.execute(original.split("-- migrate:down")[0], prepare=False)
                    c.execute(
                        "INSERT INTO public.schema_migrations(version) VALUES(%s)",
                        (record["version"],),
                    )
            for role, password in passwords.items():
                c.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD {}"
                    ).format(sql.Identifier(role), sql.Literal(password))
                )
                for name, value in LOGGING.items():
                    c.execute(
                        sql.SQL("ALTER ROLE {} SET {} = {}").format(
                            sql.Identifier(role),
                            sql.Identifier(name),
                            sql.Literal(value),
                        )
                    )
            c.execute(
                "REVOKE CONNECT,TEMPORARY ON DATABASE clip_test_identity FROM PUBLIC"
            )
            for role in passwords:
                c.execute(
                    sql.SQL(
                        "GRANT CONNECT ON DATABASE clip_test_identity TO {}"
                    ).format(sql.Identifier(role))
                )
            old = boot.proposed_grants()
            for table in list(old["clip_test_marketplace_app"]):
                if table.startswith("listings.embedding_"):
                    del old["clip_test_marketplace_app"][table]
            boot._restore_grants(c, old)
            c.execute(
                "INSERT INTO identity.users(id,account_class,status) VALUES(%s,'regular','active')",
                (uuid4(),),
            )
            before = boot.snapshot(c, migration_case.target)
        plan = dict(
            discard_confirmed=True,
            isolated_rehearsal_only=True,
            grants=boot.proposed_grants(),
            inventory_sha256=hashlib.sha256(boot.INVENTORY.read_bytes()).hexdigest(),
            manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
            expected_catalogue_sha256=before["catalogue_sha256"],
            expected_counts=before["counts"],
        )
        plan["expected_versions"] = [
            row["version"]
            for row in json.loads(MANIFEST.read_text())["migrations"][:17]
        ]
        yield Case(
            migration_case, connect, plan, passwords, reviewed_migration_directory
        )
    finally:
        with connect() as c:
            for role in passwords:
                c.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role)))
                c.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))


def versions(case):
    with case.connect() as c:
        return c.execute("SELECT count(*) FROM public.schema_migrations").fetchone()[0]


def test_real17_reset23_preserves_login_and_lock(case, monkeypatch):
    original = boot.migrations.run_migrations
    inspected = []

    def observe(*args, **kwargs):
        with case.connect() as other:
            assert other.execute(
                "SELECT pg_try_advisory_lock(%s,%s)", boot.LOCK
            ).fetchone() == (False,)
        original(*args, **kwargs)
        with case.connect() as other:
            assert other.execute(
                "SELECT pg_try_advisory_lock(%s,%s)", boot.LOCK
            ).fetchone() == (False,)
        inspected.append(True)

    monkeypatch.setattr(boot.migrations, "run_migrations", observe)
    result = case.run()
    assert (
        result["migrations"] == 23
        and result["role_identity_preserved"]
        and inspected == [True]
    )
    assert versions(case) == 23
    with case.connect() as c:
        assert c.execute("SELECT count(*) FROM identity.users").fetchone() == (0,)
        assert c.execute(
            "SELECT pg_try_advisory_lock(%s,%s)", boot.LOCK
        ).fetchone() == (True,)
        c.execute("SELECT pg_advisory_unlock(%s,%s)", boot.LOCK)
    # Same pre-reset password, actual TLS login, not SET ROLE as administrator.
    for role, password in case.passwords.items():
        with psycopg.connect(
            host=case.database.target.host,
            hostaddr="127.0.0.1",
            port=case.database.target.port,
            dbname=case.database.target.database,
            user=role,
            password=password,
            sslmode="verify-full",
            sslrootcert=str(case.database.ca),
        ) as c:
            assert c.execute("SELECT current_user,session_user").fetchone() == (
                role,
                role,
            )
            assert c.execute(
                "SELECT has_database_privilege(current_database(),'CREATE'),has_database_privilege(current_database(),'TEMPORARY')"
            ).fetchone() == (False, False)


def test_drift_refused_before_reset(case):
    with case.connect() as c:
        c.execute("CREATE SCHEMA outside_review")
        c.execute("CREATE VIEW outside_review.keep AS SELECT id FROM identity.users")
    with pytest.raises(boot.BootstrapFailure) as failure:
        case.run()
    assert not failure.value.reset_committed and versions(case) == 17
    with case.connect() as c:
        assert c.execute("SELECT to_regclass('outside_review.keep')").fetchone() == (
            "outside_review.keep",
        )


def test_reset_error_rolls_back_original_schema(case, monkeypatch):
    def fail(c):
        c.execute("DROP SCHEMA identity CASCADE")
        raise RuntimeError("controlled local failure")

    monkeypatch.setattr(boot, "_drop_project", fail)
    with pytest.raises(boot.BootstrapFailure) as failure:
        case.run()
    assert failure.value.phase == "reset" and not failure.value.reset_committed
    assert versions(case) == 17
    with case.connect() as c:
        assert c.execute("SELECT count(*) FROM identity.users").fetchone() == (1,)


def test_after_reset_failure_preserves_state_without_retry(case, monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("controlled local migration failure")

    monkeypatch.setattr(boot.migrations, "run_migrations", fail)
    with pytest.raises(boot.BootstrapFailure) as failure:
        case.run()
    assert failure.value.phase == "migrate" and failure.value.reset_committed
    assert calls == [True]
    with case.connect() as c:
        assert c.execute(
            "SELECT to_regclass('public.schema_migrations')"
        ).fetchone() == (None,)
        assert c.execute(
            "SELECT count(*) FROM pg_roles WHERE rolname IN ('clip_test_identity_app','clip_test_marketplace_app')"
        ).fetchone() == (2,)


def test_busy_wrapper_lock_refused(case):
    with case.connect() as holder:
        holder.execute("SELECT pg_advisory_lock(%s,%s)", boot.LOCK)
        try:
            with pytest.raises(boot.BootstrapFailure) as failure:
                case.run()
            assert failure.value.phase == "lock" and not failure.value.reset_committed
        finally:
            holder.execute("SELECT pg_advisory_unlock(%s,%s)", boot.LOCK)
    assert versions(case) == 17


def test_column_only_grant_refused(case):
    with case.connect() as c:
        c.execute(
            "GRANT UPDATE(id) ON identity.temporary_enrollments TO clip_test_marketplace_app"
        )
    with pytest.raises(boot.BootstrapFailure) as failure:
        case.run()
    assert not failure.value.reset_committed and versions(case) == 17


def test_tracker_row_drift_refused(case):
    """Unchanged catalog/row counts do not hide modified migration versions."""
    with case.connect() as c:
        c.execute(
            "UPDATE public.schema_migrations SET version='99999999999999' WHERE version=(SELECT min(version) FROM public.schema_migrations)"
        )
    with pytest.raises(boot.BootstrapFailure) as failure:
        case.run()
    assert not failure.value.reset_committed and versions(case) == 17


def test_restricted_marketplace_listing_trigger_with_pipeline(case):
    """Exercise real invoker/deferred trigger privileges, not just ACL booleans."""
    case.run()
    owner, listing = uuid4(), uuid4()
    with case.connect() as c:
        c.execute(
            "INSERT INTO identity.users(id,account_class,status) VALUES(%s,'regular','active')",
            (owner,),
        )
        c.execute(
            "INSERT INTO listings.embedding_pipelines(pipeline_id,encoding,state) VALUES(%s,'{}','building')",
            (bytes([17]) * 32,),
        )
        category = c.execute(
            "SELECT id FROM listings.categories ORDER BY id LIMIT 1"
        ).fetchone()[0]
        condition = c.execute(
            "SELECT code FROM listings.conditions ORDER BY code LIMIT 1"
        ).fetchone()[0]
    role = "clip_test_marketplace_app"
    with psycopg.connect(
        host=case.database.target.host,
        hostaddr="127.0.0.1",
        port=case.database.target.port,
        dbname=case.database.target.database,
        user=role,
        password=case.passwords[role],
        sslmode="verify-full",
        sslrootcert=str(case.database.ca),
        autocommit=True,
    ) as c:
        with c.transaction():
            c.execute(
                "SET CONSTRAINTS listings.embedding_generation_complete IMMEDIATE"
            )
            c.execute(
                """INSERT INTO listings.sale_listings
                (id,owner_id,title,description,category_id,condition_code,
                 asking_price_paise,negotiable,pickup_area,availability)
                VALUES(%s,%s,'Synthetic review','Synthetic review',%s,%s,10000,true,'Synthetic','available')""",
                (listing, owner, category, condition),
            )
            assert c.execute(
                "SELECT count(*) FROM listings.embedding_generations WHERE listing_id=%s",
                (listing,),
            ).fetchone() == (1,)
            for statement in [
                "UPDATE listings.embedding_pipelines SET state='retired' WHERE false",
                "DELETE FROM listings.embedding_chunks WHERE false",
                "SELECT 1 FROM identity.users LIMIT 1",
                "SELECT 1 FROM conversations.threads LIMIT 1",
            ]:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with c.transaction():
                        c.execute(statement)
            # This proves embedding integration only; FR-04 image acceptance is
            # separate. Never commit a listing lacking its required image.
            raise psycopg.Rollback()


def test_live_approval_and_manifest_gates_precede_connect(case):
    """Neither fixture mode, truthy strings nor pending manifest may reach SQL."""
    calls = []

    def unexpected_connect():
        calls.append(True)
        raise RuntimeError("must not connect")

    live = boot.migrations.MigrationTarget(15432)
    base = dict(
        case.plan,
        isolated_rehearsal_only=False,
        live_ddl_approved=True,
        affected_owner_reviewed=True,
        independent_reviewed=True,
        dependency_closure_reviewed=True,
    )
    for override in [
        dict(live_ddl_approved=False),
        dict(live_ddl_approved="false"),
        dict(affected_owner_reviewed=False),
        dict(isolated_rehearsal_only=True),
        {},
    ]:
        with pytest.raises(boot.BootstrapFailure) as failure:
            boot.bootstrap(
                unexpected_connect,
                case.database.password,
                live,
                plan=base | override,
                directory=ROOT / "database/migrations",
                manifest=MANIFEST,
                ca=case.database.ca,
                image=case.database.image,
            )
        assert failure.value.phase == "package" and not failure.value.reset_committed
        assert calls == []


def test_application_login_uses_role_logging_defaults_not_admin_options(case):
    """Actual non-superuser startup rejects SET-only admin logging overrides.

    The operator must inspect inherited privacy defaults after login, as the
    application does, without trying to change restricted settings at startup.
    """
    for role, password in case.passwords.items():
        config = dict(
            host=case.database.target.host,
            hostaddr="127.0.0.1",
            port=case.database.target.port,
            dbname=case.database.target.database,
            user=role,
            password=password,
            sslmode="verify-full",
            sslrootcert=str(case.database.ca),
            connect_timeout=3,
            autocommit=True,
        )
        with pytest.raises(psycopg.OperationalError) as failure:
            psycopg.connect(**config, options="-c log_statement=none")
        assert 'permission denied to set parameter "log_statement"' in str(
            failure.value
        )
        with psycopg.connect(**config) as connection:
            assert connection.pgconn.ssl_in_use
            for name, value in LOGGING.items():
                assert connection.execute(
                    "SELECT current_setting(%s)", (name,)
                ).fetchone() == (value,)
