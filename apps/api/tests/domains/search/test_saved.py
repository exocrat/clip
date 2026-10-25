"""Private saved-service and real HTTP contracts with explicit boundary scripts."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.contracts.domain_types import (
    SaveTargetResult,
    SavedListingAck,
    SavedListingState,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import PublicError, install_error_handlers
from app.domains.search.saved import SavedService
from app.domains.search.saved_routes import router, saved_service
from app.domains.search.wanted_models import WantedPage
from apps.api.tests.domains.search.test_draft_matches import summary
from apps.api.tests.domains.search.doubles.saved_listings import SavedListingsDouble


def setup(account_class="regular"):
    """Script persistence outputs only; native checks separately run real SQL."""
    actor = CallerContext(
        uuid4(), account_class, datetime.now(UTC) + timedelta(minutes=5)
    )
    store, identity = AsyncMock(), AsyncMock()
    identity.eligible.return_value = True
    store.existing.return_value = None
    provider = SavedListingsDouble()
    return actor, store, identity, provider, SavedService(store, provider, identity)


@pytest.mark.parametrize("account_class", ["regular", "temporary"])
def test_existing_pair_retry_needs_no_listing_lookup(account_class):
    async def exercise():
        actor, store, _, provider, service = setup(account_class)
        identifier = uuid4()
        saved = SavedListingAck(
            listing_id=identifier, saved_at=datetime.now(UTC) - timedelta(days=1)
        )
        store.existing.return_value = saved
        provider.fail = True
        assert await service.save(actor, identifier) == saved
        store.save.assert_not_awaited()
        assert provider.calls == []

    asyncio.run(exercise())


@pytest.mark.parametrize("discoverable", [True, False])
def test_new_save_requires_exact_current_target(discoverable):
    async def exercise():
        actor, store, _, provider, service = setup()
        identifier = uuid4()
        provider.targets[identifier] = SaveTargetResult(
            listing_id=identifier, discoverable=discoverable
        )
        store.save.return_value = SavedListingAck(
            listing_id=identifier, saved_at=datetime.now(UTC)
        )
        if discoverable:
            assert (await service.save(actor, identifier)).listing_id == identifier
            store.save.assert_awaited_once_with(actor.user_id, identifier)
        else:
            with pytest.raises(PublicError) as failure:
                await service.save(actor, identifier)
            assert failure.value.spec.status == 404
            store.save.assert_not_awaited()

    asyncio.run(exercise())


def test_wrong_target_and_outage_never_write():
    async def exercise():
        actor, store, _, provider, service = setup()
        identifier = uuid4()
        provider.targets[identifier] = SaveTargetResult(
            listing_id=uuid4(), discoverable=True
        )
        with pytest.raises(PublicError) as failure:
            await service.save(actor, identifier)
        assert failure.value.spec.status == 503
        provider.fail = True
        with pytest.raises(PublicError) as failure:
            await service.save(actor, identifier)
        assert failure.value.spec.status == 503
        store.save.assert_not_awaited()

    asyncio.run(exercise())


def test_unavailable_and_retired_views_keep_page_order_and_no_retired_content():
    async def exercise():
        actor, store, _, provider, service = setup()
        item = summary().model_copy(update={"availability": "unavailable"})
        retired = uuid4()
        refs = [
            SavedListingAck(listing_id=identifier, saved_at=datetime.now(UTC))
            for identifier in [item.listing_id, retired]
        ]
        store.page.return_value = refs, False
        provider.states[item.listing_id] = SavedListingState(
            listing_id=item.listing_id, listing=item, retired=False
        )
        provider.states[retired] = SavedListingState(
            listing_id=retired, listing=None, retired=True
        )
        result = await service.listing(actor, WantedPage())
        assert [row.listing_id for row in result.items] == [item.listing_id, retired]
        assert result.items[0].listing.availability == "unavailable"
        assert (
            result.items[1].model_dump()["listing"] is None and result.items[1].retired
        )
        assert provider.calls == [
            ("summaries", actor.user_id, (item.listing_id, retired))
        ]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "bad",
    [
        "missing",
        "duplicate",
        "unexpected",
        "retired_content",
        "no_live_content",
        "nested_wrong_id",
        "invalid_model",
    ],
)
def test_incomplete_or_inconsistent_state_fails_whole_page(bad):
    async def exercise():
        actor, store, identity, provider, _ = setup()
        item = summary()
        store.page.return_value = [
            SavedListingAck(listing_id=item.listing_id, saved_at=datetime.now(UTC))
        ], False
        state = SavedListingState(
            listing_id=item.listing_id, listing=item, retired=False
        )
        states = (state,)
        if bad == "missing":
            states = ()
        if bad == "duplicate":
            states = (state, state)
        if bad == "unexpected":
            states = (state.model_copy(update={"listing_id": uuid4()}),)
        if bad == "retired_content":
            states = (state.model_copy(update={"retired": True}),)
        if bad == "no_live_content":
            states = (state.model_copy(update={"listing": None}),)
        if bad == "nested_wrong_id":
            states = (
                state.model_copy(
                    update={"listing": item.model_copy(update={"listing_id": uuid4()})}
                ),
            )
        if bad == "invalid_model":
            states = ({"listing_id": str(item.listing_id), "private": "controlled"},)
        boundary = AsyncMock()
        boundary.read_saved_listing_summaries.return_value = states
        with pytest.raises(PublicError) as failure:
            await SavedService(store, boundary, identity).listing(actor, WantedPage())
        assert failure.value.spec.status == 503

    asyncio.run(exercise())


def test_empty_page_and_unsave_do_not_need_listings():
    async def exercise():
        actor, store, _, provider, service = setup()
        provider.fail = True
        store.page.return_value = [], False
        assert (await service.listing(actor, WantedPage())).items == []
        await service.unsave(actor, uuid4())
        assert provider.calls == []

    asyncio.run(exercise())


@pytest.mark.parametrize("condition", ["expired", "denied", "unavailable"])
def test_eligibility_failure_precedes_all_persistence(condition):
    async def exercise():
        actor, store, identity, _, service = setup()
        if condition == "expired":
            actor = CallerContext(
                actor.user_id, "temporary", datetime.now(UTC) - timedelta(seconds=1)
            )
        if condition == "denied":
            identity.eligible.return_value = False
        if condition == "unavailable":
            identity.eligible.side_effect = NotImplementedError
        for action in [
            lambda: service.save(actor, uuid4()),
            lambda: service.unsave(actor, uuid4()),
            lambda: service.listing(actor, WantedPage()),
        ]:
            with pytest.raises(PublicError) as failure:
                await action()
            assert (
                failure.value.spec.status
                == {"expired": 401, "denied": 403, "unavailable": 503}[condition]
            )
        store.existing.assert_not_awaited()
        store.unsave.assert_not_awaited()
        store.page.assert_not_awaited()

    asyncio.run(exercise())


def test_http_has_no_actor_selector_and_private_cache_policy():
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    actor, store, _, provider, service = setup("temporary")
    identifier = uuid4()
    provider.targets[identifier] = SaveTargetResult(
        listing_id=identifier, discoverable=True
    )
    store.save.return_value = SavedListingAck(
        listing_id=identifier, saved_at=datetime.now(UTC)
    )
    store.page.return_value = [], False
    app.dependency_overrides[saved_service] = lambda: service
    with TestClient(app) as client:
        assert client.get("/me/saved-listings").status_code == 401
        app.dependency_overrides[require_caller] = lambda: actor
        path = "/me/saved-listings/" + str(identifier)
        assert (
            client.put(
                path, json={"operation_id": str(uuid4()), "user_id": str(uuid4())}
            ).status_code
            == 422
        )
        saved = client.put(path, json={"operation_id": str(uuid4())})
        assert saved.status_code == 200 and set(saved.json()) == {
            "listing_id",
            "saved_at",
        }
        assert saved.headers["cache-control"] == "private, no-store"
        removed = client.delete(path)
        assert removed.status_code == 204 and removed.content == b""
        assert removed.headers["cache-control"] == "private, no-store"
        assert (
            client.get("/me/saved-listings?user_id=" + str(uuid4())).status_code == 422
        )
        assert client.get("/me/saved-listings?page_size=21").status_code == 422
        assert client.get("/me/saved-listings").json()["items"] == []


@pytest.mark.parametrize("window", ["future", "ended"])
def test_saved_view_retains_current_summary_outside_discovery_window(window):
    """Saved reads must not accidentally reuse available-only discovery filters."""

    async def exercise():
        actor, store, _, provider, service = setup()
        now = datetime.now(UTC)
        item = summary().model_copy(
            update={
                "available_from": (
                    now + timedelta(days=1)
                    if window == "future"
                    else now - timedelta(days=2)
                ),
                "available_until": (
                    None if window == "future" else now - timedelta(days=1)
                ),
            }
        )
        store.page.return_value = [
            SavedListingAck(listing_id=item.listing_id, saved_at=now)
        ], False
        provider.states[item.listing_id] = SavedListingState(
            listing_id=item.listing_id, listing=item, retired=False
        )
        result = await service.listing(actor, WantedPage())
        assert len(result.items) == 1 and result.items[0].listing == item
        assert result.items[0].retired is False

    asyncio.run(exercise())
