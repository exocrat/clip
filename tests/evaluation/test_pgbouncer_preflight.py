"""Pool identity and telemetry failures must block or remain visible."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from types import SimpleNamespace

import pytest

from scripts.evaluation.k6.pgbouncer_preflight import validate_pool, verify_pool
from scripts.evaluation.k6.pgbouncer_capture import collect, safe_counter_event
from scripts.evaluation.k6.real_target_preflight import _verify_database_proxy

PREFIX = "arn:aws:ecs:ap-south-1:335523638354:"
POOL = {
    "kind": "pgbouncer",
    "endpoint": "10.64.1.83",
    "service_arn": PREFIX
    + "service/clip-shared-test/clip-test-pgbouncer-ap-south-1-exp03",
    "task_definition_arn": PREFIX
    + "task-definition/clip-test-pgbouncer-ap-south-1-exp03:1",
    "image_uri": "335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:"
    + "1" * 64,
    "host_instance_id": "i-0123456789abcdef0",
}


def session():
    """Mutable fake AWS inventory lets tests fail each independent binding."""
    service = {
        "taskDefinition": POOL["task_definition_arn"],
        "desiredCount": 1,
        "runningCount": 1,
        "pendingCount": 0,
    }
    container = {
        "name": "pgbouncer",
        "image": POOL["image_uri"],
        "readonlyRootFilesystem": True,
        "environment": [{"name": "POOL_ENDPOINT", "value": POOL["endpoint"]}],
        "portMappings": [{"containerPort": 6432, "hostPort": 6432, "protocol": "tcp"}],
        "secrets": [
            {
                "name": name,
                "valueFrom": "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/"
                + path,
            }
            for name, path in {
                "POOL_IDENTITY_DSN": "identity/database-url",
                "POOL_MARKETPLACE_DSN": "listings-database-url",
                "POOL_CONVERSATIONS_DSN": "conversations/database-url",
                "POOL_TLS_BUNDLE": "pgbouncer/tls",
            }.items()
        ],
    }
    task = {
        "healthStatus": "HEALTHY",
        "taskDefinitionArn": POOL["task_definition_arn"],
        "containerInstanceArn": "container",
    }
    host = {"PrivateIpAddress": POOL["endpoint"], "State": {"Name": "running"}}
    definition = {
        "containerDefinitions": [container],
        "cpu": "1024",
        "memory": "256",
        "networkMode": "bridge",
    }
    ecs = SimpleNamespace(
        describe_services=lambda **_: {"services": [service]},
        describe_task_definition=lambda **_: {"taskDefinition": definition},
        list_tasks=lambda **_: {"taskArns": ["task"]},
        describe_tasks=lambda **_: {"tasks": [task]},
        describe_container_instances=lambda **_: {
            "containerInstances": [{"ec2InstanceId": POOL["host_instance_id"]}]
        },
    )
    ec2 = SimpleNamespace(
        describe_instances=lambda **_: {"Reservations": [{"Instances": [host]}]}
    )
    return SimpleNamespace(
        client=lambda name: {"ecs": ecs, "ec2": ec2}[name],
        container=container,
        host=host,
        task=task,
        service=service,
    )


def test_exact_pool_and_both_runtime_overrides():
    validate_pool(POOL, "335523638354", "ap-south-1")
    verify_pool(session(), POOL, PREFIX + "cluster/clip-shared-test")
    env = {"CLIP_DATABASE_PROXY_ENDPOINT": POOL["endpoint"]}
    _verify_database_proxy(None, POOL, {}, env, env)
    with pytest.raises(ValueError, match="runtime_database_proxy"):
        _verify_database_proxy(None, POOL, {}, env, {})


@pytest.mark.parametrize(
    "field,value",
    [
        ("endpoint", "127.0.0.1"),
        ("kind", "anything"),
        ("image_uri", "mutable:latest"),
        ("service_arn", PREFIX + "service/clip-shared-test/api"),
    ],
)
def test_wrong_plan_bindings_rejected(field, value):
    bad = deepcopy(POOL)
    bad[field] = value
    with pytest.raises(ValueError):
        validate_pool(bad, "335523638354", "ap-south-1")


@pytest.mark.parametrize("mutation", ["host", "image", "health", "secret", "capacity"])
def test_runtime_drift_refused(mutation):
    fake = session()
    if mutation == "host":
        fake.host["PrivateIpAddress"] = "10.64.1.7"
    elif mutation == "image":
        fake.container["image"] = "changed"
    elif mutation == "health":
        fake.task["healthStatus"] = "UNHEALTHY"
    elif mutation == "secret":
        fake.container["secrets"].pop()
    else:
        fake.service["runningCount"] = 0
    with pytest.raises(ValueError):
        verify_pool(fake, POOL, PREFIX + "cluster/clip-shared-test")


def test_telemetry_retains_failure_and_refuses_arbitrary_content():
    now = datetime.now(timezone.utc)
    message = json.dumps(
        {
            "kind": "clip_pool_stats_unavailable",
            "at_unix_ms": int(now.timestamp() * 1000),
        }
    )
    logs = SimpleNamespace(
        filter_log_events=lambda **_: {
            "events": [
                {
                    "eventId": "1",
                    "timestamp": int(now.timestamp() * 1000),
                    "message": message,
                }
            ]
        }
    )
    result = collect(logs, now - timedelta(seconds=5), now)
    assert result["state"] == "no_counter_data" and len(result["events"]) == 1
    with pytest.raises(ValueError):
        safe_counter_event(
            json.dumps(
                {
                    "kind": "clip_pool_stats",
                    "at_unix_ms": 1,
                    "stats": [
                        {
                            "database": "clip_next06_reference",
                            "secret": "not-counter-data",
                        }
                    ],
                    "pools": [],
                }
            )
        )
