"""Schema-neutral synthetic references and clocks for project tests only."""

from clip_test_fixtures.privacy import redact_snapshot
from clip_test_fixtures.providers import (
    Fail,
    Return,
    ScriptExhausted,
    ScriptedTestProvider,
    TestProviderFailure,
    make_test_provider,
)
from clip_test_fixtures.samples import (
    SyntheticClock,
    SyntheticIds,
    make_synthetic_clock,
    make_synthetic_ids,
)

from clip_test_fixtures.scenarios import (
    AsyncBarrier,
    ProviderScenarios,
    ValidationCase,
    make_provider_scenarios,
    make_unauthenticated_callers,
    make_validation_cases,
)

__all__ = [
    "redact_snapshot",
    "AsyncBarrier",
    "ProviderScenarios",
    "ValidationCase",
    "make_provider_scenarios",
    "make_unauthenticated_callers",
    "make_validation_cases",
    "Fail",
    "Return",
    "ScriptExhausted",
    "ScriptedTestProvider",
    "TestProviderFailure",
    "make_test_provider",
    "SyntheticClock",
    "SyntheticIds",
    "make_synthetic_clock",
    "make_synthetic_ids",
]
