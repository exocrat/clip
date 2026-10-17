"""Keep fixture-library checks independent of developer runtime/provider settings."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolate_fixture_environment(monkeypatch):
    """Discard inherited CLIP/AWS settings for these tests and restore them afterward."""
    for name in tuple(os.environ):
        if name.startswith(("CLIP_", "AWS_")):
            monkeypatch.delenv(name)
