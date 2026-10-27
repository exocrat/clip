# CN-02 implementation checkpoint

Owner/writer: Rahul (D), `task/cn-02-offers-contact-sharing`.
Started 2026-10-27 06:16:43 UTC from accepted main
`b09978e91620ae3877a77c5bea8a4f12df7a8907` (PR17). Aditya reviews Identity,
security and Conversations; Suraj reviews Listings selection/availability;
Mohit reviews affected Wanted Request inbox behavior.

## Step1 contract audit

Rahul verified the twelve-step plan and the seller-only **Mark as done deal**
action before this step. This increment inspects existing sources and records
the implementation map; it changes no application, schema or generated output.
There is no unresolved offer-status or seller-selection product decision.

| Rule | Confirmed behavior and canonical source |
| --- | --- |
| Offer identity and lifecycle | One logical offer per buyer/Sale Listing thread; submitted and withdrawn revisions; resubmission reuses the offer ID. See [offer lifecycle](../../decisions/offer-lifecycle.md) and [Conversations contract](../../../contracts/conversations.md#offer-records-and-listing-owned-commands). |
| Amount and notes | Nonnegative integer paise, whole rupees including zero. Amount/status are structured; optional notes are encrypted. See [private payload decision](../../decisions/private-offer-and-contact-payloads.md) and canonical OfferRevisionRequest/OfferView in contracts/source/types.py. |
| Write boundary | Listings serializes availability/window/retirement and current participant eligibility, then calls Conversations to persist its owned offer. Withdrawal remains allowed after ordinary unavailability. See [Listings contract](../../../contracts/listings.md#selection-and-listing-based-offer-commands). |
| Concurrency and retry | Expected revision guards updates; identical operation retries return their original result, changed reuse conflicts. Content removal must not allow an old operation to recreate payload. Check ambiguous outcomes and availability changes in Step3. |
| Seller selection | Listings owns setting, clearing and replacing an eligible conversation buyer, including buyers without offers. Selection does not change availability. Selected buyer is owner-only data. |
| Seller overview | Group by owned origin, filter by partner/origin/offer; retain no-offer threads. Default last activity DESC/ID DESC; amount sort places missing offers last with the same ties. Grouping must respect bounded pagination rather than claim a page is the complete listing inventory. See [combined registry](../../../contracts/combined.md#conversations-http-operations). |
| Contact sharing | Confirm membership first, then Identity's trusted actor/conversation/confirmed-field scope. Return only selected, still-present own values to the client for encryption. Store field labels with values inside ciphertext. See [Identity sharing boundary](../../decisions/identity-contact-sharing-and-cleanup.md). |
| Retention | Offer notes/revisions share the 90-day inactivity policy. Each contact share has its own 30-day payload/label lifetime. Content-free references survive; the new 30-day cleanup mechanism still requires its concrete Step8 review. See [existing cleanup mechanism](../../decisions/conversation-content-cleanup.md). |
| Wanted Requests | Response threads support discussion and contact sharing. Structured offers remain Sale Listing only. |

## Existing implementation and gaps

| Surface | Accepted implementation | CN-02 work |
| --- | --- | --- |
| Schema | conversations.offers, offer_revisions and contact_shares already exist, with pair uniqueness, ordered entries and current-revision constraints. | Step2 must inventory/reuse these, not recreate tables or rewrite published migrations. Add only demonstrated missing storage/constraints through a forward migration. |
| Offer boundary | Listings service/routes implement guarded submit and withdrawal and construct ListingOfferCommand. | PostgresConversationServices.persist_listing_offer deliberately returns503; implement the real owned transaction and member-only offer read. |
| Selection | Listings owns the HTTP operation, revision/idempotency handling and participant check through the concrete Conversations provider. | Add the real public frontend composition; recheck integrated ownership, retries and failures. |
| Availability | Listings has owner-authorized PUT availability, plus its private feature client. | Expose a bounded public Listings feature action for done-deal UI; Conversations must not import listingsApi.ts privately. |
| Inbox | Conversations queries already support membership-scoped origin/partner/offer filters and amount ordering. | Add usable grouped views, real origin display through public boundaries and complete pagination behavior. |
| Contacts | Identity implements public options/selected-own-contact providers and trusted disclosure scopes. | Conversations prepare/share HTTP operations and encrypted client flow are still absent. Use the real Identity interface when bound; unbound/error state must fail safely. |
| Client crypto | OpenE2EE13.0.0 and IndexedDB text-message sessions are implemented. | Confirm typed offer/contact payload context and ciphertext-only envelope requirements against real SDK behavior before wiring private notes/shares. No plaintext fallback. |
| Frontend map | Actual ScaffoldPages uses ConversationInboxPage and ConversationDetailPage through ConversationRuntime. | Older implementation-table rows still mention placeholders. Reconcile those rows and reserve any shared composition before Step4 edits. |

## Done-deal action approved for Step6

Place **Mark as done deal** beside the listing heading in the seller's grouped
conversation view. Only the authenticated owner can invoke it. Use the existing
Listings availability command with `availability=unavailable`, fresh owned
revision and a stable operation ID. Preserve the current time window explicitly:
AvailabilityChange's null/omitted available_until clears the end date, so pass
the current value rather than accidentally changing it. Preserve buyer selection.
Refresh authoritative listing state after success; keep failures/stale revisions
visible and avoid reporting success before the command succeeds. Existing
conversations remain accessible; unavailable content remains in My Listings and
is excluded from discovery under the existing policy. No new deal-status column
or payment/handover verification is implied by this label.

## Ordered task and checks

| Step | Output | Check/gate |
| --- | --- | --- |
| 1 | This lifecycle/interface inventory and recorded done-deal direction. | Source/contract consistency and documentation checks; human result verification. |
| 2 | Reused offer storage and only necessary forward schema additions. | Uniqueness, current revision, references, retention and safe rollback. |
| 3 | Real offer writes/reads through Listings and Conversations. | Ownership, integer paise, revision/operation conflicts, atomic entry/activity updates and retirement marker. |
| 4 | Grouped seller/buyer/request views and filters. | Membership isolation, page completeness, ordering/no-offer cases and browser checkpoint. |
| 5 | Public Listings selection action in conversation UI. | Real eligible buyer relationship, stale state, retry and failure handling. |
| 6 | Separate done-deal availability action. | Owner-only, preserve window/selection, discovery exclusion, retained chats and browser checkpoint. |
| 7 | Selected-own-contact preparation and confirmation. | Real Identity scope, membership, exact fields and no unselected values. |
| 8 | Encrypted contact entries and independent 30-day cleanup. | Review concrete destructive mechanism first; retention/FK/order/privacy checks and browser checkpoint. |
| 9 | Combined offer/selection/contact regression coverage. | Actual database/SDK paths where implemented; synthetic contacts only. |
| 10 | Cross-domain failure and ambiguous outcome behavior. | No false selection/share success or duplicate side effects. |
| 11 | Real dependency and aggregate acceptance checks. | Actual CN-CORE/ID-READY/LI-CORE and request-origin integration; full local/CI gates. |
| 12 | Evidence, task closeout and reviewed PR. | Identity/Listings affected-owner and independent peer review; separate exact merge authorization. |

## Dependencies, ownership and current state

PRE-00 and DL-00 are accepted. PR17 is merged; its reviewed head3773931 passed
hosted [Foundation quality gates](https://github.com/exocrat/clip/actions/runs/40402518748).
This is implementation availability, not automatic CN-CORE or full CN-01/NFR
acceptance. The work log still records CN-CORE, ID-READY and LI-CORE acceptance
pending. The [stub guide](../../architecture/stubs-and-integration-gates.md)
permits CN-02 Steps1–10; use real available services and label any genuinely
missing dependency double. Step1 uses no doubles. Steps11–12 retain actual
participant/contact/selection and required milestone checks.

Rahul is the bounded writer for this checkpoint, CN-02's task text, the existing
offer decision's availability clarification and own task/merge work-log rows.
No shared page, generated contract or migration is reserved by Step1. The old
CN-01 branch retains its two unpublished documentation commits unchanged; this
branch starts directly from accepted main.

Step1 checks: documentation targets, `git diff --check` and Gitleaks8.30.1 passed; no application tests
are required for this documentation-only increment. Result awaits verification.
Next: Step2 storage inventory and any necessary forward migration plan.
