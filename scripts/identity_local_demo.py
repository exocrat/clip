"""Explicit real-provider demo with an owned ephemeral local database.

Never used by app.main or images. Only two fixed Identity SecureStrings are read;
no shared database URL/master secret or cloud mutation. Real auth handlers, token
validation and mail adapters remain unchanged. Ctrl+C removes this run's SQL data.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Timer
from types import SimpleNamespace
from urllib.parse import quote, urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps/api"))

from psycopg import sql
from pydantic import SecretStr
import uvicorn

from app.application import create_app
from app.core.config import Settings
from app.domains.identity.database_setup import LOGGING, create_identity_role
from app.domains.identity.http import BrowserPolicy
from app.domains.identity.runtime_configuration import (
    RuntimeReferences,
    prepare_local_identity,
)
from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)

REFS = RuntimeReferences()


def socket_url(info, user, password):
    """Keep generated credentials in memory and use only the owned Unix socket."""
    return SecretStr(
        "postgresql:///"
        + quote(info.dbname, safe="")
        + "?"
        + urlencode(
            {
                "host": info.host,
                "port": info.port,
                "user": user,
                "password": password,
                "sslmode": "disable",
            }
        )
    )


class LocalParameters:
    """Use the local Identity URL; permit AWS reads of only two fixed references."""

    def __init__(self, client, dsn):
        self.client, self.dsn = client, dsn

    def get_parameter(self, **kwargs):
        name = kwargs.get("Name")
        if kwargs.get("WithDecryption") is not True:
            raise ValueError("Explicit decryption required")
        if name == REFS.database_url:
            return {
                "Parameter": {
                    "Name": name,
                    "Type": "SecureString",
                    "Version": 1,
                    "Value": self.dsn.get_secret_value(),
                }
            }
        if name not in (REFS.authentication_keys, REFS.email_delivery):
            raise ValueError("Unapproved parameter")
        return self.client.get_parameter(**kwargs)


@contextmanager
def demo_application(root, recipients, client):
    """Migrate fresh local SQL and create separate restricted application logins.

    Database baseline changes affect only the just-created disposable container.
    No authentication bypass, synthetic signer, mailbox endpoint or seeded account
    is installed. The marketplace pool has local Listings/Search grants only.
    """
    with disposable_identity_database(root) as admin:
        identity_password, marketplace_password = secrets.token_hex(
            32
        ), secrets.token_hex(32)
        with admin() as c:
            info = SimpleNamespace(
                dbname=c.info.dbname,
                host=c.info.host,
                port=c.info.port,
                user=c.info.user,
            )
            c.execute("REVOKE ALL ON DATABASE clip_test_identity FROM PUBLIC")
            c.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            for name, value in LOGGING.items():
                c.execute(
                    sql.SQL("SET {} = {}").format(
                        sql.Identifier(name), sql.Literal(value)
                    )
                )

        def guarded_admin():
            c = admin()
            for name, value in LOGGING.items():
                c.execute(
                    sql.SQL("SET {} = {}").format(
                        sql.Identifier(name), sql.Literal(value)
                    )
                )
            return c

        create_identity_role(
            guarded_admin,
            SecretStr(identity_password),
            expected_database="clip_test_identity",
            expected_admin=info.user,
        )
        with guarded_admin() as c, c.transaction():
            verifier = c.pgconn.encrypt_password(
                marketplace_password.encode(),
                b"clip_local_marketplace",
                b"scram-sha-256",
            ).decode()
            c.execute(
                sql.SQL(
                    "CREATE ROLE clip_local_marketplace LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 10 PASSWORD {}"
                ).format(sql.Literal(verifier))
            )
            for name, value in LOGGING.items():
                c.execute(
                    sql.SQL("ALTER ROLE clip_local_marketplace SET {} = {}").format(
                        sql.Identifier(name), sql.Literal(value)
                    )
                )
            c.execute(
                "GRANT CONNECT ON DATABASE clip_test_identity TO clip_local_marketplace"
            )
            c.execute(
                "GRANT USAGE ON SCHEMA public,listings,search,identity,conversations TO clip_local_marketplace"
            )
            c.execute(
                "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA listings,search,conversations TO clip_local_marketplace"
            )
            c.execute(
                "GRANT SELECT ON identity.participant_profiles TO clip_local_marketplace"
            )
            c.execute(
                "GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA listings,search,conversations TO clip_local_marketplace"
            )
        settings = Settings(
            _env_file=None,
            environment="test",
            debug=False,
            development_auth=False,
            isolated_listings_test_caller=False,
            serve_web_app=False,
            identity_provider="microsoft",
            email_provider="dual",
            identity_runtime_enabled=False,
            identity_browser_origins=(),
            ses_test_recipients=tuple(recipients),
            database_url=socket_url(
                info, "clip_local_marketplace", marketplace_password
            ),
        )
        bindings = prepare_local_identity(
            settings,
            BrowserPolicy(("http://localhost:5173",), development=True),
            client=LocalParameters(
                client, socket_url(info, "clip_test_identity_app", identity_password)
            ),
        )
        yield create_app(settings, identity=bindings)


def aws_client():
    """Read fixed SSM references using approved short-lived profile credentials.

    CLI export is captured privately to support AWS login without optional SDK
    CRT dependencies. Nothing is printed or persisted; boto clients keep normal
    fixed AWS endpoints and bounded SDK requests.
    """
    import boto3
    from botocore.config import Config

    result = subprocess.run(
        [
            "aws",
            "configure",
            "export-credentials",
            "--profile",
            "adityalaxmi1",
            "--format",
            "process",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    credentials = json.loads(result.stdout)
    for target, source in (
        ("AWS_ACCESS_KEY_ID", "AccessKeyId"),
        ("AWS_SECRET_ACCESS_KEY", "SecretAccessKey"),
        ("AWS_SESSION_TOKEN", "SessionToken"),
    ):
        os.environ[target] = credentials[source]
    return boto3.client(
        "ssm",
        region_name="ap-south-1",
        config=Config(
            ignore_configured_endpoint_urls=True,
            connect_timeout=3,
            read_timeout=5,
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )


def main():
    """Explicit capped live opt-in; listeners stay loopback and raw logs stay off."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-live-local", required=True, action="store_true")
    parser.add_argument("--recipient", action="append", required=True)
    parser.add_argument("--seconds", type=int, default=10800)
    args = parser.parse_args()
    if not 60 <= args.seconds <= 14400 or not 1 <= len(args.recipient) <= 5:
        parser.error("Use 60–14400 seconds and 1–5 approved recipients")
    try:
        client = aws_client()
        with TemporaryDirectory(prefix="clip-real-local-") as directory:
            with demo_application(Path(directory), args.recipient, client) as app:
                server = uvicorn.Server(
                    uvicorn.Config(
                        app,
                        host="127.0.0.1",
                        port=8000,
                        access_log=False,
                        log_config=None,
                        proxy_headers=False,
                        workers=1,
                    )
                )
                timer = Timer(
                    args.seconds, lambda: setattr(server, "should_exit", True)
                )
                timer.daemon = True
                timer.start()
                try:
                    print(
                        "Real local auth prepared; API 127.0.0.1:8000; use http://localhost:5173/sign-in. Ctrl+C deletes local demo data.",
                        flush=True,
                    )
                    server.run()
                    if not server.started:
                        raise RuntimeError
                finally:
                    timer.cancel()
        return 0
    except Exception:
        print("Local auth demo failed; private diagnostics withheld.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
