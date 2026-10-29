"""Public HTTP router adapter for the Conversations-owned entry operations."""

import re
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import field_validator
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    ConversationEntry,
    ErrorEnvelope,
    EntryPage,
    EntryQuery,
    MessageRequest,
    ReadAcknowledgement,
    ReadState,
    ConversationQuery,
    ConversationSummary,
    ConversationUnreadCount,
    PageResult,
    MemberKeyBundles,
    KeyBundle,
    MemberPreKeyBundle,
    OwnPreKeyInventory,
    PreKeyBundleRequest,
    PublicKeyBundleRequest,
    PublicKeyBundleView,
    PublicPreKeyBatchRequest,
    PublicPreKeyBatchView,
    OfferView,
    ContactOptionsView,
    ContactPreparationRequest,
    ContactShareRequest,
    SelectedOwnContacts,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError
from app.domains.conversations.messages import PostgresMessageOperations
from app.domains.conversations.queries import PostgresConversationQueries
from app.domains.conversations.key_directory import PostgresKeyDirectory
from app.domains.conversations.provider import PostgresConversationServices
from app.domains.conversations.offers import PostgresOfferOperations
from app.domains.conversations.contacts import PostgresContactPreparation

router = APIRouter(
    tags=["conversations"],
    responses={
        status: {"model": ErrorEnvelope}
        for status in (400, 401, 403, 404, 409, 422, 429, 500, 503)
    },
)


def _http_integer(value: Any) -> Any:
    """Convert decimal URL integers exactly, without accepting float-like input."""
    if isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value):
        return int(value)
    if value is None or type(value) is int:
        return value
    raise ValueError("Integer query parameter required")


class ConversationHttpQuery(ConversationQuery):
    """Parse URL strings before applying the unchanged public query constraints."""

    @field_validator(
        "page", "page_size", "offer_min_paise", "offer_max_paise", mode="before"
    )
    @classmethod
    def exact_integer_query(cls, value: Any) -> Any:
        """Keep pagination and money values exact across HTTP string parsing."""
        return _http_integer(value)


class EntryHttpQuery(EntryQuery):
    """Parse entry cursors before applying the bounded public query contract."""

    @field_validator("after_sequence", "page_size", mode="before")
    @classmethod
    def exact_integer_query(cls, value: Any) -> Any:
        """Reject decimal-looking strings instead of silently truncating them."""
        return _http_integer(value)


def create_public_provider(pool: AsyncConnectionPool) -> PostgresConversationServices:
    """Public composition seam; never authenticate callers or open a shared session."""
    return PostgresConversationServices(pool)


def _pool(request: Request) -> AsyncConnectionPool:
    """Resolve only the process pool; absent database configuration fails closed."""
    pool = getattr(request.app.state, "database_pool", None)
    if not isinstance(pool, AsyncConnectionPool):
        raise PublicError(ERRORS[503])
    return pool


def _operations(request: Request) -> PostgresMessageOperations:
    """Keep the message adapter bound to the shared process pool."""
    return PostgresMessageOperations(_pool(request))


@router.get(
    "/conversations/{conversation_id}/contact-options",
    response_model=ContactOptionsView,
    operation_id="conversations_read_contact_options",
    summary="conversations_read_contact_options",
)
async def read_contact_options(
    conversation_id: UUID,
    request: Request,
    response: Response,
    caller: CallerContext = Depends(require_caller),
) -> ContactOptionsView:
    """Read only the authenticated participant's own contact availability flags."""
    response.headers["Cache-Control"] = "no-store"
    return await PostgresContactPreparation(_pool(request)).read_options(
        caller, conversation_id
    )


@router.post(
    "/conversations/{conversation_id}/contact-preparations",
    response_model=SelectedOwnContacts,
    operation_id="conversations_prepare_own_contact_share",
    summary="conversations_prepare_own_contact_share",
)
async def prepare_own_contacts(
    conversation_id: UUID,
    payload: ContactPreparationRequest,
    request: Request,
    response: Response,
    caller: CallerContext = Depends(require_caller),
) -> SelectedOwnContacts:
    """Return confirmed own fields ephemerally for client encryption; persist nothing."""
    response.headers["Cache-Control"] = "no-store"
    return await PostgresContactPreparation(_pool(request)).prepare(
        caller, conversation_id, payload
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationEntry,
    status_code=201,
    responses={200: {"model": ConversationEntry}},
    operation_id="conversations_submit_message",
    summary="conversations_submit_message",
)
async def submit_message(
    conversation_id: UUID,
    payload: MessageRequest,
    response: Response,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> ConversationEntry:
    """Submit one ciphertext/control envelope and return 200 only for exact retry."""
    result = await _operations(request).submit_message(caller, conversation_id, payload)
    if result.replayed:
        response.status_code = 200
    return result.entry


@router.post(
    "/conversations/{conversation_id}/contact-shares",
    response_model=ConversationEntry,
    status_code=201,
    responses={200: {"model": ConversationEntry}},
    operation_id="conversations_submit_contact_share",
    summary="conversations_submit_contact_share",
)
async def submit_contact_share(
    conversation_id: UUID,
    payload: ContactShareRequest,
    response: Response,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> ConversationEntry:
    """Store a member's ciphertext-only selected-contact entry."""
    result = await _operations(request).submit_contact_share(
        caller, conversation_id, payload
    )
    if result.replayed:
        response.status_code = 200
    return result.entry


@router.get(
    "/conversations/{conversation_id}/entries",
    response_model=EntryPage,
    operation_id="conversations_read_entries",
    summary="conversations_read_entries",
)
async def read_entries(
    conversation_id: UUID,
    request: Request,
    query: Annotated[EntryHttpQuery, Query()],
    caller: CallerContext = Depends(require_caller),
) -> EntryPage:
    """Read a bounded visible entry page with a scan-through sequence cursor."""
    return await _operations(request).read_entries(
        caller,
        conversation_id,
        query,
    )


@router.get(
    "/conversations/{conversation_id}/read-state",
    response_model=ReadState,
    operation_id="conversations_read_state",
    summary="conversations_read_state",
)
async def read_state(
    conversation_id: UUID,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> ReadState:
    """Return only the authenticated member's monotonic read watermark."""
    return await _operations(request).read_state(caller, conversation_id)


@router.get(
    "/me/conversation-key",
    response_model=KeyBundle | None,
    operation_id="conversations_read_own_key",
    summary="conversations_read_own_key",
)
async def read_own_key(
    request: Request,
    response: Response,
    caller: CallerContext = Depends(require_caller),
) -> KeyBundle | None:
    """Read only the authenticated account's current public bundle, never private keys."""
    response.headers["Cache-Control"] = "no-store"
    return await PostgresKeyDirectory(_pool(request)).read_own_key(caller)


@router.put(
    "/conversations/{conversation_id}/read-state",
    response_model=ReadState,
    operation_id="conversations_acknowledge_read",
    summary="conversations_acknowledge_read",
)
async def acknowledge_read(
    conversation_id: UUID,
    payload: ReadAcknowledgement,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> ReadState:
    """Acknowledge only committed entries after the client has actually displayed them."""
    return await _operations(request).acknowledge_read(caller, conversation_id, payload)


@router.get(
    "/conversations",
    response_model=PageResult[ConversationSummary],
    operation_id="conversations_list_mine",
    summary="conversations_list_mine",
)
async def list_mine(
    request: Request,
    query: Annotated[ConversationHttpQuery, Query()],
    caller: CallerContext = Depends(require_caller),
) -> PageResult[ConversationSummary]:
    """Return an authorized, filtered inbox without reading origin-domain content."""
    return await PostgresConversationQueries(_pool(request)).list_mine(caller, query)


@router.get(
    "/conversations/unread-count",
    response_model=ConversationUnreadCount,
    operation_id="conversations_read_unread_count",
    summary="conversations_read_unread_count",
)
async def unread_count(
    request: Request, caller: CallerContext = Depends(require_caller)
) -> ConversationUnreadCount:
    """Read the current account's aggregate; no peer receipt or message data."""
    return await PostgresConversationQueries(_pool(request)).unread_count(caller)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    operation_id="conversations_read_summary",
    summary="conversations_read_summary",
)
async def read_summary(
    conversation_id: UUID,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> ConversationSummary:
    """Resolve thread metadata only for an authenticated participant."""
    return await PostgresConversationQueries(_pool(request)).read_summary(
        caller, conversation_id
    )


@router.get(
    "/conversations/{conversation_id}/offer",
    response_model=OfferView | None,
    operation_id="conversations_read_offer",
    summary="conversations_read_offer",
)
async def read_offer(
    conversation_id: UUID,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> OfferView | None:
    """Return only a current member's structured offer and optional opaque note."""
    return await PostgresOfferOperations(_pool(request)).read_offer(
        caller, conversation_id
    )


@router.get(
    "/conversations/{conversation_id}/keys",
    response_model=MemberKeyBundles,
    operation_id="conversations_read_member_keys",
    summary="conversations_read_member_keys",
)
async def read_member_keys(
    conversation_id: UUID,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> MemberKeyBundles:
    """Return current and referenced public key versions for these two members."""
    return await PostgresKeyDirectory(_pool(request)).read_member_keys(
        caller, conversation_id
    )


@router.put(
    "/me/conversation-key",
    response_model=PublicKeyBundleView,
    operation_id="conversations_register_own_key",
    summary="conversations_register_own_key",
)
async def register_own_key(
    payload: PublicKeyBundleRequest,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> PublicKeyBundleView:
    """Register only the trusted caller's public SDK bundle."""
    return await PostgresKeyDirectory(_pool(request)).register_own_key(caller, payload)


@router.get(
    "/me/conversation-prekeys",
    response_model=OwnPreKeyInventory,
    operation_id="conversations_read_own_prekey_inventory",
    summary="conversations_read_own_prekey_inventory",
)
async def read_own_inventory(
    request: Request, caller: CallerContext = Depends(require_caller)
) -> OwnPreKeyInventory:
    """Expose only remaining own public prekey counts."""
    return await PostgresKeyDirectory(_pool(request)).read_own_inventory(caller)


@router.post(
    "/me/conversation-prekeys",
    response_model=PublicPreKeyBatchView,
    operation_id="conversations_publish_own_prekeys",
    summary="conversations_publish_own_prekeys",
)
async def publish_own_prekeys(
    payload: PublicPreKeyBatchRequest,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> PublicPreKeyBatchView:
    """Publish a public prekey batch transactionally with an exact retry record."""
    return await PostgresKeyDirectory(_pool(request)).publish_own_prekeys(
        caller, payload
    )


@router.post(
    "/conversations/{conversation_id}/prekey-bundle",
    response_model=MemberPreKeyBundle,
    operation_id="conversations_consume_member_prekeys",
    summary="conversations_consume_member_prekeys",
)
async def consume_member_prekeys(
    conversation_id: UUID,
    payload: PreKeyBundleRequest,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> MemberPreKeyBundle:
    """Derive the peer server-side and atomically reserve its public prekeys."""
    return await PostgresKeyDirectory(_pool(request)).consume_member_prekeys(
        caller, conversation_id, payload
    )
