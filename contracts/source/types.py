"""Canonical typed data shapes shared by the four domain contracts.

These models describe reviewed wire and in-process values. They do not perform
authorization, persistence, provider calls, retries, encryption, or cleanup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from app.core.identifiers import format_id
from app.core.timestamps import as_utc, format_timestamp, parse_timestamp
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    SecretStr,
    WithJsonSchema,
)

UserId = UUID
ListingId = UUID
CategoryCode = str
ImageId = UUID
WantedRequestId = UUID
ConversationId = UUID
OfferId = UUID
OperationId = UUID
AccountClass = Literal["regular", "temporary"]
ContactField = Literal["email", "phone", "upi_id"]
OriginKind = Literal["sale_listing", "wanted_request"]


def _parse_contract_instant(value: datetime | str) -> datetime:
    """Reject naive/over-precise inputs and normalize accepted instants to UTC."""
    if isinstance(value, datetime):
        return as_utc(value)
    return parse_timestamp(value)


UtcInstant = Annotated[
    datetime,
    BeforeValidator(_parse_contract_instant),
    PlainSerializer(format_timestamp, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "format": "date-time"}, mode="serialization"),
]


class ContractModel(BaseModel):
    """Reject undeclared fields so contract drift fails at the boundary."""

    model_config = ConfigDict(extra="forbid")


T = TypeVar("T")


class PageResult(ContractModel, Generic[T]):
    """Stable numbered page response; ordering belongs to the owning query."""

    items: list[T]
    page: int = Field(ge=1)
    page_size: Literal[20, 50, 100]
    has_next: bool


class PageQuery(ContractModel):
    """Shared numbered-page query parameters used by domain list routes."""

    page: int = Field(default=1, ge=1)
    page_size: Literal[20, 50, 100] = 20


class ErrorDetail(ContractModel):
    """Safe field and code pair; rejected input values are never included."""

    field: str
    code: str


class ErrorBody(ContractModel):
    """Standard error code/message/details envelope."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorEnvelope(ContractModel):
    """Shared public error envelope with optional correlation identifier."""

    error: ErrorBody
    request_id: str | None = None


class SessionView(ContractModel):
    """Authenticated session summary; intentionally excludes source contacts."""

    user_id: UserId
    account_class: AccountClass
    valid_until: UtcInstant
    display_name: str | None = None


class MicrosoftLoginAttempt(ContractModel):
    """Public nonce paired with a private server-bound HttpOnly attempt cookie."""

    nonce: str = Field(min_length=32, max_length=128, repr=False)
    expires_at: UtcInstant


class CsrfToken(ContractModel):
    """Session-bound request protection token; never a session credential."""

    csrf_token: str = Field(min_length=32, max_length=128, repr=False)


class MicrosoftSessionRequest(ContractModel):
    """Provider assertion exchanged by Identity, never persisted or logged."""

    id_token: SecretStr


class RegistrationChallengeRequest(ContractModel):
    """Email address and client-chosen UUIDv4 idempotency key."""

    email: str = Field(min_length=1, max_length=254)
    operation_id: OperationId


class PasswordResetChallengeRequest(ContractModel):
    """Password-reset email and its client-chosen UUIDv4 idempotency key."""

    email: str = Field(min_length=1, max_length=254)
    operation_id: OperationId


class ChallengeAccepted(ContractModel):
    """Non-enumerating challenge acknowledgement without delivery claims."""

    challenge_id: UUID
    expires_at: UtcInstant


class ActivateTemporaryRequest(ContractModel):
    """Single-use verification and temporary account activation input."""

    challenge_id: UUID
    code: str = Field(min_length=1, max_length=32)
    password: SecretStr


class TemporarySessionRequest(ContractModel):
    """Temporary account credential exchange."""

    email: str = Field(min_length=1, max_length=254)
    password: SecretStr


class ResetTemporaryPasswordRequest(ContractModel):
    """Single-use challenge input for a password reset."""

    challenge_id: UUID
    code: str = Field(min_length=1, max_length=32)
    new_password: SecretStr


class ProfilePatch(ContractModel):
    """Own-profile partial update; omitted and explicit null have distinct meaning."""

    display_name: str | None = Field(default=None, max_length=80)


class ProfileView(ContractModel):
    """Publicly safe own-profile view without source contacts."""

    user_id: UserId
    display_name: str | None


class OwnContacts(ContractModel):
    """Authenticated owner's contact collection; each value is private."""

    email: str | None = Field(repr=False)
    phone: str | None = Field(repr=False)
    upi_id: str | None = Field(repr=False)


class ContactValueRequest(ContractModel):
    """One contact field submitted to the authenticated Identity boundary."""

    value: str = Field(min_length=1, max_length=254, repr=False)


@dataclass(frozen=True)
class ContactSharingContext:
    """Server-only scope after Conversation participation/confirmation checks.

    Not an HTTP model or authentication credential. Trusted composition installs
    this immutable record only for the approved flow; IDs alone grant nothing.
    None permits availability only; selected values require confirmed fields.
    """

    actor_id: UserId = field(repr=False)
    conversation_id: ConversationId = field(repr=False)
    confirmed_fields: frozenset[ContactField] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate opaque IDs/field scope without contacting another domain."""
        format_id(self.actor_id)
        format_id(self.conversation_id)
        if self.confirmed_fields is not None and (
            not isinstance(self.confirmed_fields, frozenset)
            or not self.confirmed_fields
            or not self.confirmed_fields <= {"email", "phone", "upi_id"}
        ):
            raise ValueError("Invalid confirmed contact fields")


class ShareableContactOptions(ContractModel):
    """Identity result: own actor ID and contact availability, never values."""

    user_id: UserId
    has_email: bool
    has_phone: bool
    has_upi_id: bool


class SelectedOwnContacts(ContractModel):
    """Requested own values only; repr hides values but serialization remains private."""

    email: str | None = Field(repr=False)
    phone: str | None = Field(repr=False)
    upi_id: str | None = Field(repr=False)


class ContactOptionsView(ContractModel):
    """Conversation-facing availability flags for the authenticated caller."""

    email_available: bool
    phone_available: bool
    upi_available: bool


class AccountEligibility(ContractModel):
    """Minimal Identity capability result with no profile or denial reason."""

    eligible: bool


class NotificationRecipient(ContractModel):
    """Ephemeral verified delivery address resolved for the worker only."""

    recipient_id: UserId
    email: str = Field(repr=False)


class Category(ContractModel):
    """Active category code/label used for new assignment."""

    code: str
    label: str


class CategoryDisplay(ContractModel):
    """Retained category code/label, including inactive historical values."""

    code: str
    label: str
    active: bool


class CatalogueView(ContractModel):
    """Stable active category and condition code/label arrays."""

    categories: list[Category]
    conditions: list[Category]


class CipherEnvelope(ContractModel):
    """Opaque encrypted payload transport metadata; never plaintext content."""

    protocol_id: str
    protocol_version: str
    envelope_version: int = Field(ge=1)
    sender_key_version: int = Field(ge=1)
    recipient_key_version: int = Field(ge=1)
    payload_base64: str = Field(min_length=1, repr=False)


class ListingSummary(ContractModel):
    """Discovery-safe sale listing summary without owner or selection fields."""

    listing_id: ListingId
    title: str
    description: str
    category_code: str
    category_label: str
    condition_code: str
    condition_label: str
    asking_price_paise: int = Field(ge=0, multiple_of=100)
    negotiable: bool
    pickup_area: str
    available_from: UtcInstant
    available_until: UtcInstant | None
    availability: Literal["available", "unavailable"]
    sensitive_purchase: bool
    image_ids: list[ImageId]


class SavedListingState(ContractModel):
    """Current safe detail or a content-free retired marker for one saved ID."""

    listing_id: ListingId
    listing: ListingSummary | None
    retired: bool


class ListingDetail(ListingSummary):
    """Sale listing detail with the optional seller proof declaration."""

    proof_available: bool | None


class ListingManagementView(ListingDetail):
    """Owner-only listing view with revision and selection state."""

    owner_id: UserId
    revision: int = Field(ge=1)
    selected_buyer_id: UserId | None = None
    selected_conversation_id: ConversationId | None = None
    created_at: UtcInstant
    updated_at: UtcInstant


class ListingOwnerView(ListingManagementView):
    """Owner command response; same privacy boundary as management view."""


class ListingQuery(ContractModel):
    """Available listing filters and numbered page controls."""

    page: int = Field(default=1, ge=1)
    page_size: Literal[20, 50, 100] = 20
    category_code: str | None = None
    condition_code: str | None = None
    negotiable: bool | None = None
    min_price_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    max_price_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    sort: Literal["created_desc", "price_asc", "price_desc"] = "created_desc"
    q: str | None = Field(default=None, max_length=120)


# Search's internal call uses the same bounded filters as the public query.
AvailableListingQuery = ListingQuery


class SaveTargetResult(ContractModel):
    """Minimal owner-authoritative answer for one saved-listing target."""

    listing_id: ListingId
    discoverable: bool


class ImageUploadRequest(ContractModel):
    """Metadata and stable idempotency key for a pending image upload."""

    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(ge=1, le=10_485_760)
    operation_id: OperationId


class UploadInstruction(ContractModel):
    """Short-lived upload instructions; the object key stays private."""

    upload_id: ImageId
    upload_url: str = Field(repr=False)
    required_headers: dict[str, str]
    url_expires_at: UtcInstant


class ConfirmedImage(ContractModel):
    """Verified object metadata after storage inspection."""

    upload_id: ImageId
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: int = Field(ge=1, le=10_485_760)


class ImageDelivery(ContractModel):
    """Time-limited authorized image URL; never an object-store key."""

    url: str = Field(repr=False)
    url_expires_at: UtcInstant


class CreateListingRequest(ContractModel):
    """Complete new listing command; owner and timestamps are server-derived."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category_code: str
    condition_code: str
    asking_price_paise: int = Field(ge=0, multiple_of=100)
    negotiable: bool
    pickup_area: str = Field(min_length=1, max_length=120)
    available_from: UtcInstant | None = None
    available_until: UtcInstant | None = None
    proof_available: bool | None = None
    image_upload_ids: list[ImageId] = Field(min_length=1, max_length=8)
    operation_id: OperationId


class ListingReplacement(ContractModel):
    """Full listing replacement with revision guard and explicit nullable fields."""

    expected_revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category_code: str
    condition_code: str
    asking_price_paise: int = Field(ge=0, multiple_of=100)
    negotiable: bool
    pickup_area: str = Field(min_length=1, max_length=120)
    available_from: UtcInstant
    available_until: UtcInstant | None
    proof_available: bool | None
    image_upload_ids: list[ImageId] = Field(min_length=1, max_length=8)
    operation_id: OperationId


class AvailabilityChange(ContractModel):
    """Owner-controlled availability update independent of time-window state."""

    expected_revision: int = Field(ge=1)
    availability: Literal["available", "unavailable"]
    available_from: UtcInstant | None = None
    available_until: UtcInstant | None = None
    operation_id: OperationId


class StartListingConversationRequest(ContractModel):
    """Idempotency key for buyer-initiated sale thread creation."""

    operation_id: OperationId


class ConversationStartResult(ContractModel):
    """Result of exact-pair conversation creation or existing-pair retry."""

    conversation_id: ConversationId
    created: bool


class SelectionChange(ContractModel):
    """Select or clear an eligible listing buyer with optimistic concurrency."""

    buyer_id: UserId | None
    conversation_id: ConversationId | None
    expected_revision: int = Field(ge=1)
    operation_id: OperationId


class CurrentOfferSummary(ContractModel):
    """Current offer only; historical revisions remain private to participants."""

    offer_id: OfferId
    revision: int = Field(ge=1)
    amount_paise: int = Field(ge=0, multiple_of=100)
    status: Literal["submitted", "withdrawn"]
    updated_at: UtcInstant


class OfferView(CurrentOfferSummary):
    """Participant-only offer result with optional encrypted sale note."""

    note_envelope: CipherEnvelope | None = None


class OfferRevisionRequest(ContractModel):
    """Submit/revise an offer without plaintext notes or payment behavior."""

    amount_paise: int = Field(ge=0, multiple_of=100)
    note_envelope: CipherEnvelope | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    operation_id: OperationId


class OfferWithdrawalRequest(ContractModel):
    """Append an offer withdrawal revision under its stable operation key."""

    offer_id: OfferId
    expected_revision: int = Field(ge=1)
    operation_id: OperationId


class WantedRequestPublic(ContractModel):
    """Authenticated marketplace request projection without author identity."""

    request_id: WantedRequestId
    title: str
    description: str
    category_code: str
    category_label: str
    budget_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    created_at: UtcInstant
    updated_at: UtcInstant


class WantedRequestOwnerView(WantedRequestPublic):
    """Request author's view with lifecycle state and revision."""

    state: Literal["open", "unavailable"]
    revision: int = Field(ge=1)


class CreateWantedRequest(ContractModel):
    """New Wanted Request; author identity is derived from trusted context."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category_code: str
    budget_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    operation_id: OperationId


class WantedRequestPatch(ContractModel):
    """Partial request update with expected revision and nullable budget."""

    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    category_code: str | None = None
    budget_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    operation_id: OperationId


class WantedRequestStateChange(ContractModel):
    """Open or hide the author's request without deleting its history."""

    expected_revision: int = Field(ge=1)
    state: Literal["open", "unavailable"]
    operation_id: OperationId


class DraftMatchRequest(ContractModel):
    """Transient title-only search input; no draft is persisted."""

    draft_title: str = Field(min_length=1, max_length=120)


class DraftMatchResult(ContractModel):
    """Bounded available-listing preview for a transient draft title."""

    items: list[ListingSummary]
    has_more: bool


class StartWantedResponse(ContractModel):
    """Idempotency key for a regular member's Wanted Request response."""

    operation_id: OperationId


class SaveListingRequest(ContractModel):
    """Idempotency key for creating the caller's saved listing pair."""

    operation_id: OperationId


class SavedListingAck(ContractModel):
    """Acknowledgement of the caller's saved pair without listing details."""

    listing_id: ListingId
    saved_at: UtcInstant


class SavedListingView(ContractModel):
    """Caller-owned saved reference with current safe detail or retired marker."""

    listing_id: ListingId
    saved_at: UtcInstant
    listing: ListingSummary | None
    retired: bool


class ConversationSummary(ContractModel):
    """Participant-scoped conversation row and current offer summary."""

    conversation_id: ConversationId
    origin_kind: OriginKind
    origin_id: UUID
    initiator_user_id: UserId
    caller_role: Literal["initiator", "origin_owner"]
    counterparty_user_id: UserId
    last_activity_at: UtcInstant
    own_last_read_sequence: int = Field(ge=0)
    unread_count: int = Field(ge=0)
    current_offer: CurrentOfferSummary | None = None


class ConversationEntry(ContractModel):
    """Ordered message/share envelope metadata; content may be retired."""

    entry_id: UUID
    sequence: int = Field(ge=1)
    kind: Literal["message", "contact_share"]
    sender_user_id: UserId
    created_at: UtcInstant
    envelope: CipherEnvelope | None = None
    content_deleted: bool = False


class EntryPage(ContractModel):
    """Ordered entry page and replay-safe cursor state."""

    items: list[ConversationEntry]
    last_sequence: int = Field(ge=0)
    has_more: bool


class EntryQuery(ContractModel):
    """Cursor and bounded page size for ascending conversation entries."""

    after_sequence: int = Field(default=0, ge=0)
    page_size: Literal[20, 50, 100] = 20


class MessageRequest(ContractModel):
    """Encrypted message plus stable retry key."""

    envelope: CipherEnvelope
    operation_id: OperationId


class ReadState(ContractModel):
    """Only the caller's authenticated monotonic read watermark."""

    own_last_read_sequence: int = Field(ge=0)


class ReadAcknowledgement(ContractModel):
    """Read acknowledgement bounded by the greatest committed sequence."""

    last_read_sequence: int = Field(ge=0)


class KeyBundle(ContractModel):
    """One user's public bundle and its compatible protocol metadata."""

    user_id: UserId
    protocol_id: str
    protocol_version: str
    key_version: int = Field(ge=1)
    bundle_base64: str = Field(min_length=1, repr=False)


class MemberKeyBundles(ContractModel):
    """Current and retained historical public bundles for thread members."""

    members: list[KeyBundle]


class PublicKeyBundleRequest(ContractModel):
    """Opaque standard padded Base64 public-key bundle registration."""

    protocol_id: str
    protocol_version: str
    bundle_base64: str = Field(min_length=1, repr=False)
    operation_id: OperationId


class PublicKeyBundleView(ContractModel):
    """Server-assigned version for the caller's public bundle."""

    user_id: UserId
    protocol_id: str
    protocol_version: str
    key_version: int = Field(ge=1)


class ContactPreparationRequest(ContractModel):
    """Explicitly selected own-contact field names, not their values."""

    fields: list[ContactField] = Field(min_length=1, max_length=3)


class ContactShareRequest(ContractModel):
    """Encrypted selected-contact share plus stable retry key."""

    envelope: CipherEnvelope
    operation_id: OperationId


class ConversationQuery(ContractModel):
    """Participant-scoped filters, stable sorting and numbered paging."""

    view: Literal["initiated", "origin_owner", "all"] = "all"
    origin_kind: OriginKind | None = None
    origin_id: UUID | None = None
    counterparty_user_id: UserId | None = None
    offer_status: Literal["submitted", "withdrawn"] | None = None
    offer_min_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    offer_max_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    sort: Literal["last_activity_desc", "offer_amount_asc", "offer_amount_desc"] = (
        "last_activity_desc"
    )
    page: int = Field(default=1, ge=1)
    page_size: Literal[20, 50, 100] = 20


# Internal cross-domain types are injected by trusted server composition. Their
# Python types document caller intent; constructing one is not an auth mechanism.
@dataclass(frozen=True)
class OriginOwnerContext:
    """In-process marker for Listings or Search's own retirement operation."""

    origin_kind: OriginKind


@dataclass(frozen=True)
class NotificationWorkerContext:
    """In-process marker injected only into the notification worker boundary."""


class ListingConversationContext(ContractModel):
    """Server-resolved Listing ID and owner for a sale-origin thread."""

    listing_id: ListingId
    owner_id: UserId


class WantedConversationContext(ContractModel):
    """Server-resolved request ID and author for a Wanted-origin thread."""

    request_id: WantedRequestId
    author_id: UserId


class ExistingWantedConversationLookup(ContractModel):
    """Exact request/responder pair lookup; this operation never creates."""

    request_id: WantedRequestId


class ListingThreadParticipantCheck(ContractModel):
    """Exact listing thread/member pair checked for seller selection."""

    listing_id: ListingId
    conversation_id: ConversationId
    candidate_user_id: UserId


class ParticipantCheck(ContractModel):
    """Boolean-only participant result; no message or offer data."""

    is_participant: bool


class ListingOfferCommand(ContractModel):
    """Server-resolved offer mutation; action distinguishes submit and withdrawal."""

    action: Literal["submit", "withdraw"]
    listing_id: ListingId
    conversation_id: ConversationId
    offer_id: OfferId | None = None
    amount_paise: int | None = Field(default=None, ge=0, multiple_of=100)
    note_envelope: CipherEnvelope | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    operation_id: OperationId


class OriginActivityRequest(ContractModel):
    """Owner-scoped activity query without thread identities or contents."""

    origin_kind: OriginKind
    origin_id: UUID


class OriginActivityResult(ContractModel):
    """Minimal retained thread count and latest participant write time."""

    thread_count: int = Field(ge=0)
    latest_participant_write_at: UtcInstant | None


class OriginRetirementCommand(ContractModel):
    """Stable retirement attempt checked atomically against every thread."""

    origin_kind: OriginKind
    origin_id: UUID
    cutoff_utc: UtcInstant
    operation_id: OperationId


class RetirementMarkerResult(ContractModel):
    """All-or-none retirement marker outcome; no cleanup is implied."""

    marked_count: int = Field(ge=0)
    already_retired: bool


class NotificationClaimRequest(ContractModel):
    """Bounded due-intent claim request using controlled UTC time."""

    now_utc: UtcInstant
    max_items: int = Field(default=20, ge=1, le=50)


class NotificationClaim(ContractModel):
    """Fenced lease metadata without address, message, contact, or ciphertext."""

    intent_id: UUID
    conversation_id: ConversationId
    recipient_id: UserId
    event_kind: Literal["unread_message"]
    due_at: UtcInstant
    target_sequence: int | None = Field(default=None, ge=1)
    fencing_token: UUID
    lease_expires_at: UtcInstant


class NotificationClaimResult(ContractModel):
    """Claims returned from one bounded lease operation."""

    claims: list[NotificationClaim]


class NotificationDispatchCheck(ContractModel):
    """Fencing token/time recheck immediately before external dispatch."""

    intent_id: UUID
    fencing_token: UUID
    now_utc: UtcInstant


class NotificationDispatchContext(ContractModel):
    """Send/suppress/defer outcome with recipient UUID only when authorized."""

    decision: Literal["send", "suppress", "defer"]
    recipient_id: UserId | None = None
    target_sequence: int | None = Field(default=None, ge=1)


class NotificationAttemptResult(ContractModel):
    """Worker result recorded against the exact active fencing token."""

    intent_id: UUID
    fencing_token: UUID
    outcome: Literal["delivered", "transient_failure", "terminal_failure", "ambiguous"]
    attempted_at: UtcInstant


class NotificationIntentState(ContractModel):
    """Non-sensitive intent state returned after one worker transition."""

    state: Literal["pending", "leased", "delivered", "suppressed", "terminal"]
    attempt_count: int = Field(ge=0)


class ConversationThreadContext(ContractModel):
    """Shared private thread selector used only in Conversations implementation."""

    conversation_id: ConversationId
