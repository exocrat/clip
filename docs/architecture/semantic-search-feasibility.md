# Hybrid search — runtime and storage feasibility checkpoint

**Origin:** SE-01 hybrid amendment checkpoint 4 / [DEC-13](../decisions/hybrid-listing-search.md).
**Status:** Mohit verified the isolated helper approach. Repository-local helper
installation and bounded Mac inference probe performed; result awaits verification.
Native SQL, production storage/write path and Linux/cloud checks remain pending.
The proposals below retain their original unimplemented status except where the
actual result section explicitly records execution.

## Verified environment and compatibility finding

Read-only inspection on 2026-10-24 found macOS **13.7.8**, ARM64, repository-local
Python **3.14.3**, uv **0.10.7**, about 84 GiB free disk space. Repository root
requires `>=3.14,<3.15`; current API Dockerfile uses Python 3.14.8 slim-trixie.
Terraform's shared API definition specifies Linux X86_64, 256 CPU units/512 MiB.
These are source settings, not a live cloud snapshot or runtime capacity proof.

PyPI release metadata shows ONNX Runtime 1.31.0 has Python 3.14 ARM64 wheels,
but requires macOS 14 via its wheel platform tag. Scanning all stable releases
found Python 3.14 ARM64 wheels from 1.24.1 onward, all tagged macOS 14. No
compatible packaged Python 3.14/macOS 13 ARM64 wheel was found. This does not
prove a custom source build impossible; that build is outside this proposal.
The latest inspected PyTorch 2.14.1 Python 3.14 ARM64 wheel also targets macOS 14.
No attempt was made to install incompatible wheels or downgrade the project.

A smaller-runtime option is the model's existing ONNX export with explicit
mask-aware mean pooling and vector normalization. This avoids selecting the
full Sentence Transformers/PyTorch dependency stack for production inference.
It still needs actual output-parity and quality checks, not merely model loading.

## Proposed local helper, pending approval

Keep the API/project on Python 3.14. Use a separate **repository-local Python
3.13.12 helper environment** for ONNX inference. uv 0.10.7's available-build list
contains `cpython-3.13.12-macos-aarch64-none`; this is an available build, not
an installed interpreter or a claim it is the newest upstream security patch.
Review upstream patch/security support before locking deployment artifacts.

Candidate direct dependencies (not an installed/resolved lock):

| Package | Pin | Mac compressed wheel | Linux AMD64 compressed wheel |
|---|---|---:|---:|
| onnxruntime | 1.23.2 | 17,196,337 bytes, cp313/macOS 13 ARM64 | 17,382,518 bytes, cp313/manylinux 2.27/2.28 |
| numpy | 2.5.4 | 12,009,826 bytes, cp313/macOS 11 ARM64 | 16,718,044 bytes, cp313/manylinux 2.27/2.28 |
| tokenizers | 0.23.3 | 3,101,381 bytes, cp310 ABI3/macOS 11 ARM64 | 3,396,193 bytes, cp310 ABI3/manylinux 2.17 |

Wheel tags indicate candidates, not proven imports/ABI compatibility. ONNX
Runtime's transitive requirements include coloredlogs, flatbuffers, packaging,
protobuf and sympy; tokenizers requires huggingface-hub. Resolve all transitive
pins, licenses, security and hashes into a separate helper lock before install.
Do not use `--no-deps` to disguise missing runtime requirements. No automatic Hub
model loading, remote code execution, paid service or credential access is planned.
Load the checked local tokenizer/model files only.

Keep downloads, helper interpreter, helper environment, caches and model artifacts
under ignored `.tools/semantic/`, using explicit uv install/cache paths and no
global links or PATH edits. Preserve `.venv`, root pyproject/lock and system Python.
A deployment helper would need a separately reviewed image build; it is not
already present in the API image. Use the same pinned inference/model pipeline
on Mac and Linux, not a hidden different implementation per platform.

Proposed process boundary: one long-lived helper child per API process, bounded
pipe messages, one CPU inference thread, one in-flight batch and at most eight
queued requests. No TCP listener or separately deployed service. Set 5-second
inference and 30-second startup deadlines; overflow/failure makes explicitly
selected hybrid requests unavailable. No query/title/description dumps in errors,
logs or crash-protocol output. Retries/restart must not grow child counts.
All of these are implementation proposals requiring verification, not existing
runtime controls.

## Candidate model pin and download envelope

Model: `sentence-transformers/all-MiniLM-L6-v2`, Apache-2.0 per model metadata.
Observed exact model revision:
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Propose the same FP32 `onnx/model.onnx` on both platforms initially:
90,405,214 bytes, LFS SHA-256
`6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452`.
The tokenizer JSON is 466,247 bytes; configuration/pooling/tokenizer metadata
must also be pinned and SHA-256 checked when retrieved. Read these small files
before defining exact tensor inputs/outputs; the export has not been inspected
or executed here. Do not substitute platform-specific quantized models without
new parity, quality, fingerprint and latency evidence.

Three direct Mac wheels plus the FP32 model total **122,712,758 bytes** before
interpreter, transitive packages, tokenizer, cache and unpacked installation.
This is a lower bound, not the total installation size. Proposed probe ceilings:
300 MiB total downloaded artifacts and 1 GiB additional disk usage; first resolve
sizes and stop before exceeding either. No download is authorized by this document.

Proposed bounded local probe after verification: imports/known tensor shape,
finite unit-normalized 384-dimensional vectors, repeatability tolerance, tokenizer
special-token handling, no-network inference, short/long/end-of-description cases,
and independent controlled paraphrase/nonmatch cases. Use at most 30 synthetic
queries and 10 minutes; record cold/warm latency, peak RSS and installed size.
Stop if combined helper/API RSS reaches 512 MiB or the helper fails to exit on
its deadline. A successful Mac probe is not Linux/cgroup/NFR evidence; Linux
AMD64 and actual configured CPU/memory limits need their own real check. Do not
increase cloud capacity or infer the 10 requests/s NFR will pass.

## Proposed description chunking

The model documents a 256-word-piece limit and 384-dimensional output. Propose
254 content tokens plus model special tokens per window, with 32-token overlap,
using the pinned tokenizer. Encode title separately and every description window;
store a title vector and ordered description chunk vectors, not duplicate text.
Aggregate description chunk similarity by maximum for candidate matching;
calibrate threshold/fusion on separate development cases before final freeze.
Include title/description source fingerprint, model/export/pooling/chunk versions
in every embedding generation. Verify final-window coverage and all 5,000 allowed
description code points. A proposed 96-chunk safety bound must be validated against
the full allowed input; overflow must fail preparation explicitly, never truncate
or silently mark complete. Thresholds/weights remain later reviewed decisions.

## Storage comparison and proposal

| Option | Benefits | Costs and gates |
|---|---|---|
| PostgreSQL `real[]`, exact cosine/dot scoring | No extension; exact scoring over the eligible corpus; preserves PostgreSQL ownership | No dedicated similarity index; scans eligible chunk vectors; must validate shape/finite normalized values and measure plans/latency |
| pgvector `vector(384)` | Vector type/distance operators; exact search and optional vector indexes | Extension availability/version on actual local/RDS engine unknown; migration/permissions review; approximate filtering can underfill results and needs dedicated correctness checks |

Propose **native PostgreSQL arrays with exact scoring for the bounded feasibility
probe**, retaining the existing full-text GIN. This is not accepted production
storage or a claim it meets NFR-02. Native vectors contain 1,536 bytes of float
payload each; 1,000 listings with 10 vectors each have 15,360,000 bytes payload,
excluding array/row/index overhead. Actual chunk counts and query execution cost
remain unmeasured. Revisit storage after measured plans; no automatic extension
installation or vector database fallback.

Proposed Listings-owned derived-generation table stores listing FK, content
fingerprint, model/config revision, generation state and ordered 384-float chunks.
Use constraints for shape/index uniqueness and application validation for finite,
nonzero/unit vectors; exact migration schema/functions need their own reviewed
plan. Join only current, matching-version, complete generations to current
eligible rows. Apply authorization/availability/category/condition/price before
similarity limits and stable sort/pagination. No private cross-domain reads.

## Proposed write, recovery and retirement protocol

1. Create/edit commits a new source fingerprint and durable pending generation
   together with the listing write; invalidate old derived data in that same
   transaction. Keyword search remains current through its generated vector.
2. An owning-domain bounded worker claims pending work with a lease. It computes
   outside the write transaction, then compares fingerprint/version/retirement
   state before atomically publishing a complete generation. Discard stale results;
   retried jobs are idempotent. Expired leases are recoverable after restart.
3. Until all request-eligible records have complete current generations, hybrid
   readiness must report incomplete coverage rather than silently missing those
   records. The concrete contract must define the `503` readiness check and its
   transaction/snapshot behavior; keyword mode remains available.
4. Retirement atomically invalidates/deletes vectors and pending work and prevents
   a delayed worker republishing them. No derived plaintext is retained. The exact
   deletion mechanism/order requires existing cleanup approval before implementing
   it; this proposal neither runs nor authorizes destructive cleanup.
5. Model/config updates prepare separately versioned generations and switch only
   after full coverage/parity checks. No mixed embedding spaces. Backfill runs
   require a fixed target, duration/concurrency/resource cap and recovery evidence.

## Remaining decisions and evidence

Verify the Python 3.13 helper alternative before installing or adding a new runtime
boundary. Native array storage, chunking/aggregation, queue/deadlines and write/
cleanup protocol are proposed concrete choices, not approved migrations or gates
already passed. If the helper or resource probe fails, stop and reconsider rather
than changing project Python, OS, cloud capacity or service dependencies.

Hybrid checkpoint 3 native checks/activation remain pending; this independent
feasibility preparation does not discharge them. Final 20+ human-reviewed query
labels, fixed-corpus comparison and original SE-CORE/DATA-READY/NFR gates remain.

## Observed candidate wheel SHA-256 values

Retained from PyPI metadata; not downloaded-file verification or a transitive lock.

| Package/platform above | SHA-256 |
|---|---|
| ONNX 1.23.2 / Mac | `2ff531ad8496281b4297f32b83b01cdd719617e2351ffe0dba5684fb283afa1f` |
| ONNX 1.23.2 / Linux | `8bace4e0d46480fbeeb7bbe1ffe1f080e6663a42d1086ff95c1551f2d39e7872` |
| NumPy 2.5.4 / Mac | `7415db95818b39ec475a5eea54d9e3b6bc83e3912158e46da3438cdce399804d` |
| NumPy 2.5.4 / Linux | `6ffa07666f8da0eef81d149934a626d0d95fbd6838432a33e66245423a9062c0` |
| Tokenizers 0.23.3 / Mac | `68649e97d5b43c44c031d8d848874a6eecae8f8fe40ea989aa777a5a83aca716` |
| Tokenizers 0.23.3 / Linux | `376851d22bcf9d650a5c3090bb83e6cf9e895fbf0595369fa4cd43c1f69b5f87` |

## Sources inspected

- [ONNX Runtime package metadata](https://pypi.org/pypi/onnxruntime/json)
- [ONNX Runtime 1.23.2 files](https://pypi.org/project/onnxruntime/1.23.2/#files)
- [NumPy 2.5.4 files](https://pypi.org/project/numpy/2.5.4/#files)
- [Tokenizers 0.23.3 files](https://pypi.org/project/tokenizers/0.23.3/#files)
- [Model metadata](https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2?blobs=true)
- [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [ONNX Runtime Python documentation](https://onnxruntime.ai/docs/get-started/with-python.html)
- [PostgreSQL arrays](https://www.postgresql.org/docs/current/arrays.html)
- [pgvector documentation, including filtering](https://github.com/pgvector/pgvector)

## Actual isolated Mac probe — 2026-10-24

The approved probe's local result, supervisor bounds and preflight metadata are
in historical receipts; see the [evaluation retrieval guidance](../evaluation/README.md).
Helper Python 3.13.12 and 24 locked packages are under
`.tools/semantic/`; API Python remains 3.14.3 and the root lock hash is unchanged.
Official release metadata now identifies 3.13.12 as superseded by 3.13.17; this
older exact probe pin is not a deployment/security-support selection. Revisit
patch/runtime/package support before production packaging.

Preflight selected compatible Mac binary wheels and found no PyPI-reported
advisories for those pinned package versions (not a comprehensive security audit).
Wheel licenses were recorded; Protobuf's BSD-style terms and tqdm's MPL/MIT terms
were inspected directly in downloaded license files where metadata was incomplete.
Packages were installed offline using hash-pinned requirements and local wheels.
31 model/wheel artifacts totaling 136,436,874 bytes passed content checks; with
the 17,680,006-byte interpreter archive the artifact envelope was 154,116,880 bytes
(about 147 MiB), below 300 MiB. uv handles interpreter retrieval; the 31 artifact
checks refer to model/wheels, not an independently rehashed retained interpreter
archive. Installed/cache/model tree uses about 528 MiB, below the 1 GiB cap.
No global links, system/PATH edits, root Python change or model Hub runtime access.

The successful run `20261024T135651961346Z` executed 14 CPU inference calls with
one inference thread and no network/child-process attempts in the probe. Model
load/validation after imports took 0.123 s (filesystem already warmed by earlier
runs), first inference 5.3 ms, warm median 4.1 ms, max 72.7 ms. These are short
local observations, not cold-machine or HTTP/load/production p95 measurements.
Helper peak RSS was 273,612,800 bytes; supervisor sampled combined helper plus
existing isolated preview API RSS at 288,473,088 bytes (about 275 MiB). The preview
API's 14,860,288-byte resident baseline is not production API capacity evidence.
The 512 MiB local stop bound was respected; Linux/cgroup fit is untested.

All vectors had 384 finite components and unit norm. Repeat maximum absolute difference
was zero; padding invariance delta was 5.96e-8. Three controlled paraphrase cases
ranked their intended fixture first (campus transport, calculus material and
study furniture); these are developer probe expectations, not human NFR labels.
A 4,822-character/903-token description covered four windows; its final window
had the largest telescope similarity but remained negative (-0.0243). This proves
coverage, not satisfactory long-description relevance or a usable threshold.
Tokenizer-only coverage of 5,000 CJK characters produced 5,000 tokens/23 windows
without dropping the final token; it is not exhaustive full-input validation.
No PyTorch reference-output parity, vocabulary fusion or native SQL was tested.

Two earlier failed probe runs are retained locally: oversized controlled fixture
`20261024T135427437998Z` and a platform-reporting function attempting a forbidden
`uname` child `20261024T135622957734Z`. Corrected the fixture and used direct OS
metadata; network/child blocking was kept, not weakened. Portable regression
checks cover full chunk bounds/overlap/overflow, fixture size and artifact
integrity. Production helper IPC/queue/restart behavior remains unimplemented.

The next Step 4 checkpoint is a concrete storage/write/migration plan, not live
hybrid activation. Original native checkpoint 3 and all data/human-label/NFR
checks remain pending.

## Concrete storage/write plan checkpoint

The [Listings-owned storage and transaction plan](semantic-listing-storage.md)
now defines proposed tables/constraints, source hashing, worker lock/lease fences,
single-statement coverage, retirement deletion and guarded migration/rollback.
It awaits human verification and affected-owner review. Its exact derived-content
deletion mechanism requires separate implementation approval; no migration or
cleanup code has been created/applied by this planning checkpoint.

## Approved storage preparation follow-up

Mohit explicitly approved the presented plan and derived-content deletion
implementation gates. Migration `20261024153316` and inactive Listings-owned
persistence/types/manifest and unit/native tests are now prepared; see the
[implementation checkpoint](semantic-listing-storage.md#implementation-checkpoint--prepared-not-native-verified).
No migration was applied and no cleanup/backfill/worker started. Native SQL,
production orchestration/read integration, code review and original NFR/data/
human-label gates remain pending.

## Native persistence follow-up

After storage preparation was verified, the native checkpoint passed the
scoped SQL migration/math/trigger/rollback/query/race tests on this Mac's fresh
private PostgreSQL 18.6 cluster. Its raw receipt is in Git history; see the
[evaluation retrieval guidance](../evaluation/README.md). All clusters were stopped and logs
retained. This discharges those prepared native assertions, not pipeline-switch/
full-data/production-helper/read/Linux or relevance/fusion/FR/NFR gates.

The native bootstrap/switch matrix also passed after that checkpoint:
resumable coverage, limits, atomic switch and
concurrent-source invalidation. Real inference/IPC/public-query integration and
production deployment/data/evaluation gates remain separate.

## Actual private IPC follow-up

[Private protocol](semantic-helper-protocol.md) and the historical IPC result
(see [evaluation retrieval guidance](../evaluation/README.md)) record the same
pinned local model through a real owned helper process,
including bounded queue/deadlines, complete source windows, repeatability and
crash/restart. This extends the original model probe; it does not activate public
hybrid search, generate DB vectors, accept Linux/cgroups or replace final relevance
labels. API Python3.14/global setup/dependency locks remain unchanged.
