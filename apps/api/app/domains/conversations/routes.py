"""Public HTTP router adapter for the Conversations-owned entry operations."""

from typing import Literal
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
)
from app.core.auth import CallerContext, require_caller
from app.core.errors import ERRORS, PublicError
from app.domains.conversations.messages import PostgresMessageOperations

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _operations(request: Request) -> PostgresMessageOperations:
    """Resolve only the process pool; absent database configuration fails closed."""
    pool = getattr(request.app.state, "database_pool", None)
    if not isinstance(pool, AsyncConnectionPool):
        raise PublicError(ERRORS[503])
    return PostgresMessageOperations(pool)


@router.post(
    "/{conversation_id}/messages",
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
    "/{conversation_id}/entries",
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
    "/{conversation_id}/read-state",
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
    "/{conversation_id}/read-state",
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
