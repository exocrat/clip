"""Check safe targeting and fallback decisions in the LI-02 cloud driver."""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from contextlib import nullcontext
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[5]
DRIVER_PATH = ROOT / "scripts/li02-demo"
RUNTIME_TERRAFORM_PATH = ROOT / "infra/terraform/domains/listings/test/ecs_runtime.tf"


def load_driver() -> ModuleType:
    """Load the executable script as a module for isolated decision tests."""
    loader = SourceFileLoader("li02_demo_driver", str(DRIVER_PATH))
    spec = importlib.util.spec_from_loader("li02_demo_driver", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capacity_error_replans_only_in_second_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The 1a retry follows an explicit 1b capacity error and fresh absence checks."""
    driver = load_driver()
    attempts: list[dict[str, str | None]] = []
    saved: list[dict[str, object]] = []

    def apply(variables, **_kwargs):
        attempts.append(variables)
        if variables["demo_database_availability_zone"] == "ap-south-1b":
            raise driver.InsufficientRdsCapacity("explicit capacity error")

    monkeypatch.setattr(driver, "terraform_apply_plan", apply)
    monkeypatch.setattr(driver, "state_addresses", lambda: [])
    monkeypatch.setattr(
        driver, "aws_json", lambda *_args, **_kwargs: {"DBInstances": []}
    )
    monkeypatch.setattr(
        driver, "save_baseline", lambda value: saved.append(value.copy())
    )

    baseline = {"rds_capacity_unavailable_zones": []}
    driver.apply_initial_infrastructure_with_rds_fallback(
        "surajs2", {"demo_enabled": "true"}, baseline
    )

    assert [item["demo_database_availability_zone"] for item in attempts] == [
        "ap-south-1b",
        "ap-south-1a",
    ]
    assert baseline["database_availability_zone"] == "ap-south-1a"
    assert baseline["rds_capacity_unavailable_zones"] == ["ap-south-1b"]
    assert len(saved) == 2


def test_generic_apply_failure_does_not_try_second_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A generic plan/apply failure never authorizes an AZ fallback."""
    driver = load_driver()
    attempts: list[str | None] = []

    def apply(variables, **_kwargs):
        attempts.append(variables["demo_database_availability_zone"])
        raise driver.DemoError("generic apply failure")

    monkeypatch.setattr(driver, "terraform_apply_plan", apply)
    baseline = {"rds_capacity_unavailable_zones": []}
    with pytest.raises(driver.DemoError, match="generic apply failure"):
        driver.apply_initial_infrastructure_with_rds_fallback(
            "surajs2", {"demo_enabled": "true"}, baseline
        )

    assert attempts == ["ap-south-1b"]
    assert baseline["rds_capacity_unavailable_zones"] == []


def test_capacity_failure_with_partial_database_stops_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any database state after the capacity error blocks the alternate plan."""
    driver = load_driver()
    attempts: list[str | None] = []

    def apply(variables, **_kwargs):
        attempts.append(variables["demo_database_availability_zone"])
        raise driver.InsufficientRdsCapacity("explicit capacity error")

    monkeypatch.setattr(driver, "terraform_apply_plan", apply)
    monkeypatch.setattr(
        driver,
        "state_addresses",
        lambda: ["aws_db_instance.demo[0]"],
    )
    monkeypatch.setattr(
        driver, "aws_json", lambda *_args, **_kwargs: {"DBInstances": []}
    )
    baseline = {"rds_capacity_unavailable_zones": []}

    with pytest.raises(driver.DemoError, match="partial LI-02 RDS state"):
        driver.apply_initial_infrastructure_with_rds_fallback(
            "surajs2", {"demo_enabled": "true"}, baseline
        )

    assert attempts == ["ap-south-1b"]
    assert baseline["rds_capacity_unavailable_zones"] == []


def test_saved_plan_apply_classifies_only_explicit_rds_capacity_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Only the known AWS error is classified for retry; raw output stays hidden."""
    driver = load_driver()
    driver.ACTIVE_PROFILE = "surajs2"
    monkeypatch.setattr(
        driver.tempfile,
        "TemporaryDirectory",
        lambda **_kwargs: nullcontext(tmp_path),
    )

    def command(args, **_kwargs):
        if "plan" in args:
            plan = next(
                item.removeprefix("-out=") for item in args if item.startswith("-out=")
            )
            Path(plan).write_bytes(b"saved-plan")
        if "show" in args:
            return "reviewed plan"
        return ""

    monkeypatch.setattr(driver, "command", command)
    monkeypatch.setattr(driver, "require_approval", lambda *_args: None)
    monkeypatch.setattr(
        driver.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=(
                "Error: creating RDS: InsufficientDBInstanceCapacity\n"
                "  with aws_db_instance.demo[0],"
            ),
            stderr="",
        ),
    )

    with pytest.raises(driver.InsufficientRdsCapacity):
        driver.terraform_apply_plan({"demo_enabled": "true"}, detect_rds_capacity=True)

    with pytest.raises(driver.DemoError, match="failed during apply"):
        monkeypatch.setattr(
            driver.subprocess,
            "run",
            lambda *_args, **_kwargs: SimpleNamespace(
                returncode=1,
                stdout=(
                    "Error: creating RDS: InsufficientDBInstanceCapacity\n"
                    "  with aws_db_instance.demo[0],\n"
                    "Error: unrelated resource failure"
                ),
                stderr="private provider details",
            ),
        )
        driver.terraform_apply_plan({"demo_enabled": "true"}, detect_rds_capacity=True)


def test_database_task_targets_only_dedicated_cluster_and_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one-shot task is placed on the isolated LI-02 capacity provider."""
    driver = load_driver()
    calls: list[tuple[str, ...]] = []
    responses = [
        {"taskDefinition": {"taskDefinitionArn": "arn:task-definition"}},
        {"tasks": [{"taskArn": "arn:task"}]},
        {"tasks": [{"lastStatus": "STOPPED", "containers": [{"exitCode": 0}]}]},
    ]

    def aws_json(_profile, *args, **_kwargs):
        calls.append(tuple(args))
        return responses.pop(0)

    monkeypatch.setattr(driver, "aws_json", aws_json)
    monkeypatch.setattr(driver, "command", lambda args, **_kwargs: "")

    driver.run_task("surajs2", "cleanup")

    run_task_call = calls[1]
    assert run_task_call[run_task_call.index("--cluster") + 1] == driver.CLUSTER
    assert (
        f"capacityProvider={driver.CAPACITY_PROVIDER},weight=1,base=1" in run_task_call
    )
    assert driver.CLUSTER == "clip-test-listings-ap-south-1-li02"
    assert driver.CAPACITY_PROVIDER == "clip-test-listings-capacity-ap-south-1-li02"


def test_stop_targets_only_the_owned_host_and_root_volume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host teardown scales only the LI-02 ASG and checks its tagged root disk."""
    driver = load_driver()
    initial = {
        "auto_scaling_group": driver.AUTO_SCALING_GROUP,
        "desired_capacity": 1,
        "instances": [{"instance_id": "i-demo", "lifecycle_state": "InService"}],
    }
    stopped = {
        "auto_scaling_group": driver.AUTO_SCALING_GROUP,
        "desired_capacity": 0,
        "instances": [],
    }
    capacities = [initial, stopped]
    aws_calls: list[tuple[str, ...]] = []
    prompts: list[tuple[str, str]] = []

    monkeypatch.setattr(
        driver, "li02_capacity_group", lambda _profile: capacities.pop(0)
    )
    monkeypatch.setattr(driver, "ensure_li02_ecs_idle", lambda _profile: None)
    monkeypatch.setattr(
        driver,
        "aws_json",
        lambda _profile, *args, **_kwargs: (
            aws_calls.append(tuple(args)) or {"Volumes": []}
        ),
    )
    monkeypatch.setattr(
        driver,
        "aws",
        lambda _profile, *args, **_kwargs: aws_calls.append(tuple(args)),
    )
    monkeypatch.setattr(
        driver,
        "require_approval",
        lambda prompt, expected: prompts.append((prompt, expected)),
    )
    monkeypatch.setattr(driver.time, "sleep", lambda _seconds: None)

    driver.wait_for_li02_host_removed("surajs2")

    assert prompts == []
    set_capacity = next(call for call in aws_calls if "set-desired-capacity" in call)
    assert (
        set_capacity[set_capacity.index("--auto-scaling-group-name") + 1]
        == driver.AUTO_SCALING_GROUP
    )
    volume_check = next(call for call in aws_calls if "describe-volumes" in call)
    assert f"Name=tag:Name,Values={driver.ROOT_VOLUME_NAME}" in volume_check
    assert all(driver.CLUSTER not in " ".join(call) for call in aws_calls)


def test_ecs_host_bootstrap_blocks_bridge_tasks_from_instance_metadata() -> None:
    """The durable host firewall protects EC2 instance credentials from tasks."""
    runtime = RUNTIME_TERRAFORM_PATH.read_text(encoding="utf-8")

    assert "169.254.169.254/32" in runtime
    assert "-i docker+" in runtime
    assert "Before=ecs.service" in runtime
    assert "systemctl enable --now clip-li02-block-task-imds.service" in runtime


@pytest.mark.parametrize(
    ("helper_name", "approved_field", "phrase_prefix"),
    [
        ("authorize_start", "start_authorized", "START LI02 DEMO "),
        ("authorize_stop", "stop_authorized", "STOP LI02 DEMO "),
    ],
)
def test_run_confirmation_is_saved_and_not_repeated(
    monkeypatch: pytest.MonkeyPatch,
    helper_name: str,
    approved_field: str,
    phrase_prefix: str,
) -> None:
    """The single start/stop confirmation persists across safe retry attempts."""
    driver = load_driver()
    approvals: list[tuple[str, str]] = []
    saved: list[dict[str, object]] = []
    monkeypatch.setattr(
        driver,
        "require_approval",
        lambda prompt, expected: approvals.append((prompt, expected)),
    )
    monkeypatch.setattr(
        driver, "save_baseline", lambda value: saved.append(value.copy())
    )
    baseline: dict[str, object] = {"run_id": "li02-unit-test"}

    getattr(driver, helper_name)(baseline)
    getattr(driver, helper_name)(baseline)

    assert len(approvals) == 1
    assert approvals[0][1] == f"{phrase_prefix}li02-unit-test"
    assert baseline[approved_field] is True
    assert len(saved) == 1
