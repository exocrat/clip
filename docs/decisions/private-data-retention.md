# Private-data retention windows and minimal integrity records

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 privacy/lifecycle review.

## Question
How long should private/authentication data persist, and which minimal records must survive cleanup?

## Options considered
- Finite content/authentication retention with narrowly scoped integrity/no-self-renewal records.
- Retain every payload indefinitely or delete all identity/origin records with content; these respectively accumulate private data or break uniqueness/non-renewal guarantees.

## Selected choice
Mohit approved these windows, measured from the stated trigger:

| Data | Retention/cleanup |
|---|---|
| Used/expired OTP challenges | Delete 24 hours after consumption or expiry, whichever first makes the challenge unusable. |
| Minimal Identity OTP request marker | Retain for the service lifetime so the same operation cannot resend after OTP cleanup. Only keyed request digest, key version, challenge ID and original expiry; no email, IP, target digest, OTP, verifier or ciphertext. |
| Expired/revoked sessions | Delete 7 days after the earlier terminal event. |
| Permanently expired/revoked temporary password hashes | Delete within 24 hours. |
| Identity source contacts/profile | Remove on user field deletion; otherwise retain while active and at most 30 days after expiry/permanent revocation. Field deletion takes effect immediately in future contact retrieval. |
| Encrypted contact shares and selected-field labels | Delete after 30 days from each share, retaining only a content-free ordering marker. |
| Conversation messages, encrypted offer notes and structured offer revision history | Purge together after 90 days without a participant write. Reads/polling/workers do not renew the timer. |
| Sent/suppressed/terminally failed notification records | Delete after 30 days from terminal completion, preserving a separately reviewed bounded replay/deduplication guard when needed. |

Access expires/revokes immediately; these windows never extend access. Preserve minimal origin/participant/thread records while the parent origin exists to maintain one-conversation-per-pair. Preserve a keyed normalized-login enrollment identifier and original activation/expiry for the service's operating lifetime to prevent temporary-account self-renewal; remove password/contact content under its own window. This identifier is sensitive/linkable, not anonymous data. Create the guard only after verified activation.

Aditya (A) approved the minimal OTP request-marker exception on
2026-10-23 19:53:44 UTC (recording time). The keyed digest is sensitive/linkable,
not anonymous. This exception does not extend OTP validity or retention of
challenge content, target/source rate records, passwords or contact data. The
owning Step7 cleanup design must preserve markers while deleting private state
under its approved rules; no destructive mechanism is authorized here.

## Rationale
Bounds retained content while avoiding replay, duplicate conversation creation or account-lifetime reset as a side effect of cleanup.

## Implications
The [schema](../architecture/mvp-database-schema.md) adds last participant activity, content-deletion markers and a minimal enrollment guard. The separate [origin-retirement decision](origin-retirement.md) defines inactive listing/request retirement and minimal origin references. Affected owners must review safe FK/current-offer/notification-target cleanup, concurrent writes, key rotation and bounded notification deduplication; image cleanup, account/profile retirement, exceptional explicit-deletion handling, and implementation ordering remain for the owning tasks. No blanket cascade or public deletion endpoint is approved. Referenced public-key metadata remains subject to the final cryptographic/reference-retirement design.

Deletion jobs belong to owning domain implementations; PD-08 creates no deployed cleanup worker. Backups need a separately approved finite retention policy and restore-time deletion/expiry reconciliation. Live database deletion does not establish backup/provider deletion or erase participant-held copies. These choices authorize policy recording, not execution of destructive cleanup or cloud changes.

## Approver
Mohit (C), explicit approval of the retention durations and minimal-record exceptions. The user later confirmed the PD-08 privacy/affected-owner schema gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Domain implementation must still enforce and test these limits.

## Supersedes
None.

## ID-01 reviewed implementation mechanism

Aditya verified the [bounded Identity cleanup design](identity-sessions-and-cleanup.md)
in Step7. OTP first-unusable time includes supersession; session terminal time
includes idle expiry. Permanent temporary credential hashes are eligible at
expiry/revocation immediately, allowing a separately approved hourly deployment
to meet the within24-hour requirement. Obsolete login/OTP source/target windows
and attempt metadata are removed24hours after their protection window ends.
Per-table batches default100/max1000; dry-run default, target-checked explicit
apply and cutoff rechecks under compatible locks. Lifetime enrollment/request
markers, key commitments and users survive this mechanism. Step7 originally
preserved contacts; the approved Step9 extension below removes private source
fields under their own thirty-day window. No active
scheduler or actual retention-deadline evidence is claimed until approved
runtime deployment/run verification. Step9 owns contact/profile cleanup.

Step9 implements the [reviewed contact/profile cleanup mechanism](identity-contact-sharing-and-cleanup.md)
with user-first locks, cutoff rechecks, bounded candidates and dry-run counts.
It clears display_name and sets the permanent profile_removed_at marker, deletes
source contacts and preserves account/enrollment/request/key records. No live
cleanup or scheduling has been enabled by this code change.
