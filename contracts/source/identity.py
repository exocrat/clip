"""Reviewed Identity HTTP operations and internal declaration-only callables."""

from app.core.auth import CallerContext
from app.core.identifiers import UserId

from contracts.source.types import (
    AccountClass,
    AccountEligibility,
    ActivateTemporaryRequest,
    ChallengeAccepted,
    ConversationId,
    ContactField,
    ContactValueRequest,
    MicrosoftSessionRequest,
    NotificationRecipient,
    NotificationWorkerContext,
    OwnContacts,
    PasswordResetChallengeRequest,
    ProfilePatch,
    ProfileView,
    RegistrationChallengeRequest,
    ResetTemporaryPasswordRequest,
    SelectedOwnContacts,
    SessionView,
    ShareableContactOptions,
    TemporarySessionRequest,
)

HTTP_OPERATIONS = (
    {
        "method": "POST",
        "path": "/auth/microsoft/sessions",
        "operation_id": "identity_create_microsoft_session",
        "body": MicrosoftSessionRequest,
        "response": SessionView,
    },
    {
        "method": "POST",
        "path": "/auth/temporary/registration-challenges",
        "operation_id": "identity_start_temporary_registration",
        "body": RegistrationChallengeRequest,
        "response": ChallengeAccepted,
        "status_code": 202,
    },
    {
        "method": "POST",
        "path": "/auth/temporary/accounts",
        "operation_id": "identity_activate_temporary_account",
        "body": ActivateTemporaryRequest,
        "response": SessionView,
        "status_code": 201,
    },
    {
        "method": "POST",
        "path": "/auth/temporary/sessions",
        "operation_id": "identity_create_temporary_session",
        "body": TemporarySessionRequest,
        "response": SessionView,
    },
    {
        "method": "POST",
        "path": "/auth/temporary/password-reset-challenges",
        "operation_id": "identity_start_password_reset",
        "body": PasswordResetChallengeRequest,
        "response": ChallengeAccepted,
        "status_code": 202,
    },
    {
        "method": "POST",
        "path": "/auth/temporary/password-resets",
        "operation_id": "identity_reset_temporary_password",
        "body": ResetTemporaryPasswordRequest,
        "status_code": 204,
    },
    {
        "method": "DELETE",
        "path": "/auth/session",
        "operation_id": "identity_logout",
        "status_code": 204,
    },
    {
        "method": "GET",
        "path": "/me",
        "operation_id": "identity_read_me",
        "response": SessionView,
    },
    {
        "method": "PATCH",
        "path": "/me/profile",
        "operation_id": "identity_update_own_profile",
        "body": ProfilePatch,
        "response": ProfileView,
    },
    {
        "method": "GET",
        "path": "/me/contacts",
        "operation_id": "identity_read_own_contacts",
        "response": OwnContacts,
    },
    {
        "method": "PUT",
        "path": "/me/contacts/{contact_kind}",
        "operation_id": "identity_set_own_contact",
        "path_parameters": {"contact_kind": ContactField},
        "body": ContactValueRequest,
        "status_code": 204,
    },
    {
        "method": "DELETE",
        "path": "/me/contacts/{contact_kind}",
        "operation_id": "identity_delete_own_contact",
        "path_parameters": {"contact_kind": ContactField},
        "status_code": 204,
    },
)


async def check_account_eligibility(
    user_id: UserId, required_class: AccountClass | None = None
) -> AccountEligibility:
    """Declare the minimal current account-capability lookup.

    This declaration returns no profile, contact, login, or denial-reason data.
    The owning Identity service supplies the eventual implementation.
    """
    raise NotImplementedError("declaration-only")


async def get_shareable_contact_options(
    caller: CallerContext, conversation_id: ConversationId
) -> ShareableContactOptions:
    """Declare actor-bound contact availability for a conversation flow.

    The caller must be the actor authorized by Conversations. Only availability
    flags are returned; this declaration reads no persistence or contact value.
    """
    raise NotImplementedError("declaration-only")


async def get_selected_own_contacts(
    caller: CallerContext,
    conversation_id: ConversationId,
    fields: frozenset[ContactField],
) -> SelectedOwnContacts:
    """Declare explicit, actor-bound own-contact retrieval for encryption.

    Only requested, currently present fields may be returned. Values are private
    and ephemeral; this declaration performs no read and always refuses calls.
    """
    raise NotImplementedError("declaration-only")


async def resolve_notification_recipient(
    context: NotificationWorkerContext, recipient_id: UserId
) -> NotificationRecipient | None:
    """Declare worker-authorized resolution of one eligible email recipient.

    The result is ephemeral and contains no profile fields. The context is
    injected by trusted worker wiring; the Python type itself is not a credential.
    """
    raise NotImplementedError("declaration-only")
