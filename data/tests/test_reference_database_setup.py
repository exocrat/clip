"""Setup refusal/order/failure controls; native harness proves actual SQL rights."""

from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_database_setup as setup


@pytest.fixture
def binding(tmp_path, monkeypatch):
    """Recreate the frozen 29-migration checkout, without changing its binding.

    Newer branch migrations must not alter this historical rehearsal or weaken
    the production guard that rejects an unreviewed migration set.
    """
    source_root = setup.ROOT
    binding = json.loads(
        Path("data/runs/next06-transfer-42-20261030-a/manifest.json").read_text()
    )["source_binding"]
    for entry in binding["files"]:
        if entry["path"].startswith("database/migrations/"):
            source = source_root / entry["path"]
            target = tmp_path / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    monkeypatch.setattr(setup, "ROOT", tmp_path)
    return binding


def test_only_bound_up_sections_are_prepared(binding):
    result = setup.migration_sources(binding)
    assert len(result) == 29
    assert [v for v, _ in result] == binding["migration_versions"]
    assert all("-- migrate:down" not in text for _, text in result)


@pytest.mark.parametrize("change", ["hash", "missing", "versions"])
def test_changed_migrations_refuse_before_database_access(binding, change):
    value = deepcopy(binding)
    if change == "hash":
        value["files"][0]["sha256"] = "0" * 64
    elif change == "missing":
        value["files"].pop(0)
    else:
        value["migration_versions"].pop()
    with pytest.raises(setup.SetupRefused):
        setup.migration_sources(value)


def test_unbound_checkout_migration_is_refused(binding):
    """A newer schema cannot silently enter a frozen reference database."""
    extra = setup.ROOT / "database/migrations/20990101000000_unreviewed.sql"
    extra.write_text("-- migrate:up\nSELECT 1;\n-- migrate:down\nSELECT 1;\n")
    with pytest.raises(setup.SetupRefused, match="migration_set_changed"):
        setup.migration_sources(binding)


class Control:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def transaction(self):
        return nullcontext()

    def execute(self, statement, args=None):
        self.calls.append(statement)
        row = None
        rows = []
        if "SELECT rolcreatedb" in statement:
            row = (True, True)
        if "SELECT datname" in statement and self.failure == "database":
            row = (setup.DATABASE,)
        if "SELECT rolname" in statement and self.failure == "role":
            rows = [(setup.LOADER,)]
        if "aclexplode" in statement and self.failure == "public":
            row = ("other_application",)
        if (
            statement.startswith("CREATE DATABASE")
            and self.failure == "create_uncertain"
        ):
            raise RuntimeError("private-error")
        return SimpleNamespace(fetchone=lambda: row, fetchall=lambda: rows)


@pytest.mark.parametrize("failure", ["database", "role", "public"])
def test_preexisting_or_public_application_access_prevents_writes(
    binding, monkeypatch, failure
):
    monkeypatch.setattr(setup, "guard", lambda *args, **kwargs: None)
    control = Control(failure)
    with pytest.raises(setup.SetupRefused):
        setup.prepare(
            control,
            lambda: pytest.fail("Target connection forbidden"),
            binding,
            record=lambda **kwargs: None,
        )
    assert not any(
        s.startswith(("CREATE ", "ALTER ", "GRANT ", "REVOKE ")) for s in control.calls
    )


def test_uncertain_create_retains_stage_and_never_retries_or_drops(
    binding, monkeypatch
):
    monkeypatch.setattr(setup, "guard", lambda *args, **kwargs: None)
    events = []
    control = Control("create_uncertain")
    with pytest.raises(RuntimeError):
        setup.prepare(
            control,
            lambda: pytest.fail("Target connection forbidden"),
            binding,
            record=lambda **event: events.append(event),
        )
    assert events[-1] == {"stage": "database_create_attempt"}
    assert sum(s.startswith("CREATE DATABASE") for s in control.calls) == 1
    assert not any(s.startswith("DROP ") for s in control.calls)
    assert all("NOLOGIN" in s for s in control.calls if s.startswith("CREATE ROLE"))


def test_target_connect_failure_leaves_inactive_roles_without_cleanup_mutation(
    binding, monkeypatch
):
    monkeypatch.setattr(setup, "guard", lambda *args, **kwargs: None)
    events = []
    control = Control()

    def failed():
        raise RuntimeError("private-connection-error")

    with pytest.raises(RuntimeError):
        setup.prepare(
            control, failed, binding, record=lambda **event: events.append(event)
        )
    assert events[-1] == {"stage": "database_opened_with_private_acl"}
    assert not any(" LOGIN" in s or s.startswith("DROP ") for s in control.calls)
    statements = control.calls
    disabled = next(
        i for i, s in enumerate(statements) if s.startswith("CREATE DATABASE")
    )
    revoke = next(
        i for i, s in enumerate(statements) if s.startswith("REVOKE ALL ON DATABASE")
    )
    enabled = next(i for i, s in enumerate(statements) if "ALLOW_CONNECTIONS true" in s)
    assert disabled < revoke < enabled


def test_autocommit_guard_prevents_false_committed_stage():
    with pytest.raises(
        setup.SetupRefused, match="autocommit_required_for_create_database"
    ):
        setup.guard(SimpleNamespace(autocommit=False), "clip_test")
