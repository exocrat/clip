# Conversations content cleanup mechanism

**Date:** 2026-10-26
**Origin:** CN-01 Step 9; Rahul authorized the proposed bounded cleanup implementation with “proceed” and “continue”.

## Selected mechanism

`ConversationCleanup` owns the 90-day inactivity purge. Its opt-in command
`scripts/conversations_cleanup.py` defaults to dry-run and emits aggregate thread
and entry counts only. It requires the expected database, host and port, checked
on every acquired connection against `CLIP_CONVERSATIONS_DATABASE_URL`. No DSN,
identifier, payload or driver error is printed. Production time comes from
PostgreSQL; there is no caller-supplied cutoff option.

Select up to100 threads by UUID (maximum1000), with latest participant activity
at or before server time minus90 days and retained entry content. For each
candidate, open one transaction, take the same thread row lock used by participant
writes, and recheck the cutoff. Equality qualifies. A newer write makes cleanup
skip that thread. Cleanup leaves sequence, activity, member/read, key-directory,
retirement-operation and no-write state untouched.

Within each eligible thread's transaction, use this order:

1. Clear each live offer's current-revision pointer and set its history-deleted
   timestamp, retaining its ID, buyer/thread uniqueness and next revision counter.
2. Delete its structured offer revisions, then encrypted payloads and contact-share
   subtype links for the thread. Shares in such an inactive thread are already
   beyond30 days; independent30-day share cleanup remains CN-02 work.
3. Set `content_deleted_at` on retained entries. Preserve routing, sequence,
   sender/operation/SDK IDs and recovery-family references. Deferred database
   constraints verify the final content graph at commit. Notification references
   remain valid because entries survive.

Message ciphertext, encrypted offer notes and offer history disappear in one
transaction. Failure rolls that thread back. Earlier threads may have committed;
a failed run reports an error rather than empty success, and reruns resume safely.
Lock waits are limited to2seconds and each SQL statement to10seconds. A batch
limits thread count, not entries per thread; an unexpectedly large thread times
out and requires operator review rather than partial deletion.

An existing operation ID stays reserved after content removal. The current
message contract returns409 for retries of purged payloads; it cannot verify
opaque-byte equality or recreate content. New participant activity may continue
in a non-retired thread using fresh operation IDs and subsequent sequences.

## Scope and approval

Rahul (D) approved this implementation mechanism. It adds no migration, scheduler,
public deletion endpoint, cross-domain table access, cloud resource or live run.
Persistent-target apply requires its own exact target/dry-run/operator approval.
This code does not remove browser-held copies or establish backup deletion.
CN-02 owns the independent30-day share path; CN-03 owns notification retention.
Affected owners review these shared lifecycle implications in the normal PR.

## Alternatives

Deleting threads would break uniqueness, retry and ordering guards. A cross-domain
cascade would violate ownership. A new deployed scheduler adds an unnecessary
runtime gate before the owner-local mechanism can be tested.

## Supersedes

None. Implements the approved [retention windows](private-data-retention.md).
