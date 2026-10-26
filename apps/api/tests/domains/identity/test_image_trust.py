"""Pinned public CA integrity and opt-in real image/libpq TLS verification.

Ordinary tests use only vendored public data. CLIP_IDENTITY_TEST_IMAGE explicitly
selects an already-built local image; no pull/build/AWS/real credential is used.
Synthetic TLS trust is container-local and temporary, never baked into the image.
"""

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

from cryptography import x509
from cryptography.hazmat.primitives import hashes
import pytest

from apps.api.tests.domains.identity.migration_fixtures import tls_database

ROOT = Path(__file__).resolve().parents[5]
CERTIFICATES = ROOT / "apps/api/app/domains/identity/certificates"


def test_public_regional_roots_match_pinned_manifest_and_are_current():
    """Check actual X.509 purpose/signatures/expiry, not just Dockerfile text."""
    manifest = json.loads((CERTIFICATES / "manifest.json").read_text())
    assert (
        manifest["source_url"]
        == "https://truststore.pki.rds.amazonaws.com/ap-south-1/ap-south-1-bundle.pem"
    )
    assert manifest["region"] == "ap-south-1"
    records = manifest["certificates"]
    assert len(records) == 3
    assert sorted(p.name for p in CERTIFICATES.glob("*.crt")) == sorted(
        row["file"] for row in records
    )
    fingerprints = set()
    for row in records:
        data = (CERTIFICATES / row["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"]
        assert len(x509.load_pem_x509_certificates(data)) == 1
        cert = x509.load_pem_x509_certificate(data)
        assert cert.subject == cert.issuer
        cert.verify_directly_issued_by(cert)
        assert cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
        assert cert.extensions.get_extension_for_class(
            x509.KeyUsage
        ).value.key_cert_sign
        assert "Amazon RDS ap-south-1 Root CA" in cert.subject.rfc4514_string()
        assert cert.subject.rfc4514_string() == row["subject"]
        assert cert.not_valid_before_utc.isoformat() == row["not_before_utc"]
        assert cert.not_valid_after_utc.isoformat() == row["not_after_utc"]
        assert cert.not_valid_before_utc <= datetime.now(UTC) < cert.not_valid_after_utc
        fingerprint = cert.fingerprint(hashes.SHA256()).hex()
        assert fingerprint == row["certificate_sha256"]
        fingerprints.add(fingerprint)
    assert len(fingerprints) == 3


@pytest.fixture(scope="module")
def image():
    """Select only an existing native local image through a Unix-socket daemon."""
    image_name = os.environ.get("CLIP_IDENTITY_TEST_IMAGE")
    if not image_name:
        pytest.skip("Explicit local image not selected")
    assert re.fullmatch(
        r"clip-api:id-ready-rds-ca-[a-z0-9.-]+|sha256:[0-9a-f]{64}", image_name
    )
    env = {key: os.environ[key] for key in ("HOME", "PATH")}
    context = subprocess.check_output(
        ["docker", "context", "show"], env=env, text=True, timeout=10
    ).strip()
    details = json.loads(
        subprocess.check_output(
            ["docker", "context", "inspect", context], env=env, timeout=10
        )
    )
    assert details[0]["Endpoints"]["docker"]["Host"].startswith("unix://")
    docker = ["docker", "--context", context]
    info = json.loads(
        subprocess.check_output(
            docker + ["image", "inspect", image_name], env=env, timeout=10
        )
    )[0]
    assert info["Os"] == "linux"
    assert info["Config"]["User"] == "10001:10001"
    assert info["Config"]["WorkingDir"] == "/app"
    assert "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt" in info["Config"]["Env"]
    assert not any(
        value.startswith(("SSL_CERT_DIR=", "PGSSLROOTCERT=", "PGSSLMODE="))
        for value in info["Config"]["Env"]
    )
    assert (
        info["Architecture"]
        == {"aarch64": "arm64", "x86_64": "amd64"}[platform.machine()]
    )
    return docker, info["Id"], env


def run_image(image, source, *, network="none", mounts=()):
    """Run bounded/read-only/non-root; scripts enter via stdin, no credential args."""
    docker, identifier, env = image
    command = docker + [
        "run",
        "--rm",
        "--pull=never",
        "--interactive",
        "--read-only",
        "--user",
        "10001:10001",
        "--network",
        network,
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=4m,mode=1777",
    ]
    for mount in mounts:
        command += ["--mount", mount]
    command += ["--entrypoint", "python", identifier, "-"]
    result = subprocess.run(
        command, input=source, text=True, capture_output=True, env=env, timeout=30
    )
    assert result.returncode == 0, "Local image TLS check failed; raw output withheld"
    return json.loads(result.stdout)


def test_actual_image_retains_system_roots_and_installs_regional_roots(image):
    result = run_image(
        image,
        """
import hashlib,json,os,pathlib,ssl
assert os.geteuid()==10001
context=ssl.create_default_context()
assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED
roots={hashlib.sha256(cert).hexdigest() for cert in context.get_ca_certs(binary_form=True)}
path=pathlib.Path('/app/apps/api/app/domains/identity/certificates')
manifest=json.loads((path/'manifest.json').read_text())
assert all(row['certificate_sha256'] in roots for row in manifest['certificates'])
# Built-in distribution roots must remain, rather than replacing the public store.
distribution={hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest() for cert in pathlib.Path('/usr/share/ca-certificates').rglob('*.crt')}
assert distribution and distribution<=roots
print(json.dumps({'regional_roots':len(manifest['certificates']),'system_roots':len(roots),'distribution_roots_retained':len(distribution),'uid':os.geteuid(),'regional_root_sha256':sorted(row['certificate_sha256'] for row in manifest['certificates'])}))
""",
    )
    assert result["regional_roots"] == 3 and result["uid"] == 10001
    expected = json.loads((CERTIFICATES / "manifest.json").read_text())
    assert result["regional_root_sha256"] == sorted(
        row["certificate_sha256"] for row in expected["certificates"]
    )


def test_actual_image_libpq_system_roots_reject_wrong_hostname(
    image, request, tmp_path
):
    """Use the shipped image CA path, without test-only environment overrides.

    A temporary read-only bind mount adds only this fixture's synthetic root to
    the image's public CA bundle. Image layers and real system files are unchanged.
    This proves the actual image SSL_CERT_FILE and installed roots work together,
    without a test-only CA-path override that could hide packaging errors.
    """
    case = request.getfixturevalue("tls_database")
    payload = json.dumps(
        {
            "password": case.password.get_secret_value(),
            "host": case.target.host,
            "user": case.target.admin,
            "database": case.target.database,
        }
    )
    common = "payload=" + payload + """
import json,os,psycopg
assert os.environ.get('SSL_CERT_FILE')=='/etc/ssl/certs/ca-certificates.crt'
assert not any(name in os.environ for name in ('SSL_CERT_DIR','PGSSLROOTCERT','PGSSLMODE'))
parameters=dict(host=payload['host'],hostaddr='127.0.0.1',port=5432,dbname=payload['database'],user=payload['user'],password=payload['password'],sslmode='verify-full',sslrootcert='system',connect_timeout=3)
"""
    unknown = run_image(
        image,
        common + """
try:
    psycopg.connect(**parameters).close()
except psycopg.OperationalError as error:
    assert 'certificate verify failed' in str(error)
else:
    raise AssertionError('Untrusted synthetic root accepted')
print(json.dumps({'untrusted_root_rejected':True}))
""",
        network="container:" + case.container,
    )
    assert unknown == {"untrusted_root_rejected": True}
    docker, identifier, env = image
    system_file = tmp_path / "ca-certificates.crt"
    container = None
    try:
        container = subprocess.check_output(
            docker
            + [
                "create",
                "--pull=never",
                "--network",
                "none",
                "--entrypoint",
                "python",
                identifier,
                "-c",
                "pass",
            ],
            env=env,
            text=True,
            timeout=10,
        ).strip()
        subprocess.run(
            docker
            + [
                "cp",
                container + ":/etc/ssl/certs/ca-certificates.crt",
                str(system_file),
            ],
            env=env,
            check=True,
            capture_output=True,
            timeout=10,
        )
    finally:
        if container:
            subprocess.run(
                docker + ["rm", container],
                env=env,
                check=True,
                capture_output=True,
                timeout=10,
            )
    system_file.write_bytes(system_file.read_bytes() + b"\n" + case.ca.read_bytes())
    system_file.chmod(0o644)
    result = run_image(
        image,
        common + """
with psycopg.connect(**parameters) as connection:
    assert connection.execute('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()==(True,)
try:
    psycopg.connect(**(parameters|{'host':'wrong-identity.invalid'})).close()
except psycopg.OperationalError as error:
    assert 'does not match host name' in str(error)
else:
    raise AssertionError('Wrong hostname accepted')
print(json.dumps({'verified_sql':True,'wrong_hostname_rejected':True}))
""",
        network="container:" + case.container,
        mounts=(
            f"type=bind,src={system_file},dst=/etc/ssl/certs/ca-certificates.crt,readonly",
        ),
    )
    assert result == {"verified_sql": True, "wrong_hostname_rejected": True}


def test_actual_image_default_startup_stays_provider_unbound(image):
    """Real loopback health/protected API check in a network-isolated container."""
    result = run_image(
        image,
        """
import json,subprocess,time,urllib.error,urllib.request
process=subprocess.Popen(['/opt/venv/bin/uvicorn','app.main:app','--app-dir','apps/api','--host','127.0.0.1','--port','8000','--no-access-log'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for attempt in range(80):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1) as response:
                assert json.load(response)=={'status':'ok'}
            break
        except (OSError,ValueError):
            if process.poll() is not None or attempt==79:raise
            time.sleep(0.1)
    try:
        urllib.request.urlopen('http://127.0.0.1:8000/wanted-requests',timeout=2)
    except urllib.error.HTTPError as error:
        assert error.code==401
    else:
        raise AssertionError('Unbound default API authorized request')
    print(json.dumps({'health':True,'protected_api_denied':True}))
finally:
    process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
""",
    )
    assert result == {"health": True, "protected_api_denied": True}
