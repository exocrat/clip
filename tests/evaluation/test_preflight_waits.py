"""Bound preparation waits without accepting a wrong target or retrying traffic."""

from __future__ import annotations
from typing import Any
import pytest
from scripts.evaluation.k6 import real_target_preflight as target


def test_dns_and_backup_transients_reinspect_full_target(monkeypatch: Any) -> None:
    clock = [0.0]
    observed = []
    calls = []
    outcomes = iter(
        ["origin_dns_load_balancer_mismatch", "database_backup_in_progress", None]
    )

    def inspect(plan: Any, factory: Any) -> dict[str, Any]:
        calls.append(plan)
        code = next(outcomes)
        if code:
            raise ValueError(code)
        return {"infrastructure_preflight_valid": True}

    monkeypatch.setattr(target, "_inspect_target_once", inspect)
    result = target.inspect_target(
        {},
        monotonic=lambda: clock[0],
        sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
        observe=observed.append,
    )
    assert result["infrastructure_preflight_valid"] and len(calls) == 3
    assert [x["reason"] for x in observed] == [
        "origin_dns_load_balancer_mismatch",
        "database_backup_in_progress",
    ]


@pytest.mark.parametrize(
    "code",
    [
        "database_account_mismatch",
        "database_state_mismatch",
        "aws_account_mismatch",
        "selected_route_weights_mismatch",
    ],
)
def test_confirmed_drift_never_waits(monkeypatch: Any, code: str) -> None:
    def inspect(*args: Any) -> Any:
        raise ValueError(code)

    monkeypatch.setattr(target, "_inspect_target_once", inspect)
    with pytest.raises(ValueError, match=code):
        target.inspect_target(
            {}, sleep=lambda _: pytest.fail("must not wait on confirmed drift")
        )


@pytest.mark.parametrize(
    ("code", "limit"),
    [("origin_dns_load_balancer_mismatch", 180), ("database_backup_in_progress", 900)],
)
def test_unresolved_target_is_still_refused_at_bound(
    monkeypatch: Any, code: str, limit: int
) -> None:
    clock = [0.0]

    def inspect(*args: Any) -> Any:
        raise ValueError(code)

    monkeypatch.setattr(target, "_inspect_target_once", inspect)
    with pytest.raises(ValueError, match=code):
        target.inspect_target(
            {},
            monotonic=lambda: clock[0],
            sleep=lambda s: clock.__setitem__(0, clock[0] + s),
            observe=lambda _: None,
        )
    assert clock[0] == limit
