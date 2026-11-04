"""Render a private, bounded transaction pool then replace this process.

Only three original app roles are accepted. Secrets are injected by ECS and
removed from the PgBouncer environment; generated files live on a private tmpfs.
Never print configuration, DSNs, authentication strings or exception details.
"""

from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import parse_qs, unquote, urlsplit

ROLES = {
    "IDENTITY": ("clip_test_identity_app", 8),
    "MARKETPLACE": ("clip_test_marketplace_app", 24),
    "CONVERSATIONS": ("clip_test_conversations_app", 4),
}
ROOT = Path("/run/clip-pool")


def parse_source(value, expected_role):
    """Refuse alternate databases, hidden libpq overrides or weakened upstream TLS."""
    uri = urlsplit(value)
    if (
        uri.scheme not in {"postgres", "postgresql"}
        or uri.hostname
        != "clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com"
        or uri.port not in {None, 5432}
        or unquote(uri.username or "") != expected_role
        or uri.path != "/clip_next06_reference"
        or uri.fragment
        or parse_qs(uri.query, strict_parsing=True, keep_blank_values=True)
        != {"sslmode": ["verify-full"], "sslrootcert": ["system"]}
    ):
        raise ValueError("invalid source")
    password = unquote(uri.password or "")
    if not password or any(ord(c) < 32 or ord(c) == 127 for c in password):
        raise ValueError("invalid credential")
    return uri.hostname, password


def auth_quote(value):
    """PgBouncer auth-file escaping uses doubled quotes, not shell escaping."""
    return '"' + value.replace('"', '""') + '"'


def render(host, database, credentials, *, root=ROOT, local_socket=None):
    """Build fixed policy; only the local native test may replace upstream with UDS.

    Eight Identity, 24 Marketplace and four Conversations backends leave headroom
    below current role limits (10/32/4) and the instance's 75 usable connections.
    There is no forced user, wildcard database, reserve pool or direct fallback.
    """
    auth = (
        "\n".join(
            f"{auth_quote(role)} {auth_quote(password)}"
            for role, password in credentials.items()
        )
        + "\n"
    )
    # Values passed here are fixed by main or owned by the local fixture.
    if not re.fullmatch(r"[a-zA-Z0-9_]+", database):
        raise ValueError("invalid database")
    if not re.fullmatch(r"[a-zA-Z0-9_./-]+", host):
        raise ValueError("invalid host")
    users = "\n".join(
        f"{role} = pool_size={limit} max_user_connections={limit}"
        for role, limit in ROLES.values()
    )
    return (
        auth,
        f"""[databases]
{database} = host={host} port=5432 dbname={database} connect_query='SET statement_timeout=5000; SET lock_timeout=1000; SET idle_in_transaction_session_timeout=5000'
[users]
{users}
[pgbouncer]
listen_addr = {'127.0.0.1' if local_socket else '0.0.0.0'}
listen_port = 6432
unix_socket_dir = {local_socket or ''}
unix_socket_mode = 0777
auth_type = scram-sha-256
auth_file = {root}/users.txt
pool_mode = transaction
max_client_conn = 160
default_pool_size = 1
min_pool_size = 0
reserve_pool_size = 0
max_db_connections = 36
max_prepared_statements = 0
query_wait_timeout = 1
query_timeout = 6
server_connect_timeout = 3
server_login_retry = 1
server_idle_timeout = 300
server_lifetime = 3600
client_idle_timeout = 300
idle_transaction_timeout = 5
server_reset_query = DISCARD ALL
server_reset_query_always = 0
client_tls_sslmode = {'disable' if local_socket else 'require'}
client_tls_key_file = {root}/server.key
client_tls_cert_file = {root}/server.crt
server_tls_sslmode = {'disable' if local_socket else 'verify-full'}
server_tls_ca_file = /etc/ssl/certs/ca-certificates.crt
log_connections = 0
log_disconnections = 0
log_pooler_errors = 0
stats_period = 30
stats_users = clip_test_identity_app
""",
    )


def main():
    """Validate injected inputs, write private files and exec without secret env."""
    try:
        os.umask(0o077)
        credentials = {}
        for name, (role, _) in ROLES.items():
            host, credentials[role] = parse_source(
                os.environ.pop(f"POOL_{name}_DSN"), role
            )
        tls = json.loads(os.environ.pop("POOL_TLS_BUNDLE"))
        endpoint = os.environ.pop("POOL_ENDPOINT")
        if not re.fullmatch(
            r"10\.64\.1\.(?:[1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])", endpoint
        ):
            raise ValueError("invalid endpoint")
        if set(tls) != {"certificate", "private_key"}:
            raise ValueError("invalid TLS bundle")
        if not tls["certificate"].startswith("-----BEGIN CERTIFICATE-----") or not tls[
            "private_key"
        ].startswith("-----BEGIN PRIVATE KEY-----"):
            raise ValueError("invalid TLS encoding")
        ROOT.mkdir(mode=0o700, exist_ok=True)
        auth, config = render(host, "clip_next06_reference", credentials)
        for name, value in {
            "users.txt": auth,
            "pgbouncer.ini": config,
            "server.crt": tls["certificate"],
            "server.key": tls["private_key"],
        }.items():
            (ROOT / name).write_text(value)
            (ROOT / name).chmod(0o600)
    except Exception:
        print("Pool startup configuration rejected; details withheld", file=sys.stderr)
        return 1
    if os.fork() == 0:
        # PgBouncer's read-only stats user sees counters, never application rows.
        # The child dies with this container; no additional cloud/API permissions.
        emit_stats(endpoint, credentials["clip_test_identity_app"])
        return 0
    os.execv("/usr/sbin/pgbouncer", ["pgbouncer", str(ROOT / "pgbouncer.ini")])


def emit_stats(endpoint, password):
    """Emit aggregate reuse/wait/connection counters every five seconds, no SQL text."""
    import psycopg
    from psycopg.rows import dict_row

    while True:
        time.sleep(5)
        try:
            with psycopg.connect(
                host=endpoint,
                hostaddr="127.0.0.1",
                port=6432,
                dbname="pgbouncer",
                user="clip_test_identity_app",
                password=password,
                sslmode="verify-full",
                sslrootcert="system",
                connect_timeout=2,
                autocommit=True,
                row_factory=dict_row,
            ) as connection:
                stats = connection.execute("SHOW STATS").fetchall()
                pools = connection.execute("SHOW POOLS").fetchall()
                print(
                    json.dumps(
                        {
                            "kind": "clip_pool_stats",
                            "at_unix_ms": time.time_ns() // 1_000_000,
                            "stats": stats,
                            "pools": pools,
                        },
                        default=lambda value: (
                            int(value)
                            if isinstance(value, Decimal) and value == int(value)
                            else float(value)
                        ),
                    ),
                    flush=True,
                )
        except Exception:
            print(
                json.dumps(
                    {
                        "kind": "clip_pool_stats_unavailable",
                        "at_unix_ms": time.time_ns() // 1_000_000,
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    sys.exit(main())
