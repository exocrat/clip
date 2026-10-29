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

Only the authenticated user may change their own profile. NEXT-03 reuses
`display_name` as the required, editable Handle: trim surrounding whitespace,
accept 3–30 ASCII letters/digits/underscores, and enforce case-insensitive
uniqueness in the API and database, including concurrent claims. Omission leaves
it unchanged; explicit null, empty or invalid input returns 422; a taken Handle
returns a safe 409. `SessionView.handle_ready` marks a completed claim. Legacy
invalid/colliding names remain stored, with setup required before completing
normal UI onboarding; IDs, authentication and existing references are preserved.
The Identity-owned `identity.participant_profiles` public view exposes only user
ID, claimed Handle and active account class. Conversations may SELECT that view
for already-authorized members; it may not read private Identity tables, source
contacts, provider identifiers or email. Missing/retired profiles expose no name.
The deployment role needs explicit SELECT on this view, separately from private
Identity role permissions. No public arbitrary-profile HTTP lookup is added.

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
or temporary account, it returns only the current authorized login delivery
destination needed by the worker; for an ineligible/removed recipient, it
returns no destination. The destination is ephemeral to dispatch and is never
copied into notification intents. Per Aditya's 2026-10-29 decision, Identity
retains the authenticated account login address encrypted for this purpose.
Microsoft uses the signed IISc email claim under the previously approved domain
policy; it does not independently prove mailbox control. Temporary accounts
use their verified or password-authenticated login email. An existing account
without a stored destination must authenticate again before resolution succeeds.
Exact typed request/result,
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

## ID-01 reviewed session extension

Aditya verified [session/CSRF/cleanup settings](../docs/decisions/identity-sessions-and-cleanup.md).
Canonical additions: POST /auth/microsoft/login-attempts returns public nonce/expiry
plus a private HttpOnly attempt cookie, consumed once on assertion exchange;
GET /auth/csrf returns a session-bound CSRF token with no-store. Session secrets
remain cookie-only; exact origin/custom-header guards apply to unsafe requests.
The [combined registry](combined.md) and canonical typed sources define these
operations; regenerate declarations. Real provider/runtime/browser and peer
integration acceptance remain pending.

## ID-01 Step8 capability/runtime implementation

[Verified policy and binding](../docs/decisions/identity-capabilities-and-runtime-binding.md)
now implement the regular/temporary matrix with fresh Identity status/class/
lifetime checks. Temporary accounts retain browsing open Wanted Requests and
wanted authorship/existing authorized conversation rights, but cannot initiate
wanted responses or manage sale listings. Domain owners retain ownership,
participant, consent and resource-state checks; explicit public discovery stays
public. Context construction alone grants no authentication.

check_account_eligibility keeps the reviewed async signature and returns only
eligible. None means either active class; a supplied class matches exactly.
Missing/ineligible targets return false; invalid arguments422 and dependency/
unconfigured runtime503 fail closed. Target IDs must come from trusted context
or authoritative domain relationships. The generated scoped wrapper contains
only technical dispatch; actual provider reads fresh SQL. No public directory,
new HTTP operation, provider/cloud setup or full FR-03 acceptance is introduced.

## Step9 trusted sharing implementation

The [reviewed sharing/cleanup decision](../docs/decisions/identity-contact-sharing-and-cleanup.md)
requires trusted composition to install the frozen, server-only
`ContactSharingContext` from the generated public module through
`core.runtime_bindings.runtime_claims({"identity.contact_share": context})`.
Conversations must first establish actual participation, derive the actor and
conversation from authoritative context, and accept only the UI-confirmed fields.
This technical scope proves nothing by construction; it is never HTTP JSON or a
client authorization flag. Identity matches actor/conversation, rechecks current
account/capability, and requires requested fields to be a subset of the confirmed
nonempty set. A participation-only context permits flags, never values. Missing
or mismatched authority is403; missing runtime binding is503. A removed requested
field yields safe422 with `fields/unavailable_contact`; do not substitute values.
Real CN membership/confirmation/client encryption checks remain pending CN-02.

Editable email preserves trimmed spelling/aliases and supports internationalized
syntax with pinned email-validator, DNS/deliverability disabled. Phone is plus
and8–15 digits with a nonzero leading country digit. UPI syntax is3–100 ASCII
characters matching local-part `[A-Za-z0-9._-]+` and handle `[A-Za-z0-9.-]+`.
No mailbox/payment verification is claimed. Source fields never change login.
Bounded cleanup removes source contacts and display names30days after the earliest
permanent revocation/temporary expiry, preserving users and lifetime markers.
Actual scheduling and observed retention deadlines remain separately gated.

## Temporary password length revision

Aditya approved an8-character minimum on2026-10-24 09:15:28 UTC (recording
time). Activation, password reset and password verification share the same
8–128 Unicode-character policy. New activation/reset passwords reject whitespace
without trimming or normalization; existing passwords retain login compatibility. The backend enforces the limit; the UI provides matching guidance.
Existing longer passwords remain valid. Hashing/session/lifetime policy is
unchanged. See [temporary authentication](../docs/decisions/temporary-authentication-storage.md).

## Step11 browser Microsoft composition

The [browser implementation mechanism](../docs/decisions/identity-provider-setup.md#step11-browser-implementation--2026-10-24)
keeps the registered code/PKCE flow and server-bound nonce/cookie/session contract.
MSAL validates its response; application state/nonce/expiry checks precede one
POST /auth/microsoft/sessions. These client checks never replace backend signature,
issuer/audience/domain/cookie/nonce checks. No HTTP/schema or eligibility-policy
change. Server never logs/persists the assertion; browser SDK redirect artifacts
are transient under its session cache with explicit cleanup, not a CLIP bearer
store. No cached-token/silent-auth fallback or automatic exchange retry. Real
provider/cache/browser evidence remains required before readiness acceptance.

## Approved email routing — 2026-10-24

The private delivery boundary keeps its signature and application-owned OTP state.
Under [the routing decision](../docs/decisions/identity-email-routing.md), one
consumed ticket may invoke a router that attempts each real provider at most once,
primary then alternate, with identical message/OTP even after uncertain failure.
Two delivered copies are possible; no new code, renewed lifetime or auth success
is inferred. No provider outcome is returned through public challenge responses.
Routing/key configuration refreshes on demand at four-hour intervals; real
configuration/provider acceptance and SES restrictions remain separate gates.
No generated/public API shape change.
