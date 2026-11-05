# Wanted-request retirement: approved local cleanup order

**Current disposition (2026-11-05 15:26:56 UTC): Aditya marks ORIGIN-RETIREMENT-BOUNDARY complete. Earlier pending/checkpoint statements below are historical; this status update records his direction and does not add new execution evidence.**

**Historical checkpoint:** Mohit approved this local mechanism/order after the
Step3 Wanted API checkpoint. ORIGIN-RETIREMENT-BOUNDARY is marked complete in the
work log. The procedure below documents implementation constraints; it does not
assert current live cleanup state or authorize a new cleanup run.

## Existing approved prerequisites

Follow [origin retirement](../decisions/origin-retirement.md),
[Search contract](../../contracts/search.md), and Conversations' reviewed public
activity/marker operations. Request unavailability must be continuous for 180 days;
every associated conversation must have no participant write for 90 days.
`closed_at` is the request anchor. Reopen clears it. Mere account expiry/logout
is not retirement eligibility. Existing threads remain participant-authorized. The marker blocks new writes;
separate retention rules control later conversation-content removal.

## Approved mechanism and exact order

1. An explicit internal, unscheduled operation processes one server-selected
   request ID. No browser retirement endpoint, cloud job, existing-data batch,
   cron activation, automatic startup cleanup, or physical origin deletion.
2. Lock the Search request and recheck live/unavailable status and 180-day anchor.
   Atomically persist a UUID operation ID plus one server-derived `now-90days`
   cutoff. Reuse an existing pair exactly after unknown outcomes. Commit before
   external calls. Pending requests cannot accept edits/reopen/new responses or
   public discovery; current owner management remains available.
3. Supply server-only `OriginOwnerContext` and `origin_kind="wanted_request"`
   to `get_origin_activity`. Treat this as preflight only. Call
   `mark_origin_retired` with the stored operation ID/cutoff for the authoritative
   all-or-none check under Conversations locks. No private Conversations table
   queries or shared database sessions. Bound each dependency call; an error or
   unknown outcome retains the pair and does no local content deletion.
4. `blocked_recent_activity` clears only the exact matching pending pair under
   the request lock. No content is removed. A later attempt uses a new pair.
   `marked`/`already_marked` permit the following single Search transaction.
5. Lock and recheck that same request, pending pair and eligibility. In that
   transaction first clear **both** request/result JSON payloads in all
   `search.wanted_command_results` rows for the request. Keep only their existing
   content-free author/scope/kind/operation/request identifiers so retries cannot
   create another request or resurrect content.
6. In the same transaction mark the request retired/unavailable, clear title,
   description, category code and budget, clear the pending pair, and advance
   revision/update time. Keep request/author IDs, original creation time and
   closure/retirement timestamps. The receipt-retirement guard prevents origin
   retirement while any receipt content remains. A failure rolls back **both**
   receipt scrubbing and origin scrubbing; the previously committed pending pair
   remains for retry against Conversations' stable result.
7. Never remove a request row, saved listing, thread, message, offer or storage
   object here. Do not modify other domains. Retired owner/public reads return
   safe 404, edits/reopen fail, and late retained-key retries conflict without
   returning content. Conversations owns subsequent conversation retention.

## Checks required before accepting this checkpoint

Use controlled times at exact 180/90-day boundaries and reset/reclose; zero/multiple
threads; recent activity; failed/unknown/delayed provider results; same-ID replay;
wrong pair; concurrent edits and competing retirement attempts; full rollback
when local cleanup fails; all receipt payloads cleared; retained keys reject late
create; no origin reopen/new response; every read hides retired content. Use only
reviewed Conversations doubles until its real provider is ready. The recorded real cross-domain and owner-review results are in the work log; this
procedure's synthetic cases are not a fresh runtime check.

## Approval boundary

Mohit approved implementing the above local transaction and coordination logic
with isolated tests. This does not authorize running
cleanup against retained/shared/live data, activate a scheduler, deploy, or perform
cloud actions. Task requires this decision explicitly: domain-task-list SE-02
Step3 says to obtain approval of the concrete destructive cleanup mechanism/order
before implementation. Public coordination approval alone did not approve it.

## Implemented local checkpoint and evidence

`wanted_retirement.py` owns the explicit one-origin coordinator, fixed2s public
call deadlines, validated preflight/marker results and unchanged pending replay.
`PostgresWantedStore.begin_retirement/clear_retirement/finalize_retirement` own
separate local transactions, exact pair fencing, eligibility recheck and atomic
receipt-first/origin-second scrubbing. Clock regression fails closed. None of
these methods is called by normal startup or exposed as an HTTP cleanup route.

Unit tests cover cutoff boundaries, incomplete responses, exceptions, deadlines,
external cancellation, unknown committed outcomes, clock regression and both
marked/already-marked results. Actual PostgreSQL tests cover the180day boundary,
reopen/reset, pair fences, lost/blocked/retried results, every receipt payload,
retired visibility/late keys, injected SQL failure rollback and competing
attempts while an owner edit is rejected. Public Conversations behavior is an
explicit reviewed test double, not real locking/integration proof.

The detailed check receipt was removed from the checkout; see the
[evaluation history guidance](../evaluation/README.md) to retrieve it from Git.
The listed race, owner, and integration checks describe the original checkpoint.
ORIGIN-RETIREMENT-BOUNDARY is marked complete in the work log; these old statements
do not reopen its task gates or assert current live state.
