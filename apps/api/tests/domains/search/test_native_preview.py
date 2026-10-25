"""Native harness target/transport/budget guards; actual inference is opt-in CLI."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from app.core.pagination import Page
from app.domains.listings.embedding_client import HelperUnavailable, SemanticHelper
from apps.api.tests.domains.search.native_preview import (
    CALLER,
    HEADERS,
    NativeCluster,
    PreviewHelper,
    PreviewIdentity,
    ROOT,
    create_app,
)


def test_only_owned_synthetic_identity_is_eligible():
    """No client selector or arbitrary synthetic user receives account capability."""
    from uuid import uuid4

    async def exercise():
        identity = PreviewIdentity()
        assert await identity.account_is_eligible(CALLER)
        assert not await identity.account_is_eligible(uuid4())

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "headers,client",
    [
        ({}, "127.0.0.1"),
        (HEADERS, "203.0.113.1"),
        ({**HEADERS, "Origin": "https://example.invalid"}, "127.0.0.1"),
    ],
)
def test_native_transport_requires_loopback_header_and_origin(headers, client):
    """Unapproved clients never reach real persistence or helper dispatch."""
    app = create_app(AsyncMock(), None, datetime.now(UTC) + timedelta(minutes=1))
    store = SimpleNamespace(browse_available_listings=AsyncMock())
    app.state.listings_store = store
    with TestClient(app, client=(client, 1)) as transport:
        assert transport.get("/listings", headers=headers).status_code == 403
    store.browse_available_listings.assert_not_awaited()


def test_real_router_sanitizes_and_expires_before_store():
    """The transport fixture never bypasses the actual service caller guard."""
    app = create_app(AsyncMock(), None, datetime.now(UTC) - timedelta(seconds=1))
    store = SimpleNamespace(browse_available_listings=AsyncMock())
    app.state.listings_store = store
    with TestClient(app) as transport:
        response = transport.get("/listings", headers=HEADERS)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "private, no-store"
        assert (
            response.headers["x-clip-preview"]
            == "search-native-model-synthetic-identity"
        )
    store.browse_available_listings.assert_not_awaited()


def test_native_cluster_has_new_private_fixed_target_clean_environment_and_cli_order():
    """Mock executable calls only; prove no ambient/existing target argument path."""
    cluster = NativeCluster()
    assert cluster.directory.name.startswith("clip-listings-test-")
    assert cluster.directory.stat().st_mode & 0o777 == 0o700
    assert cluster.socket.stat().st_mode & 0o777 == 0o700
    assert set(cluster.environment) == {"PATH", "LC_ALL", "TZ"}
    assert f"host={cluster.socket}" in cluster.url
    with (
        patch.object(cluster, "command") as command,
        patch(
            "subprocess.check_output",
            side_effect=["postgres (PostgreSQL) 18.6\n", "dbmate version 2.36.0\n"],
        ),
    ):
        cluster.start()
        migrate = command.call_args_list[-1]
        assert migrate.args[0] == "dbmate"
        assert migrate.args[1][-2:] == ["migrate", "--strict"]
        assert migrate.kwargs == {"database": True}
        cluster.stop()
        assert command.call_args.args[0] == "pg_ctl"
        assert str(cluster.cluster) in command.call_args.args[1]
        assert not cluster.started


def test_query_budget_reserves_before_await_and_refunds_on_failure():
    """Concurrent callers cannot consume more than the remaining100-window budget."""

    async def exercise():
        helper = PreviewHelper(
            ROOT / ".tools/semantic/venv/bin/python", ROOT / ".tools/semantic/model"
        )
        helper.windows_started = 99
        entered = asyncio.Event()
        finish = asyncio.Event()

        async def encode(_text):
            entered.set()
            await finish.wait()
            raise HelperUnavailable("Controlled test failure")

        with patch.object(SemanticHelper, "encode_query", side_effect=encode):
            task = asyncio.create_task(helper.encode_query("cycle"))
            await entered.wait()
            with pytest.raises(HelperUnavailable):
                await helper.encode_query("vehicle")
            finish.set()
            with pytest.raises(HelperUnavailable):
                await task
        assert helper._reserved_windows == 0
        helper.windows_started = 100
        with pytest.raises(HelperUnavailable):
            await helper.encode_query("book")
        await helper.close()

    asyncio.run(exercise())


def test_late_cancellation_cannot_skip_cleanup_or_report():
    """Reproduce SIGINT arriving at the first cleanup await, without real signals."""
    from apps.api.tests.domains.search.native_preview import complete_cleanup

    async def exercise():
        started = asyncio.Event()
        finish = asyncio.Event()
        reported = []

        async def cleanup():
            started.set()
            await finish.wait()
            reported.append("reaped_and_reported")

        task = asyncio.create_task(complete_cleanup(cleanup()))
        await started.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        finish.set()
        await task
        assert reported == ["reaped_and_reported"]

        async def failed_cleanup():
            raise RuntimeError("Controlled cleanup failure")

        with pytest.raises(RuntimeError):
            await complete_cleanup(failed_cleanup())

    asyncio.run(exercise())
