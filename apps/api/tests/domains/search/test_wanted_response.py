"""Response authorization/retry contracts; native tests supply actual row locks."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.contracts.domain_types import ConversationStartResult
from app.core.auth import CallerContext, require_caller
from app.core.errors import PublicError, install_error_handlers
from app.domains.search.wanted_response import (
    WantedResponseOrigin,
    WantedResponseService,
)
from app.domains.search.wanted_routes import router, response_service
from apps.api.tests.domains.search.doubles.wanted_response import (
    ConversationsResponseDouble,
)


class Store:
    """Script only local origin facts, not SQL or concurrency behavior."""

    def __init__(self, origin):
        self.origin = origin
        self.calls = []
        self.held = False

    @asynccontextmanager
    async def response_guard(self, identifier):
        """Track lifetime for failure/cancellation tests without pretending to lock."""
        self.calls.append(identifier)
        self.held = True
        try:
            yield self.origin
        finally:
            self.held = False


def setup():
    """Use separate server-derived author and current regular responder."""
    actor = CallerContext(uuid4(), "regular", datetime.now(UTC) + timedelta(minutes=5))
    store = Store(WantedResponseOrigin(uuid4(), "open", False, False))
    provider = ConversationsResponseDouble()
    identity = AsyncMock()
    identity.eligible.return_value = True
    return (
        actor,
        store,
        provider,
        identity,
        WantedResponseService(store, provider, identity),
    )


@pytest.mark.parametrize(
    "condition", ["temporary", "expired", "revoked", "ineligible_response"]
)
def test_denied_caller_never_accesses_origin_or_conversations(condition):
    async def exercise():
        actor, store, provider, identity, service = setup()
        if condition == "temporary":
            actor = CallerContext(actor.user_id, "temporary", actor.valid_until)
        if condition == "expired":
            actor = CallerContext(
                actor.user_id, "regular", datetime.now(UTC) - timedelta(seconds=1)
            )
        if condition == "revoked":
            identity.eligible.return_value = False
        if condition == "ineligible_response":
            identity.eligible.return_value = "true"
        with pytest.raises(PublicError) as failure:
            await service.respond(actor, uuid4())
        assert (
            failure.value.spec.status
            == {
                "temporary": 403,
                "expired": 401,
                "revoked": 403,
                "ineligible_response": 503,
            }[condition]
        )
        assert (
            store.calls == []
            and provider.create_calls == []
            and provider.lookup_calls == []
        )
        if condition in {"temporary", "expired"}:
            identity.eligible.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize("condition", ["missing", "pending", "retired", "self"])
def test_hidden_or_self_origin_never_calls_conversations(condition):
    async def exercise():
        actor, store, provider, _, service = setup()
        if condition == "missing":
            store.origin = None
        else:
            store.origin = WantedResponseOrigin(
                actor.user_id if condition == "self" else uuid4(),
                "open",
                condition == "retired",
                condition == "pending",
            )
        with pytest.raises(PublicError) as failure:
            await service.respond(actor, uuid4())
        assert failure.value.spec.status == (403 if condition == "self" else 404)
        assert (
            provider.create_calls == []
            and provider.lookup_calls == []
            and not store.held
        )

    asyncio.run(exercise())


def test_lost_result_retries_same_pair_and_closed_uses_lookup_only():
    async def exercise():
        actor, store, provider, _, service = setup()
        identifier = uuid4()
        provider.lose_once = True
        with pytest.raises(PublicError) as failure:
            await service.respond(actor, identifier)
        assert (
            failure.value.spec.status == 503
            and provider.effects == 1
            and not store.held
        )
        author = store.origin.author_id
        store.origin = WantedResponseOrigin(author, "unavailable", False, False)
        result = await service.respond(actor, identifier)
        assert (
            result.created is False
            and result.conversation_id == provider.threads[(identifier, actor.user_id)]
        )
        assert (
            len(provider.create_calls) == 1
            and len(provider.lookup_calls) == 1
            and provider.effects == 1
        )
        other = CallerContext(uuid4(), "regular", actor.valid_until)
        with pytest.raises(PublicError) as failure:
            await service.respond(other, identifier)
        assert failure.value.spec.status == 404 and provider.effects == 1

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {"conversation_id": "controlled", "created": True},
        "wrong_created",
        "wrong_id",
    ],
)
def test_malformed_create_result_is_dependency_failure(bad):
    async def exercise():
        actor, store, _, identity, _ = setup()
        provider = AsyncMock()
        value = bad
        if bad == "wrong_created":
            value = ConversationStartResult.model_construct(
                conversation_id=uuid4(), created="true"
            )
        if bad == "wrong_id":
            value = ConversationStartResult.model_construct(
                conversation_id="controlled", created=True
            )
        provider.open_or_create_wanted_conversation.return_value = value
        with pytest.raises(PublicError) as failure:
            await WantedResponseService(store, provider, identity).respond(
                actor, uuid4()
            )
        assert failure.value.spec.status == 503 and not store.held

    asyncio.run(exercise())


def test_closed_lookup_cannot_claim_creation_and_default_provider_fails_closed():
    async def exercise():
        actor, store, _, identity, _ = setup()
        store.origin = WantedResponseOrigin(uuid4(), "unavailable", False, False)
        provider = AsyncMock()
        provider.find_existing_wanted_conversation.return_value = (
            ConversationStartResult(conversation_id=uuid4(), created=True)
        )
        with pytest.raises(PublicError) as failure:
            await WantedResponseService(store, provider, identity).respond(
                actor, uuid4()
            )
        assert failure.value.spec.status == 503
        provider.open_or_create_wanted_conversation.assert_not_awaited()
        store.origin = WantedResponseOrigin(uuid4(), "open", False, False)
        with pytest.raises(PublicError) as failure:
            await WantedResponseService(store, identity=identity).respond(
                actor, uuid4()
            )
        assert failure.value.spec.status == 503 and not store.held

    asyncio.run(exercise())


def test_timeout_and_cancellation_release_local_guard(monkeypatch):
    async def exercise():
        from app.domains.search import wanted_response as module

        actor, store, _, identity, _ = setup()
        provider = AsyncMock()
        entered = asyncio.Event()

        async def hang(*args):
            """A cooperative provider can stall, but cannot hold the origin forever."""
            entered.set()
            await asyncio.Event().wait()

        provider.open_or_create_wanted_conversation.side_effect = hang
        monkeypatch.setattr(module, "_TIMEOUT", 0.01)
        service = WantedResponseService(store, provider, identity)
        with pytest.raises(PublicError) as failure:
            await service.respond(actor, uuid4())
        assert failure.value.spec.status == 503 and not store.held
        entered.clear()
        monkeypatch.setattr(module, "_TIMEOUT", 2)
        task = asyncio.create_task(service.respond(actor, uuid4()))
        await asyncio.wait_for(entered.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not store.held

    asyncio.run(exercise())


def test_http_created_and_existing_have_result_body_and_private_cache():
    actor, store, provider, identity, service = setup()
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[require_caller] = lambda: actor
    app.dependency_overrides[response_service] = lambda: service
    path = "/wanted-requests/" + str(uuid4()) + "/conversations"
    with TestClient(app) as client:
        first = client.post(path, json={"operation_id": str(uuid4())})
        repeat = client.post(path, json={"operation_id": str(uuid4())})
        assert first.status_code == 201 and repeat.status_code == 200
        assert first.json()["conversation_id"] == repeat.json()["conversation_id"]
        assert first.json()["created"] is True and repeat.json()["created"] is False
        assert set(first.json()) == set(repeat.json()) == {"conversation_id", "created"}
        assert repeat.headers["cache-control"] == "private, no-store"
        assert (
            client.post(
                path, json={"operation_id": str(uuid4()), "author_id": str(uuid4())}
            ).status_code
            == 422
        )
        assert len(provider.create_calls) == 2 and provider.effects == 1
