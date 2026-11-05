"""Check import isolation in a fresh process, unaffected by other tests' imports."""

import os
from pathlib import Path
import subprocess
import sys


def test_listing_only_startup_skips_full_app_modules_but_full_startup_loads_them():
    """Keep Lambda small without moving full-app work into its first request."""
    code = """
import asyncio
import sys
from app.application import create_app, application_lifespan
from app.core.config import Settings
settings = Settings()
create_app(settings, listings_read_only=True)
modules = [
    'app.domains.conversations.routes',
    'app.domains.search.wanted_routes',
    'app.domains.search.saved_routes',
]
notifications = 'app.domains.conversations.notifications.runtime'
assert all(name not in sys.modules for name in [*modules, notifications])
full = create_app(settings)
assert all(name in sys.modules for name in modules)
async def check_lifespan():
    async with application_lifespan(full, settings):
        assert notifications in sys.modules
asyncio.run(check_lifespan())
"""
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
