"""Owned loopback TLS PostgreSQL for the explicit local migration transport tests."""

from datetime import UTC, datetime, timedelta
import json, os, secrets, subprocess, time
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
import psycopg
from pydantic import SecretStr
import pytest

from app.domains.identity.migration_runner import MigrationTarget


@pytest.fixture(scope="module")
def tls_database(tmp_path_factory, request):
    """Only this invocation's tmpfs container/data/certificates; no cloud target."""
    hostname = getattr(request, "param", "clip-identity-migration.invalid")
    root = tmp_path_factory.mktemp("identity-migration-tls")
    root.chmod(0o755)
    env = {k: os.environ[k] for k in ("HOME", "PATH")}

    def command(args, extra=None):
        r = subprocess.run(
            args, capture_output=True, text=True, env=env | (extra or {}), timeout=60
        )
        if r.returncode:
            raise RuntimeError("Owned TLS database command failed; output withheld")
        return r.stdout.strip()

    context = command(["docker", "context", "show"])
    assert json.loads(command(["docker", "context", "inspect", context]))[0][
        "Endpoints"
    ]["docker"]["Host"].startswith("unix://")
    docker = ["docker", "--context", context]
    digests = json.loads(
        command(
            docker
            + [
                "image",
                "inspect",
                "ghcr.io/amacneil/dbmate:2.36.0",
                "--format",
                "{{json .RepoDigests}}",
            ]
        )
    )
    image = next(d for d in digests if d.startswith("ghcr.io/amacneil/dbmate@sha256:"))
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic migration CA")]
    )
    ca = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert = (
        x509.CertificateBuilder()
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(
                        NameOID.COMMON_NAME, "clip-identity-migration.invalid"
                    )
                ]
            )
        )
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
        )
        .sign(ca_key, hashes.SHA256())
    )
    (root / "ca.pem").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (root / "server.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    private = root / "server.key"
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    private.chmod(0o600)
    password = secrets.token_hex(32)
    container = None
    try:
        container = command(
            docker
            + [
                "run",
                "--detach",
                "--publish",
                "127.0.0.1::5432",
                "--tmpfs",
                "/var/lib/postgresql:rw",
                "--mount",
                f"type=bind,src={root},dst=/run/clip-tls,readonly",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_USER=clip_identity_ci",
                "--env",
                "POSTGRES_DB=clip_test_identity",
                "--env",
                "POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256",
                "--entrypoint",
                "/bin/sh",
                "postgres:18.6-bookworm",
                "-c",
                "cp /run/clip-tls/server.key /tmp/server.key && chown postgres:postgres /tmp/server.key && chmod 600 /tmp/server.key && exec docker-entrypoint.sh postgres -c ssl=on -c ssl_cert_file=/run/clip-tls/server.crt -c ssl_key_file=/tmp/server.key",
            ],
            {"POSTGRES_PASSWORD": password},
        )
        port = int(command(docker + ["port", container, "5432/tcp"]).split(":")[-1])
        target = MigrationTarget(port, isolated=True)

        def connect(database="clip_test_identity"):
            return psycopg.connect(
                host=hostname,
                hostaddr="127.0.0.1",
                port=port,
                dbname=database,
                user=target.admin,
                password=password,
                sslmode="verify-full",
                sslrootcert=str(root / "ca.pem"),
                connect_timeout=3,
                autocommit=True,
            )

        for attempt in range(60):
            try:
                with connect() as c:
                    assert c.execute("SHOW server_version_num").fetchone() == (
                        "180006",
                    )
                break
            except psycopg.OperationalError:
                if attempt == 59:
                    raise RuntimeError("Owned TLS database readiness failed") from None
                time.sleep(0.2)
        yield SimpleNamespace(
            connect=connect,
            target=target,
            password=SecretStr(password),
            ca=root / "ca.pem",
            image=image,
            docker=docker,
        )
    finally:
        if container:
            command(docker + ["rm", "--force", container])
        private.unlink(missing_ok=True)


@pytest.fixture
def migration_case(tls_database):
    """Reset only the named database in the fixture-owned server, never shared SQL."""
    with tls_database.connect("postgres") as c:
        c.execute("DROP DATABASE clip_test_identity")
        c.execute("CREATE DATABASE clip_test_identity")
    return tls_database
