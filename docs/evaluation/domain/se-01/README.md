# SE-01 functional verification ledger

This ledger covers the uncommitted `task/se-01-search` working tree based on
`defec38`. It is not acceptance of SE-CORE, DATA-READY, FR/NFR completion or a
merged revision. Detailed commands/results and human observations are in the
[work log](../../../status/work-log.md).

## Step 8 scope and authoritative behavior

The [reviewed Search contract](../../../../contracts/search.md) selects native
English all-term title/description matching and explicit recency/price sorts.
The task's “relevant/non-relevant ranking” checks therefore mean matching versus
non-matching cases plus those reviewed stable orders. No relevance-score sort
or different search semantics is introduced. Human-reviewed labels and
Success@5 remain Steps 9/11; fixture judgments do not substitute for them.

## Coverage and evidence limits

| Requirement/check | Test home | Evidence limit |
|---|---|---|
| Current regular/temporary eligibility, denied/expired/unavailable outcomes | `apps/api/tests/domains/listings/test_browse.py` | Scripted public Identity boundary; real ID-READY integration pending. |
| Title/description/all-term/English stemming, stop words, plain-text operator characters, non-matches and vector updates | `test_browse_postgres.py::exercise_native_text` | Prepared real PostgreSQL test; skipped without the disposable runner. No in-memory search acceptance. |
| Category/condition/negotiability, zero and inclusive price ranges, combined filters, active catalogue and large-price comparisons | `test_browse_postgres.py::exercise_filters_and_sorts`; request/refusal cases in `test_browse.py` | Native filtering and catalogue execution pending; isolated input/forwarding/parameterization tests pass separately. |
| Recency/price UUID ties, page continuation, sizes 20/50/100, no missing/duplicate eligible rows | `test_browse_postgres.py::exercise_browse` and filter matrix | Native execution pending. Fixture UUID namespaces are repeatable via the existing PD-09 helper; load/guard times remain explicitly relative to the test clock. |
| Unavailable/future/ended/retired/pending exclusion and same-ID transitions | `test_browse_postgres.py::exercise_visibility_transitions` and initial fixture checks | Native execution pending. Scripted HTTP freshness/cache-header tests do not prove SQL visibility. |
| Malformed/large query, exact integer money, reversed ranges, page/offset limits and no silent rounding | `test_browse.py`; `apps/web/tests/discovery-query.test.ts` | Isolated validation evidence; not rate-limit or NFR evidence. No new price quota/request-rate policy selected. |
| Actual HTTP response/request schemas match reviewed OpenAPI operation | `test_browse_contract.py` | Actual ASGI router serialization over typed scripted store pages; real data/auth/SQL remain pending. Resolves local response references and compares the complete declared error vocabulary. |
| Generated TypeScript query/response types and frontend reader match reviewed public properties | `apps/web/tests/discovery-contract.test.ts`, `discovery-api.test.ts` | Compiles against registered generated types, checks OpenAPI field sets and reader acceptance/refusal. No generated runtime SDK is assumed. |
| Fresh reads, explicit retry, cancellation, safe failure and no stale/private response fallback | `test_browse.py`; `discovery-api.test.ts` | Test-only scripts and client transport checks; normal startup never selects the UI harness. |
| Saved unavailable summary versus content-free retired marker | Search-owned `test_listings_double.py` | Contract fixtures only. Real save-target/saved-summary providers, Search save rows/API and privacy checks remain SE-02/integration work. |

Native tests use the registered
`uv run --locked python scripts/check_database.py --listings-store` command.
They run in its migrated Unix-socket PostgreSQL database with rollback-only
browse fixtures. Index eligibility diagnostics are not natural-plan choice or
latency/capacity evidence. PostgreSQL/Docker is absent on this checkout, so no
native assertion in this table is reported as passed.

## Gates still open

- Original Step 2 real schema/loading/count/FK/field checks; Steps 3–6 native
  query/filter/sort/index/transition checks and actual Identity/Listings parity.
- Final corpus, real image references and 20+ human-reviewed labels; offline
  usefulness and approved cloud measurement/review gates.
- Earlier broad Listings image-upload fixtures contain expired fixed caller
  contexts. Their 12 failures remain unresolved; no clock validation is weakened.
- Safari 16.6/macOS desktop/resizing and portrait checks are user-reported.
  Approximate default size was 1440×900; exact portrait/narrow-landscape
  dimensions and a landscape result were not supplied. User explicitly asked
  to advance to Step 8; unreported checks are not counted as verified. No physical
  phone/browser-keyboard evidence is inferred.
- The client refuses unsafe JavaScript JSON money/page numbers rather than
  rounding them. Full high-value transport compatibility needs integration
  review; this is not an approved monetary product cap.
- Independent affected-owner/peer review, full CI-equivalent checks and exact
  commit/push/merge approvals remain separate. The UI preview is not a real
  marketplace deployment or authentication result.

## Step 9 isolated evaluator preparation

[Label validation and preview arithmetic](../../../../scripts/evaluation/README.md)
are implemented with synthetic unit checks. They validate schema/provenance
bindings and preserve included failed/empty cases in the Success@5 denominator.
The CLI validates the untouched draft template or runs fixed arithmetic cases;
it cannot accept reviewed labels without a separately verified final binding.
Even perfect fixture scores carry NFR acceptance false. No final labels, actual
human review, actual retrieval usefulness or DATA-READY result are claimed.

## Hybrid amendment checkpoint 3 — lexical compiler preparation

Mohit confirms Suraj's amendment review. The owned compiler/explicit native-test
path now constructs bounded original/expanded queries using actual PostgreSQL
English normalization at execution time. Scripted-normalization unit tests prove
planning and binding only. The native rollback suite has new actual matching,
filter/pagination, description-edit and GIN-eligibility assertions; it is skipped
here because PostgreSQL/Docker is absent. Production store calls do not opt in.
See [compiler limits](../../../architecture/search-vocabulary.md). No activation,
semantic inference, real SQL pass or revised NFR result is claimed.

## Hybrid checkpoint 4 — feasibility and isolated Mac probe

[Environment/runtime/storage plan](../../../architecture/semantic-search-feasibility.md)
records verified macOS 13.7.8 and published wheel tags, sizes and model pin.
Python 3.14 ONNX ARM64 wheels require macOS 14; a project-local 3.13 helper is
proposed for review, without changing the root interpreter or installing it.
Native arrays and bounded inference/write/chunking probes are proposals only.
At that initial metadata-only checkpoint no model/import benchmark was claimed;
the subsequent approved Mac probe below records actual inference while Linux,
SQL storage and production capacity remain unverified.

The initial metadata-only checkpoint above was followed, after Mohit verified the
helper alternative, by a real [local inference result](semantic-probe/result.json),
[supervised bounds](semantic-probe/supervisor.json) and
[preflight metadata](semantic-probe/preflight.json). See the feasibility plan's
actual-result section for measurements and two retained tooling failures.
No actual SQL, production HTTP/capacity or NFR-04 acceptance is inferred.

## Hybrid checkpoint 4 — storage/write plan only

[Concrete storage and lifecycle proposal](../../../architecture/semantic-listing-storage.md)
now enumerates additive objects, constraints, fingerprint/lease fencing, one-snapshot
coverage, rollback and native acceptance cases. Human verification, affected-owner
review and explicit derived-content deletion approval remain pending. No migration,
DB write/backfill or cleanup code was executed; native/concurrency/performance
assertions are not claimed passed.

## Approved storage implementation preparation

Mohit approved all presented storage/deletion implementation gates. The new
`20261024153316` migration and inactive pipeline/types/store implement private
vector state, source invalidation, lease/generation fencing, publication and retry
without startup wiring. Unit/transport and pre-connect guard tests execute here;
two new native integrity/concurrency tests remain skipped with the existing
browse native suite. New `embedding-smoke.sql` and updated database inventory/
rollback checks are prepared, not executed. No actual SQL apply/cleanup, worker
run, single-snapshot hybrid read, Linux/production capacity or readiness/NFR
acceptance is claimed. Earlier source-bound data manifests are historical after
this new schema revision and need revalidation at the real-data gate.

## Native checkpoint C — actual SQL evidence

[Result and source fingerprints](native-postgres/result.json),
[adapter output](native-postgres/listings-tests.log),
[first apply](native-postgres/apply-first.log),
[reapply](native-postgres/apply-second.log) and
[successful stop](native-postgres/stop.log) record the final fresh native run.
It passed the 12-migration round trip and seven adapter-suite checks (four database cases/three guards), including
browse/vocabulary and embedding storage/races. This updates earlier “native
skipped” historical rows for those exact assertions; it does not assert the
entire proposed acceptance matrix or activate public hybrid search. Full-query
GIN-plan preference, publication deferral/retirement age and shared fixture order
were corrected as test issues, with failed runs retained. No production checks
were relaxed or failed samples hidden. Original real auth/provider/corpus/image/
labels/browser/full-CI/NFR gates and pipeline-switch/real-helper/read integration
remain pending.

## Native bootstrap/pipeline-switch follow-up

[Expanded result/source fingerprints](native-pipeline-switch/result.json),
[adapter output](native-pipeline-switch/listings-tests.log) and
[cluster stop](native-pipeline-switch/stop.log): eight adapter checks passed
(five native DB cases/three pre-connect guards), plus the schema round trip.
This adds the bounded registry/bootstrap/switch mutation matrix described in
the storage protocol. Serving-state metadata alone cannot guarantee post-edit
coverage; the future real public read must detect missing vectors in its own
statement and return the reviewed unavailable outcome. No API/helper/relevance
implementation is inferred from these coordinate-vector tests. Initial missing
fixture import was corrected; its failed native run is retained.

## Real helper IPC checkpoint

[Actual result](helper-ipc/result.json) and [source fingerprints](helper-ipc/source-fingerprints.json)
record18 real windows, two helper starts for the intentional crash/restart, no
overlapping helpers, full903-token/four-window long-description coverage, exact
repeatability and all helpers reaped. Three controlled matching cases ranked
intended fixtures first; neither judgments nor metrics are final human labels/NFR
acceptance. Local pipe round trips and sampled memory are not cloud HTTP evidence.

Protocol/lifecycle tests separately inject malformed/oversized/misbinding output,
timeout/queue/cancellation/close/crash and competing owners. The initial real
startup caught a client venv-path bug; preserving invocation path fixes imports
and has a dedicated regression. Shared code now compiles on helper3.13 despite
root Black's3.14 target. No DB writes/worker/public mode, real provider or final
corpus/evaluation gate is discharged by this increment.

## Private DB/helper bridge checkpoint

`embedding_worker.py` now connects committed, supported-pipeline jobs to the real
helper with overall20s budget, no inference transaction and fenced atomic
publication. Native tests cover bounded retry/defer/cancel/reclaim with fault
pipes. An explicit additional model case verifies long-text vectors persisted
exactly, actual helper crash/restart, source ABA/nontext edits and retirement.
[Scoped evidence](worker-bridge/result.json) retains model metrics, schema/log
checks, exact source fingerprints and earlier skipped/failed runs. No public
coverage/fusion or dispatcher is activated; final upstream/data/labels/deployment/
review/NFR gates remain. Earlier tables/sections describe their original staged
checkpoints and are not current whole-task acceptance claims.

## Development calibration checkpoint

The separately versioned8-listing/11-query synthetic set now has actual native
keyword/expansion/cosine measurements and90comparisons. The provisional35/65
blend/0.35/tiered/no-cap reference finds9/10intended positives versus3literal/
6expanded; one intended empty query stays empty. A long-description semantic miss
and unwanted matches remain explicit. These are fixture-author intents, never
final human labels or NFR acceptance. [Proposal](../../../architecture/hybrid-search-calibration.md)
and [source-bound evidence](calibration/result.json). No production setting or
public query path is changed; policy is unfrozen pending verification/follow-up.

## Known-vocabulary typo checkpoint

The prepared lexical compiler adds bounded unique spelling alternatives after
exact English-normalized matches. Actual native tests cover bicyle/bycicle,
multiword/AND preservation, table/tablet ambiguity, original chain versus added
chair collision, visibility, selective filters and pages/index eligibility.
[Policy](../../../architecture/search-typo-tolerance.md) and
[scoped evidence](typo-tolerance/result.json). No public activation or semantic
spelling guarantee follows. Mohit accepts the earlier vague telescope semantic
miss as a nonblocking limitation; no alternate encoding is being implemented.
The candidate scoring policy and other real integration/final evaluation gates
remain separate. Old calibration retains its original source-bound results.

## Private hybrid-read checkpoint

The selected v1 policy now has a Listings-owned one-statement reader with current
eligible-source coverage/503, keyword/typo/semantic union and stable ordering/pages.
Native math tests explicitly separate coordinate fixtures from inference. A
server-observed concurrent edit verifies old statement consistency, next-request
503 and publication recovery. The opted-in actual helper/worker/read path proves
controlled queries, missing coverage/filter recovery, closed-helper503 and
keyword independence. [Contract](../../../architecture/hybrid-listing-read.md),
[source-bound evidence](hybrid-read/result.json). Common HTTP503 is a controlled
response, not a website crash. Public contracts/activation/UI and final upstream/
data/labels/Linux/review/FR/NFR gates remain separate.

## Private keyword-relevance checkpoint

The private browse option now implements original-before-expanded/typo native
text rank with UUID ties, independently of semantic infrastructure. Native
checks include rank versus tier, proximity, unchanged membership/filters,
65-row pages and unavailable/failed semantic metadata.
[Contract](../../../architecture/keyword-listing-relevance.md),
[evidence](keyword-relevance/result.json). Shared compatibility/independent review
remain normal PR review, not a separate search-implementation permission gate.
Public mode/sort registration/UI and original real integration/evaluation gates
remain pending. No model inference is part of these keyword checks.


## Registered mode/relevance API checkpoint

Canonical query/generated declarations now agree with public validation/dispatch:
Keyword default with vocabulary/typo matching, both-mode relevance, blank browse
without semantic dependencies, blank relevance422 and absent Hybrid503. Scoped
HTTP errors retain private,no-store. [Source-bound checks](public-api/result.json)
record408 focused Python/42new mode tests,11native checks (3unselected model probes),
84web tests/build, types, boundaries, Black and generation. Scripted dispatch is
transport evidence only; native adapter/SQL checks use a private disposable DB.
UI controls, actual configured HTTP/model lifecycle/upstream integration and final
platform/data/review/FR/NFR checks remain pending; this is not readiness acceptance.


## Frontend mode/relevance checkpoint

Search now exposes Keyword(default)/Hybrid and both-mode Relevance with visible
help, explicit Hybrid503 recovery, mode-only draft preservation, URL/history
parsing and current-only request handling. [Source fingerprints/checks and exact
human browser cases](frontend-modes/result.json):102web tests plus types/lint/build,
68focused Python and5live loopback transport probes passed. Static rendering,
URL transitions and scripted request callbacks are automated evidence; actual
Safari draft/history/responsive/keyboard/error interactions await Mohit. The
running preview is explicitly synthetic: Hybrid/rank responses prove no model,
SQL or relevance quality. No real readiness/FR/NFR acceptance is claimed.


## Real native HTTP/model integration checkpoint

The frontend was human-verified as a UI-only preview. The existing integration
checkpoint now connects actual PostgreSQL vocabulary/typo/rank SQL and offline
semantic embeddings through the real collection HTTP service to the website.
Only identity and listing/image data remain synthetic. [Source-bound headless and
live-proxy evidence](native-http-model/result.json) records cycle/bicyle/vehicle
hits in both modes, wheeled vehicle/best-description keep food cold hits in Hybrid,
controlled503/keyword independence, explicit cleanup/resource checks,75Python/
105web checks and remaining gates. These3controlled listings are not final corpus,
human labels or NFR evidence. The live browser session is bounded/owned; human
real-backend browser verification and that session's final stop evidence remain
pending. Production lifecycle and all original real acceptance gates remain open.


Mohit subsequently verified the real browser preview (“It works”). The initial
Ctrl+C exposed cancellation during cleanup/report writing; it stopped API/DB and
left no helper process, but no helper-reap report. The corrected harness shields
owned async cleanup, preserves failures and passes a regression plus actual
Ctrl+C exit0/reap/report/DB-stop run. See native-http-model/ctrlc-result.json and
ctrlc-stop.log. Both private clusters are stopped and retained; no production or
final task acceptance is implied. Current focused Python total is76.


## Normal API default-off read-helper lifecycle

The normal composition root now optionally owns the real helper and a dedicated
max2autocommit read pool, with Keyword/commands retaining their transactional
pool. Invalid settings reject; expected semantic startup failure closes partial
resources and disables Hybrid, preserving Keyword. No registration/backfill/
activation/job dispatch/test caller is added to app startup. [Source-bound
lifecycle evidence](normal-api-lifecycle/result.json) records367focused tests,
actual app.main disabled/ready/unavailable13HTTP requests with real SQL/model,
separate pool modes, bounded resource observation and full owned cleanup. Only
the guarded probe overrides identity. Result awaits Mohit verification; workers,
controlled bootstrap, Linux/upstream/data/labels/CI/review/FR/NFR gates remain.


## Bounded existing-job dispatcher

The normal lifecycle result was verified; a separate default-off worker now
processes existing due jobs serially, sharing the helper with one dedicated
connection. No registry/bootstrap/backfill/serving transition. [Source-bound
worker evidence](worker-dispatch/result.json) records410focused/62narrow tests,
actual native edit/invalidation/pending Hybrid503/Keyword200/current publication/
Hybrid recovery, worker-pool failure independence and owned cleanup. The first
probe assertion used a wrong generation/chunk correlation; failed cleanup/report
are retained separately and the corrected fresh run passed. Eleven actual windows,
one simultaneous helper,366133248bytes sampled API/helper peak. Human result
verification and controlled bootstrap remain next; original upstream/platform/
data/labels/CI/review/FR/NFR gates remain incomplete.


## Explicit initial pipeline bootstrap/activation

The dispatcher result was verified. New explicit aggregate status/prepare/bounded
queue/activate operations and target-bound CLI are now checked outside startup.
[Source-bound bootstrap evidence](bootstrap/result.json):453focused/43operator
checks; first native run passes real CLI/SQL/worker/model, unavailable full-live
coverage, resume/refusal and concurrent activation/edit recovery. One helper,
11windows,345292800bytes sampled API/helper peak, all owned resources stopped.
Activation observes a complete snapshot; later edits can invalidate it and must
remain guarded until real worker recovery. No existing/shared target, fake
vectors, automatic backfill/activation or deployment. Human verification and all
original upstream/platform/data20+human labels/CI/review/FR/NFR gates remain.


## Step10 isolated load-runner preparation

Pinned repository-local k6v2.3.0 and [local-only runner/profiles](../../../../scripts/evaluation/k6/README.md)
are implemented. [Source-bound load evidence](load-runner/result.json) includes
four actual failure detections, raw/manifest/result for native30request pilot,
120evaluation/10Node checks, optional native skip and owned shutdown. Ten warm-up
and20measured expected responses at2rps; measured p95~38ms is tiny local fixture
preparation only. End-boundary extra iterations are counted without exceeding
HTTP caps; original diagnostic raw/report retained. Full-rate NFR profiles and
NFR01/02manifest templates are unapproved/not executable. Actual data/auth/labels/
platform/deployment/cost/telemetry/review/NFR gates remain; no readiness acceptance.
