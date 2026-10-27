# Generated from contracts/source/types.py; format 2. Do not edit.
"""Canonical typed data shapes shared by the four domain contracts.

These models describe reviewed wire and in-process values. They do not perform
authorization, persistence, provider calls, retries, encryption, or cleanup.
"""

from __future__ import annotations

import base64
import re
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
    model_validator,
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
    """OpenE2EE relay envelope metadata and its opaque transport payload."""

    protocol_id: str
    protocol_version: str
    envelope_version: int = Field(ge=1, le=2)
    sdk_message_type: Literal["ciphertext", "prekey_bundle", "retry_request"]
    sdk_client_message_id: str | None = Field(
        default=None, min_length=1, max_length=128
    )
    recovery_for_entry_id: UUID | None = None
    client_timestamp_ms: int = Field(ge=0, le=9_007_199_254_740_991, strict=True)
    sender_key_version: int | None = Field(default=None, ge=1)
    recipient_key_version: int | None = Field(default=None, ge=1)
    payload_base64: str = Field(min_length=1, max_length=87384, repr=False)

    @model_validator(mode="after")
    def validate_sdk_envelope_metadata(self) -> CipherEnvelope:
        """Validate selected SDK metadata while keeping payload bytes opaque."""
        if (
            self.protocol_id != "open-e2ee-signal"
            or self.protocol_version != "13.0.0"
            or self.envelope_version not in {1, 2}
        ):
            raise ValueError("unsupported conversation protocol or envelope version")
        try:
            payload = base64.b64decode(self.payload_base64, validate=True)
        except ValueError as exc:
            raise ValueError("payload must use standard padded Base64") from exc
        if (
            not 1 <= len(payload) <= 65536
            or base64.b64encode(payload).decode("ascii") != self.payload_base64
        ):
            raise ValueError("payload has invalid Base64 or byte length")
        has_versions = (
            self.sender_key_version is not None
            and self.recipient_key_version is not None
        )
        recovery_suffix = None
        if self.envelope_version == 2 and self.sdk_client_message_id is not None:
            recovery_suffix = self.sdk_client_message_id.split(":", 1)[1:]
        is_null_recovery = bool(
            recovery_suffix and recovery_suffix[0].startswith("null")
        )
        if self.sdk_message_type == "retry_request" or is_null_recovery:
            if (
                self.sender_key_version is not None
                or self.recipient_key_version is not None
            ):
                raise ValueError(
                    "retry requests must not claim encryption key versions"
                )
        elif not has_versions:
            raise ValueError("encrypted SDK envelopes require both key versions")
        if self.envelope_version == 1:
            if self.recovery_for_entry_id is not None:
                raise ValueError("legacy envelopes cannot identify a recovery target")
        else:
            if self.sdk_client_message_id is None:
                raise ValueError("v2 envelopes require the SDK client message ID")
            try:
                sdk_id_bytes = self.sdk_client_message_id.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError("SDK client message ID must be ASCII") from exc
            if len(sdk_id_bytes) > 128 or any(
                byte < 32 or byte > 126 for byte in sdk_id_bytes
            ):
                raise ValueError(
                    "SDK client message ID must be bounded printable ASCII"
                )
            recovery_id = re.fullmatch(
                r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
                r"(?::(retry-request|resend|null)(?::([2-9]|[1-9][0-9]+))?)?",
                self.sdk_client_message_id,
            )
            if recovery_id is None:
                raise ValueError("SDK client message ID has an unsupported format")
            if (
                recovery_id.group(3)
                and int(recovery_id.group(3)) > 9_007_199_254_740_991
            ):
                raise ValueError("recovery attempt exceeds the SDK safe integer range")
            is_recovery = recovery_id.group(2) is not None
            if is_recovery != (self.recovery_for_entry_id is not None):
                raise ValueError("recovery SDK IDs must bind an original entry")
            if not is_recovery and self.sdk_message_type == "retry_request":
                raise ValueError("retry requests must use a recovery SDK ID")
            if not is_recovery and UUID(recovery_id.group(1)).version != 4:
                raise ValueError("ordinary v2 SDK IDs must be UUIDv4")
            if is_recovery and recovery_id.group(2) == "retry-request":
                if self.sdk_message_type != "retry_request":
                    raise ValueError(
                        "retry-request IDs require retry request envelopes"
                    )
            elif is_recovery and self.sdk_message_type == "retry_request":
                raise ValueError(
                    "only retry-request IDs may use retry request envelopes"
                )
        return self


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
    pickup_area: str | None
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
    search_mode: Literal["keyword", "hybrid"] = "keyword"
    sort: Literal["created_desc", "price_asc", "price_desc", "relevance"] = (
        "created_desc"
    )
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
    pickup_area: str | None = Field(default=None, min_length=1, max_length=120)
    available_from: UtcInstant | None = None
    available_until: UtcInstant | None = None
    proof_available: bool | None = None
    image_upload_ids: list[ImageId] = Field(min_length=1, max_length=8)
    operation_id: OperationId


class ExistingListingImage(ContractModel):
    """Keep one of the listing's currently attached images in place/order."""

    source: Literal["existing"]
    image_id: ImageId


class NewListingImage(ContractModel):
    """Attach one newly confirmed, owner-bound image upload."""

    source: Literal["upload"]
    upload_id: ImageId


ListingImageSelection = Annotated[
    ExistingListingImage | NewListingImage,
    Field(discriminator="source"),
]


class ListingReplacement(ContractModel):
    """Replace listing details and its ordered keep/add image selection."""

    expected_revision: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    category_code: str
    condition_code: str
    asking_price_paise: int = Field(ge=0, multiple_of=100)
    negotiable: bool
    pickup_area: str | None = Field(min_length=1, max_length=120)
    available_from: UtcInstant
    available_until: UtcInstant | None
    proof_available: bool | None
    images: list[ListingImageSelection] = Field(min_length=1, max_length=8)
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

    @model_validator(mode="after")
    def validate_encrypted_note(self) -> OfferRevisionRequest:
        if (
            self.note_envelope is not None
            and self.note_envelope.sdk_message_type != "ciphertext"
        ):
            raise ValueError("offer notes require an encrypted ciphertext envelope")
        return self


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
    """Ordered message/control/share envelope metadata; content may be retired."""

    entry_id: UUID
    sequence: int = Field(ge=1)
    kind: Literal["message", "protocol_control", "contact_share"]
    sender_user_id: UserId
    created_at: UtcInstant
    envelope: CipherEnvelope | None = None
    recovery_target: RecoveryTarget | None = None
    content_deleted: bool = False

    @model_validator(mode="after")
    def validate_entry_envelope_kind(self) -> ConversationEntry:
        if self.envelope is None:
            if self.recovery_target is not None:
                raise ValueError("recovery targets require a retained envelope")
            return self
        sdk_type = self.envelope.sdk_message_type
        if self.kind == "protocol_control":
            if self.envelope.envelope_version == 1:
                if sdk_type != "retry_request" or self.recovery_target is not None:
                    raise ValueError("legacy protocol controls require a retry request")
            elif (
                self.envelope.recovery_for_entry_id is None
                or self.recovery_target is None
            ):
                raise ValueError(
                    "protocol controls require a stored v2 recovery target"
                )
        if self.kind != "protocol_control" and (
            self.envelope.recovery_for_entry_id is not None
            or self.recovery_target is not None
        ):
            raise ValueError("only protocol controls may identify a recovery target")
        if (
            self.kind == "protocol_control"
            and sdk_type == "retry_request"
            and self.envelope.envelope_version == 2
        ):
            if (
                self.envelope.sdk_client_message_id is None
                or not self.envelope.sdk_client_message_id.endswith(":retry-request")
            ):
                raise ValueError("retry requests require a retry-request SDK ID")
        if self.kind == "message" and sdk_type not in {"ciphertext", "prekey_bundle"}:
            raise ValueError("messages require encrypted SDK content")
        if self.kind == "contact_share" and sdk_type not in {"ciphertext", "prekey_bundle"}:
            raise ValueError("contact shares require encrypted SDK content")
        return self


class RecoveryTarget(ContractModel):
    """Stored original entry details used to restore recovered content in place."""

    entry_id: UUID
    sequence: int = Field(ge=1)
    sender_user_id: UserId
    created_at: UtcInstant


class EntryPage(ContractModel):
    """Visible entry page plus the last global sequence inspected for this member."""

    items: list[ConversationEntry]
    scanned_through_sequence: int = Field(ge=0)
    has_more: bool


class EntryQuery(ContractModel):
    """Cursor and bounded page size for ascending conversation entries."""

    after_sequence: int = Field(default=0, ge=0)
    page_size: Literal[20, 50, 100] = 20


class MessageRequest(ContractModel):
    """OpenE2EE envelope plus a UUIDv4 CLIP write identity."""

    envelope: CipherEnvelope
    operation_id: OperationId

    @model_validator(mode="after")
    def validate_operation_id(self) -> MessageRequest:
        """Keep v1's shared ID compatible and v2's API ID independently typed."""
        if self.operation_id.version != 4:
            raise ValueError("operation_id must be UUIDv4")
        if (
            self.envelope.envelope_version == 1
            and self.envelope.sdk_client_message_id
            not in {None, str(self.operation_id)}
        ):
            raise ValueError("v1 SDK client ID must equal operation_id")
        return self


class ReadState(ContractModel):
    """Only the caller's authenticated monotonic read watermark."""

    own_last_read_sequence: int = Field(ge=0)


class ReadAcknowledgement(ContractModel):
    """Read acknowledgement bounded by the greatest committed sequence."""

    last_read_sequence: int = Field(ge=0)


def _validate_base64_key(value: str, expected_bytes: int, label: str) -> None:
    """Require canonical standard Base64 for one SDK public-key field."""
    try:
        decoded = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise ValueError(f"{label} must use standard padded Base64") from exc
    if (
        len(decoded) != expected_bytes
        or base64.b64encode(decoded).decode("ascii") != value
    ):
        raise ValueError(f"{label} has an invalid encoding or byte length")


class PublicCompositeIdentityV1(ContractModel):
    """OpenE2EE public identity tuple; private identity keys never cross the API."""

    version: Literal[1] = 1
    x25519_public_key_base64: str = Field(min_length=1, max_length=64, repr=False)
    ed25519_public_key_base64: str = Field(min_length=1, max_length=64, repr=False)

    @model_validator(mode="after")
    def validate_public_key_lengths(self) -> PublicCompositeIdentityV1:
        _validate_base64_key(self.x25519_public_key_base64, 32, "X25519 key")
        _validate_base64_key(self.ed25519_public_key_base64, 32, "Ed25519 key")
        return self


class PublicEcSignedPreKey(ContractModel):
    """Public X25519 signed prekey and its OpenE2EE identity signature."""

    key_id: int = Field(ge=0, le=4_294_967_295)
    public_key_base64: str = Field(min_length=1, max_length=64, repr=False)
    signature_base64: str = Field(min_length=1, max_length=88, repr=False)

    @model_validator(mode="after")
    def validate_key_lengths(self) -> PublicEcSignedPreKey:
        _validate_base64_key(self.public_key_base64, 32, "EC signed prekey")
        _validate_base64_key(self.signature_base64, 64, "EC prekey signature")
        return self


class PublicKemPreKey(ContractModel):
    """Public tagged ML-KEM-1024 prekey and its identity signature."""

    key_id: int = Field(ge=0, le=4_294_967_295)
    public_key_base64: str = Field(min_length=1, max_length=2200, repr=False)
    signature_base64: str = Field(min_length=1, max_length=88, repr=False)

    @model_validator(mode="after")
    def validate_key_lengths(self) -> PublicKemPreKey:
        _validate_base64_key(self.public_key_base64, 1569, "KEM prekey")
        _validate_base64_key(self.signature_base64, 64, "KEM prekey signature")
        return self


class KeyBundle(ContractModel):
    """Typed public SDK bundle and its compatible protocol metadata."""

    user_id: UserId
    protocol_id: str
    protocol_version: str
    key_version: int = Field(ge=1)
    registration_id: int = Field(ge=1, le=16383)
    device_id: Literal[1] = 1
    identity: PublicCompositeIdentityV1
    ec_signed_prekey: PublicEcSignedPreKey
    kem_last_resort_prekey: PublicKemPreKey


class MemberKeyBundles(ContractModel):
    """Current and retained historical public bundles for thread members."""

    members: list[KeyBundle]


class PublicKeyBundleRequest(ContractModel):
    """Register own public OpenE2EE identity and reusable signed prekeys."""

    protocol_id: str
    protocol_version: str
    registration_id: int = Field(ge=1, le=16383)
    device_id: Literal[1] = 1
    identity: PublicCompositeIdentityV1
    ec_signed_prekey: PublicEcSignedPreKey
    kem_last_resort_prekey: PublicKemPreKey
    operation_id: OperationId


class PublicKeyBundleView(ContractModel):
    """Server-assigned version for the caller's public bundle."""

    user_id: UserId
    protocol_id: str
    protocol_version: str
    key_version: int = Field(ge=1)


class PublicPreKeyMaterial(ContractModel):
    """One public one-time prekey in OpenE2EE's supported client profile."""

    key_type: Literal["ecPreKey", "kemOneTimePreKey"]
    key_id: int = Field(ge=0)
    public_key_base64: str = Field(min_length=1, max_length=4096, repr=False)
    signature_base64: str | None = Field(
        default=None, min_length=1, max_length=256, repr=False
    )

    @model_validator(mode="after")
    def validate_signature_shape(self) -> PublicPreKeyMaterial:
        try:
            public_key = base64.b64decode(self.public_key_base64, validate=True)
        except ValueError as exc:
            raise ValueError("prekey bytes must use standard padded Base64") from exc
        if (
            not public_key
            or base64.b64encode(public_key).decode("ascii") != self.public_key_base64
        ):
            raise ValueError("prekey bytes must use standard padded Base64")
        expected_length = 32 if self.key_type == "ecPreKey" else 1569
        if len(public_key) != expected_length:
            raise ValueError("prekey public key has an invalid byte length")

        if self.signature_base64 is not None:
            try:
                signature = base64.b64decode(self.signature_base64, validate=True)
            except ValueError as exc:
                raise ValueError(
                    "prekey bytes must use standard padded Base64"
                ) from exc
            if (
                not signature
                or base64.b64encode(signature).decode("ascii") != self.signature_base64
            ):
                raise ValueError("prekey bytes must use standard padded Base64")
            if len(signature) != 64:
                raise ValueError("prekey signature has an invalid byte length")
        if self.key_type == "kemOneTimePreKey" and self.signature_base64 is None:
            raise ValueError("KEM one-time prekeys require an identity signature")
        if self.key_type == "ecPreKey" and self.signature_base64 is not None:
            raise ValueError("EC one-time prekeys do not carry a signature")
        return self


class PublicPreKeyBatchRequest(ContractModel):
    """Idempotent public one-time prekey publication for the active key version."""

    key_version: int = Field(ge=1)
    prekeys: list[PublicPreKeyMaterial] = Field(min_length=1, max_length=200)
    operation_id: OperationId

    @model_validator(mode="after")
    def validate_unique_prekey_ids(self) -> PublicPreKeyBatchRequest:
        identifiers = [(prekey.key_type, prekey.key_id) for prekey in self.prekeys]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("prekey IDs must be unique within each key type")
        return self


class OwnPreKeyInventory(ContractModel):
    """Counts only the authenticated account's unconsumed public prekeys."""

    key_version: int = Field(ge=1)
    ec_one_time_count: int = Field(ge=0)
    kem_one_time_count: int = Field(ge=0)


class PublicPreKeyBatchView(ContractModel):
    """Accepted public-prekey counts for the caller's active key version."""

    key_version: int = Field(ge=1)
    ec_one_time_count: int = Field(ge=0)
    kem_one_time_count: int = Field(ge=0)


class PreKeyBundleRequest(ContractModel):
    """Idempotency key for atomically reserving a member's one-time prekeys."""

    operation_id: OperationId


class MemberPreKeyBundle(ContractModel):
    """Peer's public session bundle plus any atomically consumed one-time keys."""

    key_bundle: KeyBundle
    registration_id: int = Field(ge=1, le=16383)
    device_id: Literal[1] = 1
    ec_one_time_prekey: PublicPreKeyMaterial | None = None
    kem_one_time_prekey: PublicPreKeyMaterial | None = None

    @model_validator(mode="after")
    def validate_selected_prekey_types(self) -> MemberPreKeyBundle:
        if (
            self.ec_one_time_prekey is not None
            and self.ec_one_time_prekey.key_type != "ecPreKey"
        ):
            raise ValueError("EC one-time prekey field requires an EC prekey")
        if (
            self.kem_one_time_prekey is not None
            and self.kem_one_time_prekey.key_type != "kemOneTimePreKey"
        ):
            raise ValueError("KEM one-time prekey field requires a KEM prekey")
        if self.registration_id != self.key_bundle.registration_id:
            raise ValueError("registration ID must match the registered key bundle")
        if self.device_id != self.key_bundle.device_id:
            raise ValueError("device ID must match the registered key bundle")
        return self


class ContactPreparationRequest(ContractModel):
    """Explicitly selected own-contact field names, not their values."""

    fields: list[ContactField] = Field(min_length=1, max_length=3)


class ContactShareRequest(ContractModel):
    """Encrypted selected-contact share plus stable retry key."""

    envelope: CipherEnvelope
    operation_id: OperationId

    @model_validator(mode="after")
    def validate_encrypted_contact_share(self) -> ContactShareRequest:
        if self.envelope.sdk_message_type not in {"ciphertext", "prekey_bundle"}:
            raise ValueError("contact shares require encrypted SDK content")
        return self


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


class ExistingListingConversationLookup(ContractModel):
    """Exact listing/authenticated-buyer lookup; this operation never creates."""

    listing_id: ListingId


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
    """Stable owner-authorized retirement attempt checked against every thread."""

    origin_kind: OriginKind
    origin_id: UUID
    cutoff_utc: UtcInstant
    operation_id: OperationId


class RetirementMarkerResult(ContractModel):
    """Marker outcome/count; already-marked reports the existing marker count."""

    outcome: Literal["marked", "blocked_recent_activity", "already_marked"]
    marked_count: int = Field(ge=0)


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
