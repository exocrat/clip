"""Use real botocore exception models for safe nonexistent-restore handling."""

from botocore.session import get_session
from botocore.stub import Stubber
from botocore.exceptions import ClientError
import pytest
from scripts.evaluation.nfr07_restore_observer import (
    describe_optional_instance,
    failure_code,
)


def client():
    return get_session().create_client(
        "rds",
        region_name="ap-south-1",
        aws_access_key_id="synthetic",
        aws_secret_access_key="synthetic",
        endpoint_url="https://synthetic.example.invalid",
    )


def test_real_sdk_missing_instance_is_expected_without_restore_or_network():
    rds = client()
    with Stubber(rds) as stub:
        stub.add_client_error(
            "describe_db_instances",
            service_error_code="DBInstanceNotFound",
            service_message="Synthetic missing target",
            http_status_code=404,
            expected_params={"DBInstanceIdentifier": "synthetic-restore-target"},
        )
        assert describe_optional_instance(rds, "synthetic-restore-target") is None
        stub.assert_no_pending_responses()


def test_provider_or_permission_error_is_not_mistaken_for_missing_target():
    rds = client()
    with Stubber(rds) as stub:
        stub.add_client_error(
            "describe_db_instances",
            service_error_code="AccessDenied",
            http_status_code=403,
            expected_params={"DBInstanceIdentifier": "synthetic-restore-target"},
        )
        with pytest.raises(ClientError):
            describe_optional_instance(rds, "synthetic-restore-target")


def test_failure_diagnostics_keep_codes_and_reject_private_prose():
    assert failure_code(ValueError("unsafe_input_path")) == "unsafe_input_path"
    assert (
        failure_code(ValueError("postgresql://private:secret@example.invalid"))
        == "ValueError"
    )
    error = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "PRIVATE provider prose"}},
        "DescribeDBInstances",
    )
    assert failure_code(error) == "AccessDenied"
