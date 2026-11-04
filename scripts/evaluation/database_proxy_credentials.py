"""Read-only binding of three existing role credentials for RDS Proxy.

Plans contain references/versions only. terraform_passwords returns values in
memory for ephemeral Terraform variables consumed by secret_string_wo; it never
creates resources, changes credentials or authorizes a Terraform apply.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit, parse_qs

from data.generators.reference_login import sdk_profile_session

ACCOUNT = "335523638354"
REGION = "ap-south-1"
DATABASE = "clip-shared-test-postgres"
DATABASE_NAME = "clip_next06_reference"
SOURCES = {
    "identity": ("/clip/test/identity/database-url", "clip_test_identity_app"),
    "marketplace": ("/clip/test/listings-database-url", "clip_test_marketplace_app"),
    "conversations": (
        "/clip/test/conversations/database-url",
        "clip_test_conversations_app",
    ),
}


def write_new(path: Path, value: dict[str, Any]) -> None:
    """Exclusive private output: do not overwrite earlier plans or receipts."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2) + "\n")


def validate_credentials(value: str, role: str, endpoint: str) -> dict[str, str]:
    """Decode only the intended role/database and strictly verified source TLS."""
    try:
        uri = urlsplit(value)
        if (
            uri.scheme not in {"postgres", "postgresql"}
            or uri.hostname != endpoint
            or uri.port not in (None, 5432)
            or unquote(uri.path.removeprefix("/")) != DATABASE_NAME
            or unquote(uri.username or "") != role
            or not uri.password
            or uri.fragment
            or parse_qs(uri.query, keep_blank_values=True, strict_parsing=True)
            != {"sslmode": ["verify-full"], "sslrootcert": ["system"]}
        ):
            raise ValueError
        return {"username": role, "password": unquote(uri.password)}
    except Exception:
        raise ValueError("source_credential_binding_invalid") from None


def identity(session: Any) -> str:
    """Pin the already approved operator/account before any service operation."""
    result = session.client("sts").get_caller_identity()
    if (
        result.get("Account") != ACCOUNT
        or result.get("Arn") != f"arn:aws:iam::{ACCOUNT}:user/surajs2"
    ):
        raise ValueError("proxy_operator_mismatch")
    return result["Arn"]


def prepare(session: Any, expires: datetime) -> dict[str, Any]:
    """Inventory exact source versions and destination names without decryption."""
    caller = identity(session)
    now = datetime.now(UTC)
    if expires.tzinfo is None or not now < expires <= now + timedelta(hours=24):
        raise ValueError("bounded_future_expiry_required")
    database = session.client("rds").describe_db_instances(
        DBInstanceIdentifier=DATABASE
    )["DBInstances"][0]
    if (
        database.get("DBInstanceStatus") != "available"
        or database.get("PubliclyAccessible") is not False
    ):
        raise ValueError("source_database_not_private_available")
    entries = []
    ssm, secrets = session.client("ssm"), session.client("secretsmanager")
    for name, (parameter, role) in SOURCES.items():
        source = ssm.get_parameter(Name=parameter, WithDecryption=False)["Parameter"]
        if source.get("Type") != "SecureString":
            raise ValueError("source_parameter_not_secure")
        destination = "/clip/test/rds-proxy/" + name
        try:
            existing = secrets.describe_secret(SecretId=destination)
            if existing.get("DeletedDate"):
                raise ValueError("destination_pending_deletion")
            arn = existing["ARN"]
        except secrets.exceptions.ResourceNotFoundException:
            arn = None
        entries.append(
            {
                "key": name,
                "parameter": parameter,
                "parameter_version": source["Version"],
                "role": role,
                "destination": destination,
                "existing_arn": arn,
            }
        )
    return {
        "format_version": 1,
        "purpose": "three-proxy-credential-sources",
        "account_id": ACCOUNT,
        "region": REGION,
        "caller_arn": caller,
        "database_id": DATABASE,
        "database_name": DATABASE_NAME,
        "source_endpoint": database["Endpoint"]["Address"],
        "expires_at": expires.isoformat(),
        "entries": entries,
        "changes_passwords_or_grants": False,
        "creates_proxy_or_routes_traffic": False,
    }


def terraform_passwords(
    session: Any, raw: bytes, expected_sha256: str
) -> dict[str, str]:
    """Return ephemeral inputs privately after rechecking every source binding.

    This function is read-only. Its return value must be passed directly to
    TF_VAR_database_proxy_passwords in the Terraform child environment, never
    written to a var file or printed. Actual apply requires its own exact saved
    plan approval; possessing these values authorizes no cloud mutation.
    """
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("source_plan_digest_mismatch")
    plan = json.loads(raw)
    current = prepare(session, datetime.fromisoformat(plan["expires_at"]))
    if current != plan:
        raise ValueError("credential_source_plan_drift")
    ssm = session.client("ssm")
    passwords = {}
    for entry in plan["entries"]:
        source = ssm.get_parameter(Name=entry["parameter"], WithDecryption=True)[
            "Parameter"
        ]
        if (
            source.get("Version") != entry["parameter_version"]
            or source.get("Type") != "SecureString"
        ):
            raise ValueError("source_parameter_changed")
        credentials = validate_credentials(
            source["Value"], entry["role"], plan["source_endpoint"]
        )
        passwords[entry["key"]] = credentials["password"]
    return passwords


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.output.exists()
        or args.output.is_symlink()
        or not args.output.parent.is_dir()
    ):
        parser.error("choose a new output file in an existing directory")
    try:
        session = sdk_profile_session(profile_name="surajs2", region_name=REGION)
        result = prepare(session, datetime.fromisoformat(args.expires_at))
        write_new(args.output, result)
    except Exception:
        # Provider/parser exceptions may contain secret request material.
        print(
            "Proxy credential operation failed; inspect safe metadata and prepare again. No source secret or database role was changed."
        )
        return 1
    print(
        "Read-only proxy credential preparation completed; private result: "
        + str(args.output)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
