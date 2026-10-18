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
- Seller selection is a separate Listings-owned action, not an offer acceptance/payment/reservation state, and does not automatically change availability. Authorized seller views include no-offer conversations and current submitted/withdrawn offers.
- Structured offers initially apply to Sale Listing conversations. Wanted Request response conversations support discussion/contact sharing; adding offers there requires explicit buyer-role and amount semantics first.
- Mohit's later lifecycle approval requires listing availability/window eligibility and both participants' eligibility for create/revise/resubmit. The eligible buyer may withdraw after listing unavailability; existing authorized discussion/contact sharing remains usable, subject to separate retention/retirement.
- An eligible seller may select an eligible buyer from an existing listing conversation even without an offer, while the listing is available/in-window. Withdrawal does not automatically clear selection; the seller explicitly clears/replaces it through Listings. Existing account/participant checks remain mandatory.

## Rationale
Keeps the current offer unambiguous while preserving negotiations and avoiding an implied platform-verified transaction.

## Implications
PD-08 adds cardinality/status/revision constraints after full schema review. DL-00/CN-02 must define exact API/concurrent-state/duplicate behavior consistent with these approved availability and selection rules. Withdrawal does not authorize Conversations to write Listings state. Retention/retirement follows the approved lifecycle decisions; crypto compatibility and real participant/selection integration remain explicit gates.

## Approver
Mohit (C), explicit approval of the five-part offer-lifecycle proposal. Conversations/Listings affected-owner review remains pending.

## Supersedes
None.
