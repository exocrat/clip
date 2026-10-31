"""NEXT-06 Step3 metadata inspection; no secret reads, starts or mutations.

An explicit approval flag is an execution guard, not permission by itself. The
operator must approve the exact fixed account/profile/read scope before running.
Only selected nonsecret configuration leaves this module; raw SDK responses do
not enter receipts. Import/help makes no AWS calls.
"""

import argparse
from datetime import UTC, datetime
import json
import os

from data.generators.reference_login import sdk_session

ACCOUNT = "335523638354"
PROFILE = "mohitmahapa1"
REGION = "ap-south-1"
PARAMETERS = (
    "/clip/test/identity/authentication-keys",
    "/clip/test/identity/database-url",
    "/clip/test/identity/email-delivery",
    "/clip/test/listings-database-url",
    "/clip/test/conversations/database-url",
)
FLAGS = {
    "CLIP_ENVIRONMENT",
    "CLIP_STORAGE_PROVIDER",
    "CLIP_IDENTITY_RUNTIME_ENABLED",
    "CLIP_HYBRID_SEARCH_ENABLED",
    "CLIP_HYBRID_WORKER_ENABLED",
}


def inspect(session):
    """Read <=10 bounded SDK operations after exact non-root identity validation.

    Reads STS, one ECS service/task definition, one host and RDS instance, plus
    one exact-name SSM metadata page per approved parameter. Refuse pagination
    rather than widening the window. No parameter values or arbitrary URLs.
    """
    from botocore.config import Config

    config = Config(
        connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 1}
    )
    clients = {}
    calls = 0

    def call(service, operation, **kwargs):
        nonlocal calls
        if calls >= 10:
            raise ValueError("inspection_call_limit")
        if service not in clients:
            clients[service] = session.client(service, config=config)
        calls += 1
        return getattr(clients[service], operation)(**kwargs)

    try:
        identity = call("sts", "get_caller_identity")
        if identity.get("Account") != ACCOUNT or identity.get("Arn") != (
            f"arn:aws:iam::{ACCOUNT}:user/{PROFILE}"
        ):
            raise ValueError("inspection_identity_mismatch")
        service = call(
            "ecs",
            "describe_services",
            cluster="clip-shared-test",
            services=["clip-test-api-ap-south-1-pd16"],
        )
        if service.get("failures") or len(service.get("services", [])) != 1:
            raise ValueError("inspection_service_missing")
        service = service["services"][0]
        task_arn = service["taskDefinition"]
        if not task_arn.startswith(
            f"arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/clip-test-api-ap-south-1-pd16:"
        ):
            raise ValueError("inspection_task_binding_changed")
        task = call("ecs", "describe_task_definition", taskDefinition=task_arn)[
            "taskDefinition"
        ]
        host = call("ec2", "describe_instances", InstanceIds=["i-086045c48487471de"])[
            "Reservations"
        ]
        hosts = [i for reservation in host for i in reservation["Instances"]]
        db = call(
            "rds",
            "describe_db_instances",
            DBInstanceIdentifier="clip-shared-test-postgres",
        )["DBInstances"]
        parameters = []
        for name in PARAMETERS:
            response = call(
                "ssm",
                "describe_parameters",
                ParameterFilters=[
                    {"Key": "Name", "Option": "Equals", "Values": [name]}
                ],
                MaxResults=10,
            )
            if response.get("NextToken"):
                raise ValueError("inspection_unexpected_pagination")
            rows = response.get("Parameters", [])
            if any(row.get("Name") != name for row in rows) or len(rows) > 1:
                raise ValueError("inspection_parameter_binding_changed")
            parameters.append(
                {
                    "name": name,
                    "present": bool(rows),
                    "type": rows[0]["Type"] if rows else None,
                }
            )
        return {
            "task": "NEXT-06 Step3",
            "state": "metadata_inspected",
            "recorded_utc": datetime.now(UTC).isoformat(),
            "account": ACCOUNT,
            "profile": PROFILE,
            "region": REGION,
            "api_calls": calls,
            "secret_values_read": 0,
            "mutations": 0,
            "service": {
                key: service.get(key)
                for key in (
                    "taskDefinition",
                    "desiredCount",
                    "runningCount",
                    "pendingCount",
                )
            },
            "task_configuration": {
                "cpu": task.get("cpu"),
                "memory": task.get("memory"),
                "containers": [
                    {
                        "name": c["name"],
                        "image": c["image"],
                        "flags": {
                            v["name"]: v["value"]
                            for v in c.get("environment", [])
                            if v["name"] in FLAGS
                            and v["value"] in {"true", "false", "test", "local", "s3"}
                        },
                        "secret_setting_names": sorted(
                            v["name"] for v in c.get("secrets", [])
                        ),
                    }
                    for c in task["containerDefinitions"]
                ],
            },
            "hosts": [
                {
                    "id": i["InstanceId"],
                    "type": i["InstanceType"],
                    "state": i["State"]["Name"],
                }
                for i in hosts
            ],
            "databases": [
                {
                    "id": d["DBInstanceIdentifier"],
                    "state": d["DBInstanceStatus"],
                    "engine": d["EngineVersion"],
                    "public": d["PubliclyAccessible"],
                }
                for d in db
            ],
            "parameter_metadata": parameters,
        }
    finally:
        for client in clients.values():
            client.close()


def main(argv=None):
    """Execute approved fixed metadata reads, containing private SDK failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--approved-cloud-inspection", action="store_true", required=True
    )
    parser.parse_args(argv)
    if any(k.startswith(("AWS_", "PG", "CLIP_")) for k in os.environ):
        parser.error("ambient target overrides refused")
    try:
        result = inspect(sdk_session(PROFILE, REGION))
    except Exception:
        print(
            json.dumps(
                {"state": "inspection_failed", "details": "private failure suppressed"}
            )
        )
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
