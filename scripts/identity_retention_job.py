"""Bounded host launcher for reviewed Identity cleanup; dry-run, no timer by default.

Install alongside identity_cleanup.py only on the approved private ECS host.
The existing task role reads only its fixed Identity DSN inside the container.
No credentials cross to the host, command line, output or job configuration.
Live --apply and timer installation require separate exact operator approval.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

CLEANUP_SHA = "99fb7fafc385a9292e5986d1100bee64de63c985951def181083a7ed75452304"
DOCKER = ["docker", "--host", "unix:///var/run/docker.sock"]
CATEGORIES = {
    "otp_challenges",
    "sessions",
    "temporary_credentials",
    "microsoft_login_attempts",
    "auth_source_events",
    "otp_send_reservations",
    "otp_verification_windows",
    "password_login_windows",
    "contacts",
    "notification_destinations",
    "profiles",
}


def command(args: list[str], payload: str | None = None) -> str:
    """Use only the local daemon; capture and never print raw client output."""
    result = subprocess.run(
        DOCKER + args,
        input=payload,
        capture_output=True,
        text=True,
        timeout=105,
        env={key: os.environ[key] for key in ("HOME", "PATH")},
    )
    if result.returncode:
        raise ValueError("Retention client failed")
    return result.stdout


def run_job(
    image: str, revision: int, deadline: datetime, *, apply: bool
) -> dict[str, Any]:
    """Refuse expired/image/role drift; run the unchanged bounded CLI once.

    The child has a90-second process alarm. Cleanup commits per candidate; failure
    never retries or claims atomicity. Only safe category counts leave the child.
    The host service/timer owns serialization; this function never installs one.
    """
    if (
        deadline.tzinfo is None
        or datetime.now(timezone.utc) >= deadline
        or revision < 1
    ):
        raise ValueError("Expired or invalid job scope")
    if not re.fullmatch(
        r"335523638354\.dkr\.ecr\.ap-south-1\.amazonaws\.com/clip-shared-test-api@sha256:[0-9a-f]{64}",
        image,
    ):
        raise ValueError("Invalid job image")
    source = Path(__file__).with_name("identity_cleanup.py").read_bytes()
    if hashlib.sha256(source).hexdigest() != CLEANUP_SHA:
        raise ValueError("Cleanup source drift")
    ids = command(
        [
            "ps",
            "--filter",
            "label=com.amazonaws.ecs.task-definition-family=clip-test-api-ap-south-1-pd16",
            "--filter",
            f"label=com.amazonaws.ecs.task-definition-version={revision}",
            "--format",
            "{{.ID}}",
        ]
    ).split()
    if len(ids) != 1 or re.fullmatch(r"[0-9a-f]{12,64}", ids[0]) is None:
        raise ValueError("Expected exactly one reviewed container")
    if command(["inspect", "--format", "{{.Config.Image}}", ids[0]]).strip() != image:
        raise ValueError("Running image drift")
    args = [
        "identity_cleanup.py",
        "--expected-database",
        "clip_test",
        "--batch-size",
        "100",
    ]
    if apply:
        args.append("--apply")
    payload = (
        """import sys,os,json,logging,signal
logging.disable(logging.CRITICAL)
signal.alarm(90)
sys.path.insert(0,"/app/apps/api")
try:
 import boto3
 from botocore.config import Config
 from pydantic import SecretStr
 from psycopg.conninfo import conninfo_to_dict
 from app.domains.identity.runtime_database import connection_factory
 from app.domains.identity.database_setup import LOGGING
 row=boto3.client("ssm",region_name="ap-south-1",config=Config(ignore_configured_endpoint_urls=True,connect_timeout=3,read_timeout=5,retries={"total_max_attempts":1})).get_parameter(Name="/clip/test/identity/database-url",WithDecryption=True)["Parameter"]
 if row["Type"]!="SecureString" or row["Version"]!=1:raise ValueError()
 raw=row["Value"];cfg=conninfo_to_dict(raw)
 if cfg.get("host")!="clip-shared-test-postgres.cnsu8kgiimug.ap-south-1.rds.amazonaws.com":raise ValueError()
 connect=connection_factory(SecretStr(raw),"test")
 with connect() as c:
  if c.execute("SELECT current_database(),current_user,session_user").fetchone()!=("clip_test","clip_test_identity_app","clip_test_identity_app"):raise ValueError()
  for name,value in LOGGING.items():
   if c.execute("SELECT current_setting(%s)",(name,)).fetchone()!=(value,):raise ValueError()
 os.environ["CLIP_IDENTITY_DATABASE_URL"]=raw
 del row,raw,cfg
"""
        + f" sys.argv={args!r}\n exec(compile({source.decode()!r},'identity_cleanup.py','exec'),{{'__name__':'__main__','__file__':'/app/scripts/identity_cleanup.py'}})\n"
        + """except Exception:
 print('{"failed":true}')
 sys.exit(1)
"""
    )
    result: dict[str, Any] = json.loads(
        command(["exec", "-i", ids[0], "python", "-"], payload)
    )
    if set(result) != {"dry_run", "counts"} or result["dry_run"] is not (not apply):
        raise ValueError("Unexpected cleanup result")
    counts = result["counts"]
    if (
        not isinstance(counts, dict)
        or set(counts) != CATEGORIES
        or any(
            type(value) is not int or value < 0 or value > 100
            for value in counts.values()
        )
    ):
        raise ValueError("Invalid bounded cleanup counts")
    return result


def main() -> int:
    """Print only safe counts or a fixed failure; flags never install scheduling."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--revision", required=True, type=int)
    parser.add_argument("--deadline-utc", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = run_job(
            args.image,
            args.revision,
            datetime.fromisoformat(args.deadline_utc),
            apply=args.apply,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("Identity retention job failed; inspect target and reviewed scope")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
