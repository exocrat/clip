# ID-01 Step14 — direct-API capability matrix

**Current checkpoint:** user stopped the provisioning window; cleanup complete
2026-10-28 20:31:28UTC.42consumer tests,6operator tests and7Terraform mocks
passed. Task8 wiring applied. New login/credential not created: CLI preflight
failure remains unresolved. Resume from the [window result](provisioning-window-result.json),
not from an assumed successful provisioning. Step14/FR-03 remain incomplete.

Recorded2026-10-28 16:09:06UTC; Aditya(A), source `c2d7b43`.
Owner/primary peer: Aditya(A)/Rahul(D); affected owners Suraj(B) Listings/images,
Mohit(C) Search/Wanted/Saved, Rahul(D) Conversations. Only Identity-owned tests and evidence are being changed; no application/shared-source
reservation is taken.

**Partial local execution; full Step14 acceptance remains pending.** Aditya
verified increments1–4 and the sale-owner follow-up. The keyword/resource/error follow-up is also verified; this increment audits
runtime configuration and prepares the real integration sequence (now verified);
the current increment tests the proposed separate Conversations principal;
execution receipts and limits are recorded below. No local fixture closes real
S3/Hybrid or hosted database integration gates.
[Editable matrix and source bindings](capability-matrix.json).

## Requirements and current evidence

Canonical ID-01.14 requires all real consumer paths, regular/temporary/expired/
revoked direct-API coverage, Wanted browse for both active classes, Wanted
response only for regular users, sale-listing denial, selected contact privacy
and safe cross-domain errors. No task-definition correction was required.
Source presence, previous test evidence and readiness acceptance are distinct.

- Inventory:15Listings/images +11Search/Wanted/Saved +16Conversations +5Identity
  own-profile/contact operations =47. The188base cells are expectations only,
  not a passing test count. Terminal and owner/member variants add cases.
- Remote main observed5e8d264; no open PR. This branch already contains that
  Conversations integration. Local main ref is stale; no fetch/merge was done.
- Existing combined real-session/SQL tests prove partial paths, including Wanted
  temporary-response denial and buyer offers. Directory/contact-share tests with
  synthetic request auth are supplemental, not real-cookie matrix evidence.
- Existing real-session listing/chat test controls image storage; some Search
  tests use upstream doubles. Do not count these as full real provider/consumer
  acceptance. Earlier real hosted identity/provider proof is kept separately.

## Expectations

`A` means allowed only with valid data, ownership/membership/visibility/state;
not an unconditional200. `D403` is active temporary class denial. `O` is own
upload only: an ordinary temporary actor has no upload-creation right; addressing
another actor's real intent must404. Do not fabricate temporary-owned uploads
or incorrectly expect blanket403 from confirmation/cancellation. `E` means an
allowed own-list read normally returns empty for a temporary actor. All listed
operations require real authentication: expired/revoked requests must401 with
valid request shapes before domain side effects. Hosted paths add `/api`.

| ID | Owner | Operation | Regular | Temporary | Existing evidence |
|---|---|---|---|---|---|
| M01 | listings | `GET /listings` | A | A | A6 |
| M02 | listings | `POST /listings/{listing_id}/conversations` | A | A | C1 |
| M03 | listings | `GET /catalogue` | A | A | A1, A2, A3 |
| M04 | listings | `POST /image-uploads` | A | D403 | A2, C1, A4 |
| M05 | listings | `POST /image-uploads/{upload_id}/confirm` | A | O | C1 |
| M06 | listings | `DELETE /image-uploads/{upload_id}` | A | O | No direct-session reference identified |
| M07 | listings | `GET /images/{image_id}/delivery` | A | A | No direct-session reference identified |
| M08 | listings | `POST /listings` | A | D403 | A2, C1 |
| M09 | listings | `GET /listings/{listing_id}` | A | A | No direct-session reference identified |
| M10 | listings | `GET /me/listings` | A | E | A1, A2, A3, A6 |
| M11 | listings | `PUT /listings/{listing_id}` | A | D403 | No direct-session reference identified |
| M12 | listings | `PUT /listings/{listing_id}/availability` | A | D403 | C1 |
| M13 | listings | `PUT /listings/{listing_id}/selection` | A | D403 | D2 |
| M14 | listings | `PUT /listings/{listing_id}/conversations/{conversation_id}/offer` | A | A | C1 |
| M15 | listings | `POST /listings/{listing_id}/conversations/{conversation_id}/offer-withdrawals` | A | A | C1 |
| M16 | search | `POST /wanted-requests/draft-matches` | A | A | No direct-session reference identified |
| M17 | search | `GET /wanted-requests` | A | A | A5, A6, C2 |
| M18 | search | `GET /me/wanted-requests` | A | A | A5, A6 |
| M19 | search | `POST /wanted-requests` | A | A | C2, A6 |
| M20 | search | `GET /wanted-requests/{request_id}` | A | A | No direct-session reference identified |
| M21 | search | `PATCH /wanted-requests/{request_id}` | A | A | No direct-session reference identified |
| M22 | search | `PUT /wanted-requests/{request_id}/availability` | A | A | No direct-session reference identified |
| M23 | search | `POST /wanted-requests/{request_id}/conversations` | A | D403 | C2 |
| M24 | search | `GET /me/saved-listings` | A | A | A5, A6, D4 |
| M25 | search | `PUT /me/saved-listings/{listing_id}` | A | A | A6, D4 |
| M26 | search | `DELETE /me/saved-listings/{listing_id}` | A | A | A6, D4 |
| M27 | conversations | `GET /conversations/{conversation_id}/contact-options` | A | A | C1, D1 |
| M28 | conversations | `POST /conversations/{conversation_id}/contact-preparations` | A | A | C1, D1 |
| M29 | conversations | `POST /conversations/{conversation_id}/messages` | A | A | C1, C2 |
| M30 | conversations | `POST /conversations/{conversation_id}/contact-shares` | A | A | D2 |
| M31 | conversations | `GET /conversations/{conversation_id}/entries` | A | A | C1, C2 |
| M32 | conversations | `GET /conversations/{conversation_id}/read-state` | A | A | C2 |
| M33 | conversations | `GET /me/conversation-key` | A | A | C3 |
| M34 | conversations | `PUT /conversations/{conversation_id}/read-state` | A | A | C2 |
| M35 | conversations | `GET /conversations` | A | A | C2, C3 |
| M36 | conversations | `GET /conversations/{conversation_id}` | A | A | C2 |
| M37 | conversations | `GET /conversations/{conversation_id}/offer` | A | A | C1 |
| M38 | conversations | `GET /conversations/{conversation_id}/keys` | A | A | C2 |
| M39 | conversations | `PUT /me/conversation-key` | A | A | C1, C3 |
| M40 | conversations | `GET /me/conversation-prekeys` | A | A | D3 |
| M41 | conversations | `POST /me/conversation-prekeys` | A | A | D3 |
| M42 | conversations | `POST /conversations/{conversation_id}/prekey-bundle` | A | A | D3 |
| M43 | identity | `GET /me` | A | A | A1, A2, E13 |
| M44 | identity | `PATCH /me/profile` | A | A | I1 |
| M45 | identity | `GET /me/contacts` | A | A | A1, I1, E13 |
| M46 | identity | `PUT /me/contacts/{contact_kind}` | A | A | A1, I1, E13 |
| M47 | identity | `DELETE /me/contacts/{contact_kind}` | A | A | C1, I1, E13 |

The JSON records per-operation conditions, specific missing cases and terminal
variants. `GET /me/listings` is permitted for temporary users; sale create/edit/
availability/selection remain denied. Temporary users can manage their Wanted
requests and participate in listing chats/offers, but cannot initiate Wanted
responses. Already copied encrypted shares and issued signed URLs retain their
reviewed independent lifetimes; source deletion/API denial does not erase copies.

## Evidence legend (source inspected; not rerun)

- **A1**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_real_cookie_enables_existing_listings_and_own_contact_routes`. Real regular cookie/catalogue/profile/contact flow; controlled signer/mail.
- **A2**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_temporary_cookie_does_not_authorize_seller_endpoints`. Real temporary cookie: catalogue/empty own-list read, create-upload/create-sale403.
- **A3**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_listing_routes_recheck_real_session_lifecycle`. Actual catalogue/own-list reads deny terminal regular sessions; not all Listings operations.
- **A4**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_untrusted_origin_and_csrf_cannot_mutate_listings`. Existing transport/CSRF rejection; not every mutation.
- **A5**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_real_session_reaches_accepted_search_routes`. Real regular/temporary Wanted/Saved empty-page reads only.
- **A6**: [test_application_composition.py](../../../../apps/api/tests/domains/identity/test_application_composition.py) `::test_marketplace_saved_and_wanted_reject_terminal_real_sessions`. Regular/temporary terminal reads and selected writes; not full endpoint matrix.
- **C1**: [test_conversation_identity_integration.py](../../../../apps/api/tests/test_conversation_identity_integration.py) `::test_signed_listing_publication_to_temporary_buyer_conversation`. Real cookie/SQL image-intent/listing/chat/offer/own-contact flow; image storage controlled; opaque synthetic envelopes do not prove encryption.
- **C2**: [test_conversation_identity_integration.py](../../../../apps/api/tests/test_conversation_identity_integration.py) `::test_signed_wanted_origin_to_messages_and_read_state`. Real Wanted regular/temporary author, regular response/temp response denial, member/nonmember and terminal message/read-state flows; opaque payloads.
- **C3**: [test_conversation_identity_integration.py](../../../../apps/api/tests/test_conversation_identity_integration.py) `::test_real_session_and_csrf_authorize_conversation_key_writes`. Real regular cookie/key registration/read/logout checks; not all cohorts/key operations.
- **I1**: [test_contacts_http.py](../../../../apps/api/tests/domains/identity/test_contacts_http.py) `::test_own_http_crud_security_and_no_session_disclosure`. Real Identity own-field HTTP checks; expand field/lifecycle/cross-domain combinations.
- **P1**: [test_capabilities_postgres.py](../../../../apps/api/tests/domains/identity/test_capabilities_postgres.py) `::test_regular_temporary_matrix_with_trusted_real_callers`. Policy-only real SQL with constructed trusted callers; not consumer HTTP evidence.
- **D1**: [test_conversation_contact_preparation.py](../../../../apps/api/tests/test_conversation_contact_preparation.py) `::test_real_own_contact_selection_no_writes_and_current_field_removal`. Real SQL/Identity contact boundary, synthetic request authentication; not real-cookie full matrix.
- **D2**: [test_conversation_contact_share_cleanup.py](../../../../apps/api/tests/test_conversation_contact_share_cleanup.py) `::test_offer_selection_and_contact_share_work_together_through_real_apis`. Real SQL/domain operations with synthetic request authentication; not full Identity-session proof.
- **D3**: [test_conversation_directory.py](../../../../apps/api/tests/test_conversation_directory.py) `::test_prekey_batches_atomic_retry_reservation_depletion_and_target_conflict`. Directory/prekey SQL/domain cases with synthetic callers; not full cookie matrix.
- **D4**: [test_saved_postgres.py](../../../../apps/api/tests/domains/search/test_saved_postgres.py). Real saved SQL/HTTP but explicit upstream Listing fixtures; not full real integration.
- **E13**: [closeout-review.json](../../../../docs/evaluation/identity/id-01-step-13/closeout-review.json). Human-accepted hosted Identity flows; not consumer-wide FR-03 matrix.

## Missing work and dependency gates

| Dependency | Actual evidence | What remains before acceptance |
|---|---|---|
| DL-00 / Identity contracts | Accepted baseline and implemented cookie/capability/contact services; Step13 human-accepted | No consumer substitute needed; formal ID-READY/source publication acceptance remains separately recorded. |
| LI-01 / LI-02 | Actual Listing/image routes/services and merged image-backed/chat integration; LI-02 isolated demo previously passed | Formal LI-CORE/current-owner integration acceptance remains pending; actual-storage positives and complete ownership/terminal cases remain. |
| SE-CORE / SE-02 | Actual browse, draft matches, Wanted and Saved routes/stores; real-cookie empty reads/Wanted-response flows | Formal SE-CORE and SE-02 integration acceptance pending; nonempty live-provider states and all mutations/lifecycle cases. Supported Hybrid needs real helper/model/serving coverage, not503. |
| CN-CORE / CN-01 / CN-02 | Merged main PR17/18 implementations, real provider composition, offer/contact/key routes and partial real-cookie/SQL tests | Formal CN-CORE/CN-02 integration acceptance pending; full message/contact/key/prekey cohorts/privacy cases and owner review. |
| Persistent runtime bindings | Step13 migrated23SQL and exact Identity/marketplace grants; Conversations grant denial was deliberately preserved | Current application falls back from database_dsn to marketplace database_url for Conversations, while that role has no Conversations USAGE. Need reviewed principal/DSN/grants before persistent paths can pass. Existing database_dsn seam can separate the pool; do not widen grants or provision a secret without owner/exact cloud approval. |

Task status rows are historical and do not prove the code is absent. Conversely,
merged code does not automatically accept the milestone. Reconcile owners'
current requirements/review/evidence next; no completion is inferred here.

## Ordered continuation and gates

1. **Current:** matrix/evidence inventory recorded; await human verification.
2. Reconcile actual readiness and owner evidence with this source/merged main;
   identify usable accepted paths and unresolved bindings/contracts. No milestone
   is auto-accepted; do not edit another feature privately.
3. Implement missing direct-API cases using actual Identity and consumer services
   on disposable PostgreSQL. Keep real external-service checks separate; no
   consumer auth override, missing-contract invention or Step14 stub exception.
4. Exercise every endpoint across account/session terminal and replay variants,
   owner/participant/selection/visibility/state cases, forged flags, valid CSRF/
   hostile origin, privacy/no-store/safe errors and denied-side-effect checks.
5. Complete specifically approved real storage/other runtime checks and owner-
   reviewed fixes. No cloud resource/start/secret/grant/provider action is
   authorized by this matrix. No cloud resource is needed for documentation.
6. Audit every row/scenario against executed evidence, record FR-03 outcome only
   after the full real matrix passes; then retain Step15 evidence/human/review/
   merge gates. Step13 completion does not close Step14 or all ID-01.

CN-03 notification delivery, final DATA-READY/NFR scale and the full crypto
acceptance campaign are not invented Step14 prerequisites. Existing owning
domain obligations stay distinct. No test implementation, test run, AWS action,
contract/source edit, commit or milestone change occurred in this increment.

## Increment2 — dependency and owner-evidence reconciliation

Recorded2026-10-28 16:24:14UTC. [Source/merge/review facts and concrete gaps](dependency-reconciliation.json).
Aditya verified increment1. All47per-row execution/acceptance states remain pending.

| Dependency | What is actually available | Remaining action |
|---|---|---|
| Identity/ID-READY | PR14/16 core cookie/CSRF/capability/contact paths merged; Step13 real hosted checks accepted | Formal ID-READY closeout and new operator/migration/HTTPS source publication remain separate. |
| LI-01/LI-02/LI-CORE | PR10 merged; actual image/S3 and Listings handlers; PR11 real query/save resolvers; PR18 offer/selection connection | Owner acceptance is now user-reported; bind promised exact revision/reviewer. Complete real-Identity/S3 positives and full owner/terminal matrix. |
| SE-CORE/SE-02 | PR11 real Listings public provider, Wanted/Saved implementation; PR15 Hybrid-default UI | SE-CORE accepted per user report, exact details pending. Nonempty real provider/mutation matrix and real Hybrid-serving inputs remain; no new DATA-READY/NFR gate. |
| CN-CORE/CN-01/CN-02 | PR17 concrete tuple-pool provider/routes; PR18 offers/contacts; combined real-cookie/SQL partial checks | CN-CORE accepted per user report, exact details pending. Persistent principal/DSN/grants and remaining member/key/contact/lifecycle matrix; no new CN-03 prerequisite. |

All seven relevant PRs10/11/14/15/16/17/18 are MERGED with their recorded
Foundation quality gates SUCCESS. This is historical per-PR evidence, not a
fresh current-branch CI run. PR14 has explicit human APPROVED review; PR17 has
an AI COMMENTED event; other queried PRs have no recorded GitHub review event.
Absence is not proof of no manual review: earlier human-reported review/merge
is preserved. AI comments are never counted as human approval.

Nine core handler/policy/provider/composition files were byte-compared with merged
main5e8d264 and match. Listings-to-Search's five concrete methods and final
Conversations provider composition exist. The sole application-domain delta
beyond merged main is the strict migration runner; Docker heap/config/HTTPS
operator tools/tests/docs also await publication. The47consumer paths do not
require writing new business controllers from scratch.

Aditya answered that LI-CORE, SE-CORE and CN-CORE were accepted by their owners
and will provide details. Record that positive report; do not continue describing
owner acceptance as unknown. Exact accepted revisions/reviewer details remain
unbound, and other owners' milestone/status rows were deliberately not edited.
The known merge SHAs are available implementation anchors, not invented owner
acceptance revisions. No owner was contacted by the agent.

### Concrete remaining gaps

1. **Persistent Conversations:** current source uses database_dsn else marketplace
   database_url; the preserved marketplace role lacks Conversations USAGE. Use
   the existing separate tuple-pool seam for an owner-reviewed principal/DSN/grant
   plan. No role, key, SSM mapping or privilege change is authorized here.
2. **Real image evidence:** controlled-storage cookie tests and the old synthetic-
   caller S3 demo cannot close actual Identity/S3 positive cells. Actual storage
   implementation exists; plan its required real checks separately.
3. **Hybrid positive cells:** explicit real helper/model/serving data is needed.
   Nonblank Hybrid503 is an unavailable-path outcome, not permission success.
4. **Full matrix:** all47operations still need executed/cohort/resource-condition
   evidence; complete existing partial cases rather than replacing real consumers
   with doubles. Ordinary prior auth fixtures do not prove real provider delivery.
5. **Formal revision closeout:** bind promised owner acceptance details and ID-READY
   readiness/publication; source availability and formal milestone acceptance stay
   distinct. No old work-log row is treated as proof of missing implementation.

Older handoffs' missing-provider, declaration-only Conversations,17-migration and
proposed-role/SES statements are historical and superseded by the linked actual
source and accepted Step13 receipts. They were not rewritten in other owners'
files or treated as fresh blockers. No new task-definition gap was found.

Static checks: all PR merge commits are ancestors of HEAD; nine-file main parity,
public provider method presence, source/evidence links and pending-only matrix
states checked. No tests, application/contracts changes, AWS/secret/provider
access, new stubs, owner messages, commit/push/merge or new milestone acceptance.
Next is verification of this reconciliation, then the proposed missing-case test
implementation increment with its real-integration/formal acceptance gates intact.

## Increment3 — local real-consumer execution

Aditya verified increment2 and authorized this increment. New
`apps/api/tests/domains/identity/test_consumer_capability_matrix.py` uses actual
mounted HTTP routes, real cookie/CSRF middleware, public domain providers and
network-isolated disposable PostgreSQL18.6. No consumer/caller overrides were
introduced. Ordinary SQL image metadata is fixture input, not actual storage
confirmation/delivery. Controlled signer, mail and clock retain their prior limits.

Final registered command: **15 passed in31.03s**. Every one of47operations rejects
eight terminal-session scenarios (376requests), with unchanged business-state
fingerprints. Regular/temporary cases additionally exercise nonempty reads,
Saved add/remove, Wanted editing/closure, own profile/contact CRUD, selected-only
contact preparation, deleted-contact rejection, Conversations keys/prekeys,
exact contact-share retry, read state and nonmember404. Every unsafe operation
rejects missing CSRF and hostile origin. Six regular-only operations reject a
real temporary cookie despite forged class/user headers. Request bodies are
validated against canonical models and mounted OpenAPI operation identities.

Development failures were test-harness errors: lazy included-router inventory,
a retained cookie jar during fresh login, and an incorrect contact-options
field name. Corrected assertions/fixtures; no production change was required.
Failure/final logs remain local under `/tmp/clip-id01-step14-matrix-*.log`.
Black, boundary check(0violations), Gitleaks8.30.1 source scan and whitespace
checks passed. Command and evidence limits are registered in
`docs/environment/commands.md`. No cloud access, commit or publication.

All rows have terminal execution evidence; active/resource-condition coverage
remains partial. Positive real S3/Hybrid, hosted Conversations principal/DSN/
grants, remaining ownership/replay scenarios and exact owner-accepted revision
bindings remain open. FR-03, Step14 and ID-01 remain incomplete. Increment3
awaits human result verification before increment4.

## Increment4 — ownership and replay checks

Aditya verified increment3 and authorized continuation. Five added cases in the
same Identity-owned matrix test file exercise actual offer revision and exact
retry, conflicting altered replay409, withdrawal/retry and other-buyer404 for
regular/temporary users. Actual Wanted response creation succeeds for regular
users and retries reuse the conversation (`created:false`); temporary users
receive403. Foreign Wanted edits/closure receive404. Foreign upload cancellation
receives404; seller replacement/availability/selection receive403 under the
existing owner guard. A forged owner/class body is rejected422. Rejected
requests leave business-state fingerprints unchanged.

Combined matrix command: **20 passed in35.79s**, including the previous376
terminal requests. Initial focused run:3passed/2failed due to test expectations
for Wanted's `created` flag and Listings403 owner semantics; corrected against
existing source/contracts, with no application changes. Final local log:
`/tmp/clip-id01-step14-increment4-final.log`. Black, boundaries0, Gitleaks8.30.1
and whitespace checks pass. Test hash and affected row annotations updated.
Increment4 awaits human result verification; no commit or cloud action.

This extends local ownership/replay evidence; it does not close all active
resource conditions. Owner-side sale lifecycle/positive matrix coverage, real
S3/Hybrid, hosted Conversations principal/DSN/grants and revision-bound owner
acceptance remain pending. No Step14/FR-03/full-task acceptance is claimed.

## Increment4 follow-up — positive sale-owner workflow

After Aditya verified increment4 and authorized continuation, added
`test_regular_owner_sale_commands_and_public_selection_privacy` to the same
Identity-owned test module. Actual regular-user commands cancel an unattached
upload, replace a listing, close/reopen it, select an existing conversation's
buyer and create a sale using confirmed SQL image metadata. Current revisions
are read through `/me/listings`; public command/detail responses intentionally
omit management fields. Owner public-detail reads omit owner, selection and
revision fields. This is SQL/service authorization evidence, not S3 evidence.

Focused check1passed; combined command **21passed in38.92s**. An initial test
incorrectly expected management fields in a public command response; corrected
the test to read the reviewed owner endpoint. Production unchanged. Final log
`/tmp/clip-id01-step14-sale-final.log`; Black, boundaries0, Gitleaks8.30.1 and
whitespace checks passed. Matrix hash/row evidence and current summary updated.
Await human verification. No cloud access, commit or publication. Remaining
resource/mode conditions, real image storage/Hybrid checks, hosted Conversations
principal/DSN/grants and accepted revision bindings retain their gates.

## Local follow-up — keyword, closed resources and safe errors

After the sale-owner result was verified, added two regular/temporary tests
(four cases) to the same matrix module. Actual indexed keyword search returns
nonempty filtered/sorted pages, empty out-of-range/price-filter pages; real draft
matching returns two public summaries without persisting state. Closed Wanted
requests remain visible to their author/management list, disappear from open
browse and return404 to another regular reader/responder without effects.
Malformed bodies at Listings/Wanted/Conversations/Identity return422/no-store,
never echo a synthetic private-input marker and never mutate business state.

Focused4passed; combined **25passed in44.79s**. Final local log:
`/tmp/clip-id01-step14-resources-final.log`. Black, boundaries0, whitespace and
Gitleaks8.30.1 passed;12recorded production/contract source hashes match. Updated
matrix cases/hashes and work-log checkpoint. No production change, cloud action
or commit. Await human verification. Real S3/Hybrid, remaining resource variants,
hosted Conversations database binding and revision acceptance gates persist;
full Step14/FR-03 acceptance remains pending. Next: inspect the exact existing
runtime configuration and prepare the gated integration plan, without applying
cloud/privilege changes.

## Runtime integration preparation — configuration audit

Local source/record inspection only; no AWS query, secret read, artifact download,
role/grant change or deployment. Previous resource/error result is human-verified.
No new task-definition gap: existing concrete providers support the intended
checks, but deployment configuration must catch up with merged application code.
Historical stopped-resource receipts are not a fresh live-state assertion.

### Source-backed findings

- `infra/terraform/shared/test/service.tf` already enables actual S3 for the
  Identity test profile, bucket `clip-test-listings-images-ap-south-1-id01`,
  prefix `id01`. Existing task policy permits object Put/Get/Delete only under
  that prefix. Reuse it; do not create another bucket or use isolated fake auth.
- The service injects only `CLIP_DATABASE_URL` from `/clip/test/listings-database-url`.
  `application.py` opens a separate tuple-row Conversations pool using
  `settings.database_dsn or settings.database_url`. The intended independent
  setting is therefore `CLIP_DATABASE_DSN`; its existing seam needs no controller
  redesign. Current recorded marketplace grants deliberately exclude
  Conversations. Do not broaden that role, use admin credentials in the app,
  or reuse the strict Identity login for another domain.
- No reviewed Conversations runtime-role SQL/credential mapping exists in
  `database/roles`; the domain Terraform directory is only a reservation.
  **Proposed** separate `clip_test_conversations_app` login and
  `/clip/test/conversations/database-url` SecureString are new resources/config,
  not existing facts or authorized changes. Exact per-table/trigger/function
  rights must be derived, locally tested and reviewed by Rahul before live use.
- Ordinary `apps/api/Dockerfile` is Keyword-only. Existing
  `apps/api/Dockerfile.hybrid` supplies real offline helper and worker, pinned
  Python3.13.12/wheels/model, no runtime download. `.tools/semantic` artifact
  contexts are absent in this clone; prepare only the documented exact contexts
  on approved AMD64 capacity. Existing build verification executes real inference.
- Hybrid needs explicit prepare/queue/status/activate through
  `scripts/search_pipeline.py`; enabling flags alone does not publish a serving
  pipeline. Use the pinned pipeline and exact target guards from
  `docs/architecture/listings-search-deployment.md`, with separately approved
  database writes. Existing 512MiB task settings are not verified combined sizing.
- One API process has max10marketplace +1Conversations +2Hybrid-read +1worker
  connections, plus separately inspected Identity connections. Review the total
  against actual DB capacity, not just the older13connection Search subtotal.

### Ordered implementation and execution gates

1. **Local preparation, no cloud:** derive a deny-by-default Conversations role
   proposal from actual provider SQL and triggers; prove real user flows on
   disposable SQL with separate principals, including forbidden cross-schema,
   DDL/TEMP and ownership tests. Prepare shared Terraform changes for the separate
   execution-role SSM reference/DSN binding and reviewed task sizing, plus the
   bounded actual-S3/Hybrid test procedure. Shared-file reservation and affected
   owner review precede changes. No wildcard or guessed grants.
2. **Review prerequisite:** Rahul reviews Conversations principal/permissions;
   Listings/Search owners review affected image/pipeline/runtime interfaces.
   Bind the owner acceptance details Aditya promised to actual revisions. This
   is review coordination for the human; the agent sends no teammate messages.
3. **Prepare exact cloud plan:** account335523638354, ap-south-1, existing
   shared/test. Reinspect stopped resources and drift before proposing mutations.
   Reuse protected private RDS, ECR/cluster/network/bucket; one private AMD64
   host only, sequential build/runtime, no duplicate NAT/DB. Propose
   c7i-flex.large for the combined Hybrid build/runtime (previous OOM fallback
   permission is context, not fresh plan approval). Exact task memory/CPU,
   instance duration, incremental cost/stop cap, IAM/SSM/SQL changes and
   cleanup plan must be concretely reviewed before start. Prefer no public
   proxy/DNS/browser window for direct-API checks; approve any needed loopback/
   private access separately, keeping public DB/API/SSH closed.
4. **Approved execution only:** apply the reviewed role/secret/DSN/config changes;
   build the current AMD64 Hybrid image and verify its digest, offline inference
   and runtime permissions; start one task. Prepare/backfill/activate only the
   approved synthetic sources and verify complete eligible vector coverage.
   Actual signer/provider/mail credentials stay in their approved path, never
   logs, CLI arguments or evidence. Obtain a regular and temporary real session
   using the approved human/test identity path; no fake caller or consumer.
5. **Real checks:** upload/confirm/display image bytes, rejected type/size/expiry,
   owner/foreign and terminal image access; nonblank actual Hybrid plus Keyword
   for both account classes; real persisted sale/Wanted Conversations, keys/
   offers/contact membership under the separate role; run remaining resource
   variants and complete the47operation capability evidence.503 does not pass
   a positive cell. No unnecessary email resend or load/NFR campaign.
6. **Cleanup and acceptance:** stop owned task/host, stop exclusive RDS, remove
   owned test image objects only under the reviewed exact prefix/key list;
   retain or remove new role/SSM/config only as explicitly agreed in the plan.
   Preserve shared resources and unrelated owners' data. Record exact image/
   plans/roles/checks, human verification and peer-reviewed publication. Keep
   Step14/FR-03 incomplete until all required real cells pass.

This is a reviewable preparation sequence, **not an executable cloud plan or
cloud approval request**. Next increment is local role/grant/test preparation
and shared configuration reservation; do not start AWS while those inputs,
exact plan/caps and separate authorization are missing. No tests rerun for this
source-only audit; previous25passing cases remain the latest local test result.

## Local Conversations principal proposal and verification

Aditya verified runtime preparation and authorized local role/testing work.
[`conversations-runtime.sql.proposed`](conversations-runtime.sql.proposed) is
review material, not a migration/default-startup script or live grant approval.
It names13Conversations tables with SELECT/INSERT and only seven with UPDATE,
plus schema USAGE and privacy logging defaults. No other-schema data grants,
DELETE, TRUNCATE, default future-table grants, DDL or memberships are added.
API-only scope is intentional: retention/cleanup permissions remain a separate
review, and not every recovery/retirement/concurrency path is covered here.

The matrix fixture now has an explicit opt-in role cohort. Only its owned
network-isolated PostgreSQL creates/replaces that login with ephemeral password
and revokes PUBLIC TEMP/public-schema CREATE in that disposable DB. Marketplace
and Identity retain their original real fixture paths; only the Conversations
tuple pool connects under the distinct login through the normal setting.
This does not prove live marketplace/Identity least-privilege configuration.

New `apps/api/tests/domains/identity/test_conversation_runtime_principal.py`
checks actual `current_user=session_user`, nonprivileged flags, no memberships
or object ownership and logging defaults. Direct Identity/Listings/Search
reads, schema CREATE, TEMP, TRUNCATE and DELETE fail. Existing actual cookie/
consumer flows then run under that principal: sale/Wanted threads, messages,
keys/prekeys/contact shares, offer revision/withdrawal/replay, own contacts and
nonmember/foreign-author denial, for regular and temporary users. Real fixture
FKs/triggers operate without giving cross-domain table reads to this login.

The first run failed safely503 because fixture URI reconstruction removed a
required slash; diagnostic isolated connection failure, not missing grants.
The initial inference that grants were insufficient was corrected. Fixture
role reuse was also corrected. No privilege widening fixed these failures.
Focused2passed; final combined **27passed in53.18s**. Black2files, boundaries0,
whitespace and Gitleaks8.30.1 passed. Final local log:
`/tmp/clip-id01-step14-role-final.log`. Command registry updated.

No production, shared Terraform, AWS/SSM/role or credential changes. No shared
configuration writer reservation was taken: inspect active remote work and
record the exact writer/scope before editing those files. Rahul's review of
this precise SQL proposal remains pending; human verification is not peer
approval. Next is the affected-owner review and scoped shared deployment
configuration/plan preparation. Real S3/Hybrid/hosted principal and remaining
resource acceptance stay pending; no Step14/FR-03 completion.

## Shared deployment configuration preparation — not applied

Aditya verified the distinct-principal result and authorized local configuration
preparation. Remote main rechecked5e8d264; open PR list empty. Aditya reserved
the four shared paths on `task/id-01-runtime-preparation` before editing; this
reservation is released after local checks. Other owners' source untouched.

- `consumer-runtime.tf`: default-off Conversations/Hybrid options; bounded
  API CPU/memory inputs (defaults256/512). A separate execution-role policy
  permits only `ssm:GetParameters` on the exact proposed Conversations DSN ARN.
  It does not create a login/SSM parameter or grant application-task secret reads.
- `service.tf`: task/container caps use those inputs; opt-in injects
  `CLIP_DATABASE_DSN`; real Identity environment receives explicit Hybrid flags.
  The definition depends on its injection permission. Both options require the
  real Identity profile; Hybrid refuses below512CPU/2048MiB. These are review
  guards, not measured sizing. No service count/networking/storage changes.
- `tests/consumer_runtime.tftest.hcl`: four mock plans test defaults, exact
  credential scope/binding, flags/capacity/no public proxy, and refusal of
  missing Identity or insufficient Hybrid capacity. Existing three HTTPS cases
  remain passing. Shared root README explains prerequisites and default behavior.

Pinned Terraform1.15.9 backend-free init/validate passed in a temporary copy;
**7mock plans passed**,0failed. First attempt stopped before init because system
Terraform1.16.5 was incompatible; reused the existing pinned binary and kept
version constraints unchanged. Final local mock log:
`/tmp/clip-id01-step14-terraform-final.log`; validation log:
`/tmp/clip-id01-step14-terraform-pinned.log`. Formatting, whitespace and
Gitleaks8.30.1 pass. Command registry describes the credential-free temporary
copy procedure. No Python tests rerun because only Terraform/docs changed;
previous27passing cases remain the latest Python result.

No live AWS query/plan/apply, SQL/SSM writes, credentials, build, resource start,
commit/push/merge or provider messages. Mock plans do not verify live permissions
or capacity. Rahul SQL review is still pending; shared configuration needs
affected-owner review. New role/parameter and real Hybrid build/pipeline/write
operations need the exact approved cloud plan, current identity/state/cost/caps
and cleanup review before execution. Human verification of this increment does
not replace those approvals. Next: resolve owner review/remaining local cases
and prepare the bounded real-runtime execution plan, keeping Step14 incomplete.

## Local resource-state extension — closure, retirement and key lifecycle

Aditya verified shared Terraform preparation and authorized remaining local
cases. Eight new regular/temporary cases in the Identity matrix module use
actual HTTP/services/SQL:

- Wanted self-response403; ordinary closure preserves the existing regular
  responder pair while a new responder gets404, with no duplicate writes.
- Actual Search/Conversations retirement scrubs an aged SQL fixture with zero
  threads. Subsequent reads return404; retired author writes return409 and
  foreign writes404; temporary response remains403. Nothing reopens, and
  management pages omit the scrubbed record. This does not prove threaded
  retirement or maintenance permissions under the proposed separate login.
- Closed sale preserves an existing chat, rejects new pair404 and self403,
  blocks an offer409, but permits withdrawal of the existing offer.
- Actual draft no-match returns an empty result without state changes; one-time
  prekeys deplete once, exact retries reuse reservations, rotated peer keys
  advance version and stale publish409 has no effects. Public bytes/envelopes
  remain fixtures, not SDK encryption evidence or concurrent-reservation proof.

Initial focused retirement assertions expected404 for all writes; corrected
against existing Search store/tests: retired authors receive409. No production
change. Focused groups:2pair cases passed, retirement corrected;4sale/key cases
passed. Final combined **35passed in61.32s**; Black2files, boundaries0, whitespace
and Gitleaks8.30.1 passed. Final local log:
`/tmp/clip-id01-step14-local-resource-closeout.log`. Terraform unchanged and not
rerun; its prior7mock passes remain latest. Matrix/hash/work-log updated.

Coverage audit keeps unexecuted variations explicit: threaded/pending retirement
and cross-origin/selection/revision/concurrency cases are not silently counted
as complete. Actual S3 image states/objects and nonblank real Hybrid remain
unexecuted. The proposed Conversations login is locally proven only for named
flows; hosted SQL/SSM/DSN, pipeline/build/size, reviewer/accepted-revision and
exact cloud plan gates remain. No AWS/secret/production change, commit or owner
message. Await human verification; next is the remaining narrow resource cases
or reviewed real-integration preparation, not an automatic cloud start.

## Binding/revision/concurrency checks and reported owner approval

The previously started combined run completed while the conversation was
interrupted: **42passed in71.54s**. Seven additional cases cover wrong selection
thread/candidate/self/stale revisions, correct clearing without reopening, Wanted
edit retry/stale/reopen, message exact retry/altered-operation conflict, and two
simultaneous real HTTP prekey requests. Concurrent requests use the actual
one-connection Conversations pool; this is not a multi-connection stress/NFR
claim. Two aged-thread fixture cases run pending/threaded retirement through
the distinct Conversations login: pending response404, marked participant writes
409, readable thread and two retained memberships. Initial threaded fixture
creation violated the deferred membership constraint; fixed by inserting thread
and members in one transaction, without disabling guards.

Final log `/tmp/clip-id01-step14-binding-final.log`; Black2files, boundaries0,
whitespace, Gitleaks8.30.1 and12production/contract hashes passed. No test rerun
after interruption because the completed process/receipt was recovered.

Aditya states **Rahul approved the exact SQL role proposal**, and instructed
recording and continuation. Approval is recorded as human-reported, bound to
`conversations-runtime.sql.proposed` SHA256 **6822fd82bc1d75c262d55227a385c8ca63a7aca155c8dc1b4df3c19dd73eee13**.
No direct review link was supplied. This resolves the proposed SQL-role owner
review gate; it is not cloud execution approval or blanket acceptance of every
shared configuration change. It changes permissions/binding, not table/schema
definitions. Nothing has been applied to a retained database.

### Current read-only AWS preflight and next execution sequence

Profile `adityalaxmi1` verified as account335523638354; regionap-south-1. Fresh
RDS metadata confirms `clip-shared-test-postgres` stopped/private/protected,
PostgreSQL18.6/db.t4g.micro. API desired/running/pending0 at revision7; ASG
`clip-shared-test-ecs-host` min0/max1/desired0 with no instances. Exact SSM
parameter metadata lookup for `/clip/test/conversations/database-url` returned
no record. No credentials, SQL or secret values were read; no resources changed.

1. **Prepare exact stopped/deployment plans:** retain shared/test service phase,
   existing root/state and immutable prior image until its replacement is built.
   Reconcile backend inputs/drift and preserve existing credential versions.
   Prepare separate reviewed start/stop plans for one private AMD64 host and
   the retained DB; no new NAT, DB, bucket or public endpoint. Do not claim a
   saved plan/checksum exists before actually generating and inspecting it.
2. **Role/credential provisioning window:** proposed maximum2hours, operator
   stop thresholdUSD3incremental (a stop condition, not a hard billing cap or
   price quote). Use one c7i-flex.large only, no concurrent build host; inspect
   actual host/task fit. Install an owned deadline fallback before work, stop
   new work by90minutes, abort startup after20minutes. Exact resource/SQL/SSM
   actions and current cost/remaining budget need approval before start.
   Validate live PUBLIC TEMP/schema CREATE baseline and absence of unexpected
   roles/clients first; never fix global PUBLIC ACLs implicitly. Create the
   separately approved nonprivileged login, apply only reviewed table/logging
   rights, generate/store its DSN privately as the exact SecureString, and prove
   its actual login/denials. Do not reset/migrate schema, alter existing login
   credentials or widen marketplace grants. Any role/SSM partial failure stops
   deployment and follows the separately reviewed rollback/retention plan.
3. **Runtime configuration/build:** reviewed exact execution-role parameter
   injection and task definition remain stopped until approval. Prepare pinned
   AMD64 Hybrid artifact contexts/image; review digest/build checks before its
   deployment plan. Pipeline prepare/queue/activate and associated grants need
   their own exact target/write approval. Existing Marketplace embedding rights
   must be inspected, not inferred from this Conversations proposal.
4. **Real test window/cleanup:** actual S3/Hybrid/hosted Conversations and
   remaining matrix resource conditions; obtain real sessions via the approved
   identity path. Prefer private/loopback direct API; no DNS/proxy unless
   separately approved. Stop task/host/exclusive DB on completion/failure/deadline;
   remove only approved test objects and retain/remove new role/SSM according
   to the exact plan. No rollback to a mismatched image or unrelated cleanup.

This sequence does not substitute for an exact saved Terraform/SQL/SSM execution
plan or authorize startup. Immediate next action is preparing that reviewable
plan and necessary operator artifacts. Step14/FR-03 and publication remain open.

## Role-only operator artifact and exact stopped-configuration plan

Aditya verified42-case/preflight/approval recording and authorized preparation.
New `scripts/identity_conversations_role.py` is an explicit operator helper,
not API startup and not an AWS/SSM client. It requires the exact Rahul-approved
SQL hash, absent role, fixed live host/database/admin and verify-full TLS (or
explicit owned local socket mode),23migration/head match, private logging and
a safe PUBLIC baseline. It creates only the new nonprivileged login with a
2connection limit, CONNECT and reviewed rights in one transaction, then checks
effective project-table privileges before commit. It never repairs ACLs, resets
schema, rotates existing roles, retries an unknown commit or writes SSM.
Credential URI construction retains reviewed CA/verify-full options, masks the
result and rejects user/host/options overrides. Caller owns approved credential
transport/storage and ambiguous-result recovery.

`tests/test_identity_conversations_role.py`: **5passed in2.32s** on owned
PostgreSQL18.6. Covers scoped creation/existing-role refusal, PUBLIC drift without
repair, hash/live-target rejection, masked TLS URI/override rejection and failed
postcondition rolling back the role/grants. Black2, boundaries0, whitespace and
Gitleaks8.30.1 pass. The earlier42consumer cases were not needlessly rerun.

[Exact saved-plan review](stopped-config-plan-review.json) records
SHA256 **1ae7c9262dc192166fbf938eda4ba9f0549be1e1afd60e9a4b706dabfd6c5636**
for `/tmp/clip-step14-stopped-plan-syetoapp/stopped.tfplan`, source hashes and
backend serial24, account335523638354/ap-south-1/profileadityalaxmi1.
Pinned Terraform1.15.9 produced a real **non-applying** plan against the exact
shared/test backend. Existing master/probe SecureStrings were read only into
process memory for their unchanged ephemeral/write-only inputs; versions matched
state, no values printed or stored in ordinary vars files. Private preserved
non-secret/recipient inputs and raw plan/log remain under a0700 temporary
directory, outside Git. Plan approval does not carry to changed source/state.

Exactly three resource actions (2add/1change/1destroy, counting replacement):

1. Create `aws_iam_role_policy.api_conversations_secret[0]` on the existing API
   execution role: only `ssm:GetParameters` for the exact proposed DSN parameter.
2. Replace `aws_ecs_task_definition.api[0]`: retain current immutable image,
  256CPU/512MiB, real auth/S3 and safe command; add separate DSN injection and
   explicit disabled Hybrid flags. Old definition deregistration is expected.
3. Update `aws_ecs_service.api[0]` to the new definition with desired count0.

Refresh-only drift was audited: ASG saved desired1→live0; RDS available→stopped
and advancing backup timestamp; task tag null/empty representation; prior proxy
ingress removed (current ingress empty). No ASG/RDS/SG mutation in plan.
Initial input reconstruction safely stopped on stale ASG state and inherited
tag location, then used fresh live facts/provider `tags_all`; no apply occurred.

### Exact apply boundary

Request approval only for this saved stopped-configuration plan. It starts no
paid compute/database/proxy, creates no role or SSM parameter, sends no email,
changes no existing credential, DNS, image, network or data. Existing retained
resource charges continue; this is not approval for the proposedUSD3 runtime
window. Recheck source hashes, backend serial/lock, account and credential
versions before apply; changed plan/state/inputs require new review. Apply is
bounded to10minutes; no automatic retry on ambiguity. Verify service0/host0/DB
stopped and exact new definition/permission afterward. Rollback is a separately
reviewed fresh stopped plan, not an assumed reusable deregistered revision.
Role/SSM provisioning and subsequent build/start/pipeline/test/cleanup still
need their own concrete approval. No infrastructure was applied in this increment.

## Approved stopped configuration applied

Aditya explicitly approved saved plan1ae7c926…5636. Exact source/plan hashes,
account/user, backend24 and existing credential versions matched before apply.
Apply succeeded; backend is now25. [Live result](stopped-config-result.json):
service revision8, desired/running/pending0; ASG0/empty/max1; RDS stopped, private
and protected. Actual definition preserves image/256CPU/512MiB, real auth/S3 and
safe command; binds the proposed Conversations DSN and disables Hybrid. The
execution-role policy matches exactly the one parameter/action. Parameter metadata
confirms the new SecureString remains absent; no SQL role/credential/startup,
email, DNS, schema or data action occurred. No tests rerun for this exact apply;
verification is the actual registered resources, not another mock run.
Cloud/secret inventory and work-log updated; no commit/publication. Await human
result verification. Next is the separately approved role/SSM provisioning
window and subsequent Hybrid/build/runtime/matrix work; Step14 remains open.

## Exact role/credential provisioning window — approval pending

Aditya verified the stopped apply; it remains the current baseline.
[Provisioning action plan](provisioning-window-plan.json), SHA256 **9f48802d7e77e39dbc355ccfcf61bb87eab1beafb6569e62c61a63d775ea6848**,
binds the actual retained LT3/t3.micro/AMI/subnet/SG/instance profile, protected
RDS resource ID and task8/API0, plus exact reviewed SQL/helper/CA source hashes.
This is an explicit AWS/SQL/SSM action plan, not a Terraform apply. No resource
has started while preparing it.

Proposed45minutes, stop new work by30minutes, startup abort20minutes, USD1
incremental operator threshold (not an AWS billing cap). One private t3.micro
only as an SSM tunnel; no build/app/proxy. Its new owned instance must use
Standard credits because the account default is Unlimited. Install exact owned
ASG deadline action first; automatic fallback covers EC2, while the operator
owns stopping exclusive RDS when AWS allows, including after a startup timeout.
AWS Price List exact Mumbai SKUs quote0.0112USD/h Linux t3.micro and0.021USD/h
running PostgreSQL db.t4g.micro:45min list-rate compute estimate0.02415USD,
excluding prorated root EBS, retained NAT/storage/backups/logs/data/taxes. Billing/
project forecast not queried. No new NAT, DB, public listener or IAM permission.

The window creates only reviewed `clip_test_conversations_app` (limit2), applies
the approved rights/logging, proves actual login/denials, and writes one new
Standard SecureString `/clip/test/conversations/database-url` under aws/ssm.
It reads only the fixed master credential and the new value for comparison,
all in memory; no existing credential/parameter rotation. Successful role/
parameter are retained for future runtime; compute/tunnel/fallback are cleaned.
Unexpected PUBLIC ACLs/roles/clients or ambiguous commit/storage stop work;
no automatic ACL repair, overwrite, deletion or retry. Application stays0.

Preparation caught a helper mismatch: the existing image installs reviewed RDS
roots in OS trust and uses `sslrootcert=system`. Updated the URI guard to accept
that existing setting alongside explicit absolute CA paths, retaining verify-full
and fixed target checks. Added one regression case; **6operator tests passed
in2.11s**, Black2/boundaries0 passed. No42consumer rerun or Terraform change.
Local loopback5432 availability and installed SSM plugin were checked. Only
preflight/pricing reads occurred; exact start/role/parameter/cleanup execution
awaits separate approval of this action-plan hash. Step14 remains incomplete.

## User-requested stop and checkpoint

Aditya requested shutdown and commit before token exhaustion. Closed owned SSM
tunnel; host i-036a77b684c9ba694 terminated, root vol-083ee1bd19529468f deleted,
ASG0/empty/max1, owned deadline removed, API desired/running/pending0 and RDS
confirmed stopped. New parameter absent. [Result](provisioning-window-result.json).
Window started20:11UTC. No master credential read, SQL role creation or parameter
write was reached. Preflight launcher/interpreter and SDK dependency issues were
isolated; the CLI-based preflight still failed, with its precise cause unresolved.
Do not infer a database/permission defect or retry role/secret writes blindly.
No schema/data/provider/image change. Shared retained NAT/storage still incur
costs. Next session: inspect safe CLI preflight diagnostics offline/read-only,
then review a fresh bounded window before restarting resources. Real S3/Hybrid/
hosted principal and remaining matrix/acceptance gates remain open.
