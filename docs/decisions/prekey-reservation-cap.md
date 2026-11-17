# One-time prekey reservation cap per conversation member

**Date:** 2026-11-17

**Origin:** Red-team issue #62 triage (one conversation member can exhaust a peer's shared one-time prekey pool by issuing fresh operation IDs).

## Question
How should the directory bound how many of a peer's one-time prekeys a single conversation member can reserve, without breaking legitimate first-contact or exact-retry behaviour?

## Options considered
- Leave reservation guarded only by exact `operation_id` idempotency (baseline), so each new operation ID consumes another of the peer's shared prekeys.
- Cap reservations per `(requester, peer)` across all of the peer's conversations.
- Cap reservations per `(requester, conversation)`: one outstanding grant reused for any later operation ID in the same conversation.

## Selected choice
Reserve at most one of a peer's one-time prekeys per `(caller, conversation)`. In `PostgresKeyDirectory.consume_member_prekeys`, after the exact-`operation_id` replay check and under the existing peer-account lock, a fresh operation ID for the same conversation returns the member's already-stored reservation (looked up by the request payload) instead of consuming another prekey. Exact `operation_id` retries remain idempotent as before. This bounds a single member of a single conversation to one of the peer's one-time prekeys, so that member can no longer drain the shared pool and force other members' first contact onto the last-resort prekey.

## Rationale
Legitimate first contact needs exactly one one-time prekey per conversation, so capping at one reservation per `(caller, conversation)` does not affect normal use, keeps the change localised, reuses the existing serialising lock (no new deadlock surface), and needs no schema change. A per-`(requester, peer)` cap was rejected as more likely to interfere with distinct legitimate conversations against the same peer.

## Out of scope (accepted limitations)
These are deliberately **not** addressed by this fix and are recorded as known, accepted limitations for mentor/course visibility, not as unresolved defects:

- **Coordinated / multi-conversation drain.** The cap is per `(caller, conversation)`. An attacker using many conversations or accounts can still consume one prekey each and, in aggregate, deplete a peer's pool. Defending against distributed depletion (global per-peer rate/share limits, pool replenishment guarantees) is a separate hardening effort outside #62's scope.
- **Rebootstrap / re-contact reuse.** After a peer or caller key rebootstrap, the same member re-contacting the same conversation reuses the prior stored grant rather than obtaining a fresh one-time prekey. The returned public material stays usable, but forward secrecy is not refreshed for that re-contact. This interacts with the key-replacement concerns tracked under #55 and is left to that workstream.
- **Replenishment timing.** The online client can upload new prekeys, but the rate and offline behaviour of replenishment are not changed or guaranteed here.

Issue #62 is a minor E2EE-hardening gap (no key, ciphertext, or plaintext exposure; no loss of messaging); the accepted limitations above keep the fix small and low-risk, consistent with that severity.

## Implications
- Added `PostgresKeyDirectory._existing_request_result` (request-payload lookup complementing operation-id replay). Regression test asserts a member issuing several operation IDs consumes one prekey while another member still receives a distinct one; the prior depletion and concurrency tests were updated to the new per-member semantics.
- Protocol/crypto behaviour is owned by Conversations (Rahul). Live red-team retest, owner review, merge and deployment remain their own gates; this record does not certify them.

## Approver
Aditya (Cumulonimbus dev decision for #62), 2026-11-17.

## Supersedes
None. Relates to the [E2EE design proposal](./conversation-e2ee-design-proposal.md) and the key-replacement concerns in issue #55.
