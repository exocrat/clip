# Conversations application integration checkpoint

Owner/writer: Rahul (D), `task/cn-01-conversations`. Scope verified by Rahul on
2026-10-26; Step1 inventory recorded at2026-10-26 14:51:33 UTC. This is a local
integration plan within CN-01 Steps4/6/8–10/13, not full CN-01 acceptance.

## Initial Step1 baseline and boundaries

### Subsequent participant-key readiness correction

Rahul authorized a real-project correction after the combined local website
showed a generic encryption error while the peer had never registered a key.
The temporary website harness stays under `/tmp`, uncommitted. Rahul is the
bounded writer for Conversations key service/tests, its UI/client/tests and
the Conversations/combined error-semantics documentation; no shared page edit,
schema change or new authentication mechanism is needed. Normal Aditya peer and
affected contract-owner review remain required before merge.

Ordered correction:1) distinguish participant first setup from bad/lost key
state in the actual member-key API;2) map only the explicit peer-setup reason to
clear waiting copy, disabled sending and bounded visible retry;3) verify the
transition and negative cases, record results and commit. Execute one verified
increment at a time. Until Step2, the browser still shows its old generic error.
The latest remote main has advanced to7612fd8; reconcile it and rerun exact-head
checks before continuing the earlier final PR/CI handoff, not during this fix by
silently changing the baseline.

Step1 result: member-key reads now distinguish409 `own_key/not_registered` from
`peer_key/not_registered` only after membership and account locks. Own-key and
member-key reads reuse the same current-bundle/history check. Retired, missing
after registration, incompatible, malformed and wrong-owner/version state never
maps to ordinary first setup. Seven new DB cases cover these failures and the
real HTTP own→peer→ready transition, including nonmember404/expired401. The
disposable runner passed114 tests; contracts8 current, focused mypy1, boundaries0
and pinned formatting passed. Eight real-session workflow regressions also
passed. No migration/generated-schema change was required. The initial
test attempted immutable-key updates; corrected it to model an invalid imported
new version without disabling any guard. Rahul verified Step1 before Step2.

Step2 result: the client recognises only the member-key endpoint's explicit409
`peer_key/not_registered` detail, discards server text and shows a waiting status
with sending disabled. The existing two-second visible-page poll checks readiness
without recreating keys/sessions or consuming prekeys while the peer remains
unregistered. Hidden pages pause; visibility/focus resumes checks. Once ready,
normal session setup runs again, retaining key-loss and key-change safeguards.
Other conflicts/dependency failures leave waiting and show the existing error;
they never become false first-setup states. Generation and in-flight guards
discard stale results and prevent overlapping setup, including StrictMode replay.

Five new client cases cover allowlisted/error-body parsing, waiting copy and
disabled send, visible→hidden→ready, unrelated conflict and StrictMode setup.
`npm run check` passed390 tests with3 existing skips, lint, app/test TypeScript
and production build (existing bundle-size warning). Boundary check0, generated
contracts8 current and Gitleaks source scan passed. Contract checking initially
used ambient Node and failed; rerunning with pinned Node24/npm11 passed. These
React tests use the existing labelled crypto/API lifecycle doubles, not new
real-browser or cryptographic evidence. Step2 awaits human verification; Step3
final transition/negative integration regression and main reconciliation remain.

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

## Step1 inventory and gaps (historical; results below)

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

## Step5 full regression result

All12 registered `make check` gates passed against implementation `380247a`:
Black289 files; Python1919 passed/93 skipped; data94 passed; boundaries0;
contracts8 current; consumer mypy2; web385 passed/3 skipped, lint113 files,
app/test types and build613 modules; wrapper safety35; full PostgreSQL18.6
migration lifecycle; Conversations107 actual SQL checks; Gitleaks8.30.1 snapshot.
The existing >500kB bundle advisory remains, not a build failure. Signed-in
Conversations/Identity workflows are included in the aggregate Python suite.

`scripts/check_database.py --listings-store` separately passed the full migration
lifecycle and21 actual Listings/Search store cases with3 explicit skips. Those
include native/model-specific opt-ins; neither these nor the93 general Python
skips are claimed as passed. The web skips are the opt-in native Wanted HTTP and
real-cookie HTTP fixtures, not the normal jsdom/SDK checks. The registered SQL
runners provide their own explicit database-backed evidence rather than treating
an absent runner DSN as a successful integration test.

The existing chat demo `--check-only` passed its actual disposable HTTP/SQL setup,
loopback/write guards and owned teardown. No browser/IndexedDB check was rerun.
The existing isolated Listings image UI harness was started on127.0.0.1:5174;
HTTP exercised built-page delivery, actual local image PUT/confirmation/download,
listing create/browse/save, owner unavailability/discovery removal and Wanted
creation. No prepared thread or generated output was copied in to bypass those
workflows. Stopped, resumed the same database, verified Listing/Wanted/Saved rows
were retained without reset, then stopped again. This remains fixed synthetic
Identity and temporary local image storage, not real session/S3/device evidence.

Retained local session: `/tmp/clip-listings-browser-sodlqzfg`; labelled container
`44d230e7ed9f` confirmed `Exited (0)`. Its test rows remain recoverable by the
registered resume command; image bytes intentionally vanish at shutdown. No
demo server remains running. No existing resources were deleted or stopped;
ephemeral test runners removed only their own containers. No cloud/live-provider,
shared database or persistent content cleanup occurred. No code correction was
needed. Step6 final diff/PR/review/CI handoff follows human verification.

## Step6 audit and review handoff

Fresh remote inspection on2026-10-26 19:28:38 UTC confirms main remains
`3d6c2709d93f42bda0b4a6645c633780387c99b8`, already an ancestor; no merge/rebase
is needed. The only other open PR is Search15; it was not imported. Before
handoff documentation, this branch changes123 paths (+19741/-328):

| Source of lines | Files | Added | Removed |
| --- | ---: | ---: | ---: |
| Application/UI | 41 | 6098 | 43 |
| Tests | 32 | 6462 | 8 |
| Database, smokes and archives | 13 | 2126 | 28 |
| Contracts/generated mirrors | 8 | 2273 | 209 |
| Documentation | 19 | 1960 | 35 |
| Tooling, CI and lockfile | 10 | 822 | 5 |

Audit covered the changed-path inventory, shared composition/consumer diff,
local-only SQL ownership/marker and message/key constraints, SDK/session/history
and recovery-off boundaries, generated-source/route checks, test/CI wiring,
migration provenance and privacy/configuration scope. Existing main migrations
are unchanged; only four later executable migrations are added. Exact added-file
hash comparison found one duplicated archived public-key migration, deliberately
retained as immutable branch provenance outside the executable directory. No
application/test exact-file duplicate was found; no useful test or unique evidence
was removed. The earlier redundant API README paragraph is the only cleanup.
Updated stale design/recovery implementation-status wording; no policy change.

Reviewer navigation: Aditya(A) reviews auth/CSRF/public transport, E2EE source/
dependency assurance and Conversations behavior; Suraj(B) reviews Listing origin
locking/start/reopen, public action and migration compatibility; Mohit(C) reviews
Wanted response provider binding and shared Search/schema regressions. Use
`docs/prompts/peer-review-prompt.md` against the exact final PR revision. Author
audit and passing tests are not independent human review or security approval.
Record the team's exact SDK/dependency conclusion before accepting the security
gate. Directory trust, best-effort IndexedDB and permanent history loss/no backup
remain intentional limitations, not findings waived by local tests.

Local full gates passed at code-identical380247a; later changes are evidence/
status documentation only. Publication/PR/current-head CI status is tracked in
the work log and live PR. No merge, production activation, shared migration or
cloud operation is authorized by this handoff. Exact-revision human peer/owner
approval and a separate merge instruction remain required.

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
