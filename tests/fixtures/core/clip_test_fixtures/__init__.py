"""Schema-neutral synthetic references and clocks for project tests only."""

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

__all__ = [
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
