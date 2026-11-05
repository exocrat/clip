"""Verify the isolated target and credential source without restoring anything."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import json
import pytest
from scripts.evaluation.nfr07_restore_observer import (
    _integrity_transport_options,
    _restore_credentials,
    _validate_integrity_transport_spec,
)


def fixture(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    path = tmp_path / "receipt.json"
    plan = {
        "target_db_instance_id": "clip-isolated",
        "integrity_transport": {
            "kind": "ssm_loopback",
            "hostaddr": "127.0.0.1",
            "port": 15439,
            "receipt_path": str(path),
            "forward_instance_id": "i-00000000000000001",
        },
    }
    instance = {
        "DBInstanceIdentifier": "clip-isolated",
        "DbiResourceId": "db-NEW",
        "Endpoint": {"Address": "isolated.example.invalid", "Port": 5432},
    }
    receipt = {
        "target_db_instance_id": "clip-isolated",
        "target_dbi_resource_id": "db-NEW",
        "remote_host": "isolated.example.invalid",
        "remote_port": 5432,
        "local_host": "127.0.0.1",
        "local_port": 15439,
        "forward_instance_id": "i-00000000000000001",
        "session_id": "owned-session-1234",
    }
    path.write_text(json.dumps(receipt))
    path.chmod(0o600)
    return plan, instance, receipt


class SSM:
    def describe_sessions(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs == {
            "State": "Active",
            "Filters": [{"key": "SessionId", "value": "owned-session-1234"}],
        }
        return {
            "Sessions": [
                {
                    "SessionId": "owned-session-1234",
                    "Target": "i-00000000000000001",
                    "DocumentName": "AWS-StartPortForwardingSessionToRemoteHost",
                }
            ]
        }


def test_tunnel_needs_exact_restored_resource_and_active_owned_forwarder(
    tmp_path: Path,
) -> None:
    p, i, _ = fixture(tmp_path)
    assert _integrity_transport_options(p, i, SSM()) == {
        "hostaddr": "127.0.0.1",
        "port": 15439,
    }
    assert _integrity_transport_options({}, i, None) == {}


@pytest.mark.parametrize(
    ("field", "wrong"),
    [
        ("target_db_instance_id", "source"),
        ("target_dbi_resource_id", "db-SOURCE"),
        ("remote_host", "source.example.invalid"),
        ("remote_port", 6432),
        ("local_port", 16432),
        ("forward_instance_id", "i-00000000000000002"),
    ],
)
def test_source_or_stale_tunnel_refused(tmp_path: Path, field: str, wrong: Any) -> None:
    p, i, r = fixture(tmp_path)
    r[field] = wrong
    Path(p["integrity_transport"]["receipt_path"]).write_text(json.dumps(r))
    with pytest.raises(ValueError, match="restored_target_mismatch"):
        _integrity_transport_options(p, i, SSM())


def test_tunnel_cannot_use_public_local_bind_or_unprotected_receipt(
    tmp_path: Path,
) -> None:
    p, i, _ = fixture(tmp_path)
    p["integrity_transport"]["hostaddr"] = "0.0.0.0"
    with pytest.raises(ValueError, match="transport_invalid"):
        _validate_integrity_transport_spec(p)
    p["integrity_transport"]["hostaddr"] = "127.0.0.1"
    Path(p["integrity_transport"]["receipt_path"]).chmod(0o644)
    with pytest.raises(ValueError, match="unsafe_integrity"):
        _integrity_transport_options(p, i, SSM())


def test_existing_ssm_password_is_read_only_and_bound_to_exact_arn() -> None:
    arn = "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/database-master-password"

    class Parameter:
        def get_parameter(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs == {"Name": arn, "WithDecryption": True}
            return {
                "Parameter": {
                    "ARN": arn,
                    "Type": "SecureString",
                    "Value": "synthetic-private",
                }
            }

    class Session:
        def client(self, name: str) -> Any:
            assert name == "ssm"
            return Parameter()

    p = {
        "credentials_source": "ssm_parameter",
        "region": "ap-south-1",
        "account_id": "335523638354",
        "secret_arn": arn,
    }
    assert _restore_credentials(p, Session(), {"MasterUsername": "existing_admin"}) == (
        "existing_admin",
        "synthetic-private",
    )
    p["secret_arn"] = arn + "-wrong"
    with pytest.raises(ValueError, match="parameter_mismatch"):
        _restore_credentials(p, Session(), {})


def test_real_micro_restore_manifest_accepts_a_valid_rds_instance_class() -> None:
    """The actual approved db.t4g.micro name includes both family and size."""
    from scripts.evaluation.nfr07_restore_observer import validate_plan

    arn = "arn:aws:ssm:ap-south-1:335523638354:parameter/clip/test/"
    smoke = {
        key: arn + key
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
            "conversations_database_parameter_arn",
        )
    }
    smoke.update(
        https_origin="https://restore.clip-iisc.site",
        identity_database_parameter_arn=arn + "nfr07/identity-database-url",
        identity_database_name="clip_next06_reference",
        conversations_database_name="clip_next06_reference",
        application_revision="a" * 40,
        container_image="example.invalid/reviewed@sha256:" + "b" * 64,
        expected_user_id="11111111-1111-4111-8111-111111111111",
        wanted_request_id="22222222-2222-4222-8222-222222222222",
    )
    plan = {
        "nfr_id": "nfr-07",
        "execution_permitted": True,
        "nfr_accepted": False,
        "run_id": "restore-real-class",
        "account_id": "335523638354",
        "region": "ap-south-1",
        "snapshot_arn": arn + "snapshot-binding",
        "snapshot_source_instance_id": "clip-source",
        "target_db_instance_id": "clip-isolated",
        "target_manifest_sha256": "c" * 64,
        "subnet_group": "clip-private",
        "security_group_ids": ["sg-00000000000000001"],
        "publicly_accessible": False,
        "multi_az": False,
        "restore_timeout_seconds": 1800,
        "db_instance_class": "db.t4g.micro",
        "database_name": "clip_next06_reference",
        "secret_arn": arn + "database-master-password",
        "credentials_source": "ssm_parameter",
        "rds_ca_bundle_path": "/tmp/approved-ca.pem",
        "rds_ca_bundle_sha256": "d" * 64,
        "expected_migration_head": "20261029182500",
        "source_snapshot_scope": "approved synthetic shared database",
        "smoke_session_file": "/tmp/isolated-private-session.cookie",
        "source_target_plan_path": ".tools/approved-target.json",
        "application_smoke_plan": smoke,
    }
    assert validate_plan(plan)["db_instance_class"] == "db.t4g.micro"
    for unsafe in ("/tmp/source-target.json", "../source-target.json"):
        plan["source_target_plan_path"] = unsafe
        with pytest.raises(
            ValueError, match="source_target_plan_must_be_repository_relative"
        ):
            validate_plan(plan)
    plan["source_target_plan_path"] = ".tools/approved-target.json"
    plan["db_instance_class"] = "t4g.micro"
    with pytest.raises(ValueError, match="invalid_db_instance_class"):
        validate_plan(plan)
