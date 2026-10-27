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
| Seller selection | Listings owns setting, clearing and replacing an eligible conversation buyer, including buyers without offers. Setting a buyer now also atomically marks the listing unavailable; clearing does not reopen it. Selected buyer is owner-only data. |
| Seller overview | Group by owned origin, filter by partner/origin/offer; retain no-offer threads. Default last activity DESC/ID DESC; amount sort places missing offers last with the same ties. Grouping must respect bounded pagination rather than claim a page is the complete listing inventory. See [combined registry](../../../contracts/combined.md#conversations-http-operations). |
| Contact sharing | Confirm membership first, then Identity's trusted actor/conversation/confirmed-field scope. Return only selected, still-present own values to the client for encryption. Store field labels with values inside ciphertext. See [Identity sharing boundary](../../decisions/identity-contact-sharing-and-cleanup.md). |
| Retention | Offer notes/revisions share the 90-day inactivity policy. Each contact share has its own 30-day payload/label lifetime. Content-free references survive; the new 30-day cleanup mechanism still requires its concrete Step8 review. See [existing cleanup mechanism](../../decisions/conversation-content-cleanup.md). |
| Wanted Requests | Response threads support discussion and contact sharing. Structured offers remain Sale Listing only. |

## Existing implementation and gaps

| Surface | Accepted implementation | CN-02 work |
| --- | --- | --- |
| Schema | `conversations.offers`, `offer_revisions` and `contact_shares` already exist, with pair uniqueness, ordered entries and current-revision constraints. | Step2 reuses those structures. Step3 adds only original expected-revision metadata needed for exact retries, through a forward migration; all21 prior migrations remain byte-identical. |
| Offer boundary | Listings service/routes gate submit/revise/resubmit and withdrawal; Conversations now persists revisions and provides member-only current-offer reads. | Step3 checks role/eligibility, availability ordering, exact retry intent, revision races, encrypted-note references, retention expiry and safe failure behavior through the real adapters. |
| Selection | Listings owns the HTTP operation, revision/idempotency handling and participant check through the concrete Conversations provider. | Step5 atomically selects the buyer and marks the listing unavailable; dates are preserved and clearing does not reopen. Rahul verified the updated local browser flow; affected-owner review remains pending. |
| Availability | Listings has owner-authorized PUT availability; the public feature export now supplies the seller inbox action. | Step6 implementation and local automated checks pass; human browser verification and affected-owner review remain pending. |
| Inbox | Conversations queries support membership-scoped origin/partner/offer filters and stable amount ordering; the frontend now consumes those queries and groups only the returned page. | Origin and partner names are not in the current summary contract, so the inbox shows shortened IDs. A reviewed public display-context interface remains a separate B/C/Identity integration; no feature-private lookup is used. |
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
| 5 | Public Listings selection action in conversation UI. | Real eligible buyer relationship, stale state, retry and failure handling checked; updated local browser checkpoint verified by Rahul. |
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
are required for this documentation-only increment. Rahul verified this result.

## Step2 storage verification — 2026-10-27 06:31:24 UTC

Rahul verified Step1 and authorized Step2. The existing tables and final installed
local guards cover core offer identity/current-revision/history storage; no new
migration is justified by that inventory. Rahul is the bounded writer for the
Conversations storage test file, its existing disposable-checker file list and
the corresponding storage/command documentation. All published migrations and
the head20261026090300 remain unchanged. Tables, indexes, restrictive references,
deferred current-pointer checks and local guards are reused.

`test_conversation_offer_storage.py` adds18 real PostgreSQL cases covering:

- Zero-valued first offer, revise, withdraw and resubmit under one logical ID,
  with ordered revision/entry history and a continuing sequence counter.
- Negative/non-whole-rupee amounts and unknown status, with no partial entry,
  pointer or activity update surviving rollback.
- Seller-as-buyer, wrong revision sender and Wanted Request offer rejection;
  one logical offer per buyer/thread; immutable revisions and no skipped counter.
- Missing revision at deferred commit, first/repeated withdrawal and withdrawal
  amount mismatch.
- Optional opaque-note storage with correct member key ownership, and rejection
  when sender/recipient keys are reversed.
- Existing90-day cleanup removing notes/history while retaining the pair/ID,
  next revision and expired operation marker; deletion/replay rejected and a new
  revision reusing the retained logical offer successfully.

The fixture writes direct synthetic SQL on the existing harness-owned database.
It proves storage constraints, not HTTP authorization, real encryption or the
Listings serialized command integration. No trigger is disabled or bypassed.
The fixture supplies the required SDK identity for note-bearing entries; actual
SDK payload preparation remains Step3/client work.

The expanded registered checker passed132 tests with no skips on fresh
PostgreSQL18.6 and removed its own container. Pinned Black passed both changed
Python files; boundaries0, whitespace and Gitleaks8.30.1 source checks passed. The first sandboxed
formatter stalled and was interrupted; the elevated pinned rerun/check passed.
No new migration means no new rollback path or schema inventory to reconcile.

Exact normalized request replay, including the original expected revision,
remains a Step3 service/receipt-storage obligation; existing revision rows alone
do not prove exact request equality after all states. Plan any necessary receipt
storage together with those operations, preserving the approved retention rules.
Rahul verified Step2. Next: implement the real offer persistence/read
operations through the existing Listings and Conversations public boundaries.

## Step5 seller-selection implementation — 2026-10-27 (local browser verified)

The Conversation page now injects a narrow Listings selection capability through
the existing public feature export. The authorized Conversations summary gates
the control to the Sale Listing owner; Listings remains authoritative for current
owner, eligibility, exact buyer/thread membership, availability, revision and
idempotency. The panel displays current selection, uses the current listing
revision, retries an uncertain command with the same operation ID, and reloads
after a stale-revision conflict. It does not describe selection as accepting an
offer, reserving an item, or completing a deal.

Focused UI/API/composition tests passed19 cases; the full pinned web gate passed
lint,417 tests with3 existing skips, TypeScript checks and production build. The
disposable Listings PostgreSQL workflow passed21 tests with3 skips. The local
two-browser harness mounts the real Listings and Conversations routers/stores;
its selection-and-clear check passed with the real Conversations participant
check and synthetic fixed identities. Gitleaks8.30.1, Black and whitespace
checks passed. Full details and file responsibilities are recorded in the
Step5 work-log entry.

The user then clarified that selecting a buyer must also mark the listing
unavailable. The Listings store now stages the selection under the existing
origin guard, then marks it unavailable before committing the same transaction
and saved result. It increments the revision once, preserves a non-null date
window, and leaves availability unchanged when clearing selection. No migration
or trigger replacement is needed. UI confirmation reports both effects; a
reopened listing with a retained selected buyer shows its actual available
state and permits selecting that buyer again. The final focused suite passed20
tests; the PostgreSQL and browser API workflows cover the amended effect.
See the work log for checks and tool-version limits. Rahul confirmed the updated
local browser flow works at 2026-10-27 10:18:54 UTC against `e103562`. Browser
version/viewport details were not supplied. The preview was stopped and its
disposable database removed. The local check does not prove real Identity
sign-in or overall CN-CORE/ID-READY/LI-CORE acceptance. Step6 is next.

## Step6 done-deal implementation — 2026-10-27 (browser verification pending)

The seller's Sale Listing group heading now includes **Mark as done deal**.
Buyer and Wanted Request groups receive no action. A narrow injected port calls
the public Listings availability export with the current revision, both current
window values and a stable operation ID, then reloads owner-only state. Existing
selection is preserved by Listings. Uncertain outcomes retain the original
request for retry; revision conflicts refresh state before a new attempt.
Already unavailable listings show their status rather than another write.

The full web gate passed lint118,424 tests/3 existing skips, app/test types and
production build on available Node26/npm12 (required Node24/npm11 CI remains
pending). Five focused action cases and the real page-composition case cover
window preservation, retry/conflict, owner gating and refreshed state. The local
SQL/API harness verifies retained selection, exact availability replay, buyer
denial and accessible conversations. Black, boundaries and Gitleaks pass.
The harness explicitly reopens its own fixture through Listings after its
checks so the human receives an available, unselected listing. See the updated
browser walkthrough; interactive verification and affected-owner review remain.

## Step3 implementation scope (awaiting human verification)

Rahul verified Step2 and approved this retry clarification: submit/revise/resubmit
retries first obey Listings' current availability gate. Once unavailable, return
an unavailable conflict even if an earlier attempt saved; keep that offer's
history. Withdrawal remains allowed after ordinary unavailability. No additional
public replay-lookup operation is introduced.

Rahul is the bounded writer for Conversations offer implementation/router/provider,
its tests, the narrow Listings error/deadline and row-lock adapter, a forward offer-request
metadata migration and matching migration-head checks, plus the affected contract
and evidence text. Suraj reviews Listings changes and Aditya reviews Conversations
and Identity integration. Use revision-owned expected-request metadata rather
than retaining duplicate ciphertext or unbounded request/response copies.

The first real HTTP checks exposed an existing Listings `FOR UPDATE` lock
blocking Conversations' independent FK key-share check when the offer trigger
updates thread activity. The offer guard now uses `FOR NO KEY UPDATE`, matching
the existing thread-creation guard: seller changes remain serialized, without
blocking the structural FK. No trigger/FK protection was removed. The focused
Conversations runner passed156 PostgreSQL checks, including the ambiguous-timeout
cases. The full `make check` passed1930 Python tests/142 database-only skips,
94 data,403 web/3 skips; formatting, boundaries, contracts/types, web build,
wrapper safety, clean/repeated PostgreSQL migrations and full rollback/reapply,
and Gitleaks also passed. See the Step3 work-log entry for the full gate summary.
No shared target was migrated and no cloud action was performed. Rahul verified
Step3 on 2026-10-27. Rahul verified Step4's responsive browser checkpoint at
2026-10-27 07:43:40 UTC. Step5 seller selection is the next checkpoint. Details
and exact check results are in the work log.
