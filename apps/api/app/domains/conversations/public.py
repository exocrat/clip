# Generated declaration-only conversations interface; format 2. Do not edit.
"""Reviewed Conversations HTTP operations and internal public callables."""

from app.core.auth import CallerContext
from app.contracts.domain_types import (
    ContactOptionsView,
    ContactPreparationRequest,
    ContactShareRequest,
    ConversationEntry,
    ConversationId,
    ConversationQuery,
    ConversationStartResult,
    ConversationSummary,
    EntryPage,
    EntryQuery,
    ExistingWantedConversationLookup,
    ListingConversationContext,
    ListingOfferCommand,
    ListingThreadParticipantCheck,
    MemberKeyBundles,
    MessageRequest,
    NotificationAttemptResult,
    NotificationClaimRequest,
    NotificationClaimResult,
    NotificationDispatchCheck,
    NotificationDispatchContext,
    NotificationIntentState,
    NotificationWorkerContext,
    OfferView,
    OriginActivityRequest,
    OriginActivityResult,
    OriginOwnerContext,
    OriginRetirementCommand,
    PageResult,
    ParticipantCheck,
    PublicKeyBundleRequest,
    PublicKeyBundleView,
    ReadAcknowledgement,
    ReadState,
    RetirementMarkerResult,
    SelectedOwnContacts,
    ShareableContactOptions,
    WantedConversationContext,
)

HTTP_OPERATIONS = (
    {
        "method": "GET",
        "path": "/conversations",
        "operation_id": "conversations_list_mine",
        "query": ConversationQuery,
        "response": PageResult[ConversationSummary],
    },
    {
        "method": "GET",
        "path": "/conversations/{conversation_id}",
        "operation_id": "conversations_read_summary",
        "path_parameters": {"conversation_id": ConversationId},
        "response": ConversationSummary,
    },
    {
        "method": "GET",
        "path": "/conversations/{conversation_id}/entries",
        "operation_id": "conversations_read_entries",
        "path_parameters": {"conversation_id": ConversationId},
        "query": EntryQuery,
        "response": EntryPage,
    },
    {
        "method": "POST",
        "path": "/conversations/{conversation_id}/messages",
        "operation_id": "conversations_submit_message",
        "path_parameters": {"conversation_id": ConversationId},
        "body": MessageRequest,
        "response": ConversationEntry,
        "status_code": 201,
        "responses": {200: ConversationEntry},
    },
    {
        "method": "GET",
        "path": "/conversations/{conversation_id}/read-state",
        "operation_id": "conversations_read_state",
        "path_parameters": {"conversation_id": ConversationId},
        "response": ReadState,
    },
    {
        "method": "PUT",
        "path": "/conversations/{conversation_id}/read-state",
        "operation_id": "conversations_acknowledge_read",
        "path_parameters": {"conversation_id": ConversationId},
        "body": ReadAcknowledgement,
        "response": ReadState,
    },
    {
        "method": "GET",
        "path": "/conversations/{conversation_id}/offer",
        "operation_id": "conversations_read_offer",
        "path_parameters": {"conversation_id": ConversationId},
        "response": OfferView | None,
    },
    {
        "method": "GET",
        "path": "/conversations/{conversation_id}/keys",
        "operation_id": "conversations_read_member_keys",
        "path_parameters": {"conversation_id": ConversationId},
        "response": MemberKeyBundles,
    },
    {
        "method": "PUT",
        "path": "/me/conversation-key",
        "operation_id": "conversations_register_own_key",
        "body": PublicKeyBundleRequest,
        "response": PublicKeyBundleView,
    },
    {
        "method": "GET",
        "path": "/conversations/{conversation_id}/contact-options",
        "operation_id": "conversations_read_contact_options",
        "path_parameters": {"conversation_id": ConversationId},
        "response": ContactOptionsView,
    },
    {
        "method": "POST",
        "path": "/conversations/{conversation_id}/contact-preparations",
        "operation_id": "conversations_prepare_own_contact_share",
        "path_parameters": {"conversation_id": ConversationId},
        "body": ContactPreparationRequest,
        "response": SelectedOwnContacts,
    },
    {
        "method": "POST",
        "path": "/conversations/{conversation_id}/contact-shares",
        "operation_id": "conversations_submit_contact_share",
        "path_parameters": {"conversation_id": ConversationId},
        "body": ContactShareRequest,
        "response": ConversationEntry,
        "status_code": 201,
        "responses": {200: ConversationEntry},
    },
)


async def open_or_create_listing_conversation(
    caller: CallerContext, request: ListingConversationContext
) -> ConversationStartResult:
    """Declare idempotent creation of one Listings-origin buyer thread."""
    raise NotImplementedError("declaration-only")


async def open_or_create_wanted_conversation(
    caller: CallerContext, request: WantedConversationContext
) -> ConversationStartResult:
    """Declare idempotent creation of one Search-origin response thread."""
    raise NotImplementedError("declaration-only")


async def find_existing_wanted_conversation(
    caller: CallerContext, request: ExistingWantedConversationLookup
) -> ConversationStartResult | None:
    """Declare exact-pair read-only lookup for ambiguous retries or closure."""
    raise NotImplementedError("declaration-only")


async def check_listing_thread_participant(
    caller: CallerContext, request: ListingThreadParticipantCheck
) -> ParticipantCheck:
    """Declare boolean-only seller-selection membership verification."""
    raise NotImplementedError("declaration-only")


async def persist_listing_offer(
    caller: CallerContext, request: ListingOfferCommand
) -> OfferView:
    """Declare Listings-authorized offer persistence without origin-table reads."""
    raise NotImplementedError("declaration-only")


async def get_origin_activity(
    context: OriginOwnerContext, request: OriginActivityRequest
) -> OriginActivityResult:
    """Declare an owner-scoped preflight; unknown state fails closed, not as zero."""
    raise NotImplementedError("declaration-only")


async def mark_origin_retired(
    context: OriginOwnerContext, request: OriginRetirementCommand
) -> RetirementMarkerResult:
    """Declare an idempotent all-thread marker operation; it never deletes content."""
    raise NotImplementedError("declaration-only")


async def claim_due_notification_intents(
    context: NotificationWorkerContext, request: NotificationClaimRequest
) -> NotificationClaimResult:
    """Declare a bounded fenced claim with no address or message content."""
    raise NotImplementedError("declaration-only")


async def read_notification_dispatch_context(
    context: NotificationWorkerContext, request: NotificationDispatchCheck
) -> NotificationDispatchContext:
    """Declare an immediate lease/read-watermark check before email dispatch."""
    raise NotImplementedError("declaration-only")


async def record_notification_attempt(
    context: NotificationWorkerContext, request: NotificationAttemptResult
) -> NotificationIntentState:
    """Declare a fenced worker outcome update without provider payload data."""
    raise NotImplementedError("declaration-only")
