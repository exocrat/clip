"""Exact-plan-gated isolated RDS restore and integrity observer for NFR-07."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPSHandler,
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)

AWS_ID = re.compile(r"^[0-9]{12}$")
IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
ARN = re.compile(r"^arn:aws:[a-z0-9-]+:[a-z0-9-]*:[0-9]{12}:.+$")
REGION = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+(?:-[a-z]+)?-\d$")
MIGRATION = re.compile(r"^[0-9]{14}$")
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


def validate_plan(plan: Any) -> dict[str, Any]:
    """Check exact source/target bindings and the isolated restore limits."""
    if (
        not isinstance(plan, dict)
        or plan.get("nfr_id") != "nfr-07"
        or plan.get("execution_permitted") is not True
        or plan.get("nfr_accepted") is not False
    ):
        raise ValueError("approved_nfr07_plan_required")
    if not isinstance(plan.get("run_id"), str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{2,63}", plan["run_id"]
    ):
        raise ValueError("invalid_run_id")
    if not isinstance(plan.get("account_id"), str) or not AWS_ID.fullmatch(
        plan["account_id"]
    ):
        raise ValueError("invalid_account_id")
    if not isinstance(plan.get("region"), str) or not REGION.fullmatch(plan["region"]):
        raise ValueError("invalid_region")
    if not isinstance(plan.get("snapshot_arn"), str) or not ARN.fullmatch(
        plan["snapshot_arn"]
    ):
        raise ValueError("invalid_snapshot_arn")
    if not isinstance(
        plan.get("snapshot_source_instance_id"), str
    ) or not IDENTIFIER.fullmatch(plan["snapshot_source_instance_id"]):
        raise ValueError("invalid_snapshot_source")
    if not isinstance(
        plan.get("target_db_instance_id"), str
    ) or not IDENTIFIER.fullmatch(plan["target_db_instance_id"]):
        raise ValueError("invalid_target_db_instance_id")
    if not isinstance(plan.get("target_manifest_sha256"), str) or not SHA256.fullmatch(
        plan["target_manifest_sha256"]
    ):
        raise ValueError("invalid_target_manifest_hash")
    if not isinstance(plan.get("subnet_group"), str) or not IDENTIFIER.fullmatch(
        plan["subnet_group"]
    ):
        raise ValueError("invalid_subnet_group")
    groups = plan.get("security_group_ids")
    if (
        not isinstance(groups, list)
        or not groups
        or len(groups) > 5
        or any(
            not isinstance(value, str) or not re.fullmatch(r"sg-[0-9a-f]{8,17}", value)
            for value in groups
        )
        or len(set(groups)) != len(groups)
    ):
        raise ValueError("invalid_security_groups")
    if (
        plan.get("publicly_accessible") is not False
        or plan.get("multi_az") is not False
        or plan.get("restore_timeout_seconds") != 1800
    ):
        raise ValueError("unsafe_restore_settings")
    if not isinstance(plan.get("db_instance_class"), str) or not re.fullmatch(
        r"db\.[a-z0-9-]+", plan["db_instance_class"]
    ):
        raise ValueError("invalid_db_instance_class")
    if not isinstance(plan.get("database_name"), str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]{0,62}", plan["database_name"]
    ):
        raise ValueError("invalid_database_name")
    if not isinstance(plan.get("secret_arn"), str) or not ARN.fullmatch(
        plan["secret_arn"]
    ):
        raise ValueError("invalid_secret_arn")
    if (
        not isinstance(plan.get("rds_ca_bundle_path"), str)
        or not plan["rds_ca_bundle_path"].strip()
        or not isinstance(plan.get("rds_ca_bundle_sha256"), str)
        or not SHA256.fullmatch(plan["rds_ca_bundle_sha256"])
    ):
        raise ValueError("rds_ca_bundle_binding_required")
    if not isinstance(
        plan.get("expected_migration_head"), str
    ) or not MIGRATION.fullmatch(plan["expected_migration_head"]):
        raise ValueError("invalid_expected_migration_head")
    if (
        not isinstance(plan.get("source_snapshot_scope"), str)
        or not plan["source_snapshot_scope"].strip()
    ):
        raise ValueError("snapshot_scope_required")
    smoke = plan.get("application_smoke_plan")
    if not isinstance(smoke, dict) or set(smoke) != {
        "https_origin",
        "cluster_arn",
        "service_arn",
        "load_balancer_arn",
        "listener_arn",
        "listener_rule_arn",
        "certificate_arn",
        "target_group_arn",
        "task_definition_arn",
        "database_parameter_arn",
        "application_revision",
        "container_image",
        "expected_user_id",
        "wanted_request_id",
    }:
        raise ValueError("application_smoke_plan_required")
    origin = urlsplit(
        smoke["https_origin"] if isinstance(smoke.get("https_origin"), str) else ""
    )
    if (
        origin.scheme != "https"
        or not origin.hostname
        or origin.path
        or origin.query
        or origin.fragment
        or origin.username
        or origin.password
    ):
        raise ValueError("application_smoke_https_origin_required")
    for key in (
        "cluster_arn",
        "service_arn",
        "load_balancer_arn",
        "listener_arn",
        "listener_rule_arn",
        "certificate_arn",
        "target_group_arn",
        "task_definition_arn",
        "database_parameter_arn",
    ):
        if not isinstance(smoke[key], str) or not ARN.fullmatch(smoke[key]):
            raise ValueError("application_smoke_resource_binding_required")
    if not isinstance(smoke["application_revision"], str) or not re.fullmatch(
        r"[0-9a-f]{40}", smoke["application_revision"]
    ):
        raise ValueError("application_smoke_revision_required")
    if (
        not isinstance(smoke["container_image"], str)
        or "@sha256:" not in smoke["container_image"]
        or not SHA256.fullmatch(smoke["container_image"].rsplit("@sha256:", 1)[1])
    ):
        raise ValueError("application_smoke_image_digest_required")
    if any(
        not isinstance(smoke[key], str) or not UUID.fullmatch(smoke[key])
        for key in ("expected_user_id", "wanted_request_id")
    ):
        raise ValueError("application_smoke_fixture_ids_required")
    return plan


def validate_restore_approval(
    plan: dict[str, Any], approval: Any, plan_sha256: str | None = None
) -> dict[str, Any]:
    """Require separate human approval for this one snapshot-to-target restore."""
    keys = {
        "approval_id",
        "human_approved",
        "approved_at_utc",
        "expires_at_utc",
        "plan_sha256",
        "action",
        "run_id",
        "account_id",
        "region",
        "snapshot_arn",
        "target_db_instance_id",
        "subnet_group",
        "security_group_ids",
        "db_instance_class",
        "publicly_accessible",
        "multi_az",
    }
    if (
        not isinstance(approval, dict)
        or set(approval) != keys
        or approval.get("human_approved") is not True
        or approval.get("action") != "rds.restore_db_instance_from_db_snapshot"
    ):
        raise ValueError("exact_restore_action_approval_required")
    if plan_sha256 is None or approval.get("plan_sha256") != plan_sha256:
        raise ValueError("restore_approval_plan_hash_mismatch")
    for key in (
        "run_id",
        "account_id",
        "region",
        "snapshot_arn",
        "target_db_instance_id",
        "subnet_group",
        "security_group_ids",
        "db_instance_class",
        "publicly_accessible",
        "multi_az",
    ):
        if approval.get(key) != plan.get(key):
            raise ValueError("restore_approval_target_mismatch")
    for key in ("approved_at_utc", "expires_at_utc"):
        value = approval.get(key)
        if not isinstance(value, str):
            raise ValueError("invalid_approval_time")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("invalid_approval_time") from None
        if parsed.tzinfo is None:
            raise ValueError("invalid_approval_time")
    approved_at = datetime.fromisoformat(
        approval["approved_at_utc"].replace("Z", "+00:00")
    )
    expiry = datetime.fromisoformat(approval["expires_at_utc"].replace("Z", "+00:00"))
    if (
        approved_at > datetime.now(timezone.utc)
        or expiry <= datetime.now(timezone.utc)
        or expiry <= approved_at
    ):
        raise ValueError("restore_approval_expired")
    if (
        not isinstance(approval["approval_id"], str)
        or not approval["approval_id"].strip()
    ):
        raise ValueError("invalid_approval_id")
    return approval


def _utc() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _verify_smoke_session(plan: dict[str, Any], cookie: str) -> None:
    """Check the approved regular test-user session before starting a restore."""
    smoke = plan["application_smoke_plan"]
    if not re.fullmatch(r"__Host-clip_session=[A-Za-z0-9._~+/=-]{1,2048}", cookie):
        raise ValueError("nfr07_smoke_session_missing_or_invalid")

    class RefuseRedirects(HTTPRedirectHandler):
        def redirect_request(
            self,
            req: Request,
            fp: Any,
            code: int,
            msg: str,
            headers: Any,
            newurl: str,
        ) -> Request | None:
            return None

    opener = build_opener(ProxyHandler({}), HTTPSHandler(), RefuseRedirects())
    request = Request(
        smoke["https_origin"].rstrip("/") + "/api/me",
        headers={
            "Accept": "application/json",
            "Cookie": cookie,
            "Cache-Control": "no-cache",
        },
        method="GET",
    )
    try:
        with opener.open(request, timeout=5) as response:
            raw = response.read(100_001)
            if response.status != 200 or len(raw) > 100_000:
                raise ValueError("nfr07_smoke_session_check_failed")
        identity = json.loads(raw)
    except HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError:
        raise ValueError("nfr07_smoke_session_check_failed") from None
    expiry_text = identity.get("valid_until") if isinstance(identity, dict) else None
    if (
        not isinstance(identity, dict)
        or identity.get("user_id") != smoke["expected_user_id"]
        or identity.get("account_class") != "regular"
        or not isinstance(expiry_text, str)
    ):
        raise ValueError("nfr07_smoke_session_identity_mismatch")
    try:
        expiry = datetime.fromisoformat(expiry_text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("nfr07_smoke_session_expiry_invalid") from None
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("nfr07_smoke_session_expired")


def _write_exclusive(path: Path, document: dict[str, Any]) -> None:
    """Write a private new receipt without replacing earlier evidence."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        payload = (
            json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
        ).encode()
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("evidence_write_failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _integrity_checks(connection: Any, expected_head: str) -> dict[str, Any]:
    """Run read-only migration, FK, and representative relationship checks."""
    checks: dict[str, bool] = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        checks["select_1"] = cursor.fetchone() == (1,)
        cursor.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version DESC LIMIT 1"
        )
        row = cursor.fetchone()
        checks["migration_head"] = row is not None and row[0] == expected_head
        cursor.execute(
            "SELECT COUNT(*) FROM pg_constraint WHERE contype='f' AND NOT convalidated"
        )
        checks["foreign_keys_validated"] = cursor.fetchone()[0] == 0
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM listings.sale_listings l JOIN identity.users u ON u.id=l.owner_id WHERE l.retired_at IS NULL)"
        )
        checks["user_listing_relationship"] = bool(cursor.fetchone()[0])
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM search.wanted_requests w JOIN identity.users u ON u.id=w.author_id WHERE w.retired_at IS NULL)"
        )
        checks["user_wanted_request_relationship"] = bool(cursor.fetchone()[0])
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM conversations.threads t JOIN conversations.members m ON m.conversation_id=t.id JOIN identity.users u ON u.id=m.user_id WHERE (t.listing_id IS NOT NULL AND EXISTS (SELECT 1 FROM listings.sale_listings l WHERE l.id=t.listing_id)) OR (t.wanted_request_id IS NOT NULL AND EXISTS (SELECT 1 FROM search.wanted_requests w WHERE w.id=t.wanted_request_id)))"
        )
        checks["conversation_origin_and_member_relationship"] = bool(
            cursor.fetchone()[0]
        )
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM conversations.offers o JOIN conversations.offer_revisions r ON r.offer_id=o.id AND r.revision=o.current_revision JOIN conversations.threads t ON t.id=o.conversation_id)"
        )
        checks["conversation_offer_relationship"] = bool(cursor.fetchone()[0])
    return checks


def _verify_application_smoke(
    plan: dict[str, Any],
    ecs: Any,
    elbv2: Any,
    acm: Any,
    ssm: Any,
    rds_instance: dict[str, Any],
    session_cookie: str,
) -> dict[str, Any]:
    """Verify the smoke service points at the restored DB, then read one fixture."""
    smoke = plan["application_smoke_plan"]
    clusters = (
        ecs.describe_clusters(clusters=[smoke["cluster_arn"]]).get("clusters") or []
    )
    if (
        len(clusters) != 1
        or clusters[0].get("clusterArn") != smoke["cluster_arn"]
        or clusters[0].get("status") != "ACTIVE"
    ):
        raise ValueError("smoke_ecs_cluster_mismatch")
    services = (
        ecs.describe_services(
            cluster=smoke["cluster_arn"], services=[smoke["service_arn"]]
        ).get("services")
        or []
    )
    if len(services) != 1:
        raise ValueError("smoke_ecs_service_missing")
    service = services[0]
    if (
        service.get("serviceArn") != smoke["service_arn"]
        or service.get("status") != "ACTIVE"
        or service.get("desiredCount", 0) < 1
        or service.get("runningCount") != service.get("desiredCount")
        or service.get("pendingCount", 0) != 0
    ):
        raise ValueError("smoke_ecs_service_unhealthy")
    task_definition_arn = service.get("taskDefinition")
    if task_definition_arn != smoke["task_definition_arn"]:
        raise ValueError("smoke_task_definition_binding_mismatch")
    task_definition = (
        ecs.describe_task_definition(taskDefinition=task_definition_arn).get(
            "taskDefinition"
        )
        or {}
    )
    containers = task_definition.get("containerDefinitions") or []
    matching = [
        container
        for container in containers
        if container.get("image") == smoke["container_image"]
    ]
    if len(matching) != 1:
        raise ValueError("smoke_application_image_mismatch")
    database_secrets = [
        item
        for item in matching[0].get("secrets", [])
        if item.get("name") == "CLIP_DATABASE_URL"
    ]
    if (
        len(database_secrets) != 1
        or database_secrets[0].get("valueFrom") != smoke["database_parameter_arn"]
    ):
        raise ValueError("smoke_database_secret_binding_mismatch")
    target_groups = {
        item.get("targetGroupArn") for item in service.get("loadBalancers", [])
    }
    groups = (
        elbv2.describe_target_groups(TargetGroupArns=sorted(target_groups)).get(
            "TargetGroups"
        )
        if target_groups
        else []
    )
    if (
        target_groups != {smoke["target_group_arn"]}
        or not groups
        or any(
            smoke["load_balancer_arn"] not in group.get("LoadBalancerArns", [])
            for group in groups
        )
    ):
        raise ValueError("smoke_load_balancer_service_binding_mismatch")
    balancers = (
        elbv2.describe_load_balancers(
            LoadBalancerArns=[smoke["load_balancer_arn"]]
        ).get("LoadBalancers")
        or []
    )
    origin = urlsplit(smoke["https_origin"])
    if len(balancers) != 1:
        raise ValueError("smoke_load_balancer_missing")
    listeners = (
        elbv2.describe_listeners(LoadBalancerArn=smoke["load_balancer_arn"]).get(
            "Listeners"
        )
        or []
    )
    listener = next(
        (row for row in listeners if row.get("ListenerArn") == smoke["listener_arn"]),
        None,
    )
    if (
        listener is None
        or listener.get("Protocol") != "HTTPS"
        or listener.get("Port") != 443
    ):
        raise ValueError("smoke_https_listener_mismatch")
    certificates = (
        elbv2.describe_listener_certificates(ListenerArn=smoke["listener_arn"]).get(
            "Certificates"
        )
        or []
    )
    if not any(
        row.get("CertificateArn") == smoke["certificate_arn"] for row in certificates
    ):
        raise ValueError("smoke_tls_certificate_binding_mismatch")
    certificate = (
        acm.describe_certificate(CertificateArn=smoke["certificate_arn"]).get(
            "Certificate"
        )
        or {}
    )
    names = certificate.get("SubjectAlternativeNames") or [
        certificate.get("DomainName", "")
    ]
    host = origin.hostname or ""
    if certificate.get("Status") != "ISSUED" or not any(
        name.lower() == host.lower()
        or name.startswith("*.")
        and host.lower().endswith(name[1:].lower())
        and host.count(".") == name.count(".")
        for name in names
    ):
        raise ValueError("smoke_tls_hostname_not_covered")
    rules = elbv2.describe_rules(ListenerArn=smoke["listener_arn"]).get("Rules") or []
    rule = next(
        (row for row in rules if row.get("RuleArn") == smoke["listener_rule_arn"]), None
    )
    if rule is None:
        raise ValueError("smoke_listener_rule_missing")
    host_matches = False
    path_matches = False
    for condition in rule.get("Conditions", []):
        if condition.get("Field") == "host-header":
            values = condition.get("HostHeaderConfig", {}).get(
                "Values", condition.get("Values", [])
            )
            host_matches = host in values
        if condition.get("Field") == "path-pattern":
            values = condition.get("PathPatternConfig", {}).get(
                "Values", condition.get("Values", [])
            )
            path_matches = "/api/*" in values or "/api/wanted-requests/*" in values
    actions = rule.get("Actions") or []
    target_matches = any(
        action.get("Type") == "forward"
        and (
            action.get("TargetGroupArn") == smoke["target_group_arn"]
            or any(
                target.get("TargetGroupArn") == smoke["target_group_arn"]
                for target in action.get("ForwardConfig", {}).get("TargetGroups", [])
            )
        )
        for action in actions
    )
    if not host_matches or not path_matches or not target_matches:
        raise ValueError("smoke_origin_routing_binding_mismatch")
    healthy_targets: list[dict[str, Any]] = []
    for target_group in sorted(target_groups):
        healthy_targets.extend(
            row
            for row in (
                elbv2.describe_target_health(TargetGroupArn=target_group).get(
                    "TargetHealthDescriptions"
                )
                or []
            )
            if row.get("TargetHealth", {}).get("State") == "healthy"
        )
    if len(healthy_targets) < service.get("desiredCount", 1):
        raise ValueError("smoke_no_healthy_application_target")

    parameter = (
        ssm.get_parameter(
            Name=smoke["database_parameter_arn"], WithDecryption=True
        ).get("Parameter")
        or {}
    )
    if parameter.get("ARN") != smoke["database_parameter_arn"] or not isinstance(
        parameter.get("Value"), str
    ):
        raise ValueError("smoke_database_parameter_unavailable")
    database_url = urlsplit(parameter["Value"])
    endpoint = rds_instance.get("Endpoint") or {}
    if (
        database_url.scheme not in {"postgres", "postgresql"}
        or database_url.hostname != endpoint.get("Address")
        or database_url.port != endpoint.get("Port")
        or database_url.path.strip("/") != plan["database_name"]
    ):
        raise ValueError("smoke_database_parameter_target_mismatch")

    class RefuseRedirects(HTTPRedirectHandler):
        def redirect_request(
            self,
            req: Request,
            fp: Any,
            code: int,
            msg: str,
            headers: Any,
            newurl: str,
        ) -> Request | None:
            return None

    opener = build_opener(ProxyHandler({}), HTTPSHandler(), RefuseRedirects())

    def get_json(path: str) -> dict[str, Any]:
        request = Request(
            smoke["https_origin"].rstrip("/") + path,
            headers={
                "Accept": "application/json",
                "Cookie": session_cookie,
                "Cache-Control": "no-cache",
            },
            method="GET",
        )
        try:
            with opener.open(request, timeout=5) as response:
                if response.status != 200:
                    raise ValueError("smoke_application_read_failed")
                body_bytes = response.read(1_000_001)
                if len(body_bytes) > 1_000_000:
                    raise ValueError("smoke_application_response_too_large")
        except HTTPError:
            raise ValueError("smoke_application_http_error") from None
        except URLError:
            raise ValueError("smoke_application_transport_error") from None
        try:
            body = json.loads(body_bytes)
        except UnicodeError, json.JSONDecodeError:
            raise ValueError("smoke_application_response_invalid") from None
        if not isinstance(body, dict):
            raise ValueError("smoke_application_response_invalid")
        return body

    identity = get_json("/api/me")
    if identity.get("user_id") != smoke["expected_user_id"]:
        raise ValueError("smoke_application_auth_identity_mismatch")
    body = get_json(f"/api/wanted-requests/{smoke['wanted_request_id']}")
    if body.get("request_id") != smoke["wanted_request_id"]:
        raise ValueError("smoke_application_fixture_mismatch")
    return {
        "verified": True,
        "service_arn": smoke["service_arn"],
        "task_definition_arn": task_definition_arn,
        "application_revision_declared": smoke["application_revision"],
        "container_image_digest_verified": smoke["container_image"],
        "database_parameter_arn": smoke["database_parameter_arn"],
        "database_target_matches_restored_instance": True,
        "load_balancer_arn": smoke["load_balancer_arn"],
        "listener_arn": smoke["listener_arn"],
        "listener_rule_arn": smoke["listener_rule_arn"],
        "certificate_arn": smoke["certificate_arn"],
        "target_group_arn": smoke["target_group_arn"],
        "fixture_read_status": 200,
        "authenticated_user_verified": True,
        "wanted_fixture_read_status": 200,
    }


def run(
    plan: dict[str, Any], approval: dict[str, Any], *, profile_name: str | None = None
) -> dict[str, Any]:
    """Restore the exact snapshot to a new private target and inspect it read-only."""
    import boto3  # type: ignore[import-untyped]
    import psycopg

    session = boto3.Session(profile_name=profile_name, region_name=plan["region"])
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    if identity.get("Account") != plan["account_id"]:
        raise ValueError("aws_account_mismatch")
    smoke_cookie = os.environ.get("CLIP_NFR07_SMOKE_SESSION_COOKIE", "")
    _verify_smoke_session(plan, smoke_cookie)
    rds = session.client("rds")
    ecs = session.client("ecs")
    elbv2 = session.client("elbv2")
    acm = session.client("acm")
    snapshot_rows = (
        rds.describe_db_snapshots(DBSnapshotIdentifier=plan["snapshot_arn"]).get(
            "DBSnapshots"
        )
        or []
    )
    if (
        len(snapshot_rows) != 1
        or snapshot_rows[0].get("DBSnapshotArn") != plan["snapshot_arn"]
        or snapshot_rows[0].get("Status") != "available"
    ):
        raise ValueError("approved_snapshot_not_available")
    snapshot = snapshot_rows[0]
    if (
        snapshot.get("DBInstanceIdentifier") != plan["snapshot_source_instance_id"]
        or plan["target_db_instance_id"] == plan["snapshot_source_instance_id"]
    ):
        raise ValueError("snapshot_source_or_target_mismatch")
    paginator = rds.get_paginator("describe_db_snapshots")
    available_managed = [
        row
        for page in paginator.paginate(
            DBInstanceIdentifier=plan["snapshot_source_instance_id"],
            SnapshotType="automated",
        )
        for row in page.get("DBSnapshots", [])
        if row.get("Status") == "available"
    ]
    if (
        not available_managed
        or max(available_managed, key=lambda row: row.get("SnapshotCreateTime"))[
            "DBSnapshotArn"
        ]
        != plan["snapshot_arn"]
    ):
        raise ValueError("snapshot_is_not_latest_available_managed_backup")
    try:
        existing = (
            rds.describe_db_instances(
                DBInstanceIdentifier=plan["target_db_instance_id"]
            ).get("DBInstances")
            or []
        )
    except rds.exceptions.DBInstanceNotFound:
        existing = []
    if existing:
        raise ValueError("isolated_restore_target_already_exists")
    started_ns = time.monotonic_ns()
    started_utc = _utc()
    rds.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier=plan["target_db_instance_id"],
        DBSnapshotIdentifier=plan["snapshot_arn"],
        DBInstanceClass=plan["db_instance_class"],
        DBSubnetGroupName=plan["subnet_group"],
        VpcSecurityGroupIds=plan["security_group_ids"],
        PubliclyAccessible=False,
        MultiAZ=False,
        Tags=[
            {"Key": "Project", "Value": "clip"},
            {"Key": "Experiment", "Value": "nfr-07"},
            {"Key": "RunId", "Value": plan["run_id"]},
            {"Key": "CleanupOwner", "Value": "project-owner"},
        ],
    )
    events = [
        {"event": "restore_requested", "at_utc": started_utc, "elapsed_monotonic_ms": 0}
    ]
    deadline = started_ns + plan["restore_timeout_seconds"] * 1_000_000_000
    instance = None
    while time.monotonic_ns() < deadline:
        rows = (
            rds.describe_db_instances(
                DBInstanceIdentifier=plan["target_db_instance_id"]
            ).get("DBInstances")
            or []
        )
        if len(rows) != 1:
            raise ValueError("restore_target_disappeared")
        instance = rows[0]
        events.append(
            {
                "event": "rds_status",
                "status": instance.get("DBInstanceStatus"),
                "at_utc": _utc(),
                "elapsed_monotonic_ms": (time.monotonic_ns() - started_ns) / 1_000_000,
            }
        )
        if instance.get("DBInstanceStatus") == "available":
            break
        time.sleep(min(15, max(1, (deadline - time.monotonic_ns()) / 1_000_000_000)))
    if instance is None or instance.get("DBInstanceStatus") != "available":
        raise ValueError("restore_deadline_exceeded")
    actual_groups = {
        item.get("VpcSecurityGroupId") for item in instance.get("VpcSecurityGroups", [])
    }
    if (
        instance.get("PubliclyAccessible") is not False
        or instance.get("MultiAZ") is not False
        or instance.get("DBSubnetGroup", {}).get("DBSubnetGroupName")
        != plan["subnet_group"]
        or actual_groups != set(plan["security_group_ids"])
    ):
        raise ValueError("restore_target_network_mismatch")
    endpoint = instance.get("Endpoint") or {}
    if not endpoint.get("Address") or type(endpoint.get("Port")) is not int:
        raise ValueError("restore_endpoint_unavailable")
    secrets = session.client("secretsmanager")
    secret = secrets.get_secret_value(SecretId=plan["secret_arn"])
    secret_document = json.loads(secret.get("SecretString", "{}"))
    username, password = secret_document.get("username"), secret_document.get(
        "password"
    )
    if (
        not isinstance(username, str)
        or not username
        or not isinstance(password, str)
        or not password
    ):
        raise ValueError("restore_secret_invalid")
    ca_path = Path(plan["rds_ca_bundle_path"]).resolve(strict=True)
    ca_hash = hashlib.sha256(ca_path.read_bytes()).hexdigest()
    if ca_hash != plan["rds_ca_bundle_sha256"]:
        raise ValueError("rds_ca_bundle_hash_mismatch")
    with psycopg.connect(
        host=endpoint["Address"],
        port=endpoint["Port"],
        dbname=plan["database_name"],
        user=username,
        password=password,
        sslmode="verify-full",
        sslrootcert=str(ca_path),
        connect_timeout=10,
        options="-c default_transaction_read_only=on",
    ) as connection:
        checks = _integrity_checks(connection, plan["expected_migration_head"])
    application_smoke = _verify_application_smoke(
        plan, ecs, elbv2, acm, session.client("ssm"), instance, smoke_cookie
    )
    completed_ns = time.monotonic_ns()
    completed_utc = _utc()
    elapsed_ms = (completed_ns - started_ns) / 1_000_000
    return {
        "format_version": 1,
        "nfr_id": "nfr-07",
        "run_id": plan["run_id"],
        "account_id": plan["account_id"],
        "region": plan["region"],
        "snapshot_arn": plan["snapshot_arn"],
        "snapshot_source_instance": snapshot.get("DBInstanceIdentifier"),
        "snapshot_created_at": (
            snapshot.get("SnapshotCreateTime").isoformat()
            if snapshot.get("SnapshotCreateTime")
            else None
        ),
        "snapshot_scope": plan["source_snapshot_scope"],
        "target_db_instance_id": plan["target_db_instance_id"],
        "target_manifest_sha256": plan["target_manifest_sha256"],
        "rds_ca_bundle_sha256": ca_hash,
        "approval_id": approval["approval_id"],
        "operator_arn": identity.get("Arn"),
        "restore_requested_at_utc": started_utc,
        "checks_completed_at_utc": completed_utc,
        "elapsed_ms_through_integrity_checks": elapsed_ms,
        "within_30_minutes": elapsed_ms <= 1_800_000,
        "integrity_checks": checks,
        "application_smoke_verified": application_smoke["verified"],
        "application_smoke": application_smoke,
        "nfr07_accepted": False,
        "cleanup_status": "target_retained_until_separately_approved_cleanup",
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = None
    approval = None
    try:
        if (
            args.plan.stat().st_size > 1_000_000
            or args.approval.stat().st_size > 32_000
        ):
            raise ValueError("input_too_large")
        plan_bytes = args.plan.read_bytes()
        plan = validate_plan(json.loads(plan_bytes))
        approval = validate_restore_approval(
            plan,
            json.loads(args.approval.read_text(encoding="utf-8")),
            hashlib.sha256(plan_bytes).hexdigest(),
        )
        output = run(plan, approval, profile_name=args.profile)
        _write_exclusive(args.output, output)
        print(
            json.dumps(
                {
                    "nfr_id": "nfr-07",
                    "run_id": plan["run_id"],
                    "within_30_minutes": output["within_30_minutes"],
                    "application_smoke_verified": output["application_smoke_verified"],
                    "nfr07_accepted": False,
                    "output": str(args.output),
                },
                sort_keys=True,
            )
        )
        return (
            0
            if output["within_30_minutes"]
            and all(output["integrity_checks"].values())
            and output["application_smoke_verified"]
            else 1
        )
    except Exception:
        if plan is not None and approval is not None and not args.output.exists():
            failure = {
                "format_version": 1,
                "nfr_id": "nfr-07",
                "run_id": plan["run_id"],
                "account_id": plan["account_id"],
                "region": plan["region"],
                "snapshot_arn": plan["snapshot_arn"],
                "target_db_instance_id": plan["target_db_instance_id"],
                "approval_id": approval["approval_id"],
                "run_outcome": "failed_or_incomplete",
                "failure_type": "input_provider_restore_or_integrity_error",
                "restore_action_may_have_started": True,
                "nfr07_accepted": False,
                "application_smoke_verified": False,
                "cleanup_status": "inspect_exact_target_state_before_any_follow_up",
            }
            _write_exclusive(args.output, failure)
            print(
                json.dumps(
                    {
                        "nfr_id": "nfr-07",
                        "run_id": plan["run_id"],
                        "run_outcome": "failed_or_incomplete",
                        "nfr07_accepted": False,
                        "output": str(args.output),
                    },
                    sort_keys=True,
                )
            )
            return 1
        parser.exit(2, "NFR-07 restore refused or incomplete\n")


if __name__ == "__main__":
    raise SystemExit(main())
