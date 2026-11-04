"""Read-only binding checks for the explicitly pinned existing-host pool.

This proves deployment identity/health, not SQL correctness or capacity. The
separate authenticated smoke must pass before pilot approval. No credential
values or certificate private keys are read by this check.
"""

import re
from typing import Any

KEYS = {
    "kind",
    "endpoint",
    "service_arn",
    "task_definition_arn",
    "image_uri",
    "host_instance_id",
}


def validate_pool(value: Any, account: str, region: str) -> None:
    """Refuse ambiguous service, host, image or endpoint declarations."""
    prefix = f"arn:aws:ecs:{region}:{account}:"
    if (
        not isinstance(value, dict)
        or set(value) != KEYS
        or value["kind"] != "pgbouncer"
        or not all(isinstance(item, str) for item in value.values())
        or not re.fullmatch(
            r"10\.64\.1\.(?:[1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])",
            value["endpoint"],
        )
        or not re.fullmatch(r"i-[0-9a-f]{17}", value["host_instance_id"])
        or value["service_arn"]
        != prefix + "service/clip-shared-test/clip-test-pgbouncer-ap-south-1-exp03"
        or not re.fullmatch(
            re.escape(prefix)
            + r"task-definition/clip-test-pgbouncer-ap-south-1-exp03:[1-9][0-9]*",
            value["task_definition_arn"],
        )
        or not re.fullmatch(
            re.escape(
                f"{account}.dkr.ecr.{region}.amazonaws.com/clip-shared-test-api@sha256:"
            )
            + r"[0-9a-f]{64}",
            value["image_uri"],
        )
    ):
        raise ValueError("invalid_pgbouncer_binding")


def verify_pool(session: Any, pool: dict[str, Any], cluster: str) -> None:
    """Require one separate healthy task on the exact existing private host."""
    ecs = session.client("ecs")
    services = ecs.describe_services(
        cluster=cluster, services=[pool["service_arn"]]
    ).get("services", [])
    if len(services) != 1:
        raise ValueError("pgbouncer_service_missing")
    service = services[0]
    if any(
        (
            service.get("taskDefinition") != pool["task_definition_arn"],
            service.get("desiredCount") != 1,
            service.get("runningCount") != 1,
            service.get("pendingCount") != 0,
        )
    ):
        raise ValueError("pgbouncer_service_not_stable")
    task_definition = ecs.describe_task_definition(
        taskDefinition=pool["task_definition_arn"]
    )["taskDefinition"]
    containers = task_definition.get("containerDefinitions", [])
    if len(containers) != 1:
        raise ValueError("pgbouncer_container_shape")
    container = containers[0]
    expected_secrets = {
        "POOL_IDENTITY_DSN": "identity/database-url",
        "POOL_MARKETPLACE_DSN": "listings-database-url",
        "POOL_CONVERSATIONS_DSN": "conversations/database-url",
        "POOL_TLS_BUNDLE": "pgbouncer/tls",
    }
    account, region = (
        pool["service_arn"].split(":")[4],
        pool["service_arn"].split(":")[3],
    )
    secret_prefix = f"arn:aws:ssm:{region}:{account}:parameter/clip/test/"
    if (
        container.get("name") != "pgbouncer"
        or container.get("image") != pool["image_uri"]
        or task_definition.get("networkMode") != "bridge"
        or task_definition.get("cpu") != "1024"
        or task_definition.get("memory") != "256"
        or not container.get("readonlyRootFilesystem")
        or container.get("portMappings")
        != [{"containerPort": 6432, "hostPort": 6432, "protocol": "tcp"}]
        or container.get("command")
        or container.get("entryPoint")
        or container.get("environment")
        != [{"name": "POOL_ENDPOINT", "value": pool["endpoint"]}]
        or {row["name"]: row["valueFrom"] for row in container.get("secrets", [])}
        != {key: secret_prefix + path for key, path in expected_secrets.items()}
    ):
        raise ValueError("pgbouncer_definition_mismatch")
    arns = ecs.list_tasks(
        cluster=cluster, serviceName=pool["service_arn"], desiredStatus="RUNNING"
    ).get("taskArns", [])
    tasks = (
        ecs.describe_tasks(cluster=cluster, tasks=arns).get("tasks", []) if arns else []
    )
    if (
        len(tasks) != 1
        or tasks[0].get("healthStatus") != "HEALTHY"
        or tasks[0].get("taskDefinitionArn") != pool["task_definition_arn"]
    ):
        raise ValueError("pgbouncer_task_not_healthy")
    instances = ecs.describe_container_instances(
        cluster=cluster, containerInstances=[tasks[0]["containerInstanceArn"]]
    )["containerInstances"]
    if (
        len(instances) != 1
        or instances[0].get("ec2InstanceId") != pool["host_instance_id"]
    ):
        raise ValueError("pgbouncer_host_mismatch")
    rows = session.client("ec2").describe_instances(
        InstanceIds=[pool["host_instance_id"]]
    )["Reservations"]
    hosts = [host for row in rows for host in row.get("Instances", [])]
    if (
        len(hosts) != 1
        or hosts[0].get("PrivateIpAddress") != pool["endpoint"]
        or hosts[0].get("State", {}).get("Name") != "running"
    ):
        raise ValueError("pgbouncer_endpoint_mismatch")
