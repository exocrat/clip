"""Read-only AWS and HTTPS preflight for one bounded experiment target.

This command is read-only: it never sends workload traffic, changes AWS
resources, or authorizes a measurement. With an explicit environment-variable
name it can check one supplied session against the planned regular test-user
ID, after completing the target checks; it never prints the session value.
Data identity and source provenance still need their separately reviewed
evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import ssl
from typing import Any, cast

from scripts.evaluation.k6.pgbouncer_preflight import validate_pool, verify_pool
from scripts.evaluation.k6.lambda_concurrency import (
    validate_binding,
    verify as verify_concurrency,
)
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPSHandler,
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)
from urllib.parse import unquote, urlsplit

PLAN_KEYS = {
    "format_version",
    "purpose",
    "run_id",
    "configuration",
    "aws_profile",
    "account_id",
    "region",
    "expected_caller_arn",
    "expected_user_id",
    "api_origin",
    "resources",
    "routing",
    "revisions",
    "evidence_path",
    "execution_permitted",
    "nfr_accepted",
}
RESOURCE_KEYS = {
    "load_balancer_arn",
    "listener_arn",
    "listener_rule_arn",
    "certificate_arn",
    "ecs_cluster_arn",
    "ecs_service_arn",
    "ecs_task_definition_arn",
    "ecs_target_group_arn",
    "lambda_function_arn",
    "lambda_target_group_arn",
    "database_instance_id",
    "database_name",
    "database_parameter_arn",
}
ROUTING_KEYS = {
    "lambda_weight_percent",
    "methods",
    "path_regexes",
    "stickiness_enabled",
}
REVISION_KEYS = {
    "ecs_image_uri",
    "lambda_image_uri",
    "application_revision",
    "dataset_fingerprint",
    "model_revision",
}
ARN_RESOURCE_KEYS = {
    "load_balancer_arn",
    "listener_arn",
    "listener_rule_arn",
    "certificate_arn",
    "ecs_cluster_arn",
    "ecs_service_arn",
    "ecs_task_definition_arn",
    "ecs_target_group_arn",
    "lambda_function_arn",
    "lambda_target_group_arn",
    "database_parameter_arn",
}
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}\Z")
AWS_ID = re.compile(r"[0-9]{12}\Z")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
APPROVED_PATHS = ["^/api/listings$", "^/api/listings/[0-9A-Fa-f-]{36}$"]
SESSION_COOKIE = re.compile(r"__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}\Z")
UUID4 = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)


def _exact_object(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(code)
    return value


def _verify_database_proxy(
    rds: Any,
    proxy: dict[str, Any] | None,
    database: dict[str, Any],
    ecs_environment: dict[str, Any],
    lambda_environment: dict[str, Any] | None,
) -> None:
    """Bind both runtime overrides to one healthy proxy and its exact source DB.

    Old/direct plans refuse an unrecorded override. A healthy proxy alone is not
    sufficient: its target, TLS and bounded backend policy must also match.
    """
    expected = proxy["endpoint"] if proxy is not None else None
    for environment in (ecs_environment, lambda_environment):
        if (
            environment is not None
            and environment.get("CLIP_DATABASE_PROXY_ENDPOINT") != expected
        ):
            raise ValueError("runtime_database_proxy_mismatch")
    if proxy is None or proxy.get("kind") == "pgbouncer":
        return
    rows = rds.describe_db_proxies(DBProxyName=proxy["name"]).get("DBProxies", [])
    if len(rows) != 1 or any(
        (
            rows[0].get("DBProxyArn") != proxy["arn"],
            rows[0].get("Endpoint") != proxy["endpoint"],
            rows[0].get("Status") != "available",
            rows[0].get("EngineFamily") != "POSTGRESQL",
            rows[0].get("RequireTLS") is not True,
            rows[0].get("DebugLogging") is not False,
            rows[0].get("IdleClientTimeout") != 300,
        )
    ):
        raise ValueError("database_proxy_state_mismatch")
    groups = rds.describe_db_proxy_target_groups(DBProxyName=proxy["name"]).get(
        "TargetGroups", []
    )
    expected_pool = {
        "ConnectionBorrowTimeout": 1,
        "MaxConnectionsPercent": 75,
        "MaxIdleConnectionsPercent": 50,
        "InitQuery": "SET statement_timeout='5s'; SET lock_timeout='1s'; SET idle_in_transaction_session_timeout='5s'",
    }
    if (
        len(groups) != 1
        or groups[0].get("TargetGroupName") != "default"
        or any(
            groups[0].get("ConnectionPoolConfig", {}).get(key) != value
            for key, value in expected_pool.items()
        )
    ):
        raise ValueError("database_proxy_pool_mismatch")
    targets = rds.describe_db_proxy_targets(
        DBProxyName=proxy["name"], TargetGroupName="default"
    ).get("Targets", [])
    if len(targets) != 1 or any(
        (
            targets[0].get("Type") != "RDS_INSTANCE",
            targets[0].get("RdsResourceId") != database.get("DbiResourceId"),
            not database.get("DbiResourceId"),
            targets[0].get("Endpoint") != database.get("Endpoint", {}).get("Address"),
            targets[0].get("Port") != database.get("Endpoint", {}).get("Port"),
            targets[0].get("TargetHealth", {}).get("State") != "AVAILABLE",
        )
    ):
        raise ValueError("database_proxy_target_mismatch")


def validate_plan(plan: Any) -> dict[str, Any]:
    """Check complete plan shape and A/B routing semantics before AWS access."""
    _exact_object(plan, PLAN_KEYS, "invalid_plan_shape")
    if (
        type(plan["format_version"]) is not int
        or plan["format_version"] not in (1, 2, 3)
        or plan["purpose"] != "clip-read-experiment-target"
        or plan["execution_permitted"] is not False
        or plan["nfr_accepted"] is not False
        or not isinstance(plan["run_id"], str)
        or not RUN_ID.fullmatch(plan["run_id"])
        or plan["configuration"] not in {"A", "B"}
        or not isinstance(plan["aws_profile"], str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", plan["aws_profile"])
        or not isinstance(plan["account_id"], str)
        or not AWS_ID.fullmatch(plan["account_id"])
        or not isinstance(plan["region"], str)
        or not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", plan["region"])
    ):
        raise ValueError("invalid_plan_values")
    origin = urlsplit(plan["api_origin"] if isinstance(plan["api_origin"], str) else "")
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.username
        or origin.password
        or origin.path
        or origin.query
        or origin.fragment
        or origin.port not in (None, 443)
    ):
        raise ValueError("https_origin_required")
    resources = _exact_object(
        plan["resources"],
        RESOURCE_KEYS
        | ({"database_proxy"} if plan["format_version"] in (2, 3) else set())
        | ({"lambda_concurrency"} if plan["format_version"] == 3 else set()),
        "invalid_resource_shape",
    )
    proxy = resources.get("database_proxy")
    if plan["format_version"] == 3:
        validate_pool(proxy, plan["account_id"], plan["region"])
        validate_binding(resources["lambda_concurrency"], plan["configuration"])
    elif proxy is not None:
        _exact_object(
            proxy, {"arn", "name", "endpoint"}, "invalid_database_proxy_shape"
        )
        if (
            not isinstance(proxy["name"], str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{1,62}", proxy["name"])
            or not isinstance(proxy["endpoint"], str)
            or not re.fullmatch(
                r"[a-z][a-z0-9-]*\.proxy-[a-z0-9]+\.ap-south-1\.rds\.amazonaws\.com",
                proxy["endpoint"],
            )
            or not isinstance(proxy["arn"], str)
            or not re.fullmatch(
                r"arn:aws:rds:"
                + re.escape(plan["region"])
                + ":"
                + plan["account_id"]
                + r":db-proxy:prx-[a-z0-9]+",
                proxy["arn"],
            )
        ):
            raise ValueError("invalid_database_proxy_binding")
    routing = _exact_object(plan["routing"], ROUTING_KEYS, "invalid_routing_shape")
    revisions = _exact_object(
        plan["revisions"], REVISION_KEYS, "invalid_revision_shape"
    )
    for key in (
        "load_balancer_arn",
        "listener_arn",
        "certificate_arn",
        "ecs_cluster_arn",
        "ecs_service_arn",
        "ecs_task_definition_arn",
        "ecs_target_group_arn",
        "database_parameter_arn",
    ):
        if not isinstance(resources[key], str) or not resources[key].startswith(
            "arn:aws:"
        ):
            raise ValueError("invalid_resource_arn")
    if (
        not isinstance(resources["database_instance_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9-]{1,63}", resources["database_instance_id"])
        or not isinstance(resources["database_name"], str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,63}", resources["database_name"])
    ):
        raise ValueError("invalid_database_instance")
    caller = plan["expected_caller_arn"]
    if not isinstance(caller, str) or not (
        caller.startswith("arn:aws:iam::" + plan["account_id"] + ":role/")
        or caller.startswith("arn:aws:iam::" + plan["account_id"] + ":user/")
    ):
        raise ValueError("invalid_expected_caller")
    if not isinstance(plan["expected_user_id"], str) or not UUID4.fullmatch(
        plan["expected_user_id"]
    ):
        raise ValueError("invalid_expected_test_user")
    for key in ARN_RESOURCE_KEYS:
        arn = resources[key]
        if arn is None:
            continue
        parts = arn.split(":", 5)
        if (
            len(parts) != 6
            or parts[0] != "arn"
            or parts[1] != "aws"
            or parts[3] != plan["region"]
            or parts[4] != plan["account_id"]
        ):
            raise ValueError("resource_account_or_region_mismatch")
    for key in (
        "ecs_image_uri",
        "application_revision",
        "dataset_fingerprint",
        "model_revision",
    ):
        if not isinstance(revisions[key], str) or not revisions[key]:
            raise ValueError("missing_revision_binding")
    if (
        not SHA256.fullmatch(revisions["ecs_image_uri"].rsplit("@", 1)[-1])
        or not re.fullmatch(r"[0-9a-f]{40}", revisions["application_revision"])
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", revisions["dataset_fingerprint"])
        or not re.fullmatch(r"[0-9a-f]{40,64}", revisions["model_revision"])
    ):
        raise ValueError("invalid_immutable_revision")
    if plan["configuration"] == "A":
        if (
            any(
                resources[key] is not None
                for key in (
                    "listener_rule_arn",
                    "lambda_function_arn",
                    "lambda_target_group_arn",
                )
            )
            or revisions["lambda_image_uri"] is not None
            or routing["lambda_weight_percent"] != 0
        ):
            raise ValueError("configuration_a_must_be_ecs_only")
    else:
        for key in (
            "listener_rule_arn",
            "lambda_function_arn",
            "lambda_target_group_arn",
        ):
            if not isinstance(resources[key], str) or not resources[key].startswith(
                "arn:aws:"
            ):
                raise ValueError("configuration_b_resources_required")
        if not isinstance(revisions["lambda_image_uri"], str) or not SHA256.fullmatch(
            revisions["lambda_image_uri"].rsplit("@", 1)[-1]
        ):
            raise ValueError("immutable_lambda_image_required")
        if (
            type(routing["lambda_weight_percent"]) is not int
            or not 0 <= routing["lambda_weight_percent"] <= 100
        ):
            raise ValueError("invalid_lambda_weight")
    if (
        routing["methods"] != ["GET"]
        or routing["path_regexes"] != APPROVED_PATHS
        or routing["stickiness_enabled"] is not False
    ):
        raise ValueError("unapproved_route_scope")
    evidence_path = Path(
        plan["evidence_path"] if isinstance(plan["evidence_path"], str) else ""
    )
    if (
        evidence_path.is_absolute()
        or ".." in evidence_path.parts
        or not evidence_path.parts
    ):
        raise ValueError("invalid_evidence_path")
    return cast(dict[str, Any], plan)


def _role_name(role_arn: str) -> str:
    return role_arn.rsplit("/", 1)[-1]


def _host_addresses(host: str) -> set[str]:
    """Resolve the complete current address sets for the planned and ALB hosts."""
    try:
        return {
            address
            for row in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            if isinstance((address := row[4][0]), str)
        }
    except OSError:
        raise ValueError("target_dns_resolution_failed") from None


class _NoRedirect(HTTPRedirectHandler):
    """Keep even the unauthenticated target check on its planned origin."""

    def redirect_request(
        self,
        request: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        new_url: str,
    ) -> Request | None:
        return None


def _check_listener(elbv2: Any, plan: dict[str, Any]) -> dict[str, Any]:
    resource = plan["resources"]
    listeners = elbv2.describe_listeners(LoadBalancerArn=resource["load_balancer_arn"])[
        "Listeners"
    ]
    listener = next(
        (
            row
            for row in listeners
            if row.get("ListenerArn") == resource["listener_arn"]
        ),
        None,
    )
    if (
        listener is None
        or listener.get("Protocol") != "HTTPS"
        or listener.get("Port") != 443
    ):
        raise ValueError("https_listener_mismatch")
    certs = elbv2.describe_listener_certificates(ListenerArn=resource["listener_arn"])[
        "Certificates"
    ]
    if not any(
        row.get("CertificateArn") == resource["certificate_arn"] for row in certs
    ):
        raise ValueError("listener_certificate_mismatch")
    return cast(dict[str, Any], listener)


def _check_routing(
    elbv2: Any, plan: dict[str, Any], listener: dict[str, Any]
) -> dict[str, Any]:
    resource, routing = plan["resources"], plan["routing"]
    if plan["configuration"] == "A":
        if any(
            action.get("Type") == "forward"
            and action.get("TargetGroupArn") != resource["ecs_target_group_arn"]
            for action in listener.get("DefaultActions", [])
        ):
            raise ValueError("configuration_a_default_route_mismatch")
        rules = elbv2.describe_rules(ListenerArn=resource["listener_arn"])["Rules"]
        for rule in rules:
            if rule.get("IsDefault"):
                continue
            has_selected_path = any(
                condition.get("Field") == "path-pattern"
                and set(condition.get("PathPatternConfig", {}).get("RegexValues", []))
                & set(APPROVED_PATHS)
                for condition in rule.get("Conditions", [])
            )
            has_get = any(
                condition.get("Field") == "http-request-method"
                and "GET"
                in condition.get("HttpRequestMethodConfig", {}).get("Values", [])
                for condition in rule.get("Conditions", [])
            )
            if has_selected_path and has_get:
                raise ValueError("configuration_a_selected_reads_rule_present")
        return {
            "configuration": "A",
            "selected_rule": False,
            "ecs_weight_percent": 100,
            "lambda_weight_percent": 0,
        }
    rules = elbv2.describe_rules(ListenerArn=resource["listener_arn"])["Rules"]
    rule = next(
        (row for row in rules if row.get("RuleArn") == resource["listener_rule_arn"]),
        None,
    )
    if rule is None or str(rule.get("Priority")) != "10":
        raise ValueError("selected_reads_rule_missing")
    for other in rules:
        if (
            other.get("IsDefault")
            or other.get("RuleArn") == resource["listener_rule_arn"]
        ):
            continue
        try:
            precedes = int(other.get("Priority", "50000")) < 10
        except TypeError, ValueError:
            raise ValueError("listener_rule_priority_unreadable") from None
        if precedes:
            raise ValueError("higher_priority_listener_rule_requires_review")
    conditions = rule.get("Conditions", [])
    method_values = [
        condition.get("HttpRequestMethodConfig", {}).get("Values", [])
        for condition in conditions
        if condition.get("Field") == "http-request-method"
    ]
    path_values = [
        condition.get("PathPatternConfig", {}).get("RegexValues", [])
        for condition in conditions
        if condition.get("Field") == "path-pattern"
    ]
    if method_values != [["GET"]] or path_values != [APPROVED_PATHS]:
        raise ValueError("selected_route_condition_mismatch")
    actions = [
        action for action in rule.get("Actions", []) if action.get("Type") == "forward"
    ]
    if len(actions) != 1:
        raise ValueError("selected_route_action_mismatch")
    forward = actions[0].get("ForwardConfig", {})
    stickiness = forward.get("TargetGroupStickinessConfig", {})
    if stickiness.get("Enabled") is not False:
        raise ValueError("unexpected_route_stickiness")
    targets = {
        row.get("TargetGroupArn"): row.get("Weight")
        for row in forward.get("TargetGroups", [])
    }
    expected = {
        resource["lambda_target_group_arn"]: routing["lambda_weight_percent"],
        resource["ecs_target_group_arn"]: 100 - routing["lambda_weight_percent"],
    }
    if len(forward.get("TargetGroups", [])) != 2 or targets != expected:
        raise ValueError("selected_route_weights_mismatch")
    return {
        "configuration": "B",
        "selected_rule": True,
        "ecs_weight_percent": expected[resource["ecs_target_group_arn"]],
        "lambda_weight_percent": expected[resource["lambda_target_group_arn"]],
    }


def verify_lambda_startup(function: dict[str, Any]) -> None:
    """Refuse diagnostic overrides or startup/deadline drift before measurements.

    Async initialization preserves work across the initial ten-second window;
    it does not relax the five-second invocation or client request deadline.
    Container startup must use the reviewed image command, never tracing code.
    """
    image = function.get("ImageConfigResponse", {})
    overrides = image.get("ImageConfig", {})
    if (
        function.get("Timeout") != 5
        or function.get("LastUpdateStatus") != "Successful"
        or function.get("Environment", {})
        .get("Variables", {})
        .get("AWS_LWA_ASYNC_INIT")
        != "true"
        or image.get("Error")
        or any(
            overrides.get(key) for key in ("Command", "EntryPoint", "WorkingDirectory")
        )
    ):
        raise ValueError("lambda_startup_configuration_mismatch")


def inspect_target(plan: dict[str, Any], session_factory: Any = None) -> dict[str, Any]:
    """Read actual AWS topology and an unauthenticated HTTPS liveness endpoint."""
    validate_plan(plan)
    if session_factory is None:
        from data.generators.reference_login import sdk_profile_session

        session_factory = sdk_profile_session
    session = session_factory(
        profile_name=plan["aws_profile"], region_name=plan["region"]
    )
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    if identity.get("Account") != plan["account_id"]:
        raise ValueError("aws_account_mismatch")
    expected_caller = plan["expected_caller_arn"]
    actual_caller = identity.get("Arn")
    if expected_caller.startswith(f"arn:aws:iam::{plan['account_id']}:user/"):
        identity_matches = actual_caller == expected_caller
    else:
        assumed_prefix = f"arn:aws:sts::{plan['account_id']}:assumed-role/{_role_name(expected_caller)}/"
        identity_matches = isinstance(actual_caller, str) and actual_caller.startswith(
            assumed_prefix
        )
    if not identity_matches:
        raise ValueError("aws_caller_mismatch")
    resources = plan["resources"]
    elbv2 = session.client("elbv2")
    lb = elbv2.describe_load_balancers(
        LoadBalancerArns=[resources["load_balancer_arn"]]
    )["LoadBalancers"]
    if (
        len(lb) != 1
        or lb[0].get("State", {}).get("Code") != "active"
        or lb[0].get("Scheme") != "internet-facing"
    ):
        raise ValueError("load_balancer_state_mismatch")
    planned_host = urlsplit(plan["api_origin"]).hostname
    if _host_addresses(planned_host) != _host_addresses(lb[0].get("DNSName", "")):
        raise ValueError("origin_dns_load_balancer_mismatch")
    listener = _check_listener(elbv2, plan)
    routing = _check_routing(elbv2, plan, listener)
    ecs = session.client("ecs")
    services = ecs.describe_services(
        cluster=resources["ecs_cluster_arn"], services=[resources["ecs_service_arn"]]
    )
    rows = services.get("services", [])
    if len(rows) != 1 or services.get("failures"):
        raise ValueError("ecs_service_missing")
    service = rows[0]
    if (
        service.get("taskDefinition") != resources["ecs_task_definition_arn"]
        or service.get("desiredCount", 0) < 1
        or service.get("runningCount", 0) != service.get("desiredCount")
        or service.get("pendingCount", 0) != 0
    ):
        raise ValueError("ecs_service_revision_or_health_mismatch")
    service_targets = service.get("loadBalancers", [])
    if (
        len(service_targets) != 1
        or service_targets[0].get("targetGroupArn") != resources["ecs_target_group_arn"]
    ):
        raise ValueError("ecs_service_target_group_mismatch")
    taskdef = ecs.describe_task_definition(
        taskDefinition=resources["ecs_task_definition_arn"]
    )["taskDefinition"]
    containers = taskdef.get("containerDefinitions", [])
    app = next(
        (container for container in containers if container.get("name") == "api"), None
    )
    if app is None or app.get("image") != plan["revisions"]["ecs_image_uri"]:
        raise ValueError("ecs_immutable_image_mismatch")
    db_secrets = [
        row for row in app.get("secrets", []) if row.get("name") == "CLIP_DATABASE_URL"
    ]
    if (
        len(db_secrets) != 1
        or db_secrets[0].get("valueFrom") != resources["database_parameter_arn"]
    ):
        raise ValueError("ecs_database_parameter_mismatch")
    lambda_environment = None
    if plan["configuration"] == "B":
        lam = session.client("lambda")
        function = lam.get_function_configuration(
            FunctionName=resources["lambda_function_arn"]
        )
        if (
            function.get("State") != "Active"
            or function.get("PackageType") != "Image"
            or function.get("FunctionArn") != resources["lambda_function_arn"]
        ):
            raise ValueError("lambda_function_state_mismatch")
        verify_lambda_startup(function)
        env = function.get("Environment", {}).get("Variables", {})
        lambda_environment = env
        if env.get("CLIP_LAMBDA_DATABASE_PARAMETER_ENABLED") != "true":
            raise ValueError("lambda_database_binding_disabled")
        if function.get("ImageConfigResponse", {}).get("Error"):
            raise ValueError("lambda_image_configuration_error")
        code = lam.get_function(FunctionName=resources["lambda_function_arn"])
        image_uri = code.get("Code", {}).get("ResolvedImageUri") or code.get(
            "Code", {}
        ).get("ImageUri")
        if image_uri != plan["revisions"]["lambda_image_uri"]:
            raise ValueError("lambda_immutable_image_mismatch")
        verify_concurrency(
            lam, resources["lambda_function_arn"], resources.get("lambda_concurrency")
        )
        role_name = _role_name(function.get("Role", ""))
        iam = session.client("iam")
        can_read_parameter = False
        for policy_name in iam.list_role_policies(RoleName=role_name).get(
            "PolicyNames", []
        ):
            policy = iam.get_role_policy(
                RoleName=role_name, PolicyName=policy_name
            ).get("PolicyDocument", {})
            statements = policy.get("Statement", [])
            if isinstance(statements, dict):
                statements = [statements]
            for statement in statements:
                actions = statement.get("Action", [])
                allowed = statement.get("Resource", [])
                if isinstance(actions, str):
                    actions = [actions]
                if isinstance(allowed, str):
                    allowed = [allowed]
                if (
                    "ssm:GetParameter" in actions
                    and resources["database_parameter_arn"] in allowed
                ):
                    can_read_parameter = True
        if not can_read_parameter:
            raise ValueError("lambda_database_parameter_permission_mismatch")
    rds_client = session.client("rds")
    rds = rds_client.describe_db_instances(
        DBInstanceIdentifier=resources["database_instance_id"]
    )["DBInstances"]
    if (
        len(rds) != 1
        or rds[0].get("DBInstanceStatus") != "available"
        or rds[0].get("PubliclyAccessible") is not False
    ):
        raise ValueError("database_state_mismatch")
    if rds[0].get("DBInstanceArn", "").split(":")[4] != plan["account_id"]:
        raise ValueError("database_account_mismatch")
    if plan["format_version"] == 3:
        verify_pool(session, resources["database_proxy"], resources["ecs_cluster_arn"])
    _verify_database_proxy(
        rds_client,
        resources.get("database_proxy"),
        rds[0],
        {row["name"]: row.get("value") for row in app.get("environment", [])},
        lambda_environment,
    )
    parameter = (
        session.client("ssm")
        .get_parameter(Name=resources["database_parameter_arn"], WithDecryption=True)
        .get("Parameter", {})
    )
    if (
        parameter.get("ARN") != resources["database_parameter_arn"]
        or parameter.get("Type") != "SecureString"
        or not isinstance(parameter.get("Value"), str)
    ):
        raise ValueError("database_parameter_identity_mismatch")
    dsn = urlsplit(parameter["Value"])
    database_name = unquote(dsn.path.removeprefix("/"))
    endpoint = rds[0].get("Endpoint", {})
    if (
        dsn.scheme not in {"postgresql", "postgresql+psycopg"}
        or dsn.hostname != endpoint.get("Address")
        or (dsn.port or 5432) != endpoint.get("Port")
        or database_name != resources["database_name"]
    ):
        raise ValueError("database_parameter_target_mismatch")
    origin = plan["api_origin"]
    opener = build_opener(
        ProxyHandler({}),
        _NoRedirect(),
        HTTPSHandler(context=ssl.create_default_context()),
    )
    request = Request(
        origin + "/health",
        headers={"Accept": "application/json", "Cache-Control": "no-cache"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=5) as response:
            body = response.read(4096)
            if response.status != 200 or json.loads(body) != {"status": "ok"}:
                raise ValueError("https_liveness_check_failed")
    except HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError:
        raise ValueError("https_liveness_check_failed") from None
    return {
        "infrastructure_preflight_valid": True,
        "run_id": plan["run_id"],
        "configuration": plan["configuration"],
        "account_id": plan["account_id"],
        "region": plan["region"],
        "aws_identity_verified": True,
        "load_balancer_active": True,
        "https_certificate_binding_verified": True,
        "routing": routing,
        "ecs_service_healthy": True,
        "ecs_image_verified": True,
        "ecs_database_parameter_reference_verified": True,
        "lambda_database_parameter_permission_verified": plan["configuration"] == "B",
        "database_parameter_resolves_to_planned_instance": True,
        "lambda_image_verified": plan["configuration"] == "B",
        "lambda_startup_configuration_verified": plan["configuration"] == "B",
        "database_available_private": True,
        "database_proxy_verified": resources.get("database_proxy") is not None,
        "https_liveness_verified": True,
        "origin_dns_to_load_balancer_verified": True,
        "application_revision_attested": False,
        "dataset_and_index_fingerprints_attested": False,
        "session_checked": False,
        "workload_started": False,
        "measurement_authorized": False,
        "remaining_checks": [
            "application_revision_attestation",
            "dataset_and_index_fingerprints",
            "authenticated_session_identity",
            "approved_run_and_resource_limits",
            "checked_workload_bundle_and_timing_binary",
            "private_raw_evidence_capture",
        ],
    }


def check_session_identity(
    plan: dict[str, Any],
    cookie: str,
    *,
    needs_csrf: bool = False,
    expected_user_id: str | None = None,
) -> dict[str, Any]:
    """Confirm a supplied session is the planned regular test account.

    The caller must invoke this only after local plan and live-target checks.
    The cookie and optional CSRF token stay in memory and are never reported.
    """
    validate_plan(plan)
    user_id = expected_user_id or plan["expected_user_id"]
    if not isinstance(user_id, str) or not UUID4.fullmatch(user_id):
        raise ValueError("invalid_expected_test_user")
    if not isinstance(cookie, str) or not SESSION_COOKIE.fullmatch(cookie):
        raise ValueError("session_cookie_missing_or_invalid")
    origin = plan["api_origin"]
    opener = build_opener(
        ProxyHandler({}),
        _NoRedirect(),
        HTTPSHandler(context=ssl.create_default_context()),
    )
    request = Request(
        origin + "/api/me",
        headers={
            "Accept": "application/json",
            "Cookie": cookie,
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with opener.open(request, timeout=5) as response:
            body_bytes = response.read(100_001)
            if response.status != 200 or len(body_bytes) > 100_000:
                raise ValueError("session_identity_check_failed")
        body = json.loads(body_bytes)
    except HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError:
        raise ValueError("session_identity_check_failed") from None
    if (
        not isinstance(body, dict)
        or body.get("user_id") != user_id
        or body.get("account_class") != "regular"
        or not isinstance(body.get("valid_until"), str)
    ):
        raise ValueError("session_identity_mismatch")
    try:
        valid_until = datetime.fromisoformat(body["valid_until"].replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("session_expiry_invalid") from None
    if valid_until.tzinfo is None or valid_until <= datetime.now(timezone.utc):
        raise ValueError("session_expired")
    csrf_token = None
    if needs_csrf:
        csrf_request = Request(
            origin + "/api/auth/csrf",
            headers={
                "Accept": "application/json",
                "Cookie": cookie,
                "Cache-Control": "no-cache",
            },
            method="GET",
        )
        try:
            with opener.open(csrf_request, timeout=5) as response:
                csrf_bytes = response.read(4097)
                if response.status != 200 or len(csrf_bytes) > 4096:
                    raise ValueError("csrf_check_failed")
            csrf_doc = json.loads(csrf_bytes)
        except HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError:
            raise ValueError("csrf_check_failed") from None
        csrf_token = (
            csrf_doc.get("csrf_token")
            if isinstance(csrf_doc, dict) and set(csrf_doc) == {"csrf_token"}
            else None
        )
        if not isinstance(csrf_token, str) or not re.fullmatch(
            r"[A-Za-z0-9._~+/=-]{32,128}", csrf_token
        ):
            raise ValueError("csrf_check_failed")
    return {
        "session_identity_verified": True,
        "test_user_id_matches": True,
        "regular_account_verified": True,
        "session_expiry_checked": True,
        "csrf_obtained": needs_csrf,
        "csrf_token": csrf_token,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument(
        "--inspect-live",
        action="store_true",
        help="perform read-only AWS and unauthenticated HTTPS checks",
    )
    parser.add_argument(
        "--session-env",
        help="verify the cookie from this environment variable after live preflight",
    )
    parser.add_argument(
        "--expected-user-id", help="expected synthetic regular-account UUID"
    )
    args = parser.parse_args()
    try:
        if args.plan.stat().st_size > 100_000:
            raise ValueError("plan_too_large")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        validate_plan(plan)
        if args.session_env and (not args.inspect_live or not args.expected_user_id):
            raise ValueError("live_session_check_requires_target_and_user")
        if args.expected_user_id and not args.session_env:
            raise ValueError("session_environment_required")
        if args.inspect_live:
            result = inspect_target(plan)
        else:
            result = {
                "plan_valid": True,
                "run_id": plan["run_id"],
                "configuration": plan["configuration"],
                "live_target_checked": False,
                "measurement_authorized": False,
            }
        if args.session_env:
            cookie = os.environ.get(args.session_env, "")
            result["session_identity"] = check_session_identity(
                plan, cookie, expected_user_id=args.expected_user_id
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        code = (
            str(error)
            if isinstance(error, ValueError)
            and re.fullmatch(r"[a-z_]{1,80}", str(error))
            else "target_preflight_failed"
        )
        parser.exit(
            2, f"Read-only target preflight failed: {code}; no workload was started\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
