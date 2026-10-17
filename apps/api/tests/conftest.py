"""Isolation shared by the API foundation tests."""

import os

import pytest

# Importing decorated functions makes the shared fixtures available to API tests.
# Their module defines no autouse behavior and never establishes HTTP identity.
from clip_test_fixtures.pytest_fixtures import (
    concurrency_barrier,
    expected_errors,
    provider_scenarios,
    regular_caller,
    synthetic_clock,
    synthetic_ids,
    temporary_caller,
    unauthenticated_callers,
    validation_cases,
)


@pytest.fixture(autouse=True)
def isolate_api_environment(monkeypatch):
    """Discard developer API/AWS settings and restore them after each test.

    Tests select synthetic configuration explicitly and must not need credentials
    or accidentally use a developer's local settings. Values are never logged.
    """
    for name in tuple(os.environ):
        if name.startswith(("CLIP_", "AWS_")):
            monkeypatch.delenv(name)
