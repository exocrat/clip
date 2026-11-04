"""Real verified TLS on both pool legs; all certificates/roles are disposable."""

from datetime import UTC, datetime, timedelta
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from apps.api.tests.domains.identity.postgres_fixtures import (
    disposable_identity_database,
)


def test_both_tls_legs_and_certificate_rejection(tmp_path):
    """Exercise real PostgreSQL SSL, hostname verification and plaintext refusal."""
    if os.environ.get("CLIP_NATIVE_PGBOUNCER_TESTS") != "1":
        pytest.skip("explicit owned Docker pool TLS test required")
    spec = importlib.util.spec_from_file_location(
        "pool_entrypoint_tls", Path("infra/pgbouncer/entrypoint.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    docker = ["docker", "--context", "default"]

    def run(args):
        result = subprocess.run(
            docker + args, capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, "owned TLS test command failed; output withheld"
        return result.stdout.strip()

    with disposable_identity_database(tmp_path, profile_limits=True) as admin:
        with admin() as db:
            root = Path(db.info.host)
            db.execute(
                "CREATE ROLE clip_test_identity_app LOGIN PASSWORD 'synthetic-tls-only'"
            )
            key = ec.generate_private_key(ec.SECP256R1())
            name = x509.Name(
                [x509.NameAttribute(NameOID.COMMON_NAME, "local-pool-test")]
            )
            now = datetime.now(UTC)
            cert = (
                x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=1))
                .not_valid_after(now + timedelta(hours=1))
                .add_extension(
                    x509.BasicConstraints(ca=True, path_length=0), critical=True
                )
                .add_extension(
                    x509.SubjectAlternativeName(
                        [x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
                    ),
                    critical=False,
                )
                .sign(key, hashes.SHA256())
            )
            pem = cert.public_bytes(serialization.Encoding.PEM)
            (root / "server.crt").write_bytes(pem)
            (root / "server.key").write_bytes(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            )
            # Separate copies: PostgreSQL requires ownership by its own OS user.
            (root / "postgres.key").write_bytes((root / "server.key").read_bytes())
            (root / "postgres.key").chmod(0o600)
            run(
                [
                    "exec",
                    "--user",
                    "0",
                    admin.profile_container_id,
                    "chown",
                    "postgres:postgres",
                    "/run/clip-identity/postgres.key",
                ]
            )
            db.execute("ALTER SYSTEM SET ssl_cert_file='/run/clip-identity/server.crt'")
            db.execute(
                "ALTER SYSTEM SET ssl_key_file='/run/clip-identity/postgres.key'"
            )
            db.execute("ALTER SYSTEM SET ssl='on'")
            db.execute("SELECT pg_reload_conf()")
        auth, config = module.render(
            "127.0.0.1",
            "clip_test_identity",
            {"clip_test_identity_app": "synthetic-tls-only"},
            root=Path("/run/clip-pool"),
        )
        config = config.replace(
            "server_tls_ca_file = /etc/ssl/certs/ca-certificates.crt",
            "server_tls_ca_file = /run/clip-pool/server.crt",
        )
        (root / "users.txt").write_text(auth)
        (root / "pgbouncer.ini").write_text(config)
        identifier = run(
            [
                "run",
                "--detach",
                "--network",
                f"container:{admin.profile_container_id}",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--mount",
                f"type=bind,src={root},dst=/run/clip-pool",
                "--entrypoint",
                "/usr/sbin/pgbouncer",
                "clip-pgbouncer:review-20261104",
                "/run/clip-pool/pgbouncer.ini",
            ]
        )
        try:
            time.sleep(0.5)
            # No test password in command arguments/output; auth is read privately.
            program = """import psycopg
from pathlib import Path
password=Path('/run/clip-pool/users.txt').read_text().split('"')[3]
params=dict(host='127.0.0.1',port=6432,user='clip_test_identity_app',password=password,dbname='clip_test_identity',sslmode='verify-full',sslrootcert='/run/clip-pool/server.crt',connect_timeout=3)
with psycopg.connect(**params) as c:
 assert c.pgconn.ssl_in_use
 assert c.execute('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()==(True,)
for override in [dict(sslmode='disable'),dict(host='wrong-name.invalid',hostaddr='127.0.0.1'),dict(sslrootcert='/etc/ssl/certs/ca-certificates.crt')]:
 try:
  with psycopg.connect(**(params|override)) as c: c.execute('SELECT 1')
 except psycopg.OperationalError: pass
 else: raise AssertionError('TLS rejection missing')
print('verified-both-legs-and-three-rejections')
"""
            assert (
                run(["exec", identifier, "python", "-c", program])
                == "verified-both-legs-and-three-rejections"
            )
            # Exercise the image's actual emitter against real TLS/stats rows,
            # including Decimal values. Stop after one iteration, without
            # changing its connection or serialization implementation.
            telemetry_program = """import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('pool_runtime','/opt/clip-pool/entrypoint.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
calls=0
def one_iteration(_):
 global calls
 calls+=1
 if calls>1: raise SystemExit(0)
module.time.sleep=one_iteration
password=Path('/run/clip-pool/users.txt').read_text().split('"')[3]
module.emit_stats('127.0.0.1',password)
"""
            event = json.loads(
                run(
                    [
                        "exec",
                        "--env",
                        "SSL_CERT_FILE=/run/clip-pool/server.crt",
                        identifier,
                        "python",
                        "-c",
                        telemetry_program,
                    ]
                )
            )
            assert event["kind"] == "clip_pool_stats"
            assert event["stats"] and event["pools"]
            assert any(row["total_xact_count"] > 0 for row in event["stats"])
        finally:
            run(["rm", "--force", identifier])
