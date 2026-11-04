"""Offline contract and lifecycle checks for the narrow Lambda composition."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

from fastapi import FastAPI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import SecretStr

import app.application as composition
from app.application import application_lifespan, create_app
from app.core.config import Settings
from app.core.database_transport import check_async_proxy_connection
from app.core.database import PoolLifecycle


def test_lambda_read_app_exposes_only_the_two_reviewed_get_paths():
    """Keep all non-approved paths and methods off the Lambda app surface."""
    app = create_app(Settings(environment="test"), listings_read_only=True)

    paths = app.openapi()["paths"]
    assert set(paths) == {
        "/health",
        "/api/listings",
        "/api/listings/{listing_id}",
    }
    assert set(paths["/api/listings"]) == {"get"}
    assert set(paths["/api/listings/{listing_id}"]) == {"get"}


def test_lambda_read_lifecycle_uses_single_pools_and_skips_other_runtimes(monkeypatch):
    """Prove startup opens bounded read pools without Conversations or S3 work."""
    shared_dsn = "postgresql://synthetic@database.invalid/clip"
    settings = Settings(
        environment="test",
        database_url=SecretStr(shared_dsn),
        database_dsn=SecretStr("postgresql://conversations.invalid/clip"),
        storage_provider="s3",
        image_bucket="synthetic-bucket",
        image_region="ap-south-1",
        image_key_prefix="synthetic-prefix",
    )
    events: list[tuple[str, object]] = []
    database_pool = MagicMock(spec=AsyncConnectionPool)

    async def opened(**kwargs):
        events.append(("open", kwargs))

    async def waited(**kwargs):
        events.append(("wait", kwargs))

    async def closed():
        events.append(("close", None))

    database_pool.open.side_effect = opened
    database_pool.wait.side_effect = waited
    database_pool.close.side_effect = closed

    def dictionary_factory(**kwargs):
        assert kwargs == {
            "conninfo": shared_dsn,
            "kwargs": {"row_factory": dict_row},
            "configure": check_async_proxy_connection,
            "check": None,
            "min_size": 0,
            "max_size": 1,
            "timeout": 5,
            "max_waiting": 64,
            "open": False,
        }
        return database_pool

    def forbidden_conversations_factory(_dsn: str) -> PoolLifecycle:
        raise AssertionError("Lambda read startup must not open a Conversations pool")

    def forbidden_storage_factory(*_args):
        raise AssertionError("Lambda read startup must not create S3 storage")

    @asynccontextmanager
    async def forbidden_notifications(*_args, **_kwargs):
        raise AssertionError("Lambda read startup must not initialize notifications")
        yield

    monkeypatch.setattr(composition, "notification_runtime", forbidden_notifications)
    real_search_runtime = composition.search_runtime

    @asynccontextmanager
    async def bounded_search_runtime(search_settings, **kwargs):
        assert kwargs == {
            "pool_max_size": 1,
            "enable_worker": False,
            "retain_idle_connections": False,
        }
        async with real_search_runtime(search_settings, **kwargs) as runtime:
            yield runtime

    monkeypatch.setattr(composition, "search_runtime", bounded_search_runtime)
    application = FastAPI()

    async def exercise():
        async with application_lifespan(
            application,
            settings,
            pool_factory=dictionary_factory,
            storage_factory=forbidden_storage_factory,
            conversation_pool_factory=forbidden_conversations_factory,
            read_only_listings=True,
        ):
            assert application.state.database_pool is None
            assert application.state.conversations_public is None
            assert application.state.wanted_store is None
            assert application.state.saved_store is None
            assert application.state.listings_conversations is None
            assert application.state.listings_image_storage is None
            assert application.state.search_runtime.state == "disabled"

    asyncio.run(exercise())
    assert events[0] == (
        "open",
        {},
    )
    assert events[1] == ("wait", {"timeout": 5})
    assert events[-1] == ("close", None)
