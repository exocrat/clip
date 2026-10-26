# Identity own contacts, trusted sharing scope and private-data cleanup

**Date:** 2026-10-24
**Origin:** ID-01 Step9 verified plan, recorded2026-10-24 06:50:21 UTC.

## Question
How should Step9 enforce own-contact updates, deliberate scoped disclosure and
source-profile cleanup without reverse domain dependencies?

## Options considered
- Explicit immutable server scope after owning Conversation checks, with fresh
  Identity authorization and shared user-first cleanup locks (selected).
- IDs or client flags alone; these cannot establish participation or consent.

## Selected choice
Aditya verified adding explicit own-profile implementation to Step9, existing
reviewed own-contact routes/validation, actor-bound sharing and30-day cleanup.
Display names trim to1–80 Unicode code points, omission unchanged/null clears.
Contact email/phone/UPI are trimmed, bounded and syntactically validated; contact
email is not authentication and never changes the separate login key. Use
pinned email-validator syntax only with DNS/deliverability disabled, preserving
the entered trimmed contact spelling. Internationalized syntax is supported;
no deliverability/mailbox/bank/payment verification is claimed. E.164 contact
phone is plus and8–15 digits; VPA is3–100 ASCII local-part@handle.

## Trusted disclosure boundary
Introduce a frozen non-HTTP ContactSharingContext with actor/conversation IDs
and optional confirmed-fields set. A generic technical runtime-claims scope is
installed only by trusted server composition after Conversations proves
participation and the UI's explicit confirmation. Availability can use a
participation-only scope; selected values require a nonempty confirmed-field
scope matching the actor/conversation/request. Construction is not proof of
membership; caller preconditions and real Conversation/client integration remain
required. Browser JSON/headers cannot install claims. Identity checks its own
fresh actor state and reads only that actor's fields, never reverse-imports
Conversations or reads its private tables.

Own-contact management uses the authenticated owner normally, without a sharing
permit. Generated internal sharing functions bind real providers but fail closed
outside the matching trusted scope. Options return flags only; selection returns
only requested/confirmed/still-present fields with unselected fields null. If a
requested field was removed, fail safely422 rather than substitute another value.
Keep all contact values out of general/session responses, logs/errors/evidence;
repr fields are hidden. No public sharing or user-directory endpoint is added.

## Cleanup mechanism
Extend the existing bounded dry-run/default, target-checked apply mechanism to
remove contacts and clear display_name/set profile_removed_at once the earliest
permanent revocation/temporary expiry reaches30days. Lock/recheck the user before
its contact/profile mutation; no account/enrollment/request/key marker deletion.
Field deletion is immediate for subsequent reads; previously returned/client-
encrypted copies retain their own Conversations policy. Schedule/live cleanup
still requires separate approval and runtime evidence. All local tests delete
only synthetic data in their own disposable database.

## Rationale
The scope makes caller preconditions explicit while preserving the directed call
graph. Field-only writes and user-first locks prevent lost unrelated values and
serialize terminal cleanup. Syntax-only validation avoids provider dependency or
unintended address/payment verification claims.

## Implications
Conversations must review and bind its actual participation/confirmation flow;
source edits cannot erase already encrypted participant-held copies. Runtime
scheduling, backup retention and observed deletion deadlines remain independent
gates. No shared schema migration or HTTP contract shape changes are required.

## Approver
Aditya(A), explicit Step9 plan verification. Independent affected-owner/peer and
actual Conversations membership/confirmation/encryption checks remain for their
named integration checkpoints; no FR/NFR/ID-READY closeout is implied.

## Supersedes
Resolves Step9 mechanism under [private-data retention](private-data-retention.md)
and [private contact payloads](private-offer-and-contact-payloads.md), preserving
[scoped runtime binding](identity-capabilities-and-runtime-binding.md).
