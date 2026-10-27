# One current offer with revision and withdrawal history

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 Conversations/Listings review.

## Question
How are structured offers revised/withdrawn, and how do they relate to selection and conversation origin?

## Options considered
- One logical buyer/conversation offer with immutable revisions and a current pointer.
- Multiple independently current offers or overwritten history, making the current amount/status ambiguous.

## Selected choice
- One logical offer per buyer and Sale Listing conversation; unique `(conversation_id, buyer_id)`. Revisions append history and atomically advance the current revision.
- Status is `submitted` or `withdrawn`. Only the offer's buyer may create/revise/withdraw it; resubmission after withdrawal appends a new submitted revision to the same logical offer.
- Preserve amount/note change and withdrawal revisions under the later approved retention policy. Withdrawal retains the prior amount in its new revision. Optional notes remain client-encrypted. Use expected-revision checks and operation keys for stale-update/retry handling.
- When approved retention removes history, preserve the minimal logical offer ID/pair and monotonically allocated next-revision counter; clear the current pointer under an explicit history-deleted marker. A later new revision reuses the same logical offer rather than creating a duplicate pair or resurrecting deleted content. Exact deferred cleanup constraints remain affected-owner review.
- Seller selection is a Listings-owned action, not an offer acceptance/payment/reservation state. Setting an eligible buyer from an existing Sale Listing conversation atomically marks the listing unavailable; authorized seller views include no-offer conversations and current submitted/withdrawn offers.
- Structured offers initially apply to Sale Listing conversations. Wanted Request response conversations support discussion/contact sharing; adding offers there requires explicit buyer-role and amount semantics first.
- Mohit's later lifecycle approval requires listing availability/window eligibility and both participants' eligibility for create/revise/resubmit. The eligible buyer may withdraw after listing unavailability; existing authorized discussion/contact sharing remains usable, subject to separate retention/retirement.
- An eligible seller may select an eligible buyer from an existing listing conversation even without an offer, while the listing is available/in-window. Listings atomically persists the buyer/conversation and marks the listing unavailable, preserving its time window. Clearing the selected buyer does not reopen the listing. Existing account/participant checks remain mandatory.

## Rationale
Keeps the current offer unambiguous while preserving negotiations and avoiding an implied platform-verified transaction.

## Implications
PD-08 adds cardinality/status/revision constraints after full schema review. DL-00/CN-02 must define exact API/concurrent-state/duplicate behavior consistent with these approved availability and selection rules. Listings owns the availability-gated offer command and calls Conversations to persist offer records; Conversations never calls Listings. Withdrawal does not authorize Conversations to write Listings state. Retention/retirement follows the approved lifecycle decisions; crypto compatibility and real participant/selection integration remain explicit gates.

## Seller availability action clarification — 2026-10-27

Rahul requested and verified a seller-only **Mark as done deal** button beside
the listing heading in the grouped Conversations view, to be implemented in CN-02
Step6. The action explicitly calls Listings' existing availability command to
set the listing unavailable, preserving its window and buyer selection. Existing
threads stay accessible and the listing follows the existing unavailable
discovery/My Listings rules. Selection and this explicit availability action
remain distinct actions. Mark as done deal is useful when a seller wants to take
the listing off the market without selecting a buyer. Selecting a buyer also
marks the listing unavailable through the separate atomic selection command.
Neither action verifies payment or handover; no new deal-status field is
implied. Listings-owner code review remains required for the concrete
UI/public-boundary integration.

### Seller selection also marks the listing unavailable — 2026-10-27

Rahul directed and verified this CN-02 Step5 behavior clarification. Setting an
eligible buyer from an existing listing conversation atomically stores the
buyer/conversation pair and changes seller availability to `unavailable` in
Listings, preserving its current time window. The operation retains its revision
and idempotency protections; on failure or conflict neither selection nor
availability changes. Clearing a selection does not reopen the listing.
Unavailable listings leave discovery and remain available in the owner's
management view; existing conversations remain accessible. Selection does not
mean an offer was accepted, an item reserved, payment/handover verified, or a
deal completed. Keep **Mark as done deal** as an independent way to mark the
listing unavailable without choosing a buyer.

## Availability-first offer retry clarification — 2026-10-27

Rahul approved checking current Listings availability before replaying a
submit/revise/resubmit operation. If the listing is unavailable or outside its
window, return a state conflict rather than presenting the earlier saved offer
as a successful current submission. The earlier offer stays readable as history;
ordinary unavailability still permits withdrawal. While the action remains
allowed, an identical operation returns its original revision and changed reuse
conflicts. Retention removes request metadata with revision history and never
allows a retry to restore deleted content. No additional replay-lookup interface
is needed for this rule.

## Approver
Mohit (C), explicit approval of the five-part offer-lifecycle proposal. The user later confirmed the PD-08 Conversations/Listings affected-owner gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). CN-02/LI-02 retain their implementation and concurrency checks.

## Supersedes
None.
