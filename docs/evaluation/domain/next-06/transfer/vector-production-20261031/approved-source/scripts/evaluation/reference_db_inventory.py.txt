"""Prepared fixed-target read-only probe with safe versioned diagnostics.

No cloud use without exact approval. Raw CLI/container errors and credentials
never enter reports. The executed v1 source/payload/receipt are retained separately.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from uuid import uuid4

ACCOUNT = "335523638354"
INSTANCE = "i-086045c48487471de"
HOST = "clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com"
PARAMETER = "/clip/test/listings-database-url"
IMAGE = (
    "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:"
    "97482cb4fb697eee230e66d134c165e557dac7d71a165e6034c88747f1738245"
)
CONTAINER = "clip-next06-readonly-inventory"


HOST_STAGES = frozenset(
    {
        "tools",
        "cli_version",
        "host_identity",
        "cached_image",
        "container_name",
        "connection_secret",
        "sql_child",
        "cleanup",
        "complete",
    }
)
SQL_STAGES = frozenset(
    {
        "sql_import",
        "input",
        "dsn_parse",
        "dsn_binding",
        "connect",
        "session",
        "privileges",
        "migrations",
        "schemas",
        "proposed_database",
        "complete",
    }
)
REASONS = frozenset(
    {
        "command_failed",
        "command_timeout",
        "command_unavailable",
        "command_output_bound",
        "invalid_json",
        "required_existing_tools_absent",
        "cli_version_unrecognized",
        "aws_cli_v2_required",
        "host_role_mismatch",
        "container_name_already_exists",
        "connection_secret_bound",
        "child_report_invalid",
        "child_failed",
        "cleanup_not_confirmed",
        "unexpected_error",
        "explicit_approval_required",
    }
)
SQL_REASONS = frozenset(
    {
        "input_bound",
        "indirection",
        "target_tls",
        "restricted_runtime_secret_required",
        "actual_target",
        "privileged_role_refused",
        "rds_superuser_refused",
        "unexpected_error",
    }
)
FAILURE_TYPES = frozenset(
    {
        "ProbeError",
        "ProbeRefused",
        "ValueError",
        "TypeError",
        "KeyError",
        "AttributeError",
        "JSONDecodeError",
        "UnicodeDecodeError",
        "OSError",
        "FileNotFoundError",
        "PermissionError",
        "TimeoutExpired",
        "ModuleNotFoundError",
        "OperationalError",
        "ProgrammingError",
        "DatabaseError",
        "InsufficientPrivilege",
        "InvalidPassword",
        "UndefinedTable",
        "OtherError",
    }
)
PROVIDER_CODES = frozenset(
    {
        "AccessDenied",
        "AccessDeniedException",
        "ParameterNotFound",
        "InvalidKeyId",
        "ExpiredToken",
        "ExpiredTokenException",
        "UnrecognizedClientException",
        "KMSAccessDeniedException",
        "ThrottlingException",
    }
)
METADATA_KEYS = {
    "identity",
    "roles",
    "migration_versions",
    "schemas",
    "proposed_database_already_exists",
}
HOST_KEYS = {
    "format_version",
    "state",
    "stage",
    "reason",
    "failure_type",
    "return_code",
    "provider_error",
    "child_stage",
    "child_reason",
    "sqlstate",
    "cli_version",
    "cleanup",
    "metadata",
}

# Fixed child: only these SQL operations are permitted by the prepared payload.
SQL_PROBE = r"""
import json,re,sys
class ProbeRefused(Exception): pass
stage='sql_import'
try:
    import psycopg
    from psycopg.conninfo import conninfo_to_dict
    stage='input'
    raw=sys.stdin.buffer.read(16385)
    if not raw or len(raw)>16384: raise ProbeRefused('input_bound')
    stage='dsn_parse'
    p=conninfo_to_dict(raw.decode())
    stage='dsn_binding'
    if set(p)-{'host','port','dbname','user','password','sslmode','sslrootcert','application_name','connect_timeout'}: raise ProbeRefused('indirection')
    if p.get('host')!='clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com' or p.get('port','5432')!='5432' or p.get('sslmode')!='verify-full' or not p.get('sslrootcert'): raise ProbeRefused('target_tls')
    if not p.get('dbname') or not p.get('user') or p['user'] in {'postgres','rdsadmin'}: raise ProbeRefused('restricted_runtime_secret_required')
    stage='connect'
    with psycopg.connect(raw.decode(),autocommit=True,connect_timeout=5,options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000',application_name='clip-next06-readonly-inventory') as c:
        with c.transaction():
            c.execute('SET TRANSACTION READ ONLY')
            stage='session'
            identity=c.execute("SELECT current_database(),current_user,session_user,current_setting('server_version_num'),current_setting('transaction_read_only')").fetchone()
            if identity[1]!=identity[2] or identity[3]!='180006' or identity[4]!='on' or not c.pgconn.ssl_in_use: raise ProbeRefused('actual_target')
            stage='privileges'
            roles=c.execute("SELECT rolname,rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname IN (current_user,'clip_next06_loader','clip_next06_runtime') ORDER BY rolname").fetchall()
            if any(any(r[1:]) for r in roles): raise ProbeRefused('privileged_role_refused')
            if c.execute("SELECT oid FROM pg_roles WHERE rolname='rds_superuser' AND pg_has_role(current_user,oid,'MEMBER')").fetchone(): raise ProbeRefused('rds_superuser_refused')
            stage='migrations'
            versions=c.execute('SELECT version FROM public.schema_migrations ORDER BY version').fetchall()
            stage='schemas'
            schemas=c.execute("SELECT nspname FROM pg_namespace WHERE nspname IN ('identity','listings','search','conversations') ORDER BY nspname").fetchall()
            stage='proposed_database'
            proposed=c.execute("SELECT datname FROM pg_database WHERE datname='clip_next06_reference'").fetchall()
    print(json.dumps({'format_version':2,'state':'readonly_metadata_passed','stage':'complete','metadata':{'identity':identity,'roles':roles,'migration_versions':[r[0] for r in versions],'schemas':[r[0] for r in schemas],'proposed_database_already_exists':bool(proposed)}}))
except Exception as error:
    names={'ProbeRefused','ValueError','TypeError','KeyError','AttributeError','JSONDecodeError','UnicodeDecodeError','OSError','ModuleNotFoundError','OperationalError','ProgrammingError','DatabaseError','InsufficientPrivilege','InvalidPassword','UndefinedTable'}
    kind=type(error).__name__
    code=getattr(error,'sqlstate',None)
    if code is not None and (not isinstance(code,str) or not re.fullmatch(r'[0-9A-Z]{5}',code)): code=None
    print(json.dumps({'format_version':2,'state':'refused_or_failed','stage':stage,'reason':str(error) if isinstance(error,ProbeRefused) else 'unexpected_error','failure_type':kind if kind in names else 'OtherError','sqlstate':code}))
    sys.exit(1)
"""


class ProbeError(RuntimeError):
    """Only code-owned classifications; never raw process/SQL error text."""

    def __init__(self, reason, *, return_code=None, provider_error=None):
        if reason not in REASONS:
            raise ValueError("unknown_probe_reason")
        super().__init__(reason)
        self.reason = reason
        self.return_code = (
            return_code
            if type(return_code) is int and -255 <= return_code <= 255
            else None
        )
        self.provider_error = (
            provider_error if provider_error in PROVIDER_CODES else None
        )


def run(argv, *, env, timeout, content=None, allow_nonzero=False):
    """Capture privately; only SQL child stdout may be inspected on nonzero exit."""
    try:
        result = subprocess.run(
            argv,
            env=env,
            input=content,
            stdin=None if content is not None else subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ProbeError("command_timeout") from None
    except OSError:
        raise ProbeError("command_unavailable") from None
    if len(result.stdout) > 65536 or len(result.stderr) > 65536:
        raise ProbeError("command_output_bound")
    if result.returncode and not allow_nonzero:
        match = (
            re.search(rb"An error occurred \(([A-Za-z0-9_.]+)\)", result.stderr)
            if os.path.basename(argv[0]) == "aws"
            else None
        )
        code = match.group(1).decode("ascii") if match else None
        raise ProbeError(
            "command_failed", return_code=result.returncode, provider_error=code
        )
    return result if allow_nonzero else result.stdout


def parse_json(raw):
    """Never include decoder exceptions, raw bytes or extra fields in diagnostics."""
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as error:
        raise ProbeError("invalid_json") from None
    if not isinstance(value, dict):
        raise ProbeError("invalid_json")
    return value


def valid_metadata(value):
    """Allow only the expected bounded catalog metadata, not arbitrary child output."""
    if not isinstance(value, dict) or set(value) != METADATA_KEYS:
        return False
    identity = value["identity"]
    identifier = (
        lambda s: isinstance(s, str)
        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,62}", s) is not None
    )
    if (
        not isinstance(identity, list)
        or len(identity) != 5
        or not all(identifier(x) for x in identity[:3])
        or identity[1] != identity[2]
        or identity[3:] != ["180006", "on"]
    ):
        return False
    roles = value["roles"]
    if not isinstance(roles, list) or not 1 <= len(roles) <= 3:
        return False
    if any(
        not isinstance(r, list)
        or len(r) != 4
        or not identifier(r[0])
        or any(type(b) is not bool or b for b in r[1:])
        for r in roles
    ):
        return False
    versions = value["migration_versions"]
    if (
        not isinstance(versions, list)
        or len(versions) > 100
        or any(
            not isinstance(v, str) or re.fullmatch(r"[0-9]{1,20}", v) is None
            for v in versions
        )
    ):
        return False
    schemas = value["schemas"]
    return (
        isinstance(schemas, list)
        and len(schemas) <= 4
        and all(
            isinstance(s, str)
            and s in {"identity", "listings", "search", "conversations"}
            for s in schemas
        )
        and type(value["proposed_database_already_exists"]) is bool
    )


def validate_child_report(raw, return_code):
    """Retain only versioned success or fixed failure classifications from SQL child."""
    try:
        v = parse_json(raw)
        if type(return_code) is not int or not -255 <= return_code <= 255:
            raise ValueError
        if type(v.get("format_version")) is not int or v["format_version"] != 2:
            raise ValueError
        if v.get("state") == "readonly_metadata_passed":
            if (
                set(v) != {"format_version", "state", "stage", "metadata"}
                or return_code != 0
                or v.get("stage") != "complete"
                or not valid_metadata(v.get("metadata"))
            ):
                raise ValueError
        else:
            if (
                set(v)
                != {
                    "format_version",
                    "state",
                    "stage",
                    "reason",
                    "failure_type",
                    "sqlstate",
                }
                or v.get("state") != "refused_or_failed"
                or return_code == 0
                or v.get("stage") not in SQL_STAGES - {"complete"}
                or v.get("reason") not in SQL_REASONS
                or v.get("failure_type") not in FAILURE_TYPES
                or (
                    v.get("sqlstate") is not None
                    and (
                        not isinstance(v["sqlstate"], str)
                        or re.fullmatch(r"[0-9A-Z]{5}", v["sqlstate"]) is None
                    )
                )
            ):
                raise ValueError
        return v
    except (ValueError, TypeError, KeyError) as error:
        raise ProbeError("child_report_invalid") from None


def validate_host_report(raw):
    """Controller-side schema check; no permissive forwarding of remote output."""
    try:
        v = parse_json(raw)
        if (
            set(v) != HOST_KEYS
            or type(v["format_version"]) is not int
            or v["format_version"] != 2
        ):
            raise ValueError
        if v["stage"] not in HOST_STAGES or v["cleanup"] not in {
            "not_started",
            "absent",
            "removed",
            "foreign_refused",
            "unconfirmed",
        }:
            raise ValueError
        if v["cli_version"] is not None and (
            not isinstance(v["cli_version"], str)
            or re.fullmatch(r"[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}", v["cli_version"])
            is None
        ):
            raise ValueError
        if v["return_code"] is not None and (
            type(v["return_code"]) is not int or not -255 <= v["return_code"] <= 255
        ):
            raise ValueError
        if (
            v["provider_error"] is not None
            and v["provider_error"] not in PROVIDER_CODES
        ):
            raise ValueError
        if v["sqlstate"] is not None and (
            not isinstance(v["sqlstate"], str)
            or re.fullmatch(r"[0-9A-Z]{5}", v["sqlstate"]) is None
        ):
            raise ValueError
        if v["child_stage"] is not None and v["child_stage"] not in SQL_STAGES - {
            "complete"
        }:
            raise ValueError
        if v["child_reason"] is not None and v["child_reason"] not in SQL_REASONS:
            raise ValueError
        if v["state"] == "readonly_metadata_passed":
            if (
                v["stage"] != "complete"
                or v["cleanup"] not in {"absent", "removed"}
                or not valid_metadata(v["metadata"])
                or v["reason"] is not None
                or v["failure_type"] is not None
                or v["return_code"] != 0
                or any(
                    v[k] is not None
                    for k in (
                        "provider_error",
                        "child_stage",
                        "child_reason",
                        "sqlstate",
                    )
                )
            ):
                raise ValueError
        elif v["state"] == "refused_or_failed":
            if (
                v["reason"] not in REASONS
                or v["failure_type"] not in FAILURE_TYPES
                or v["metadata"] is not None
            ):
                raise ValueError
        else:
            raise ValueError
        return v
    except (ValueError, TypeError, KeyError) as error:
        raise ProbeError("child_report_invalid") from None


def window_outcome(report):
    """Normalize future window status from verified cleanup flags, never its old label."""
    attempts = report.get("resource_start_attempts")
    if (
        not isinstance(attempts, dict)
        or set(attempts) != {"rds", "ec2"}
        or any(type(v) is not bool for v in attempts.values())
    ):
        return "cleanup_pending_operator_attention"
    if not any(attempts.values()):
        return "blocked_before_starts"
    cleanup = report.get("cleanup", {})
    if not isinstance(cleanup, dict):
        return "cleanup_pending_operator_attention"
    if cleanup.get("pending") or any(
        attempts[k]
        and cleanup.get({"ec2": "host_stopped", "rds": "rds_stopped"}[k]) is not True
        for k in attempts
    ):
        return "cleanup_pending_operator_attention"
    probe = report.get("probe_report", report.get("metadata", {}))
    if (
        isinstance(probe, dict)
        and isinstance(report.get("remote_status"), dict)
        and report["remote_status"].get("status") == "Success"
        and probe.get("state") == "readonly_metadata_passed"
    ):
        return "phase_a_passed_and_stopped"
    return "probe_failed_resources_stopped"


def cleanup_container(docker, env, name, run_id):
    """Prove absence or label ownership; remove only immutable owned ID and verify absence."""
    try:
        present = run(
            [
                docker,
                "ps",
                "--all",
                "--filter",
                f"name=^/{name}$",
                "--format",
                "{{.ID}}",
            ],
            env=env,
            timeout=10,
        )
        if not present.strip():
            return "absent"
        owned = (
            run(
                [
                    docker,
                    "inspect",
                    "--format",
                    '{{.Id}} {{index .Config.Labels "clip-next06-run"}}',
                    name,
                ],
                env=env,
                timeout=10,
            )
            .decode()
            .strip()
            .split()
        )
        if (
            len(owned) != 2
            or owned[1] != run_id
            or re.fullmatch(r"[0-9a-f]{64}", owned[0]) is None
        ):
            return "foreign_refused"
        run([docker, "rm", "--force", owned[0]], env=env, timeout=10)
        remaining = run(
            [
                docker,
                "ps",
                "--all",
                "--filter",
                f"id={owned[0]}",
                "--format",
                "{{.ID}}",
            ],
            env=env,
            timeout=10,
        )
        return "removed" if not remaining.strip() else "unconfirmed"
    except (ProbeError, UnicodeError) as error:
        return "unconfirmed"


def main(argv=None):
    """Fixed approved mode, targets and read-only child; emit a single safe report."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--approved-readonly-inventory", action="store_true")
    args = parser.parse_args(argv)
    if not args.approved_readonly_inventory:
        print(json.dumps({"format_version": 2, "state": "explicit_approval_required"}))
        return 2
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/root"),
        "AWS_CONFIG_FILE": "/dev/null",
        "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
        "AWS_MAX_ATTEMPTS": "1",
        "AWS_PAGER": "",
        "AWS_CLI_AUTO_PROMPT": "off",
    }
    report = {
        "format_version": 2,
        "state": "refused_or_failed",
        "stage": "tools",
        "reason": None,
        "failure_type": None,
        "return_code": None,
        "provider_error": None,
        "child_stage": None,
        "child_reason": None,
        "sqlstate": None,
        "cli_version": None,
        "cleanup": "not_started",
        "metadata": None,
    }
    aws, docker = shutil.which("aws"), shutil.which("docker")
    run_id = uuid4().hex
    name = f"{CONTAINER}-{run_id}"
    launched = False
    try:
        if not aws or not docker:
            raise ProbeError("required_existing_tools_absent")
        report["stage"] = "cli_version"
        version = run([aws, "--version"], env=env, timeout=5, allow_nonzero=True)
        match = re.search(
            rb"\baws-cli/([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})\b",
            version.stdout + b" " + version.stderr,
        )
        if version.returncode or not match:
            raise ProbeError("cli_version_unrecognized", return_code=version.returncode)
        report["cli_version"] = match.group(1).decode("ascii")
        if report["cli_version"].split(".", 1)[0] != "2":
            raise ProbeError("aws_cli_v2_required")
        base = [
            aws,
            "--region",
            "ap-south-1",
            "--no-cli-pager",
            "--cli-connect-timeout",
            "5",
            "--cli-read-timeout",
            "10",
        ]
        report["stage"] = "host_identity"
        identity = parse_json(
            run(
                base + ["sts", "get-caller-identity", "--output", "json"],
                env=env,
                timeout=20,
            )
        )
        if (
            identity.get("Account") != ACCOUNT
            or identity.get("Arn")
            != f"arn:aws:sts::{ACCOUNT}:assumed-role/clip-shared-test-ecs-instance/{INSTANCE}"
        ):
            raise ProbeError("host_role_mismatch")
        report["stage"] = "cached_image"
        run(
            [docker, "image", "inspect", "--format", "{{.Id}}", IMAGE],
            env=env,
            timeout=10,
        )
        report["stage"] = "container_name"
        present = run(
            [
                docker,
                "ps",
                "--all",
                "--filter",
                f"name=^/{name}$",
                "--format",
                "{{.ID}}",
            ],
            env=env,
            timeout=10,
        )
        if present.strip():
            raise ProbeError("container_name_already_exists")
        report["stage"] = "connection_secret"
        parameter = parse_json(
            run(
                base
                + [
                    "ssm",
                    "get-parameter",
                    "--name",
                    PARAMETER,
                    "--with-decryption",
                    "--output",
                    "json",
                ],
                env=env,
                timeout=20,
            )
        )
        secret = parameter["Parameter"]["Value"].encode()
        if not 0 < len(secret) <= 16384:
            raise ProbeError("connection_secret_bound")
        report["stage"] = "sql_child"
        launched = True
        child = run(
            [
                docker,
                "run",
                "--pull=never",
                "--rm",
                "--interactive",
                "--name",
                name,
                "--label",
                f"clip-next06-run={run_id}",
                "--network",
                "host",
                "--entrypoint",
                "python",
                IMAGE,
                "-c",
                SQL_PROBE,
            ],
            env=env,
            timeout=60,
            content=secret,
            allow_nonzero=True,
        )
        value = validate_child_report(child.stdout, child.returncode)
        report["return_code"] = child.returncode
        if value["state"] != "readonly_metadata_passed":
            report.update(
                reason="child_failed",
                failure_type=value["failure_type"],
                child_stage=value["stage"],
                child_reason=value["reason"],
                sqlstate=value["sqlstate"],
            )
        else:
            report.update(
                state="readonly_metadata_passed",
                stage="complete",
                metadata=value["metadata"],
            )
    except Exception as error:
        report["state"] = "refused_or_failed"
        report["failure_type"] = (
            type(error).__name__
            if type(error).__name__ in FAILURE_TYPES
            else "OtherError"
        )
        if isinstance(error, ProbeError):
            report.update(
                reason=error.reason,
                return_code=error.return_code,
                provider_error=error.provider_error,
            )
        else:
            report["reason"] = "unexpected_error"
    finally:
        if launched:
            report["cleanup"] = cleanup_container(docker, env, name, run_id)
            if (
                report["cleanup"] not in {"absent", "removed"}
                and report["state"] == "readonly_metadata_passed"
            ):
                report.update(
                    state="refused_or_failed",
                    stage="cleanup",
                    reason="cleanup_not_confirmed",
                    failure_type="ProbeError",
                    metadata=None,
                )
        # Revalidate our own envelope before it can reach SSM or a future caller.
        safe = validate_host_report(json.dumps(report))
        print(json.dumps(safe))
    return 0 if report["state"] == "readonly_metadata_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
