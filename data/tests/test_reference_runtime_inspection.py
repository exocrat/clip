"""Exact-account, no-secret metadata inspection controls; never contacts AWS."""

import json
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_runtime_inspection as subject


def session(*, wrong_identity=False, pagination=False):
    """Expose only approved reads and record every request; reject any mutation."""
    calls = []
    task = f"arn:aws:ecs:{subject.REGION}:{subject.ACCOUNT}:task-definition/clip-test-api-ap-south-1-pd16:11"

    def client(service, **kwargs):
        def call(operation, **params):
            calls.append((service, operation, params))
            if operation == "get_caller_identity":
                return {
                    "Account": "wrong" if wrong_identity else subject.ACCOUNT,
                    "Arn": f"arn:aws:iam::{subject.ACCOUNT}:user/{subject.PROFILE}",
                }
            if operation == "describe_services":
                return {"services": [{"taskDefinition": task, "desiredCount": 0}]}
            if operation == "describe_task_definition":
                return {
                    "taskDefinition": {
                        "containerDefinitions": [
                            {
                                "name": "api",
                                "image": "approved-image",
                                "environment": [
                                    {"name": "SECRET", "value": "must-never-appear"},
                                    {
                                        "name": "CLIP_HYBRID_SEARCH_ENABLED",
                                        "value": "false",
                                    },
                                ],
                                "secrets": [
                                    {
                                        "name": "CLIP_DATABASE_URL",
                                        "valueFrom": "not-output",
                                    }
                                ],
                            }
                        ]
                    }
                }
            if operation == "describe_instances":
                return {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": "i-086045c48487471de",
                                    "InstanceType": "t3.micro",
                                    "State": {"Name": "stopped"},
                                }
                            ]
                        }
                    ]
                }
            if operation == "describe_db_instances":
                return {
                    "DBInstances": [
                        {
                            "DBInstanceIdentifier": "clip-shared-test-postgres",
                            "DBInstanceStatus": "stopped",
                            "EngineVersion": "18.6",
                            "PubliclyAccessible": False,
                        }
                    ]
                }
            if operation == "describe_parameters":
                return {
                    "Parameters": [],
                    **({"NextToken": "stop"} if pagination else {}),
                }
            raise AssertionError("Unapproved AWS operation")

        return SimpleNamespace(
            close=lambda: None,
            **{
                op: lambda _op=op, **params: call(_op, **params)
                for op in (
                    "get_caller_identity",
                    "describe_services",
                    "describe_task_definition",
                    "describe_instances",
                    "describe_db_instances",
                    "describe_parameters",
                )
            },
        )

    return SimpleNamespace(client=client), calls


def test_exact_read_scope_and_redacted_output():
    sdk, calls = session()
    result = subject.inspect(sdk)
    assert len(calls) == result["api_calls"] == 10
    assert result["secret_values_read"] == result["mutations"] == 0
    assert "must-never-appear" not in json.dumps(result)
    assert "not-output" not in json.dumps(result)
    assert all(c[1] != "get_parameter" for c in calls)


def test_wrong_account_stops_before_other_reads():
    sdk, calls = session(wrong_identity=True)
    with pytest.raises(ValueError, match="identity_mismatch"):
        subject.inspect(sdk)
    assert len(calls) == 1


def test_pagination_never_expands_scope():
    sdk, calls = session(pagination=True)
    with pytest.raises(ValueError, match="unexpected_pagination"):
        subject.inspect(sdk)
    assert len(calls) == 6


def test_no_approval_flag_never_constructs_sdk(monkeypatch):
    def forbidden(*args):
        raise AssertionError("SDK constructed before approval guard")

    monkeypatch.setattr(subject, "sdk_session", forbidden)
    with pytest.raises(SystemExit):
        subject.main([])
