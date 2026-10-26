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

## Contract correction approved for Step2

`contracts/conversations.md` requires existing buyer/listing retries after ordinary
unavailability. `open_or_create_listing_conversation` can create and has no
availability argument. Calling it on an unavailable origin could create a new
thread; denying it unconditionally would block legitimate reopening. The current
public contract has no read-only Listing counterpart to
`find_existing_wanted_conversation`.

Rahul verified the smallest correction: typed
`find_existing_listing_conversation(caller, request)` with request `{listing_id}`
and result `ConversationStartResult | None`. It reads only the authenticated
caller's exact buyer/listing pair, checks current account/owner eligibility, and
never inserts a thread. Listings owns the origin lock/state check and decides
whether to use lookup or creation; retirement/pending state remains fail closed.
The canonical sources and generated mirrors now contain this lookup. No general
policy change was made.

## Step2 implementation result

Listings now owns a real HTTP/service start operation and a public
`StartListingConversationAction` in the existing page slot. It derives owner
and buyer on the server, validates the operation UUID, returns201/200 for new/
existing pairs, and performs a read-only lookup after ordinary unavailability.
Its new state guard uses `FOR NO KEY UPDATE`: seller state writes serialize, but
the separate Conversations insertion can perform its FK key-share. Calls are
bounded to2seconds, and retries resolve by exact pair after an unknown result.

The action uses existing cookie/CSRF transport, keeps its operation UUID through
failure/retry, validates the response before navigating, and aborts on account
boundary unmount. It exposes no browser actor/owner selector. Offers, selection
and contact sharing were not implemented in this increment.

Verification:107 disposable PostgreSQL18.6 checks passed (5 new Listing cases),
web385 passed/3 skipped including4 new page-action cases, app/test TypeScript,
Biome and build passed; focused backend mypy4 and contract declarations9 passed.
The complete contract plus existing Listings route/offer/retirement/image-service
regression selection passed118 tests. Contract freshness8, boundaries0, pinned
formatting and Gitleaks8.30.1 also passed.
Tests here use synthetic request authentication with actual owner services,
Identity eligibility SQL and database side effects. Real cookie-backed combined
workflows remain Step3. The new page action has automated interaction coverage;
its human walkthrough belongs to that combined checkpoint, not a repetition of
the earlier verified private-chat demo.

## Step3 signed-in integration result

The shared application now has8 Conversations real-session tests (7 new cases)
using the existing disposable PostgreSQL fixture and actual cookie/CSRF middleware.
The combined selection with the existing Identity application-composition suite
passed24 tests with warnings treated as errors. No application/configuration or
schema changes were needed in this step.

- Sale Listing: real upload intent/confirmation and publication, regular seller
  self-denial, temporary buyer thread creation, public-key registration, message/
  reply, owner availability change and existing-pair reopening; a new stranger
  cannot create on the unavailable origin or read the private thread.
- Wanted Request: regular and temporary authors create through Search HTTP;
  self-response and temporary response initiation are denied. A regular responder
  creates/retries the actual thread, registers account-bound public keys, submits/
  retries a message, and the author observes unread/read-watermark changes.
  Fetching entries does not acknowledge them. Invalid recipient key versions and
  browser sender spoofing refuse before entry creation. Nonmembers cannot read
  metadata/keys/entries/read state or send/acknowledge. Logout (including old-cookie
  replay), revocation and expiry deny subsequent reads and writes. Independent
  read-only SQL confirms one thread, two members and one entry after retries and
  denials; no fixture SQL created those records.

The controlled external ports are Microsoft signing/discovery, OTP mail and image
storage metadata. These are not live-provider or S3 evidence. Keys/envelopes in
these HTTP tests are explicitly shape-valid synthetic public/opaque bytes, not
an encryption substitute or new cryptographic evidence; the actual SDK/two-client
checks remain separately recorded. No fixed caller/provider success override was
installed for Identity, Listings, Search or Conversations. Existing browser checks
were not repeated. Full regression and existing isolated demos remain Step5;
normal review/merge and full CN-01 acceptance remain pending.

## Step4 runtime preparation result

Rahul is the bounded writer for runtime tests and the API/command/evidence
documentation in this checkpoint; no shared application/page/configuration
implementation changes were needed. `test_database_lifespan.py` adds10 cases
against the actual combined lifecycle with controlled pool I/O: shared URL versus
explicit Conversations DSN, normal exit, marketplace construction/wait failure,
body failure and marketplace-close failure. Both row-format pools preserve their
bounds; providers/stores use actual constructors, Search stays disabled by default,
and the Conversations pool closes even when marketplace teardown raises. A real
SQL-session test also confirms its actual Conversations pool closes on app exit
and the app clears the public provider reference.

Lifecycle/configuration/production-security selection passed78 tests; signed-in
composition selection passed24 (Step3 flows retained). Normal web typecheck/build
passed613 modules, with the existing >500kB chunk advisory. The final real-pool
shutdown assertion is checked in the8-test Conversations cookie suite. These are
local checks, not container/cloud/provider or schema/grant readiness evidence.

The API README now describes all four domains, existing pool/factory bindings,
same-logical-database requirement, full reviewed migration chain and separate
grant/Identity/TLS/proxy gates, lazy tuple-pool/liveness limits, normal bundle/image
composition and absent CN-02/CN-03 workers. The command registry records the local
checks. Removed one redundant overlapping API test paragraph; preserved unique test
coverage/evidence. No new worker, startup migration, schema probe, secret path,
grant or production-auth activation was introduced. Step5 full regressions and
isolated-demo lifecycle remain next, after human verification.

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
