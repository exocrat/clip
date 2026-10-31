"""Explicit reference-data cloud adapter; import performs no cloud/SQL I/O.

The operator supplies reviewed bindings and clients. No infrastructure creation,
schema migration, grant, session creation, retry, deletion or reset is implemented.
Actual deployment/Identity/media acceptance remains a separate integration gate.
"""

from base64 import b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re

from psycopg.conninfo import conninfo_to_dict

from .reference import validate_reference
from .reference_load import canonical_id
from .reference_rows import insert_rows

ACCOUNT = "335523638354"
REGION = "ap-south-1"


class CloudLoadRejected(ValueError):
    """Fixed safe refusal; provider/SQL exceptions must not become public output."""


@dataclass(frozen=True)
class CloudTarget:
    """Nonsecret operator-reviewed exact bindings; not proof of action approval."""

    account: str
    region: str
    profile: str
    host: str
    port: int
    database: str
    role: str
    server_version_num: str
    bucket: str
    prefix: str
    source_revision: str
    logical_data_fingerprint: str
    sensitive_threshold_paise: int

    def __post_init__(self):
        """Reject wrong accounts, broad targets and unsafe names before any client call."""
        if self.account != ACCOUNT or self.region != REGION:
            raise CloudLoadRejected("project_account_region_required")
        for value in (
            self.profile,
            self.host,
            self.database,
            self.role,
            self.bucket,
            self.prefix,
        ):
            if (
                not isinstance(value, str)
                or not value
                or any(c.isspace() for c in value)
            ):
                raise CloudLoadRejected("explicit_target_required")
        if (
            not re.fullmatch(r"[a-zA-Z0-9.-]+", self.host)
            or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", self.bucket)
            or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", self.database)
            or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", self.role)
            or self.database in {"postgres", "template0", "template1"}
            or self.role in {"postgres", "rdsadmin"}
            or type(self.port) is not int
            or not 1 <= self.port <= 65535
            or not re.fullmatch(r"[0-9]{6}", self.server_version_num)
            or not re.fullmatch(r"[0-9a-f]{40}", self.source_revision)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", self.logical_data_fingerprint)
            or type(self.sensitive_threshold_paise) is not int
            or self.sensitive_threshold_paise < 0
        ):
            raise CloudLoadRejected("invalid_target_binding")
        # Run-owned namespace is mandatory; never adopt an entire feature prefix.
        if not re.fullmatch(
            r"[a-z0-9_-]+(?:/[a-z0-9_-]+)*/next06-[a-z0-9-]+", self.prefix
        ):
            raise CloudLoadRejected("run_owned_prefix_required")

    def object_key_for(self, upload_id):
        """Match the real Listings provider's prefix/uploadUUID key convention."""
        return f"{self.prefix}/{canonical_id(upload_id)}"


def validate_binding(target, bundle, secret):
    """Check input revision/fingerprint/settings and strict TLS target before connect."""
    manifest = bundle["manifest"]
    if (
        manifest["logical_data_fingerprint"] != target.logical_data_fingerprint
        or manifest["source_binding"]["base_revision"] != target.source_revision
        or manifest["sensitive_purchase_threshold_paise"]
        != target.sensitive_threshold_paise
    ):
        raise CloudLoadRejected("input_target_binding_mismatch")
    params = conninfo_to_dict(secret)
    if set(params) - {
        "host",
        "port",
        "dbname",
        "user",
        "password",
        "sslmode",
        "sslrootcert",
        "connect_timeout",
    }:
        raise CloudLoadRejected("connection_indirection_forbidden")
    if any(
        params.get(k) != v
        for k, v in {
            "host": target.host,
            "port": str(target.port),
            "dbname": target.database,
            "user": target.role,
            "sslmode": "verify-full",
        }.items()
    ) or not params.get("sslrootcert"):
        raise CloudLoadRejected("exact_tls_database_required")


def guard_database(connection, target, bundle):
    """Verify real session/transport/TLS/schema and emptiness before object writes."""
    identity = connection.execute(
        "SELECT current_database(),current_user,session_user,current_setting('server_version_num')"
    ).fetchone()
    if (
        identity
        != (target.database, target.role, target.role, target.server_version_num)
        or connection.info.host != target.host
        or connection.info.port != target.port
        or not connection.pgconn.ssl_in_use
    ):
        raise CloudLoadRejected("actual_database_target_mismatch")
    versions = {
        r[0] for r in connection.execute("SELECT version FROM public.schema_migrations")
    }
    if versions != set(bundle["manifest"]["source_binding"]["migration_versions"]):
        raise CloudLoadRejected("schema_binding_mismatch")
    privileges = connection.execute(
        "SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user"
    ).fetchone()
    if privileges != (False, False, False):
        raise CloudLoadRejected("restricted_loader_role_required")
    if connection.execute(
        "SELECT count(*) FROM listings.embedding_pipelines"
    ).fetchone() != (0,):
        raise CloudLoadRejected("fresh_pipeline_registry_required")
    if connection.execute(
        "SELECT (SELECT count(*) FROM identity.users),(SELECT count(*) FROM listings.sale_listings),(SELECT count(*) FROM listings.image_uploads),(SELECT count(*) FROM listings.images)"
    ).fetchone() != (0, 0, 0, 0):
        raise CloudLoadRejected("nonempty_target_refused")


class Ledger:
    """Create-only private JSONL: retain planned keys even for uncertain PUT outcomes.

    No URLs, SQL secrets or raw provider errors enter the ledger. A failed run is
    not retried automatically; an operator inspects only these exact keys before
    separately approved cleanup. Files are evidence, never resume instructions.
    """

    def __init__(self, path: Path):
        if not path.is_absolute() or any(p.is_symlink() for p in path.parents):
            raise CloudLoadRejected("private_absolute_ledger_required")
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        self.stream = os.fdopen(descriptor, "w", encoding="utf-8")

    def record(self, **event):
        self.stream.write(json.dumps(event, sort_keys=True) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


def upload_verified(s3, target, bundle, image_root, ledger):
    """Create-only PUT and bounded real GET/hash inspection for every planned object."""
    total = 0
    for image in bundle["image_plan"]:
        content = (image_root / image["source_relative_path"]).read_bytes()
        if (
            len(content) != image["size_bytes"]
            or hashlib.sha256(content).hexdigest() != image["sha256"]
        ):
            raise CloudLoadRejected("source_bytes_changed")
        key = target.object_key_for(image["upload_id"])
        ledger.record(state="put_planned", key=key, sha256=image["sha256"])
        s3.put_object(
            Bucket=target.bucket,
            Key=key,
            ExpectedBucketOwner=ACCOUNT,
            Body=content,
            ContentType=image["media_type"],
            IfNoneMatch="*",
            ChecksumSHA256=b64encode(bytes.fromhex(image["sha256"])).decode(),
        )
        response = s3.get_object(
            Bucket=target.bucket, Key=key, ExpectedBucketOwner=ACCOUNT
        )
        body = response.get("Body")
        if body is None:
            raise CloudLoadRejected("object_body_missing")
        try:
            actual = body.read(10485761)
        finally:
            body.close()
        if (
            response.get("ServerSideEncryption") != "AES256"
            or response.get("ContentLength") != len(content)
            or response.get("ContentType") != image["media_type"]
            or len(actual) != len(content)
            or hashlib.sha256(actual).hexdigest() != image["sha256"]
        ):
            raise CloudLoadRejected("uploaded_bytes_mismatch")
        ledger.record(state="bytes_verified", key=key, sha256=image["sha256"])
        total += len(content)
    return {
        "objects_verified": len(bundle["image_plan"]),
        "logical_object_bytes": total,
    }


def load_cloud(
    *, target, bundle, image_root, secret, sts, s3, connect, ledger, execute=False
):
    """Execute one approved bounded load; no default activation, rollback deletion or retry.

    SQL inserts are atomic and recheck emptiness under exclusive locks after media
    transfer. S3 writes cannot roll back with SQL: the ledger retains all attempted
    keys, including unknown PUT outcomes. Target migrations/grants must preexist.
    Caller supplies a global deadline and clients with bounded timeouts/no retries.
    """
    if execute is not True:
        raise CloudLoadRejected("explicit_execution_required")
    validate_reference(bundle, image_root=image_root)
    validate_binding(target, bundle, secret)
    identity = sts.get_caller_identity()
    if identity.get("Account") != ACCOUNT or not str(
        identity.get("Arn", "")
    ).startswith(
        (f"arn:aws:iam::{ACCOUNT}:user/", f"arn:aws:sts::{ACCOUNT}:assumed-role/")
    ):
        raise CloudLoadRejected("nonroot_project_identity_required")
    s3.head_bucket(Bucket=target.bucket, ExpectedBucketOwner=ACCOUNT)
    with connect(
        secret,
        autocommit=True,
        connect_timeout=5,
        options="-c statement_timeout=60000 -c lock_timeout=5000",
    ) as connection:
        guard_database(connection, target, bundle)
        ledger.record(
            state="target_checked",
            account=ACCOUNT,
            bucket=target.bucket,
            prefix=target.prefix,
        )
        media = upload_verified(s3, target, bundle, image_root, ledger)
        guard_database(connection, target, bundle)
        ledger.record(state="sql_planned", fingerprint=target.logical_data_fingerprint)
        validation = insert_rows(
            connection,
            bundle,
            object_key_for=target.object_key_for,
            audit=datetime.now(UTC),
        )
        ledger.record(
            state="sql_committed", fingerprint=target.logical_data_fingerprint
        )
    return {
        "state": "cloud bulk loaded; real auth/delivery/vector/freeze gates pending",
        "input_fingerprint": target.logical_data_fingerprint,
        **media,
        **validation,
        "real_session_auth_verified": False,
        "real_signed_delivery_verified": False,
        "semantic_pipeline_verified": False,
        "data_ready": False,
    }


def main(argv=None):
    """Offline plan or explicitly activated approved-target load; redact failures.

    The CLI imposes a15minute deadline. It cannot start resources, migrate schema,
    provision roles, reset data, resume failed writes or clean up object keys.
    """
    import argparse
    import signal
    from dataclasses import asdict
    from . import files
    from .reference import read_reference

    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("action", choices=("plan", "load"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    ledger = None
    previous = None
    try:
        read_reference(args.name, image_root=args.image_root)
        bundle = files._read_json(files._run_path(args.name) / "dataset.json")
        target = (
            CloudTarget(**json.loads(args.target.read_text())) if args.target else None
        )
        if args.action == "plan":
            if args.execute or args.ledger:
                raise CloudLoadRejected("plan_is_offline_only")
            print(
                json.dumps(
                    {
                        "state": "offline plan; no target approved or cloud calls",
                        "account": ACCOUNT,
                        "region": REGION,
                        "input_fingerprint": bundle["manifest"][
                            "logical_data_fingerprint"
                        ],
                        "source_revision": bundle["manifest"]["source_binding"][
                            "base_revision"
                        ],
                        "objects": 1000,
                        "logical_bytes": 925881224,
                        "target": asdict(target) if target else None,
                        "required_target_fields": list(
                            CloudTarget.__dataclass_fields__
                        ),
                        "remaining_gates": "operator target/cost/action approval, real auth/media/vectors/freeze",
                    },
                    indent=2,
                )
            )
            return 0
        if not args.execute or target is None or args.ledger is None:
            raise CloudLoadRejected("target_ledger_execution_required")
        if any(k.startswith(("PG", "AWS_")) for k in os.environ):
            raise CloudLoadRejected("ambient_target_overrides_forbidden")
        secret = os.environ.get("CLIP_DATABASE_URL", "")
        validate_binding(target, bundle, secret)
        from .reference_login import sdk_session
        from botocore.config import Config
        import psycopg

        def deadline(signum, frame):
            raise TimeoutError("cloud_load_deadline")

        previous = signal.signal(signal.SIGALRM, deadline)
        signal.alarm(900)
        ledger = Ledger(args.ledger)
        session = sdk_session(target.profile, REGION)
        config = Config(
            connect_timeout=5,
            read_timeout=30,
            retries={"total_max_attempts": 1},
            signature_version="s3v4",
        )
        report = load_cloud(
            target=target,
            bundle=bundle,
            image_root=args.image_root,
            secret=secret,
            sts=session.client(
                "sts", config=config.merge(Config(signature_version="v4"))
            ),
            s3=session.client("s3", config=config),
            connect=psycopg.connect,
            ledger=ledger,
            execute=True,
        )
        print(json.dumps(report, default=str))
        return 0
    except Exception as error:
        # Provider/SQL errors may contain keys, credentials or source values.
        # Keep only safe classification; uncertain writes require operator review.
        if ledger is not None:
            try:
                ledger.record(
                    state="failed_or_uncertain", failure_type=type(error).__name__
                )
            except OSError:
                pass  # Earlier fsynced planned-key events remain the recovery boundary.
        print(
            json.dumps(
                {
                    "state": "refused_or_failed",
                    "failure_type": type(error).__name__,
                    "automatic_retry": False,
                    "data_ready": False,
                }
            )
        )
        return 1
    finally:
        if previous is not None:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
        if ledger is not None:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
