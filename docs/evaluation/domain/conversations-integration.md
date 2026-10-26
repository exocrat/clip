# Conversations application integration checkpoint

Owner/writer: Rahul (D), `task/cn-01-conversations`. Scope verified by Rahul on
2026-10-26; Step1 inventory recorded at2026-10-26 14:51:33 UTC. This is a local
integration plan within CN-01 Steps4/6/8–10/13, not full CN-01 acceptance.

## Baseline and boundaries

Fetched `origin/main` is `3d6c2709d93f42bda0b4a6645c633780387c99b8` (Identity
PR14, including Search/Listings PR11). It is already an ancestor of this branch;
local `main` is stale and is not the comparison baseline. Implementation head
before this documentation increment: `1b77308`. No Conversations PR is open;
PR15 (`hybrid-nochoice`) is separate active Search work. Preserve the separate
`task/cn-01-two-person-demo` worktree; do not import its inspection-panel/demo
changes implicitly.

Use real Identity, Listings, Search and Conversations services in one app.
Local integration tests may control external signer/mail/storage ports under
the existing reviewed fixtures; no fixed caller override establishes real
session evidence. Never seed a thread or copy generated results instead of
exercising the owner HTTP workflow being tested. Existing fixtures can supply
synthetic inputs, accounts and external-provider responses with their limits
stated. Existing browser send/reload/offline/unread/read-ack checks stay verified.

## Inventory and exact gaps

| Surface | Current evidence | Work still needed |
| --- | --- | --- |
| Application | `app/application.py` mounts the domains, binds a real Conversations provider and owns bounded tuple/dictionary pools | Check startup failure/schema/configuration and complete lifecycle coverage; preserve normal/isolated profiles |
| Listing origin | Contract declares `POST /listings/{listing_id}/conversations`; provider implements thread creation | Listings route/service/client action are absent; `ListingDetailPage` still has a placeholder |
| Wanted origin | Search route/service uses the real Conversations provider; `test_real_search_response_uses_identity_and_closed_exact_pair_lookup` checks actual stores | Extend to signed-in HTTP create/respond/message flow and terminal-session/resource checks |
| Identity/chat | `test_conversation_identity_integration.py` covers real cookie/CSRF key registration and logout | Full actor-to-origin-to-thread/message workflow, nonmember denial, expiry/revocation and side effects |
| Web session | Public `ConversationRuntime` uses public Identity state and shared `sessionFetch` | Connect Listing action through a public feature export; preserve logout/session isolation and existing pages |
| Runtime | Existing config,21-file SQL chain, explicit Identity launcher and `/health` liveness contract | Document combined startup/configuration/build/migrations and verify available local pieces; no invented readiness or worker claims |

## Contract correction needed before Step2

`contracts/conversations.md` requires existing buyer/listing retries after ordinary
unavailability. `open_or_create_listing_conversation` can create and has no
availability argument. Calling it on an unavailable origin could create a new
thread; denying it unconditionally would block legitimate reopening. The current
public contract has no read-only Listing counterpart to
`find_existing_wanted_conversation`.

Propose the smallest correction: typed
`find_existing_listing_conversation(caller, request)` with request `{listing_id}`
and result `ConversationStartResult | None`. It reads only the authenticated
caller's exact buyer/listing pair, checks current account/owner eligibility, and
never inserts a thread. Listings owns the origin lock/state check and decides
whether to use lookup or creation; retirement/pending state remains fail closed.
Update canonical contract sources and regenerate mirrors in Step2 only after
human verification of this correction. No general policy change is proposed.

## Ordered implementation and checks

1. Inventory/reservation: this record, frontend map and current work-log row.
   Read-only Git/source checks plus documentation diff/link checks; no app change.
2. Listing connection: owner-side service/locking, missing HTTP adapter, typed
   Conversations port correction, and public Listing action in the existing slot.
   Check new/existing pair, unavailable/retired/pending state, eligibility,
   duplicates and close/create races on the actual database.
3. Signed-in combined flows: actual auth/CSRF and owner HTTP workflows for Sale
   Listings/Wanted Requests into private messaging, key binding, read state and
   terminal-session denial. Controlled external providers are explicitly labeled.
4. Runtime preparation: reuse shared settings/pools/migrations and existing
   Search workers. Check startup/shutdown/failure paths and document configuration.
   CN-02 offers/contacts and CN-03 delivery remain explicitly unavailable where
   unimplemented; no substitute worker, deployment or cloud action.
5. Regression: full `make check`, Conversations disposable DB checks, combined
   Identity tests, `scripts/check_database.py --listings-store` and existing
   isolated Listings demo lifecycle checks. Do not repeat the verified human chat
   walkthrough. Record available versus unverified provider/device behavior.
6. Handoff: compare against freshly fetched main, inspect line sources and safe
   exact duplication, update docs/PR, normal push and final-head hosted CI.
   Aditya is primary peer; Suraj reviews Listings and Mohit reviews Search impact.
   Exact merge revision still needs separate human approval.

At this baseline the diff adds18202/removes313 lines: application5864/35,
tests5662/8, database+archives2126/28, docs1506/38, contracts/tooling3044/204.
Review exact duplicates and unused material as implementation proceeds; do not
delete unique tests, archived migration provenance or useful evidence for size.

No live-provider/secret bootstrap, shared database migration, persistent cleanup,
cloud tests or deployment is authorized by this local plan. Those later gates
do not block preparing the integration PR described here.
