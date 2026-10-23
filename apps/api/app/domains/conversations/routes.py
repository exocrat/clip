"""Public HTTP router adapter for the Conversations-owned entry operations."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from psycopg_pool import AsyncConnectionPool

from app.contracts.domain_types import (
    ConversationEntry,
    EntryPage,
    EntryQuery,
    MessageRequest,
    ReadAcknowledgement,
    ReadState,
    ConversationQuery,
    ConversationSummary,
    PageResult,
    MemberKeyBundles,
    MemberPreKeyBundle,
    OwnPreKeyInventory,
    PreKeyBundleRequest,
    PublicKeyBundleRequest,
    PublicKeyBundleView,
    PublicPreKeyBatchRequest,
    PublicPreKeyBatchView,
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError
from app.domains.conversations.messages import PostgresMessageOperations
from app.domains.conversations.queries import PostgresConversationQueries
from app.domains.conversations.key_directory import PostgresKeyDirectory

router = APIRouter(tags=["conversations"])


def _pool(request: Request) -> AsyncConnectionPool:
    """Resolve only the process pool; absent database configuration fails closed."""
    pool = getattr(request.app.state, "database_pool", None)
    if not isinstance(pool, AsyncConnectionPool):
        raise PublicError(ERRORS[503])
    return pool


def _operations(request: Request) -> PostgresMessageOperations:
    """Keep the message adapter bound to the shared process pool."""
    return PostgresMessageOperations(_pool(request))


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationEntry,
    status_code=201,
    responses={200: {"model": ConversationEntry}},
    operation_id="conversations_submit_message",
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


@router.get(
    "/conversations/{conversation_id}/entries",
    response_model=EntryPage,
    operation_id="conversations_read_entries",
)
async def read_entries(
    conversation_id: UUID,
    request: Request,
    after_sequence: int = Query(default=0, ge=0),
    page_size: Literal[20, 50, 100] = Query(default=20),
    caller: CallerContext = Depends(require_caller),
) -> EntryPage:
    """Read a bounded visible entry page with a scan-through sequence cursor."""
    return await _operations(request).read_entries(
        caller,
        conversation_id,
        EntryQuery(after_sequence=after_sequence, page_size=page_size),
    )


@router.get(
    "/conversations/{conversation_id}/read-state",
    response_model=ReadState,
    operation_id="conversations_read_state",
)
async def read_state(
    conversation_id: UUID,
    request: Request,
    caller: CallerContext = Depends(require_caller),
) -> ReadState:
    """Return only the authenticated member's monotonic read watermark."""
    return await _operations(request).read_state(caller, conversation_id)


@router.put(
    "/conversations/{conversation_id}/read-state",
    response_model=ReadState,
    operation_id="conversations_acknowledge_read",
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
)
async def list_mine(
    request: Request,
    query: Annotated[ConversationQuery, Query()],
    caller: CallerContext = Depends(require_caller),
) -> PageResult[ConversationSummary]:
    """Return an authorized, filtered inbox without reading origin-domain content."""
    return await PostgresConversationQueries(_pool(request)).list_mine(caller, query)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    operation_id="conversations_read_summary",
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
    "/conversations/{conversation_id}/keys",
    response_model=MemberKeyBundles,
    operation_id="conversations_read_member_keys",
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
