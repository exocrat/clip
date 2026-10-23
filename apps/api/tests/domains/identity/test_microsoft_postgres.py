"""Real validator/account races on a new private Unix-socket PostgreSQL only.

No host port, retained data or ambient DSN is accepted. The enclosing test-only
parent directory is private; SCRAM authenticates the mounted disposable socket.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

import psycopg
import pytest

from app.core.errors import PublicError
from app.domains.identity.microsoft_accounts import (
    MicrosoftAccountService,
    PostgresMicrosoftAccounts,
)
from apps.api.tests.domains.identity.microsoft_fixtures import NONCE, TENANT

ROOT = Path(__file__).resolve().parents[5]


@pytest.fixture(scope="module")
def disposable_database(tmp_path_factory):
    """Create one fresh database, migrate it and remove only its own container."""
    root = tmp_path_factory.mktemp("identity-postgres")
    root.chmod(0o700)
    socket = root / "socket"
    socket.mkdir()
    socket.chmod(0o777)
    password = secrets.token_hex(24)
    env = {key: os.environ[key] for key in ("HOME", "PATH")}

    def command(args, extra=None):
        p = subprocess.run(
            args, env=env | (extra or {}), capture_output=True, text=True, timeout=90
        )
        if p.returncode:
            raise RuntimeError(
                "Disposable Identity database command failed; arguments/output withheld"
            )
        return p.stdout.strip()

    context = command(["docker", "context", "show"])
    endpoint = json.loads(command(["docker", "context", "inspect", context]))[0][
        "Endpoints"
    ]["docker"]["Host"]
    assert endpoint.startswith("unix://"), "Local Docker required"
    docker = ["docker", "--context", context]
    container = None

    def connect():
        return psycopg.connect(
            host=str(socket),
            dbname="clip_test_identity",
            user="clip_identity_ci",
            password=password,
            connect_timeout=3,
            autocommit=True,
        )

    try:
        container = command(
            docker
            + [
                "run",
                "--detach",
                "--network",
                "none",
                "--stop-timeout",
                "5",
                "--tmpfs",
                "/var/lib/postgresql:rw",
                "--mount",
                f"type=bind,src={socket},dst=/run/clip-identity",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_USER=clip_identity_ci",
                "--env",
                "POSTGRES_DB=clip_test_identity",
                "--env",
                "POSTGRES_INITDB_ARGS=--auth-local=scram-sha-256 --auth-host=scram-sha-256",
                "postgres:18.6-bookworm",
                "postgres",
                "-c",
                "unix_socket_directories=/var/run/postgresql,/run/clip-identity",
                "-c",
                "unix_socket_permissions=0777",
                "-c",
                "timezone=UTC",
            ],
            {"POSTGRES_PASSWORD": password},
        )
        for attempt in range(45):
            try:
                with connect() as c:
                    assert (
                        c.execute("SHOW server_version_num").fetchone()[0] == "180006"
                    )
                break
            except psycopg.OperationalError:
                if attempt == 44:
                    raise RuntimeError(
                        "Disposable PostgreSQL readiness failed"
                    ) from None
                time.sleep(0.2)
        command(
            docker
            + [
                "run",
                "--rm",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--network",
                f"container:{container}",
                "--env",
                "DATABASE_URL",
                "--mount",
                f"type=bind,src={ROOT}/database/migrations,dst=/db/migrations,readonly",
                "ghcr.io/amacneil/dbmate:2.36.0",
                "--env-file",
                "/dev/null",
                "--migrations-dir",
                "/db/migrations",
                "--no-dump-schema",
                "migrate",
                "--strict",
            ],
            {
                "DATABASE_URL": f"postgres://clip_identity_ci:{password}@127.0.0.1:5432/clip_test_identity?sslmode=disable"
            },
        )
        yield connect
    finally:
        if container:
            command(docker + ["rm", "--force", container])


@pytest.fixture
def accounts(disposable_database):
    """Reset only Identity rows in this fixture's otherwise-unused disposable DB."""
    with disposable_database() as c:
        c.execute("DELETE FROM identity.external_identities")
        c.execute("DELETE FROM identity.users")
    return PostgresMicrosoftAccounts(disposable_database)


def counts(connect):
    with connect() as c:
        return c.execute(
            "SELECT (SELECT count(*) FROM identity.users), (SELECT count(*) FROM identity.external_identities), (SELECT count(*) FROM identity.sessions)"
        ).fetchone()


def test_concurrent_signed_callbacks_create_one_account(
    signed_tokens, accounts, disposable_database
):
    service = MicrosoftAccountService(signed_tokens.validator(), accounts)
    token = signed_tokens.token()
    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(
            workers.map(
                lambda _: service.authenticate(token, expected_nonce=NONCE), range(16)
            )
        )
    assert len({r.user_id for r in results}) == 1 and results[0].user_id.version == 4
    assert counts(disposable_database) == (1, 1, 0)


def test_subject_and_issuer_are_the_key_not_email(
    signed_tokens, accounts, disposable_database
):
    service = MicrosoftAccountService(signed_tokens.validator(), accounts)
    first = service.authenticate(signed_tokens.token(), expected_nonce=NONCE)
    again = service.authenticate(
        signed_tokens.token({"email": "another-synthetic-fixture@iisc.ac.in"}),
        expected_nonce=NONCE,
    )
    assert again.user_id == first.user_id
    second = service.authenticate(
        signed_tokens.token({"sub": "other-subject"}), expected_nonce=NONCE
    )
    other_tenant = "66666666-7777-4888-8999-000000000000"
    third = service.authenticate(
        signed_tokens.token(
            {
                "tid": other_tenant,
                "iss": "https://login.microsoftonline.com/" + other_tenant + "/v2.0",
            }
        ),
        expected_nonce=NONCE,
    )
    assert len({first.user_id, second.user_id, third.user_id}) == 3
    assert counts(disposable_database) == (3, 3, 0)


@pytest.mark.parametrize(
    "status", ["revoked", "pending", "profile_removed", "temporary"]
)
def test_existing_ineligible_mapping_never_reactivated(
    signed_tokens, accounts, disposable_database, status
):
    service = MicrosoftAccountService(signed_tokens.validator(), accounts)
    result = service.authenticate(signed_tokens.token(), expected_nonce=NONCE)
    with disposable_database() as c:
        if status == "temporary":
            # Create a legacy inconsistent class binding using valid schema rows.
            # Never disable the new immutable trigger or change original user class.
            c.execute("DELETE FROM identity.external_identities")
            c.execute("DELETE FROM identity.users")
            c.execute(
                "INSERT INTO identity.users (id, account_class, status) VALUES (%s, 'temporary', 'pending')",
                (result.user_id,),
            )
            c.execute(
                "INSERT INTO identity.external_identities (id, user_id, provider, issuer, subject) VALUES (gen_random_uuid(), %s, 'microsoft', %s, 'synthetic-subject')",
                (
                    result.user_id,
                    "https://login.microsoftonline.com/" + TENANT + "/v2.0",
                ),
            )
        elif status == "pending":
            c.execute(
                "UPDATE identity.users SET status='pending' WHERE id=%s",
                (result.user_id,),
            )
        else:
            c.execute(
                "UPDATE identity.users SET status='revoked', revoked_at=created_at WHERE id=%s",
                (result.user_id,),
            )
            if status == "profile_removed":
                c.execute(
                    "UPDATE identity.users SET profile_removed_at=created_at WHERE id=%s",
                    (result.user_id,),
                )
    with pytest.raises(PublicError) as exc:
        service.authenticate(signed_tokens.token(), expected_nonce=NONCE)
    assert exc.value.spec.status == 401 and counts(disposable_database) == (1, 1, 0)


def test_invalid_token_never_writes(signed_tokens, accounts, disposable_database):
    service = MicrosoftAccountService(signed_tokens.validator(), accounts)
    with pytest.raises(PublicError):
        service.authenticate(
            signed_tokens.token({"email": "synthetic@example.invalid"}),
            expected_nonce=NONCE,
        )
    assert counts(disposable_database) == (0, 0, 0)


def test_mapping_failure_rolls_back_user_and_redacts(
    signed_tokens, accounts, disposable_database
):
    with disposable_database() as c:
        c.execute(
            "CREATE FUNCTION identity.synthetic_abort_mapping() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'PRIVATE_DATABASE_PAYLOAD'; END; $$"
        )
        c.execute(
            "CREATE TRIGGER synthetic_abort_mapping BEFORE INSERT ON identity.external_identities FOR EACH ROW EXECUTE FUNCTION identity.synthetic_abort_mapping()"
        )
    try:
        service = MicrosoftAccountService(signed_tokens.validator(), accounts)
        with pytest.raises(PublicError) as exc:
            service.authenticate(signed_tokens.token(), expected_nonce=NONCE)
        assert exc.value.spec.status == 503 and "PRIVATE" not in str(exc.value)
        assert counts(disposable_database) == (0, 0, 0)
    finally:
        with disposable_database() as c:
            c.execute(
                "DROP TRIGGER synthetic_abort_mapping ON identity.external_identities"
            )
            c.execute("DROP FUNCTION identity.synthetic_abort_mapping()")
