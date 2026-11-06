# Deterministic synthetic-data tooling

**Current NEXT-06:** [Frozen dataset and task-wide review](../docs/evaluation/domain/next-06/task-wide-review.md), with22canonical reviewed queries. Older preparation sections below retain their historical context. Formal human/current-headCI/peer acceptance remains separate.

## SE-01 isolated schema-shaped corpus

`data.generators.search_preview` reuses PD-09 IDs, hashing and private named-run
IO for the reviewed user/listing fields. Existing PD-09 commands and their
load refusal are unchanged. See [the Search preview format](formats/search-preview.md).

With locked dependencies installed, run from the repository root:

```bash
uv run --locked python -m data.generators.search_preview generate --name search-preview-42 --seed 42 --users 5000 --listings 1000 --logical-time 2026-10-24T09:00:00.000000Z
uv run --locked python -m data.generators.search_preview validate --name search-preview-42
```

On Mohit's checkout, `.venv/bin/python` can replace `uv run --locked python`
after repository-local locked setup. Logical time is explicit fixture input,
not the machine clock; reuse it for repeat generation. Choose a fresh run name;
there is no overwrite. Datasets are ignored; manifests can be retained.

The implemented PostgreSQL loader has not been exercised against PostgreSQL in
this checkout. It requires an independently prepared empty local database named
`clip_test_search_preview`, with role `clip_search_preview` owning the fixture
tables and every current repository migration/catalogue applied. Local database
setup/ordered migration execution remain pending until a PostgreSQL runtime is
available. Then supply its real canonical Unix-socket directory:

```bash
CLIP_ENVIRONMENT=test uv run --locked python -m data.generators.search_loader --name search-preview-42 --socket-dir /absolute/local/socket/directory --isolated-preview
```

The socket path must not traverse symlinks (use `/private/tmp` on macOS rather
than `/tmp`). Unset ambient `CLIP_DATABASE_URL`, `DATABASE_URL` and `PG*`
overrides; never supply application credentials to this fixture route. The
loader verifies fixed database/role/Unix transport, migration versions and active
catalogue, locks/checks empty tables, and inserts in one transaction. Deferred
constraints/counts must pass before commit. It creates no credentials or auth
bypass and performs no storage/provider calls.

There is **no reset command**: nonempty targets are refused. Destructive cleanup
requires separate exact-target review and approval. Synthetic image metadata
has no backing objects; it cannot validate LI-02 or support cloud measurement.
Real loading/FKs/indexes/images and final DATA-READY remain pending at SE-01
steps 2/4/9. Local fixture tests do not establish PostgreSQL ranking or NFRs.

PD-09 supplies **preview-only** records/manifests, not final domain data or a
database loader. [Prerequisites](prerequisites.md) assign real adapters/loading,
population/integrity/index validation and human relevance judgments to
SE-01/DATA-READY after actual ID-READY/LI-CORE schemas and DL-00 contracts.
PD-08 deferred acceptance remains recorded under Mohit's preparation exception.

## Setup and commands

From the repository root, use the existing locked Python 3.14 environment:

```bash
uv sync --locked
uv run --locked python -m data.generators --seed 42 --users 3 --listings 2
uv run --locked python -m data.generators.files generate --name preview-42 --seed 42 --users 3 --listings 2
uv run --locked python -m data.generators.files validate --name preview-42
```

The first generator streams controlled JSON Lines to stdout without file IO.
The file generator creates only `data/runs/preview-42/dataset.json` and
`manifest.json`; both commands print the validated logical fingerprint and exit
0 on success. Explicit signed-64-bit seed and counts each 0–100,000 are required.
Run names are 1–64 lowercase ASCII letters/digits, `_` or `-`, beginning with a
letter/digit. No arbitrary path, database URL or provider target is accepted.

The [preview API](generators/README.md) supplies stable UUIDv4-shaped fixture IDs,
synthetic labels, reserved `example.invalid` addresses and pure validation hooks.
The [manifest format](formats/manifest.md) identifies generator/config/preview
schema versions, seed/counts, UTC audit time and canonical logical fingerprint.
Changing only generation time leaves records/fingerprint unchanged. No real
contact, credential, private key, OTP, private message or live object is imported.

## Local safety, retention and reproducibility

- Existing run directories are refused, even if empty or incomplete. There is
  **no overwrite or reset command**. Choose a fresh name; inspect any old output
  and its retained manifest before separately deciding whether to remove it.
- Root/run/file symlinks and nonregular JSON files are rejected. Generation
  reserves a new owner-private directory and exclusively creates each file.
  Interrupted IO can leave partial output; missing/altered/mismatched files fail
  validation. Keep one writer and do not modify paths concurrently with a run.
- Validation is local only, rejects duplicate JSON keys and files over 128 MiB,
  and verifies records/config/counts/fingerprint plus matching manifest. Invalid
  arguments, unsafe targets, IO failures and integrity failures exit 2 with safe
  diagnostics. Fix the cause and use a fresh name; never guess a remote target.
- `.gitignore` excludes only `data/runs/*/dataset.json`, the regenerable preview
  payload. Source, formats, inputs and per-run manifests remain eligible for Git.
  Retain reviewed manifests for meaningful reproducibility/evaluation runs with
  the accepted code revision; do not indiscriminately commit disposable runs.
- Regenerate under a fresh run name with the retained manifest's seed/counts and
  the **same generator/config/schema versions and code revision**, then validate
  and compare fingerprints. Audit time differs intentionally. A retained preview
  manifest does not recreate a final domain dataset through this scaffold.
- Final evaluation source inputs, reviewed labels/manifests and evidence needed
  to reproduce results must be retained through SE-01's reviewed policy. No
  blanket JSON/data ignore rule hides them. No cleanup/cloud action is implied.

## Loading and readiness gates

```bash
uv run --locked python -m data.generators.files load
```

This deliberately exits **2**, naming required DL-00 contracts, ID-READY/LI-CORE
schemas and SE-01 adapter/loader validation. It performs no DB connection/write
and never claims data loaded. SE-01 later implements/registers actual safe
generate/load/reset/validate commands against the accepted domain schema.

DATA-READY requires actual >=5,000 users/>=1,000 listings with integrity,
availability and index checks, reproducible logical fingerprints, and >=20
human-reviewed representative queries/relevant listing IDs. NFR-04's final
Success@5 evaluation remains SE-01 work. PD-09 Step 5 supplies the
[query-label format and human-review procedure](formats/query-labels.md) and
[empty draft template](evaluation/query-labels.template.json). SE-01 stores the
reviewed final label set at `data/evaluation/query-labels.json`, derived from
that template; the template itself contains no final judgments or listing IDs.
Versioned NFR workload profiles belong under `data/evaluation/workloads/`.
Evaluator/load/recovery/restore source tools belong under
`scripts/evaluation/`, with exact commands registered by their owning tasks.

## Verification and review handoff

Run the persistent local suite and repository Python format check:

```bash
uv run --locked python -m pytest data/tests -q -W error
make check-python-format
```

Use `python -m pytest` so the repository root is importable without changing the
shared pytest configuration. The combined Python check is:

```bash
uv run --locked python -m pytest apps/api/tests tests data/tests -q -W error
```

Tests use only synthetic inputs and private temporary directories. They check
cross-process repeatability, IDs/RNG, count bounds/hooks, UTC/fingerprint and
tamper handling, path/symlink/overwrite/incomplete-output safety, CLI diagnostics,
missing loader prerequisites, draft-label safety and Git retention. Warnings
fail the run. A failed check needs its original cause fixed within ownership;
never bypass validation or reinterpret missing domain inputs as loaded data.

Step 6 local evidence: **63 PD-09 tests passed; 361 combined Python tests passed;
pinned Black check passed across 42 files**. These counts describe the current
checkpoint, not a permanent expected test count. PD-12/PD-13 must include the
explicit data-test invocation when integrating CI/common commands; root default
pytest discovery currently targets only `apps/api/tests` and `tests`.

Mohit verified all six local steps and the local closeout audit. This does not
accept PD-08, final domain adapters/population/labels, DATA-READY or any NFR.
Unfinished PD-08 work now belongs to pre-domain integration under the
[handoff decision](../docs/decisions/database-integration-handoff.md). PD-09 still
requires independent peer review and the accepted upstream/main handoff under the recorded preparation
exception. No task commit/push/merge is authorized by running these checks.

## NEXT-06 reference inputs and local loading

The approved November-evaluation recipe now contains **5,000 regular users and
1,000 listings**, stable until **1 December 2026, 00:00 UTC**. Temporary-account
permission tests use separate fresh fixtures with their unchanged14day lifetime.
The exact45topic/synonym pairs, category/condition/price/optional-field counts and
cutoff live in `data/evaluation/reference-recipe.json`. Original photos remain
external and are bound by `reference-image-inputs.json`; originals are never
converted, renamed or linked into writable test storage.

`data.generators.reference` reuses stable IDs/canonical hashes/named-run guards.
Independent SHA256 assignments preserve all distributions; topic assignment cycles
five topics within each independently ordered category. It generates local record
bundles and1000relative image plans, not credentials, sessions, database rows,
objects, vectors or human judgments. `generate` requires today's UTCmidnight,
fresh run name, explicit image root and threshold; `validate` is read-only and
rejects altered photos/inputs/source/claims. Exact logical hashes exclude audit
timestamps/root path but bind base Git revision plus source/config/photo digests.
Final accepted source revision and freeze remain pending.

```sh
.venv/bin/python -m data.generators.reference generate --name next06-transfer-42-20261030-a --logical-time 2026-10-30T00:00:00.000000Z --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --sensitive-threshold-paise 500000
.venv/bin/python -m data.generators.reference generate --name next06-transfer-42-20261030-b --logical-time 2026-10-30T00:00:00.000000Z --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --sensitive-threshold-paise 500000
.venv/bin/python -m data.generators.reference validate --name next06-transfer-42-20261030-a --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images
.venv/bin/python -m data.generators.reference validate --name next06-transfer-42-20261030-b --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images
CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_local --name next06-transfer-42-20261030-a --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --isolated-local-reference
.venv/bin/pytest data/tests -q -W error
```

The recorded named runs already exist; future generation needs a fresh name and
that day's UTCmidnight before the cutoff. All earlier next06-reference[-v1]-42
runs are superseded local diagnostics under the previous mixed-user/week recipe;
they are not the November-evaluation pair. No generated-input overwrite or
existing-target reset is supported.
Raw datasets are ignored; legible completion manifests can be retained in Git.

`reference_load.py` copies45verified sources into new owned immutable blobs and
backs1000distinct keys with those bytes. It checks the real DB/login/Unix path/
version/migrations, locks empty tables and inserts schema-adapted users/listings/
confirmed-image metadata only after byte verification. Deferred constraints,
full row/image projections, current availability and actual text indexes must pass.
It refuses a second load. Source photos and existing targets are untouched.

The local runner creates only `/private/tmp/clip-next06-reference-<random>`, using
repo PG18.6/dbmate2.36.0, no TCP/listener/Docker/AWS. It requires explicit test
activation, rejects ambient targets, needs2GiBfree and has a ten-minute work cap.
It stops its cluster and retains evidence on exit. A separate probe clone checks
real Listings handlers/SQL with a trusted caller/SQL-eligibility and real-file
storage fixture: eight browse pages,1000owner image deliveries with byte hashes,
hidden/anonymous denial and normal upload-intent/confirmation/create/detail.
These do not establish actual Identity session or S3 permissions. Actual new-
listing vector/search is pending in this default run. PostgreSQL text vectors
are not semantic embeddings.

Add `--embeddings` to the same local command to exercise the installed pinned
all-MiniLM-L6-v2 model, supported prepare/queue/worker/activate operations and
current coverage for all1000nonretired sources (including hidden listings).
`scripts/evaluation/reference_embeddings.py` checks bounded real HTTP searches
in both modes, Hybrid keyword inclusion and visible-only unique results. The
separate normal-publication clone uses the actual background dispatcher; its
new listing must have a current vector and appear in Hybrid results. Baseline
rows/coverage remain unchanged. The helper is stopped/reaped, with production
per-call limits and an additional finite2500window ceiling. No install/download,
fake inference, external target or human relevance labels are involved.

```sh
CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_local --name next06-transfer-42-20261030-a --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --isolated-local-reference --embeddings
```

See [the reviewed load plan](../docs/architecture/reference-dataset-loading.md).
Cloud use requires a separately approved actual DB/bucket/prefix/IAM/runtime/cost/
cleanup plan; none of these local commands accepts or writes a cloud target.
Actual cloud photo delivery/auth/embeddings, human labels, reset/reload and freeze
remain required. Local vectors do not accept DATA-READY. Code/schema/config changes can still require revalidation; the
amendment removes expiry-driven regeneration during November, not every recheck.


### NEXT-06 Step5 draft human review

The [22query review package](../docs/evaluation/domain/next-06/step-05/review.md)
links the complete actual1000listing catalogue, independent machine candidate
suggestions and `data/evaluation/query-labels.draft.json`. Its approved-format
review/judgment/final-binding fields remain null. Inspect content and policy;
provide actual human topic/ID corrections before any reviewed labels. Final
readiness/source/contract/freeze prerequisites still gate acceptance and scoring.

```sh
.venv/bin/python -m scripts.evaluation.search validate-labels --labels data/evaluation/query-labels.draft.json
```

Expected: format valid, draft, scoring not allowed, human review not verified.

### NEXT-06 Step6 isolated rebuild and freeze candidate

```sh
CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_local --name next06-transfer-42-20261030-a --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --isolated-local-reference --embeddings --rebuild-check
```

`--rebuild-check` requires `--embeddings`. It first encodes1000sources, then drops
and recreates only the fixed reference database this invocation just created,
reapplies all migrations, reloads the unchanged bundle/media and re-encodes text.
It refuses unowned/stopped/mismatched targets; no force/disconnect, existing target
argument, source-photo deletion or generated-input overwrite is available. Local
media is retained and all byte bindings are verified again. Logical rows/media,
actual SQLvector parts/source fingerprints and index definitions must match.
Random generation IDs and audit times are deliberately excluded from logical
comparisons. Both helpers and the owned cluster stop; private receipts remain.
The ordinary loader still refuses nonempty databases.

The [Step6 evidence](../docs/evaluation/domain/next-06/step-06/result.json) and
[freeze candidate](../docs/evaluation/domain/next-06/step-06/freeze-candidate.json)
retain exact inputs, counts and fingerprints. This section records the pre-acceptance freeze candidate. NEXT-06/DATA-READY is
now complete per the [accepted task-wide review](../docs/evaluation/domain/next-06/task-wide-review.md)
and [work-log status](../docs/status/work-log.md). The22accepted judgments and
source bindings remain unchanged; revalidate only after material input changes.


NEXT-06/DATA-READY is complete; no new load is required. Use the [frozen
manifest](../docs/evaluation/domain/next-06/frozen-dataset.json) and [accepted
task-wide review](../docs/evaluation/domain/next-06/task-wide-review.md) for the
release, its provenance and verification limits.


### NEXT-06 prepared cloud adapter (offline preparation complete)

`data.generators.reference_cloud plan` validates a named input and prints an offline
plan without constructing clients. `load` is explicit/operator-only. The accepted NEXT-06 load is recorded in the
task-wide review; do not rerun it just to recreate the published release. `reference-cloud-target.template.json` intentionally contains
nulls for operator-owned live bindings and cannot execute unchanged. See the
[accepted task-wide review](../docs/evaluation/domain/next-06/task-wide-review.md)
for the accepted result and evidence limits. The cleanup removed the earlier
operator handoff, so the invocation forms are retained here for a future, newly
reviewed target (replace every placeholder; do not replay the accepted load):

```sh
.venv/bin/python -m data.generators.reference_cloud plan --name <prepared-run-name> --image-root /absolute/path/to/clip-dataset-images
.venv/bin/python -m data.generators.reference_cloud load --name <prepared-run-name> --image-root /absolute/path/to/clip-dataset-images --target /absolute/private/approved-target.json --ledger /absolute/private/new-run-ledger.jsonl --execute
```

The `plan` form is offline. The `load` form can write S3 and the database: it
requires a reviewed current target and scope, private inputs and a fresh ledger,
explicit approval, bounded cost and time, and a recovery/cleanup plan. An error or
timeout can have a partial or uncertain outcome; inspect the ledger and actual
state before proposing recovery. Never print secrets or signed URLs. The adapter
retains its account and non-root identity guards; new operations require fresh
review and approval.

`reference_rows.py` shares schema-aware insertion/verification between local and
cloud adapters; the local wrapper's original fixed DB/role/Unix/object guards remain.
Every cloud object must pass create-only upload and actual bounded GET/hash checks
before confirmed SQLmetadata. The final transaction checks emptiness under locks.
SQL/media projections account for target-specific authoritative object keys, so
cloud key mappings differ from the local reference-local namespace; stable source
records and the input logical fingerprint must remain unchanged.

Tests use explicit synthetic guard fixtures and Botocore Stubber for request/byte
semantics; they are not real S3/IAM/session/deployment evidence. The native local
rebuild checks the actual shared SQL, real photo bytes, model and dispatcher.
The [accepted NEXT-06 task-wide review](../docs/evaluation/domain/next-06/task-wide-review.md)
records completion, final checks and the limits of the retained evidence.


### Complete published transfer

Mohit explicitly authorized including real images and raw payloads with this PR.
[Transfer instructions](transfer/README.md) document the tracked42.5MB archive,
52member hashes, safe extraction and both current payloads. This is the explicit
exception to earlier outside-Git photo/payload guidance. Active inputs are
next06-transfer-42-20261030-a/b; earlier dec01/week runs remain historical diagnostics.
A source-only rebind preserves all records and22accepted judgments. Validation
accepts the recorded known ancestor plus exact current source/schema/config/photo
hashes, so publication alone does not invalidate the corpus.


### Browser-login SDK support

`reference_login.py` bridges a named AWS CLI browser-login profile into the SDK
using bounded `aws configure export-credentials --format process` capture. Tokens
stay in memory, preserve their expiry and refresh from that same explicit profile.
The bridge writes no credential/config files; AWS CLI manages its normal existing
login cache. It requires no access-key creation, new IAM allowances or optional
botocore[crt] installation. Existing non-login profiles retain normal SDK behavior.
Import/session construction performs no export or network request. Export failures,
timeouts, malformed/expired responses are rejected with fixed safe diagnostics.

The cloud loader still checks the actual account/non-root identity before any
storage/database operation; compatible credentials never imply target/action
approval. STS uses standard SigV4 while S3 retains S3SigV4. The approved preflight
verified this bridge with a real project STS request and retained only identity
metadata, not credential output. See the latest preflight evidence under
`docs/evaluation/domain/next-06/transfer/` for route/permission observations.

### NEXT-06 current Step5 canonical labels

`data/evaluation/query-labels.json` now contains22unchanged Mohit-reviewed cases, all included, bound to the actual7efd142e corpus, a12f4a3dataset source and6edb52bpublic contracts. Mohit explicitly chose the recorded acceptance timestamp as reviewed_at. Revalidate locally with `.venv/bin/python -m scripts.evaluation.reference_labels validate --image-root /absolute/path/to/clip-dataset-images`; original/restored payload/photos and full accepted Git objects are required. The command reconstructs actual inputs, committed source and recorded cloud/rebuild bindings without network/inference/scoring. `write` refuses existing output. Historical drafts and earlier freeze candidates remain historical; the accepted
Step6 frozen manifest and DATA-READY status are recorded separately.

### NEXT-06 Step6 frozen release

[The immutable frozen manifest](../docs/evaluation/domain/next-06/frozen-dataset.json) now binds actual5,000users/1,000listings/images,2,000vector parts and22reviewed labels. Verify with `reference_release validate` as indexed in the command registry. Both generated record sets,52archive members/45photos, load ledger, pinned model and real reset/cloud-native hashes match. Step3normal workflow completion is explicitly human-reported from another executor. No data/labels regenerated or cloud objects deleted. [Task-wide review](../docs/evaluation/domain/next-06/task-wide-review.md) lists source/provenance/checks and the recorded user/CI/peer/merge acceptance and its limits.
