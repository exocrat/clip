"""Producer target/expiry/uncertainty/budget controls; native run proves real SQL/model."""

import asyncio
from contextlib import nullcontext
from datetime import datetime, UTC, timedelta
from types import SimpleNamespace

import pytest

from scripts.evaluation import reference_vector_access as access
from scripts.evaluation import reference_vector_pipeline as pipeline


class Connection:
    def __init__(self, failure=None):
        self.failure = failure
        self.calls = []

    def transaction(self):
        return nullcontext()

    def execute(self, statement, args=None):
        self.calls.append(statement)
        row = None
        if isinstance(statement, str):
            if "SELECT oid FROM pg_roles" in statement:
                row = (55,) if self.failure == "existing" else None
            elif "count(*) FROM pg_roles" in statement:
                row = (1 if self.failure == "runtime" else 2,)
            elif "SELECT (SELECT count" in statement:
                row = (1000, 1, 0, 0) if self.failure == "pipeline" else (1000, 0, 0, 0)
            elif "aclexplode" in statement:
                row = ("other_application",) if self.failure == "public" else None
            elif "SELECT oid,rolcanlogin" in statement:
                row = (123,) + (False,) * 7
            elif "SELECT oid,rolsuper" in statement:
                row = (999 if self.failure == "oid" else 123,) + (False,) * 6
            elif "SELECT rolcanlogin" in statement:
                row = (False,)
        elif self.failure == "uncertain":
            raise RuntimeError("synthetic-private-value")
        return SimpleNamespace(fetchone=lambda: row)


@pytest.fixture(autouse=True)
def no_transport(monkeypatch):
    monkeypatch.setattr(access, "guard_admin", lambda *args, **kwargs: None)


@pytest.mark.parametrize("failure", ["existing", "runtime", "pipeline", "public"])
def test_existing_or_unsafe_state_never_creates_role(failure):
    c = Connection(failure)
    instance = access.VectorAccess()
    with pytest.raises(access.LoadAccessRefused):
        instance.activate(
            c,
            expires=datetime.now(UTC) + timedelta(minutes=30),
            record=lambda **event: None,
        )
    assert not any(
        isinstance(s, str) and s.startswith(("CREATE ", "GRANT ", "ALTER "))
        for s in c.calls
    )


@pytest.mark.parametrize("seconds", [-1, 60, 3000])
def test_producer_expiry_is_short_and_explicit(seconds):
    c = Connection()
    with pytest.raises(access.LoadAccessRefused):
        access.VectorAccess().activate(
            c,
            expires=datetime.now(UTC) + timedelta(seconds=seconds),
            record=lambda **event: None,
        )
    assert not c.calls


def test_uncertain_activation_is_not_repeated_and_cleanup_binds_oid():
    instance = access.VectorAccess()
    events = []
    with pytest.raises(RuntimeError):
        instance.activate(
            Connection("uncertain"),
            expires=datetime.now(UTC) + timedelta(minutes=30),
            record=lambda **event: events.append(event),
        )
    assert instance.attempted and events[-1]["stage"] == "vector_activation_attempt"
    with pytest.raises(access.LoadAccessRefused, match="already_attempted"):
        instance.activate(
            Connection(),
            expires=datetime.now(UTC) + timedelta(minutes=30),
            record=lambda **event: None,
        )
    with pytest.raises(access.LoadAccessRefused, match="cleanup_ownership"):
        instance.close(Connection("oid"), record=lambda **event: None)
    instance.close(Connection(), record=lambda **event: events.append(event))
    assert instance.closed and events[-1]["stage"] == "vector_disabled_password_cleared"
    assert "synthetic-private-value" not in str(events)


def test_unattempted_close_never_modifies_another_role():
    c = Connection()
    access.VectorAccess().close(c, record=lambda **event: None)
    assert not c.calls


@pytest.mark.parametrize("operation", ["listing", "query"])
def test_model_window_budget_refuses_before_process_or_model(operation):
    helper = pipeline.VectorHelper.__new__(pipeline.VectorHelper)
    helper.windows_started = 2400

    async def run():
        with pytest.raises(pipeline.HelperUnavailable, match="window_budget"):
            if operation == "listing":
                await helper.encode_listing("synthetic title", "synthetic description")
            else:
                await helper.encode_query("synthetic query")

    asyncio.run(run())


@pytest.mark.parametrize(
    "state,live,conflict",
    [("serving", 1000, False), ("absent", 999, False), ("absent", 1000, True)],
)
def test_occupied_or_changed_scope_never_prepares_pipeline(
    monkeypatch, state, live, conflict
):
    class Operator:
        def __init__(self, connection):
            pass

        async def status(self):
            return SimpleNamespace(state=state, live=live, conflicting_serving=conflict)

        async def prepare(self):
            pytest.fail("Refused pipeline reached mutation")

    monkeypatch.setattr(pipeline, "EmbeddingBootstrap", Operator)
    with pytest.raises(ValueError, match="fresh_vector_pipeline"):
        asyncio.run(pipeline.produce(None, None, record=lambda **event: None))


def test_wrong_actual_producer_is_rejected_before_transport_or_mutation():
    class Result:
        async def fetchone(self):
            return {
                "db": "clip_next06_reference",
                "role": "wrong",
                "login": "wrong",
                "version": "180006",
            }

    async def execute(statement):
        return Result()

    with pytest.raises(ValueError, match="actual_vector_producer_target"):
        asyncio.run(
            pipeline.guard_producer(SimpleNamespace(autocommit=True, execute=execute))
        )


@pytest.mark.parametrize(
    "ready,closed,expected",
    [
        (1000, True, "vectors_published_resources_stopped"),
        (999, True, "vector_window_failed_resources_stopped"),
        (1000, False, "cleanup_pending_operator_attention"),
    ],
)
def test_partial_coverage_or_unclosed_access_cannot_pass(ready, closed, expected):
    report = {
        "resource_start_attempts": {"rds": True, "ec2": True},
        "cleanup": {
            "host_stopped": True,
            "rds_stopped": True,
            "vector_disabled_password_cleared": closed,
            "owned_model_closed": True,
            "owned_tunnel_exited": True,
            "owned_session_terminated": True,
        },
        "vector_passed": True,
        "vector_result": {
            "coverage": {
                "state": "serving",
                "live": 1000,
                "ready": ready,
                **{
                    k: 0
                    for k in (
                        "missing",
                        "stale",
                        "pending",
                        "leased",
                        "failed",
                        "invalid_parts",
                    )
                },
            }
        },
    }
    assert pipeline.window_outcome(report) == expected
