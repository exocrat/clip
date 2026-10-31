"""One-window NEXT-06 loader access; inert import, no AWS or stored credentials.

Caller owns exact cloud action approval, private tunnel, deadline and access
closeout. New ephemeral password is returned only in memory; never log/repr it.
A failed/uncertain activation still requires close() with the same role-OID proof.
No persistent parameter, role creation, migration, grant or automatic retry.
"""

from datetime import datetime, UTC
from pathlib import Path
import secrets

from psycopg import sql
from psycopg.conninfo import make_conninfo

from scripts.evaluation.reference_admin_inventory import ADMIN, HOST, LOGGING
from scripts.evaluation.reference_database_setup import DATABASE, LOADER, RUNTIME
from data.generators.reference_cloud import CloudLoadRejected

PORT = 5432


class LoadAccessRefused(CloudLoadRejected):
    """Fixed code-only refusal; SQL errors/passwords must not enter evidence."""


def guard_admin(connection, *, owned_socket=None):
    """Verify fixed isolated admin target, transport/version and privacy defaults."""
    if connection.autocommit is not True or connection.execute(
        "SELECT current_database(),current_user,session_user,current_setting('server_version_num')"
    ).fetchone() != (DATABASE, ADMIN, ADMIN, "180006"):
        raise LoadAccessRefused("isolated_admin_target_required")
    if connection.execute(
        "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()"
    ).fetchone() != (ADMIN,):
        raise LoadAccessRefused("isolated_database_owner_changed")
    if owned_socket is None:
        params = connection.info.get_parameters()
        if (
            connection.info.host != HOST
            or connection.info.port != PORT
            or params.get("hostaddr") != "127.0.0.1"
            or params.get("sslmode") != "verify-full"
            or not connection.pgconn.ssl_in_use
        ):
            raise LoadAccessRefused("private_verified_tls_required")
    elif (
        not isinstance(owned_socket, Path)
        or not owned_socket.is_absolute()
        or not str(owned_socket).startswith("/private/tmp/clip-next06-reference-")
        or owned_socket.name != "pgsocket"
        or owned_socket.is_symlink()
        or connection.info.host != str(owned_socket)
        or connection.info.port != 55438
    ):
        raise LoadAccessRefused("owned_native_socket_required")
    for name, value in LOGGING.items():
        if connection.execute("SELECT current_setting(%s)", (name,)).fetchone() != (
            value,
        ):
            raise LoadAccessRefused("privacy_settings_changed")
    for name in ("pgaudit.log", "auto_explain.log_min_duration"):
        if connection.execute("SELECT current_setting(%s,true)", (name,)).fetchone()[
            0
        ] not in (None, "", "none", "-1"):
            raise LoadAccessRefused("extended_logging_enabled")


class WindowAccess:
    """Bind one fresh inactive loader OID; activate once and revoke on every outcome.

    The wrapper retains only a safe OID/attempt flag. Password expires within45min;
    expiry bounds new authentication, not already open sessions. Caller must close
    SQL sessions and invoke close() before terminating its owned tunnel/resources.
    """

    def __init__(self):
        self.role_oid = None
        self.attempted = False
        self.closed = False

    def activate(self, connection, *, expires, record, owned_socket=None):
        """Generate a private credential and activate only the prepared loader role.

        Evidence precedes uncertain SQL dispatch. All row/role/source/media guards
        remain the load adapter's responsibility before any PUT or SQL insert.
        Never call twice, rotate an existing credential, or activate runtime.
        """
        if self.attempted or self.closed:
            raise LoadAccessRefused("activation_already_attempted")
        guard_admin(connection, owned_socket=owned_socket)
        now = datetime.now(UTC)
        if (
            not isinstance(expires, datetime)
            or expires.tzinfo is None
            or not 300 <= (expires - now).total_seconds() <= 2700
        ):
            raise LoadAccessRefused("bounded_aware_expiry_required")
        rows = connection.execute(
            "SELECT oid,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls,rolvaliduntil FROM pg_roles WHERE rolname=%s",
            (LOADER,),
        ).fetchone()
        runtime = connection.execute(
            "SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s",
            (RUNTIME,),
        ).fetchone()
        if (
            rows is None
            or rows[1:8] != (False,) * 7
            or rows[8] is not None
            or runtime != (False,) * 7
        ):
            raise LoadAccessRefused("fresh_inactive_roles_required")
        if connection.execute(
            "SELECT 1 FROM pg_auth_members WHERE member=%s", (rows[0],)
        ).fetchone():
            raise LoadAccessRefused("unexpected_loader_membership")
        if (
            connection.execute(
                "SELECT 1 FROM pg_class WHERE relowner=%s LIMIT 1", (rows[0],)
            ).fetchone()
            or connection.execute(
                "SELECT 1 FROM pg_namespace WHERE nspowner=%s LIMIT 1", (rows[0],)
            ).fetchone()
        ):
            raise LoadAccessRefused("loader_must_not_own_schema_or_relations")
        if connection.execute(
            "SELECT (SELECT count(*) FROM identity.users),(SELECT count(*) FROM listings.sale_listings),(SELECT count(*) FROM listings.image_uploads),(SELECT count(*) FROM listings.images),(SELECT count(*) FROM listings.embedding_pipelines)"
        ).fetchone() != (0, 0, 0, 0, 0):
            raise LoadAccessRefused("fresh_empty_target_required")
        password = secrets.token_urlsafe(32)
        self.role_oid = rows[0]
        self.attempted = True
        record(
            stage="loader_activation_attempt",
            role_oid=self.role_oid,
            expires_utc=expires.astimezone(UTC).isoformat(),
        )
        with connection.transaction():
            connection.execute("SET LOCAL password_encryption='scram-sha-256'")
            connection.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {} VALID UNTIL {}").format(
                    sql.Identifier(LOADER),
                    sql.Literal(password),
                    sql.Literal(expires.isoformat()),
                )
            )
        record(stage="loader_activated", role_oid=self.role_oid)
        return make_conninfo(
            host=HOST,
            port=PORT,
            dbname=DATABASE,
            user=LOADER,
            password=password,
            sslmode="verify-full",
            sslrootcert="system",
        )

    def close(self, connection, *, record, owned_socket=None):
        """Clear only this invocation's attempted loader password; prove NOLOGIN.

        Refuse an OID/membership/privilege drift instead of disabling a different
        role. No session killing or retry; caller records pending cleanup on error.
        Runtime and shared application roles are never modified.
        """
        if not self.attempted or self.closed:
            return
        guard_admin(connection, owned_socket=owned_socket)
        row = connection.execute(
            "SELECT oid,rolsuper,rolcreatedb,rolcreaterole,rolinherit,rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s",
            (LOADER,),
        ).fetchone()
        if (
            row != (self.role_oid, False, False, False, False, False, False)
            or connection.execute(
                "SELECT 1 FROM pg_auth_members WHERE member=%s", (self.role_oid,)
            ).fetchone()
        ):
            raise LoadAccessRefused("loader_cleanup_ownership_or_privilege_drift")
        record(stage="loader_revoke_attempt", role_oid=self.role_oid)
        with connection.transaction():
            connection.execute(
                sql.SQL(
                    "ALTER ROLE {} NOLOGIN PASSWORD NULL VALID UNTIL 'epoch'"
                ).format(sql.Identifier(LOADER))
            )
            if connection.execute(
                "SELECT rolcanlogin FROM pg_roles WHERE oid=%s", (self.role_oid,)
            ).fetchone() != (False,):
                raise LoadAccessRefused("loader_disable_not_verified")
        self.closed = True
        record(stage="loader_disabled_password_cleared", role_oid=self.role_oid)


def storage_preflight(s3, target):
    """Check exact owner/region/private encryption and empty run prefix before writes.

    Operator permissions are proved only by later real calls, never inferred from
    a policy listing. No object is written/deleted or bucket configuration changed.
    """
    args = {"Bucket": target.bucket, "ExpectedBucketOwner": target.account}
    s3.head_bucket(**args)
    if s3.get_bucket_location(**args).get("LocationConstraint") != target.region:
        raise LoadAccessRefused("bucket_region_changed")
    block = s3.get_public_access_block(**args).get("PublicAccessBlockConfiguration", {})
    if any(
        block.get(k) is not True
        for k in (
            "BlockPublicAcls",
            "IgnorePublicAcls",
            "BlockPublicPolicy",
            "RestrictPublicBuckets",
        )
    ):
        raise LoadAccessRefused("bucket_public_access_guard")
    if (
        s3.get_bucket_policy_status(**args).get("PolicyStatus", {}).get("IsPublic")
        is not False
    ):
        raise LoadAccessRefused("bucket_policy_not_private")
    rules = (
        s3.get_bucket_encryption(**args)
        .get("ServerSideEncryptionConfiguration", {})
        .get("Rules", [])
    )
    if (
        len(rules) != 1
        or rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm")
        != "AES256"
    ):
        raise LoadAccessRefused("sse_s3_required")
    ownership = (
        s3.get_bucket_ownership_controls(**args)
        .get("OwnershipControls", {})
        .get("Rules", [])
    )
    if ownership != [{"ObjectOwnership": "BucketOwnerEnforced"}]:
        raise LoadAccessRefused("owner_enforced_bucket_required")
    listing = s3.list_objects_v2(**args, Prefix=target.prefix + "/", MaxKeys=1)
    if (
        listing.get("Contents")
        or listing.get("KeyCount") != 0
        or listing.get("IsTruncated") is not False
    ):
        raise LoadAccessRefused("empty_new_run_prefix_required")
    return {
        "state": "storage_preflight_passed",
        "objects_before": 0,
        "encryption": "AES256",
        "public": False,
    }


def verify_owned_listener(raw, group_id, getpgid):
    """Accept only an owned loopback5432 listener from bounded lsof -Fpn output."""
    try:
        if not isinstance(raw, bytes) or len(raw) > 4096:
            raise ValueError
        fields = raw.decode("ascii").splitlines()
        pids = {
            int(line[1:])
            for line in fields
            if line.startswith("p") and line[1:].isdigit()
        }
        names = [line[1:] for line in fields if line.startswith("n")]
        if (
            len(pids) != 1
            or not names
            or any(name not in {"127.0.0.1:5432", "[::1]:5432"} for name in names)
        ):
            raise ValueError
        if getpgid(next(iter(pids))) != group_id:
            raise ValueError
    except ValueError, OSError, UnicodeError:
        raise LoadAccessRefused("owned_loopback_listener_not_proved") from None


class BoundedStorage:
    """Permit only reviewed bucket checks and one PUT/GET per exact planned key.

    The fsynced upload ledger is the recovery boundary; this in-memory guard never
    resumes, retries or deletes. Deadline/call limits apply before provider dispatch.
    """

    READS = frozenset(
        {
            "head_bucket",
            "get_bucket_location",
            "get_public_access_block",
            "get_bucket_policy_status",
            "get_bucket_encryption",
            "get_bucket_ownership_controls",
            "list_objects_v2",
        }
    )

    def __init__(self, client, target, allowed_keys, *, deadline, clock):
        self.client = client
        self.target = target
        self.allowed_keys = frozenset(allowed_keys)
        self.deadline = deadline
        self.clock = clock
        self.calls = 0
        self.attempted = set()
        self.put_confirmed = set()

    def __getattr__(self, name):
        if name not in self.READS | {"put_object", "get_object"}:
            raise LoadAccessRefused("storage_operation_not_approved")

        def dispatch(**kwargs):
            if self.calls >= 2008 or self.clock() >= self.deadline:
                raise LoadAccessRefused("storage_budget_or_deadline")
            if (
                kwargs.get("Bucket") != self.target.bucket
                or kwargs.get("ExpectedBucketOwner") != self.target.account
            ):
                raise LoadAccessRefused("storage_owner_or_bucket_drift")
            if name == "list_objects_v2" and (
                kwargs.get("Prefix") != self.target.prefix + "/"
                or kwargs.get("MaxKeys") != 1
            ):
                raise LoadAccessRefused("storage_prefix_listing_not_approved")
            if name in {"put_object", "get_object"}:
                key = kwargs.get("Key")
                if key not in self.allowed_keys or (name, key) in self.attempted:
                    raise LoadAccessRefused("storage_key_or_retry_not_approved")
                if name == "put_object" and kwargs.get("IfNoneMatch") != "*":
                    raise LoadAccessRefused("create_only_storage_required")
                if name == "get_object" and key not in self.put_confirmed:
                    raise LoadAccessRefused("only_confirmed_new_object_read_allowed")
                self.attempted.add((name, key))
            self.calls += 1
            result = getattr(self.client, name)(**kwargs)
            if name == "put_object":
                self.put_confirmed.add(kwargs["Key"])
            return result

        return dispatch


def load_window_outcome(report):
    """Derive load closeout from actual result and verified access/compute cleanup."""
    attempts = report.get("resource_start_attempts")
    if (
        not isinstance(attempts, dict)
        or set(attempts) != {"rds", "ec2"}
        or any(type(v) is not bool for v in attempts.values())
    ):
        return "cleanup_pending_operator_attention"
    if not any(attempts.values()):
        return "blocked_before_starts"
    cleanup = report.get("cleanup")
    if (
        not isinstance(cleanup, dict)
        or cleanup.get("pending")
        or any(
            attempts[k]
            and cleanup.get({"ec2": "host_stopped", "rds": "rds_stopped"}[k])
            is not True
            for k in attempts
        )
    ):
        return "cleanup_pending_operator_attention"
    if (
        cleanup.get("loader_cleanup_pending")
        or cleanup.get("tunnel_close_pending")
        or cleanup.get("session_close_pending")
    ):
        return "cleanup_pending_operator_attention"
    if report.get("load_passed") is True and any(
        cleanup.get(k) is not True
        for k in (
            "loader_disabled_password_cleared",
            "owned_tunnel_exited",
            "owned_session_terminated",
        )
    ):
        return "cleanup_pending_operator_attention"
    result = report.get("load_result", {})
    if (
        report.get("load_passed") is True
        and isinstance(result, dict)
        and result.get("objects_verified") == 1000
        and result.get("users_verified") == 5000
        and result.get("listings_verified") == 1000
    ):
        return "cloud_load_passed_resources_stopped"
    return "cloud_load_failed_resources_stopped"
