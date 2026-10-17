"""Consume shared scenario fixtures without implementing domain business policies."""

import asyncio
from dataclasses import FrozenInstanceError

import pytest
from starlette.requests import Request

from app.core.auth import CallerContext, require_caller
from app.core.config import load_settings
from app.core.errors import PublicError
from app.core.identifiers import parse_id
from app.core.money import validate_paise
from app.core.pagination import PageRequest
from app.core.timestamps import parse_timestamp
from clip_test_fixtures import (
    AsyncBarrier,
    TestProviderFailure,
    make_test_provider,
    make_validation_cases,
)


@pytest.fixture
def script_settings(monkeypatch):
    """Explicitly select only test helpers for this test module, restoring settings later."""
    monkeypatch.setenv("CLIP_ENVIRONMENT", "test")
    for kind in ("identity", "email", "storage"):
        monkeypatch.setenv("CLIP_" + kind.upper() + "_PROVIDER", "fake")
    return load_settings()


def test_retry_scenario_requires_a_second_explicit_call(
    script_settings, provider_scenarios, synthetic_ids
):
    """No retry occurs until the consumer repeats the operation deliberately."""
    provider = make_test_provider(script_settings, "storage", provider_scenarios.retry)
    with pytest.raises(TestProviderFailure):
        asyncio.run(provider.call())
    assert provider.call_count == 1 and provider.remaining == 1
    assert asyncio.run(provider.call()) == synthetic_ids.listing_id
    assert provider.call_count == 2


def test_duplicate_request_scenario_preserves_both_attempts(
    script_settings, provider_scenarios, synthetic_ids
):
    """Repeated identical calls remain observable; no domain deduplication is claimed."""
    provider = make_test_provider(
        script_settings, "storage", provider_scenarios.duplicate
    )
    assert asyncio.run(provider.call()) == synthetic_ids.listing_id
    assert asyncio.run(provider.call()) == synthetic_ids.listing_id
    assert provider.call_count == 2


def test_concurrency_fixture_forces_overlap(
    script_settings, provider_scenarios, synthetic_ids, concurrency_barrier
):
    """Both consumers enter before release, then consume distinct scripted outcomes."""
    provider = make_test_provider(
        script_settings, "storage", provider_scenarios.concurrent
    )
    entered = []

    async def scenario():
        """Run bounded concurrent consumers with a deterministic shared rendezvous."""

        async def worker(name):
            """Enter the shared gate before consuming one provider outcome."""
            entered.append(name)
            await concurrency_barrier.wait()
            assert len(entered) == 2
            return await provider.call()

        return await asyncio.wait_for(
            asyncio.gather(worker("first"), worker("second")), timeout=2
        )

    results = asyncio.run(scenario())
    assert set(results) == {synthetic_ids.listing_id, synthetic_ids.other_listing_id}
    assert provider.call_count == 2 and provider.remaining == 0


def test_partial_failure_scripts_keep_results_separate(
    script_settings, provider_scenarios, synthetic_ids
):
    """Independent scripts supply a success and a downstream failure, not a DB transaction."""
    primary = make_test_provider(script_settings, "storage", provider_scenarios.primary)
    downstream = make_test_provider(
        script_settings, "email", provider_scenarios.downstream
    )
    result = asyncio.run(primary.call())
    with pytest.raises(TestProviderFailure) as captured:
        asyncio.run(downstream.call())
    assert captured.value.reason == "unavailable"
    assert result == synthetic_ids.listing_id
    assert primary.call_count == downstream.call_count == 1


def test_unauthenticated_cases_are_rejected_with_explicit_clock(
    unauthenticated_callers, synthetic_clock
):
    """Missing/untyped contexts fail the dependency; expiry uses deterministic test time."""
    assert set(unauthenticated_callers) == {"missing", "untyped", "expired"}
    for caller in unauthenticated_callers.values():
        with pytest.raises(PublicError) as captured:
            if isinstance(caller, CallerContext):
                caller.require_current(synthetic_clock.now)
            else:
                asyncio.run(
                    require_caller(Request({"type": "http", "clip.caller": caller}))
                )
        assert captured.value.spec.status == 401
        assert captured.value.spec.code == "unauthenticated"
    with pytest.raises(TypeError):
        unauthenticated_callers["missing"] = None


def validate_case(case):
    """Apply the real shared helper selected by a reviewed synthetic rule name."""
    match case.rule:
        case "uuid":
            return parse_id(case.value)
        case "timestamp":
            return parse_timestamp(case.value)
        case "money":
            return validate_paise(case.value)
        case "page":
            return PageRequest(page=case.value)
        case "page_size":
            return PageRequest(page_size=case.value)
        case _:
            raise AssertionError("Unknown synthetic validation rule")


@pytest.mark.parametrize("case_name", [case.name for case in make_validation_cases()])
def test_validation_boundary_fixtures_match_shared_rules(case_name, validation_cases):
    """Case IDs expose safe names only while the actual shared helpers enforce bounds."""
    case = next(item for item in validation_cases if item.name == case_name)
    if case.valid:
        validate_case(case)
    else:
        with pytest.raises(ValueError):
            validate_case(case)


def test_scenario_scripts_and_case_metadata_cannot_be_reassigned(
    provider_scenarios, validation_cases
):
    """Shared inputs remain immutable between tests; representation omits case values."""
    with pytest.raises(FrozenInstanceError):
        provider_scenarios.retry = ()
    with pytest.raises(FrozenInstanceError):
        validation_cases[0].value = "changed"
    assert "00000000" not in repr(validation_cases[0])


@pytest.mark.parametrize("parties", [0, -1, True, 1.5])
def test_concurrency_gate_rejects_invalid_task_counts(parties):
    """A malformed gate cannot silently create a permanently blocked test."""
    with pytest.raises(ValueError):
        AsyncBarrier(parties)


def test_concurrency_gate_is_one_use():
    """A completed gate rejects extra participants instead of reusing stale state."""
    gate = AsyncBarrier(1)
    asyncio.run(gate.wait())
    with pytest.raises(AssertionError, match="participant limit"):
        asyncio.run(gate.wait())
