# Identity contract

**Status:** Step 10 domain-owner documentation review is reported approved by
the user. Step 11 typed declarations are generated from this contract and the
[combined registry](combined.md). Identity behavior/provider implementation
remains with ID-01.

## Scope and ownership

Identity owns account identity, authentication credentials/sessions, account
eligibility, the user's own profile and source contact values. It supplies the
trusted `CallerContext` consumed by protected domain operations. Identity does
not own listings, Wanted Requests, conversation membership, contact-share
payloads, or notification-intent state. No public user directory or account
deletion endpoint is introduced.

## Account classes and lifecycle

| Class | Authentication and capabilities |
|---|---|
| Regular | Sign in through server-validated Microsoft identity for an approved IISc domain. May browse/search, save listings, create/manage Wanted Requests, create sale listings, start conversations, submit offers, and use approved contact sharing. No temporary-account expiry applies. |
| Temporary | Register with a separate email-verification flow, then normally sign in with a password. May browse/search, save listings, create/manage Wanted Requests, start listing-origin conversations and submit offers. May not create sale listings or start a Wanted Request response conversation. |
| Pending, expired or revoked | Pending accounts receive no authenticated marketplace capability. Expired/revoked account-level access is denied immediately, even before cleanup removes expired records. Routes explicitly defined as public by their owning domain remain public. |

For a temporary account, only the first successful initial email verification
sets `activated_at`; `expires_at` is exactly 14 × 24 hours later as a UTC-aware
instant. Registration, password entry, resend, repeated verification, login,
password reset and profile edits never restart that lifetime. A minimal keyed
normalized-login enrollment guard preserves the original activation/expiry and
prevents self-renewal for the service's operating lifetime. It is linkable
authentication data, not anonymous data.

Temporary email OTP is used only for initial verification and forgotten-password
reset. It is not a routine login option. Reset atomically changes the password
hash, consumes the purpose-bound reset challenge and revokes all existing
sessions; it does not reactivate or extend an expired/revoked account. OTPs,
passwords and session bearer tokens are never stored or logged in raw form.

Regular sign-in validates the Microsoft token on the server, including
signature, issuer, audience, expiry, required identity claims and approved
IISc-domain membership. The verified provider/issuer/subject tuple is the
idempotent account lookup key. Raw bearer tokens are not persisted. Frontend
domain checks are presentation only and never grant access.

## Trusted caller and authorization

Identity supplies the existing immutable `CallerContext` only after verifying
the credential and current account/session state. It contains `user_id`,
`account_class` (`regular` or `temporary`) and an aware UTC `valid_until` no
later than the applicable credential, session or account expiry. The shared
Python type is not proof of authentication. No client-provided ID, class,
ownership flag or capability can create or extend this context.

Identity rechecks current revocation/session state when establishing protected
request context. Each domain still authorizes access to its own resource and
action; a valid sign-in alone is not permission. Logout invalidates the current
session. Password reset or account revocation invalidates all affected sessions
for subsequent requests. No domain queries Identity's private tables.

## Own profile and source contacts

Only the authenticated user may read or change their own profile. The current
schema provides optional `display_name`; this contract adds no public profile
lookup or other profile fields. Exact display-name limits and update semantics
are finalized with operation details in Step 9 and reviewed in Step 10.

The authenticated user may collect, update or delete their own shareable
`email`, `phone` and `upi_id` values. Temporary login email/password identity is
stored separately from these editable contact values. No general profile,
listing, search or notification response exposes source contacts. User-requested
field deletion takes effect immediately in future reads. Otherwise, retain
source contacts only while the account is active and remove them no later than
30 days after expiry or permanent revocation.

The internal declarations
[`get_shareable_contact_options`](source/identity.py) and
[`get_selected_own_contacts`](source/identity.py) require the trusted actor to
bind to a conversation participant; callers cannot choose a target `user_id`.
Knowing another user's ID is never sufficient.
The options operation returns availability flags only. The selected-contact
operation accepts only the supported field names and returns only values the
actor explicitly selected and that remain available. It is callable only in
the approved conversation/contact-sharing flow after the caller's participation
and consent are established; the user must confirm before disclosure. The
client encrypts the resulting selected values before Conversations stores a
share. Do not return unselected values, use this interface for notifications,
or include values in errors, logs, analytics, fixtures or evidence.

The typed declarations take an explicit `CallerContext` and conversation scope,
so trusted actor binding is visible in the canonical source and provider
declaration before implementation.
The internal contact functions are not HTTP routes or OpenAPI/TypeScript
operations unless a later reviewed contract explicitly maps a user-facing
capability.

## Internal eligibility and notification-recipient boundaries

Listings, Search and Conversations may call Identity's narrow
`check_account_eligibility` operation when a cross-domain operation requires a
current account check. The target ID must come from the caller's trusted
context or the calling domain's own authoritative relationship; browser input
alone is never sufficient. The result is only whether the account is currently
eligible for the requested regular/temporary capability. It returns no
profile, contact, login, expiry or revocation detail. The authenticated actor's
`CallerContext` remains established by Identity's normal request-auth boundary.
The exact typed request/result and operation-specific safe errors are finalized
in Step 9.

`resolve_notification_recipient` is a separate, narrowly authorized internal
Identity operation callable only from the Conversations-owned CN-03 delivery
path. It is not `get_shareable_contact_options`,
`get_selected_own_contacts`, or a broad profile read. For an eligible regular
or temporary account, it returns only the current verified delivery
destination needed by the worker; for an ineligible/removed recipient, it
returns no destination. The destination is ephemeral to dispatch and is never
copied into a notification-intent record. Exact typed request/result,
eligibility recheck, safe outcome codes and dependency behavior are finalized
in Step 9 and owner-reviewed in Step 10. Its typed request includes the
server-injected `NotificationWorkerContext`; the value is not a credential and
must be supplied only by trusted worker wiring. Identity does not call
Conversations.

## Retention and errors

| Record | Required behavior |
|---|---|
| Used/expired OTP challenge | Remove 24 hours after consumption or expiry, whichever first makes it unusable. Bind each challenge to one account and purpose; consume once. |
| Expired/revoked session | Remove 7 days after the earlier terminal event; access ends immediately. |
| Temporary password hash | Remove within 24 hours after permanent expiry/revocation. |
| Enrollment guard | Preserve the keyed normalized login and original activation/expiry for the service's operating lifetime; do not retain the password or contact payload with it. |
| Source contact/profile values | Remove on user deletion; otherwise no later than 30 days after expiry/permanent revocation. |

Use the shared safe error envelope and stable status categories. Distinguish
unauthenticated from forbidden where this does not disclose account existence;
do not expose token-validation details, whether an unverified login exists,
OTP values, password state, raw provider errors, contact values or session
tokens. Invalid contact fields use safe `422` field codes; throttling uses the
shared `429` code. Provider failure must not create a successful identity or
pretend an OTP was delivered.

## Later contract work

Step 9 assigns stable operation names and records full input/output/nullability,
limits, authorization, errors, reads/writes, transaction boundaries,
idempotency, concurrency, dependency failures and test cases. Domain-owner
documentation review is reported approved; provider and abuse-control settings
that ID-01 requires the human to approve remain gates before enabling a real
provider. No live provider, account, credential, database, or cloud action is
authorized here.
