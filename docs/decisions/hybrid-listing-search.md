# DEC-13 — Hybrid listing search amendment

**Date:** 2026-10-24
**Origin:** SE-01, human-requested amendment after the isolated Step 9 checkpoint.
**Status:** Mohit verified the six-step design and staged vocabulary/native
normalization, local model/storage, native pipeline, helper IPC and DB/helper
bridge checkpoints. Development calibration is performed; its proposed reference
policy was subsequently selected as v1 for the verified private-read plan; its
implementation/check result awaits verification. Public activation is separate.
Suraj's amendment review is
user-reported, without a separate artifact; exact implementation review, public
integration, Linux/resources and original acceptance gates remain pending.

## User-interface amendment — 2026-10-26

Mohit requested Hybrid as the default and removal of the visible mode choice,
including the Keyword recovery button, to simplify search. Keyword implementation,
explicit legacy URLs and public API mode support remain available in code. The
API's declared Keyword default is unchanged: Search UI explicitly sends Hybrid.
Clean/reset UI URLs use Hybrid; explicit Keyword URLs round-trip without silently
changing mode. Newest-first remains the default sort. Semantic outages show a
plain search-unavailable message and Retry, without silently switching modes.
This supersedes earlier UI mode-toggle/default guidance only; real-provider,
model availability, review and NFR acceptance gates remain in force.

## Question

How should search combine common curated item concepts with description-based
semantic matching across cycles, books, furniture, electronics and other item
types? “Vehicle” finding a bicycle is an example, not the scope boundary.

## Options considered

- Existing indexed English full-text matching: reproducible and already
  implemented locally, but word normalization does not infer conceptual relations.
- Curated query expansion alone: predictable common synonyms and broader terms,
  but limited to maintained vocabulary.
- Hybrid retrieval: retain indexed full-text search, add curated expansion and
  local text embeddings, with explicit relevance ordering and evaluation gates.

## Selected choice

Prepare hybrid retrieval as a gated amendment within SE-01. Preserve PostgreSQL
as authoritative and preserve the required indexed full-text baseline. No
separate search service, paid embedding API, image-aware search or cloud change
is selected. Nothing in this amendment declares the semantic runtime feasible
or deployed. Do not change the submitted PRD.

### Matching and vocabulary

Use title and description as the only embedding inputs. Curated concepts are a
versioned internal search vocabulary, not seller-required tags, another category
catalogue, or human relevance judgments. Existing item-category filters retain
their existing meanings and catalogue source.

Start with reviewed common concepts across item types: cycle/bicycle, book/
textbook, chair, table, phone and laptop. These are proposed starter concepts,
not a closed list. The [versioned vocabulary and proposed rules](../architecture/search-vocabulary.md)
now record the human-verified checkpoint 2 output. Model aliases separately from directional broader/narrower
relations: searching vehicle may expand to bicycle, motorcycle and car; searching
bicycle must not thereby expand to every vehicle. Ambiguous “bike” needs an
explicit vocabulary decision. A textbook relation also needs review rather than
assuming every book is a textbook.

Compile original terms and permitted alternatives into parameterized PostgreSQL
query expressions. Retain AND between independent query concepts, OR within
reviewed alternatives, and plain-text handling of user input. Version and bound
expansion; the exact limits and initial vocabulary are amendment Step 2 outputs.
Unknown terms still use ordinary lexical matching and, in hybrid mode, semantic
retrieval. Do not derive expected test judgments from this vocabulary.

### Retrieval, scoring and public behavior

Propose an optional `search_mode` with `keyword` (default) and `hybrid`, plus an
explicit `relevance` sort. These are proposed wire changes only: existing generated
models/OpenAPI and endpoints remain unchanged until verified contract registration/
generation and compatible validation/dispatch are prepared together. Shared
compatibility and independent review follow the normal PR process. `keyword` includes approved curated
expansion once implemented; it always retains native indexed full-text retrieval.
Empty `q` is ordinary browse; ignore the matching mode and reject `relevance`
without nonblank text. Existing default recency and explicit price orders retain
their meanings over the selected matching set.

Hybrid retrieval unions lexical/expanded and semantic candidates, deduplicates
IDs and uses stronger weight for keyword/vocabulary evidence in relevance order.
Do not claim an exact hit always outranks every semantic hit until the reviewed
fusion rule guarantees it. Select and freeze fusion rule, score threshold,
weights, candidate limits and description chunk aggregation using development
cases independent of the final evaluation set, before amendment Step 5 activation.
Avoid arbitrary unvalidated similarity cutoffs or automatic threshold tuning
against final labels. Semantic similarity is not proof of item relevance.

All candidate paths use actual caller eligibility and current listing visibility
and filters before candidate caps, ordering and pagination. Otherwise unavailable
or filtered records could crowd out valid results. Relevance order needs a stable
UUID tie-breaker; use a fixed corpus/model/configuration for reproducibility.
Do not rerank each already-paginated page independently. Candidate caps must be
explicit, reported in evaluation settings, and consistent across continuation
pages. Price/recency ordering must operate over the same documented matching set.

An explicitly selected hybrid request returns the shared `503 dependency_unavailable`
when required semantic capability is unavailable; it never silently returns a
keyword-only success presented as hybrid. Keyword mode remains usable. Internal
monitoring/evaluation records degraded state without logging private query text.
No frontend changes occur until the public mode/error/sort contract is reviewed.

### Ownership, embedding freshness and retirement

Listings owns sale records, native index and any derived sale embeddings and
retrieval. Mohit implements the approved SE-01 query work inside that boundary,
coordinating shared paths with Suraj. Search does not read Listings private
storage or create its own projection. Reuse the public query boundary for later
wanted-request suggestions; no wanted/saved implementation is added here.

Each derived embedding must carry listing ID, title/description content
fingerprint, model revision and chunking/configuration version. Semantic matching
must reject a stale or wrong-version embedding. Edits invalidate old derived
content atomically with the listing write; keyword retrieval remains current.
If embeddings are populated asynchronously, track incomplete coverage explicitly
and do not silently represent incomplete semantic coverage as ready. Creation,
edit, failed/retried generation and model migration need a reviewed transactional
or durable pending-work protocol before runtime integration.

Retirement removes/invalidate derived vectors and chunks through the approved
owning-domain transaction/cleanup protocol; visibility filtering alone is not
retention cleanup. Add no separate plaintext description copies. Current
availability is checked at request time regardless of embedding freshness. No
cross-domain private-table joins, shared cache authorization, raw query logging,
or cloud object access are introduced. Concrete cleanup implementation retains
its existing separate approval requirements.

### Model, dependency and storage feasibility gate

Candidate: `sentence-transformers/all-MiniLM-L6-v2`, local CPU inference only.
The model card documents 384-dimensional embeddings and truncation beyond 256
word pieces. Title/description coverage therefore requires reviewed token-based
chunking/overlap and aggregation, rather than silently discarding long endings.
Model quality for campus listings is unproven until evaluated.

Amendment Step 4 must verify Python 3.14/macOS ARM64 and deployment Linux AMD64
compatibility, pinned package/model revisions and checksums, licensing, download
and installed sizes, locked reproducibility, CPU/memory and concurrency needs.
Inspect actual configured runtime resources; repository test definitions currently
include 256 CPU units/512 MiB, not evidence that model inference will fit.
No global installation, model download, new service or resource increase is
performed by this decision. All future local packages/caches stay project-local.

Checkpoint 4's [runtime/storage investigation](../architecture/semantic-search-feasibility.md)
found macOS 13.7.8 incompatible with published Python 3.14 ONNX wheels (macOS 14
minimum). A separate project-local Python 3.13 helper and native-array probe are
were verified for the isolated probe. The local helper/model now runs on this Mac
with a bounded inference result recorded there; native storage, production IPC/
capacity and Linux verification remain pending. Root Python 3.14 is unchanged.

The [concrete storage/write plan](../architecture/semantic-listing-storage.md)
proposes native-array objects, same-transaction invalidation, lease/publication
fencing and retirement cleanup. Mohit approved all presented plan and exact deletion-implementation gates.
Migration/inactive persistence and tests passed their scoped fresh native DB
checkpoint. No application worker/public search is activated; exact-code review,
real helper/read integration and final data/NFR gates remain pending.

Storage remains a decision gate: compare PostgreSQL-native storage/exact scoring
with a PostgreSQL vector extension, checking managed/local support, migrations,
filter-correct query plans, size and latency. Do not install an extension or
silently choose a separate vector database. Record the exact storage/index,
backfill/recovery and write-path plan and obtain verification before execution.
If compatibility or resources fail, stop with measured evidence and propose a
revised runtime; do not automatically change Python, introduce a service or
claim curated expansion alone supplies semantic retrieval.

## Local calibration follow-up — provisional

The [development calibration report](../architecture/hybrid-search-calibration.md)
records actual native keyword/expansion/cosine measurements and90comparisons on
8synthetic listings/11queries, separate from final human labels. A35/65 title/
maximum-description blend at0.35 finds9/10intended positives versus3literal/
6expanded and preserves the intended empty case, but still misses a telescope
for a stargazing query buried in long filler. The current model/configuration is
unchanged. The threshold/tiers/no-cap proposal is a development reference only;
do not freeze or activate it before verification and a separately verified
long-description follow-up. Earlier feasibility paragraphs record their staged
checkpoint states; native/IPC/bridge results are now linked in the work log.
No public mode/sort, provider acceptance, dispatcher or final FR/NFR is inferred.

## Known-vocabulary typo amendment

Mohit subsequently accepts the vague telescope/stargazing miss as a nonblocking
limitation and explicitly authorizes vocabulary-only typo tolerance. Do not infer
scoring-policy freeze, a new model/encoding requirement or public activation.
The [known-vocabulary spelling policy](../architecture/search-typo-tolerance.md)
adds bounded near spellings of reviewed concepts/aliases after exact English
normalization, preserves the full original query and independent AND groups,
rejects tied owners/short inputs and falls back completely on work/correction
limits. It uses no general dictionary, package, database extension or model
change. Initial-letter mistakes/unfamiliar listing/brand words are outside this
conservative scope; a close real word can gain an extra known-vocabulary match.
Record policy/compiler source alongside vocabulary/model for future evaluation.
Prepared code/native checks do not activate expansion or change public fields.

## Verified private-read reference

Mohit verified35/65 title/maximum-description blend,0.35 semantic cutoff,
original>expanded/typo>semantic relevance tiers with score/UUID ties, no semantic
pre-cap, and controlled503 for unavailable current coverage. This selected
implementation reference is hybrid-blend-v1. The
[private reader contract](../architecture/hybrid-listing-read.md) implements it
inside Listings with one snapshot for eligibility/coverage/union/order/page;
public input/generated/UI/dispatch activation remains a later gate. The existing
shared503 code is dependency_unavailable, not a new service_unavailable wire code.
The accepted telescope limitation and final real evaluation obligations remain.

## Public mode and both-mode relevance direction

Mohit selects Keyword as initial/default mode with an explicit switch to Hybrid
or back at any time and short per-mode explanations. He accepted the recommendation
to offer Relevance in both modes. The earlier suggested hybrid-only restriction
was not selected. Keyword relevance must use a separate PostgreSQL text-ranking
rule and remain independent of model artifacts/capability/coverage; Hybrid keeps
the verified private blend. Default recency/price choices remain available in both.
The [exact public proposal](../../contracts/search-mode-proposal.md) defines
request combinations, ranking, blank text, compatibility, UI switching/error copy
and review/implementation checks. This is documentation preparation, not public
source/type registration, runtime activation or exact affected-owner approval.

## Ordered amendment checkpoints

These remain SE-01 subcheckpoints, not a replacement for its original steps.

| Checkpoint | Output | Verification gate |
|---|---|---|
| 1 — document | This decision and linked canonical requirement amendments | Mohit verifies result; affected-owner review before new runtime signatures/schema |
| 2 — vocabulary | Reviewed versioned concepts, directionality, bounds, ambiguity and multiword tests | Human verifies vocabulary/rules |
| 3 — lexical integration | Indexed expansion in Listings boundary and native tests | PostgreSQL execution required; isolated scripts cannot prove SQL |
| 4 — feasibility/embedding preparation | Pinned runtime and model/storage/chunking/write-path plan, resource evidence | Verify concrete dependencies/storage/cleanup plan; no silent resource expansion |
| 5 — hybrid integration | Reviewed fusion/settings, public contract/generated types, UI mode/relevance option, freshness/failure tests | Real provider/schema parity, native pagination and browser verification |
| 6 — evaluation | Frozen baseline/hybrid comparison and performance evidence | Final real dataset, 20+ human-reviewed queries and applicable original NFR gates |

Model inference cannot be validated by a fake similarity scorer. Any temporary
embedding double is explicitly consumer-only; real runtime/native checks remain
pending. The existing stub guide permits original SE-01 isolated work, not
acceptance of this new model/storage dependency. Reconcile it against the reviewed
concrete contract/architecture before using doubles for hybrid integration.

## Rationale

Curated expansion supplies predictable common relationships; semantic retrieval
can generalize beyond that vocabulary. PostgreSQL documents query rewriting;
Sentence Transformers documents dense retrieval's ability to match related
wording. Neither documentation nor model selection establishes correctness,
latency, platform compatibility or acceptance on this repository.

- [PostgreSQL query rewriting](https://www.postgresql.org/docs/current/textsearch-features.html)
- [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Candidate model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

## Implications

Amend SE-01 Steps 4/5/7/8 and revisit Step 9/11 measurement inputs as needed.
Existing completed lexical/contract tests remain baseline evidence, not proof of
hybrid behavior. Final labels remain manually reviewed relevant listing IDs tied
to a frozen actual corpus and reviewed query context. Create separate development
cases for tuning; compare both paths against the same final set without changing
judgments to improve scores. Record model/vocabulary/configuration fingerprints
alongside code/data/contract/labels. NFR-01/02/04 and SE-CORE/DATA-READY remain open.
SE-02 remains unstarted. No PR, publication, cloud, hosting or merge action is
implied; those keep their separate reviews/approvals.

## Approver

Mohit Mahapatra verified the proposed six-step design and authorized documentation
Step 1 on 2026-10-24. This is not independent peer approval of the eventual code/PR. Mohit subsequently confirmed
Suraj reviewed and approved the amendment; no separate review artifact is linked. Implementation checkpoints require their own
human verification under the reusable task protocol.

## Supersedes

Amends the planned search capabilities in the [Search contract](../../contracts/search.md)
and [SE-01](../tasks/domain-task-list.md), while retaining the required PostgreSQL
baseline and current runtime contract until the explicit integration gate.

## Search ownership and keyword relevance implementation clarification

Mohit clarified that search behavior and implementation decisions are his. The
previously described separate Suraj-approval gate before search/public-contract
implementation was overstated. Shared-interface compatibility and independent
review remain part of the normal PR process; human step verification and exact
merge approval retain their existing roles. This does not waive peer review or
authorize a merge/cloud action. The verified keyword-relevance-v1 rule is now
[prepared/native-checked privately](../architecture/keyword-listing-relevance.md);
public generated fields/API/UI remain the next separately verified stages.


## Public API checkpoint implementation

Mohit verified private keyword relevance and the next source/generated/API plan.
The canonical ListingQuery now registers search_mode (keyword default, hybrid)
and relevance sort. Owned dispatch enables vocabulary/typo matching for Keyword,
uses the native rank flag for relevance, and delegates nonblank Hybrid only with
explicit helper injection. Blank text bypasses semantic dependencies; blank
relevance/invalid enums are422; absent capability is503 without fallback. Active
catalogue validation precedes absent-helper503 when supplied. The scoped browse
route keeps common error responses private,no-store. UI controls, lifecycle and
all original real upstream/data/platform/review/FR/NFR gates remain pending. No
worker/helper startup, package, cloud or Git publication change is introduced.


## Real native HTTP/model integration checkpoint

Mohit verified frontend behavior as UI-only and the existing plan's next local
integration checkpoint. A separate explicit test harness now creates a fresh
private native database, bootstraps3controlled listings through the real embedding
worker, and manages one offline helper plus an idle autocommit pool for the actual
browse HTTP service. Both real HTTP and website-proxy checks pass; synthetic
Identity/image metadata remain explicit. The native backend is distinguished from
scripted UI fixtures through response metadata/disclosure. No production app
startup or provider/cloud integration is enabled. Bounded session and cleanup
checks are in the [source-bound evidence](../evaluation/domain/se-01/native-http-model/result.json).
Original data/labels/evaluation/Linux/upstream/review/FR/NFR gates still apply.


## Normal API helper lifecycle checkpoint

Mohit verified explicit default-off settings and normal read capability lifecycle.
The composition root now owns the real helper through Listings search_runtime;
nonblank Hybrid uses a separate max2autocommit pool, while Keyword/commands retain
the original transactional pool. Malformed settings fail validation; expected
helper/read-pool startup failure closes partial resources and disables Hybrid
without fake/fallback success. Cancellation/shutdown and later construction
failure close owned resources; cleanup failures propagate. No pipeline register,
backfill, serving transition, worker scheduling or test caller enters normal
startup. [Lifecycle specification](../architecture/normal-api-search-runtime.md)
records settings/checks and all remaining actual upstream/platform/resource/data/
evaluation/review gates. No package, deployment, cloud or Git approval is inferred.


## Existing-job dispatcher checkpoint

Mohit verified the normal lifecycle result and bounded worker plan. A separate
default-off flag now enables serial due-job processing through the existing
worker/store, sharing the real helper with1dedicated autocommit connection.
Ten-job bursts/idle/failure pacing and worker-first cancellation cleanup preserve
existing leases/retries/publication guards. No automatic registration, initial
backfill or serving transition is introduced. The native probe proves empty
registry remains idle and a real source edit recovers current Hybrid after
background publication, with Keyword independence during pending work/worker
pool failure. [Contract/evidence](../architecture/semantic-embedding-dispatcher.md).
Controlled bootstrap is next, after this result's verification; original real
upstream/platform/resource/data/labels/CI/review/FR/NFR gates remain pending.


## Controlled initial bootstrap checkpoint

Mohit verified the dispatcher result and explicit bootstrap plan. Pinned-space
status/prepare/bounded queue/separate activation operations and a target-bound
operator CLI are implemented. They preserve current jobs and refuse incomplete
full-live coverage or another serving pipeline; no auto registration/backfill/
activation in app startup and no shared target approval. A real private native
CLI/worker/model probe passes unavailable-source coverage, resume/refusal and
concurrent activation/edit recovery. [Contract/evidence](../architecture/semantic-pipeline-bootstrap.md).
Actual deployment/upstream/platform/data/labels/NFR/CI/review gates remain; this
checkpoint does not supply or run a shared deployment target.
