"""Isolation shared by the API foundation tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_api_environment(monkeypatch):
    """Discard developer API/AWS settings and restore them after each test.

    Tests select synthetic configuration explicitly and must not need credentials
    or accidentally use a developer's local settings. Values are never logged.
    """
    for name in tuple(os.environ):
        if name.startswith(("CLIP_", "AWS_")):
            monkeypatch.delenv(name)
