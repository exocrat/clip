# Conversation recovery transport — approved contract revision

**Date:** 2026-10-24
**Origin:** CN-01 Steps 6/8/9, isolated OpenE2EE recovery integration.
**Status:** Rahul verified the detailed revision on 2026-10-24 06:33:47 UTC.
The format and behavior below are approved for implementation. The recovery
storage migration, typed contracts, generated outputs and PostgreSQL message
provider support the v2 transport and preserve v1 reads. The isolated client
SDK protocol-control path is implemented and tested; browser/page integration
and real-service checks remain pending. Normal affected-owner code review
remains part of the PR process.

## Sender content-recovery policy

CLIP explicitly configures OpenE2EE `protocol.contentRecovery.mode` as `off` in
every client constructor. The SDK must not keep its additional resendable
plaintext record, even if a future local store qualifies for protected
recovery. On a failed decryption, the SDK may still send its retry request;
the original sender then answers with the SDK's null control and the original
message is not restored. The existing CLIP-local conversation-history cache
is separate and remains governed by its local-only history design; this choice
adds no backup or service-side plaintext storage.

When page-level control handling is wired, describe this to the sender as a
recipient decryption problem, not as a failed send: the encrypted entry may
have been accepted by the service even though the recipient could not read it.
Do not offer automatic resend; a user retry would be a new message.

## Problem and SDK evidence

The pinned `@open-e2ee/signal-protocol-sdk@13.0.0` produces recovery IDs such as
`<retry-id>:retry-request`, `<retry-id>:resend` and `<retry-id>:null`, with
`:<attempt>` from attempt 2. They are not UUIDv4 values. Its
`IncomingEnvelope.clientMessageId` must preserve this SDK ID when a transport
assigns its own entry ID. The current CLIP adapter requires a UUIDv4 SDK ID,
equates it with `operation_id`, and does not return it with entries.

The actual SDK retry-envelope constructor was exercised with synthetic
metadata on Node 24; its first automatic request failed CLIP's UUID rule.
Inspection of the installed release also confirms that
`processIncomingEnvelope` rejects retry requests; their supported receive
path is `receiveIncomingEnvelopes`. Ordinary encrypted recovery responses
still require the SDK's receive and retry-family handling, not a custom
decryption or resend algorithm.

## Approved identifiers and wire fields

Keep protocol version `13.0.0` and encrypted application-payload version `1`.
Introduce transport `envelope_version = 2`; this is an envelope metadata
revision, not a change to the cryptographic protocol or its ciphertext.

| Field | Meaning |
|---|---|
| `MessageRequest.operation_id` | Existing UUIDv4 API write identity. Generate it once and persist it before submitting an SDK send; identical HTTP retries reuse it. Ordinary application sends may continue using the same UUID as their SDK ID. |
| `CipherEnvelope.sdk_client_message_id` | Required v2 string containing the SDK's exact `clientMessageId`, preserved on submit, storage and retrieval. Accept ordinary UUIDv4 IDs and the pinned SDK's recovery-family IDs; limit to 128 ASCII characters and validate the family/attempt grammar. Do not strip suffixes or replace the SDK ID with a CLIP UUID. |
| `CipherEnvelope.recovery_for_entry_id` | Null for a new application message. For a retry request, resend or null response, identifies the original retained chat entry being recovered. It is a routing claim checked by the server, not cryptographic proof of the SDK payload. |
| `ConversationEntry.entry_id` and `sequence` | Existing server-assigned identity and ordered transport position. Every committed recovery entry receives its own values. They remain distinct from the SDK ID and the original chat entry. |
| `ConversationEntry.recovery_target` | Null for ordinary entries. For recovery entries, server-derived original `{entry_id, sequence, sender_user_id, created_at}`. It lets the client attach recovered content to the original chat position without inventing a new user message. |

Keep the existing envelope protocol/type/timestamp/key-version/payload fields.
`retry_request` has null key versions and an opaque unencrypted payload.
Encrypted resends have the original application's key-version context and
SDK timestamp; SDK null responses have no application-content context and
carry null application key-version references. They must use the SDK's
internal-control receive path. The v2 type validator must
distinguish those cases explicitly rather than treating every encrypted
SDK envelope as a user message.

The original `recovery_for_entry_id` refers to a chat-message entry, never a
different conversation, contact share, offer or recovery transport entry.
When the SDK reports a failed recovery response, local recovery metadata maps
that transport entry back to its original chat entry. The original ID remains
stable through every attempt.

## Submission, correlation and authorization

1. Preserve two durable idempotency scopes: `(sender, operation_id)` and
   `(sender, sdk_client_message_id)`. Before posting, the client atomically
   stores the SDK-ID-to-operation-ID mapping, exact prepared envelope,
   conversation, peer and original-message reference. A retry or restart
   reuses that mapping and its prepared bytes. Concurrent attempts cannot
   allocate different CLIP operations for one SDK send.
2. The server checks membership and derives sender/recipient as today. For a
   recovery target, verify the original is a retained encrypted chat message
   in this same thread. Only its recipient may request recovery; only its
   sender may send a response. Bind a recovery family to the requester,
   original entry and other member on its first accepted request. Reject
   family reuse for another original, thread or peer. A response must match
   an accepted request and its attempt; it cannot establish a family itself.
3. The server never parses the opaque SDK payload. The outer SDK-ID grammar,
   target reference and member roles are metadata checks. The SDK validates
   the retry request and retry-family behavior; the recipient verifies the
   decrypted application context against the original target context.
4. The client records the original outgoing application route durably before
   encryption: conversation, peer, operation/SDK ID, key versions and SDK
   timestamp. A recovery response must resolve exactly one saved original
   route. It must not choose a thread from a timestamp alone or use whichever
   conversation page happens to be open. Missing or ambiguous correlation
   fails closed. Retain account/peer/thread isolation across restarts.
5. The pinned SDK's direct-message retry lookup uses peer/device and the
   original timestamp. Allocate SDK timestamps atomically and monotonically
   for each local account/peer across its conversations, so two original
   sends cannot overwrite that lookup at the same millisecond. These remain
   SDK metadata, never authoritative activity or ordering times.
6. Recovery cannot bypass a changed/unaccepted participant identity, a lost
   local key, the thread's no-write marker, existing request limits or content
   retention. If the original payload is purged, reject recovery with the
   existing safe expired-write conflict. Preserve the minimal ID/reference
   guards so a later attempt cannot recreate expired content.

For the same CLIP operation or SDK ID, changes to conversation, target, type,
timestamp, key versions or opaque payload are conflicts. An HTTP retry with
the identical saved operation and bytes returns the original committed entry.
Using a new CLIP UUID for an already bound SDK ID is a conflict, rather than a
second successful send. Server entry/sequence allocation and guard writes
commit atomically with the payload.

For a recovery-family SDK ID, the root is the SDK's lowercase UUID-shaped
retry ID; do not require its UUID version bits to be v4. The allowed suffix
is `retry-request`, `resend` or `null`, optionally followed by a canonical
decimal attempt number of at least 2 within JavaScript's safe-integer range.
Ordinary SDK IDs remain UUIDv4. Other SDK forms, including repair traffic,
remain unsupported until their own routing and replay behavior is reviewed.

## Receive, history and notification behavior

Every recovery request/response is returned as `kind = protocol_control`,
including an encrypted resend or SDK null response. Extend the kind/type
validation accordingly. The server returns it only to its recipient and
does not increment unread chat counts or create notification intents. Keep
the approved server-generated participant-activity timestamp and retention
rules for these writes; recovery does not introduce client-controlled times.

Reconstruct SDK input with the actual transport `entry_id` as `id` and the
unchanged `sdk_client_message_id` as `clientMessageId`. Route retry requests
and null responses through the SDK's supported control handling. Never
render their payload or pass a retry request to chat decryption.

For an SDK-validated content resend, check the original conversation,
participants, key versions and timestamp inside the decrypted application
payload, then durably store the text at the original chat entry ID/sequence.
The SDK retry-family result and the server's target must agree. The original
message, a resend and repeated recovery responses produce at most one local
chat message. Complete SDK receive work only after durable application
history storage succeeds. SDK completion is not a user read acknowledgement;
the displayed original message determines that acknowledgement.

Advance the polling cursor only after the relevant SDK work is safely
handled. A failed transport/storage operation keeps the entry retryable. A
malformed control that the SDK definitively drops must not block all later
chat entries. A handled request or null response does not prove that the
original content was recovered; retain a safe pending/unrecoverable state as
appropriate. Log none of the payloads, keys or recovery identifiers.

## Rollout and required checks

This document records the approved revision. Do not advertise v2 in generated
schemas while the server would discard its fields. Update canonical
types and human-readable contracts together, regenerate with the existing
generator, and add a new forward migration for SDK IDs, target references,
family bindings and uniqueness guards. Keep committed migration history.

Retained v1 messages must remain readable: their original SDK ID can be
reconstructed from the server's stored `client_operation_id`. Do this within
Conversations, without rewriting ciphertext or querying another domain.
Do not infer recovery metadata for old rows that never stored it. New
clients submit v2 only after server support is ready; v1 compatibility and
rejection behavior must be explicit and tested before rollout.

Use two actual SDK clients and synthetic HTTP fixtures, followed by real
API/PostgreSQL integration when dependencies are ready. Required cases:

- An original fails to decrypt, produces a real SDK recovery request, and
  recovers from the SDK response under the original chat entry.
- Request/response redelivery, attempt 2, ambiguous HTTP commit, adapter
  restart and concurrent tabs preserve both IDs and replay the saved bytes.
- Null responses, invalid controls and responses with no accepted request
  never render as user messages or create unread/notification side effects.
- Wrong member/thread/target/family/attempt and changed-key routing fail
  safely; same-peer cross-thread and timestamp-collision cases cannot resend
  a different conversation's content.
- Local-history failure remains retryable; cursor and SDK completion cannot
  skip unpersisted content. Recovery and original delivery deduplicate.
- Purged content, thread retirement and expired SDK reliability records
  cannot resurrect chat history or bypass existing write protections.
- v1 history, v2 submission/retrieval, ID conflicts, schema generation and
  database migration checks pass without sensitive evidence.

This revision does not supply key recovery or backups. Real Identity/origin
integration, browser durability and CN-CORE/NFR acceptance retain their
existing task gates.

## Review and supersession

**Approver:** Rahul (D) verified the detailed revision on
2026-10-24 06:33:47 UTC. Normal affected-owner code review remains required.
Conversations owns the implementation; Identity/notification
consumers review changed entry/read-state semantics through the normal PR.

**Supersedes after implementation:** the v1 assumption that every SDK ID is
a UUIDv4 equal to `operation_id`, and the assumption that every encrypted
`ciphertext`/`prekey_bundle` SDK send is a new user message. It leaves the
selected OpenE2EE release, application encryption format and no-backup policy
unchanged.
