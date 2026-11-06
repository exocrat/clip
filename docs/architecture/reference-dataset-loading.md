# NEXT-06 Step3: reviewed reference-data load and media path

**Status:** NEXT-06/DATA-READY is marked complete in the [work log](../status/work-log.md)
and [task-wide review](../evaluation/domain/next-06/task-wide-review.md). This guide
preserves the implementation/reproducibility path; its “pending” gates describe the
original preparation checkpoint. They are not current task status or reusable
approval for a new data operation.

## Inputs and ownership

Use only the validated December-cutoff next06-transfer-42-20261030 a/b reference-input pair and the
external45photo inventory. Revalidate the input/manifest pair, schema/code binding,
source digests, current runtime threshold and comparison window before writes.
Seed42,5000regular reference users,1000listings/owners/images and independent
assignments are unchanged. Bulk adaptation is owned by Search/data; Identity and
Listings owners review affected record/validation assumptions before final use.
No product API contract, schema, policy, global tool or shared page change.

The existing preview loader is not used: its one-byte metadata refers to absent
objects and its users omit current Handle/lifecycle fields. The final loader must
use the actual29migration schema and current category/condition codes/labels.
Only code review and tests of this explicitly scoped loader authorize the rehearsal;
this document records the reviewed procedure, not approval of a shared/cloud load.

## Local-only target and bounds

- New0700owner-private directory `/private/tmp/clip-next06-reference-<random>/`,
  containing PGDATA, Unix socket, logs, local objects and receipts. Never accept an
  existing directory, DSN, host, socket, bucket, source prefix or arbitrary tool.
- Reuse repo `.tools/native-db/pgsql` PostgreSQL18.6 and pinned dbmate2.36.0.
  Initialize a new cluster and apply all29current migrations. Database
  `clip_test_next06_reference`; login/owner `clip_next06_loader`. Unix transport
  only; `listen_addresses=''`; no published port, Docker, external service or AWS.
- Check actual database/role/server-version/Unix transport and the exact migrated
  version set before DML. Refuse ambient DB/libpq/AWS target overrides and require
  explicit test/local opt-in. Guard counts under locks, not just a preflight read.
- Require at least2GiBfree disk; cap the owned rehearsal at10minutes. Use bounded
  SQL/subprocess timeouts. Stop only the cluster created by this invocation on
  success/failure/interruption, retaining its private files/receipt for inspection.
  No shared-data reset, broad process kill or source-file cleanup.

## Materialize actual local bytes before confirmed metadata

1. Read and verify each45source file against its exact approved digest, type and
   size. Copy bytes into owner-private content-addressed files inside the new
   target, with immutable/read-only content. Do not link to or modify originals.
2. Create1000distinct local object-key entries backed by those verified copies;
   hard links may reuse the owned immutable bytes so physical storage is about
   42MB, while logical object volume is925881224bytes. Rehash every planned entry.
3. Bind generated upload IDs to the storage boundary's authoritative object-key
   builder; planned relative names in Step2 are not blindly treated as production
   S3 keys. Preserve generated image/upload/operation IDs and record a target
   mapping/digest receipt. An actual S3 prefix/bucket belongs to the later plan.
4. Only after successful byte verification may the bulk local SQL transaction
   record confirmed upload/image metadata with matching owner/type/size. Local
   file-backed storage is an explicit test provider, not evidence of S3 or real
   public signed delivery. No success/ready flag is inferred from filenames.

The typed local image adapter, if used for application checks, implements the
reviewed ListingsImageStorage protocol only in an explicitly isolated composition.
It reads actual owned bytes; no dummy byte-size or fabricated object is accepted.
Normal production startup must never discover or enable it implicitly.

## Transaction and post-load assertions

- Revalidate inputs before opening the transaction. Set bounded lock/statement
  timeouts and UTC; lock the target Identity/listing/upload/image tables and
  require them empty. Resolve catalogue UUIDs by active code; compare expected
  conditions, category count and sensitivity flags to current schema/config.
- Insert5000synthetic user rows with valid unique claimed Handles, approved
  regular/temporary class/lifetime/status and recorded creation times. Do not
  create passwords, OTPs, Microsoft assertions, tokens, sessions, real contacts,
  private encryption keys or email/provider jobs.
- Insert1000sale listings with the original stable IDs/regular owner mapping,
  exact historical/tied creation/update times, current integer-paise fields,
  omitted/null proof distinction, category/window/state and pickup assignments.
  PostgreSQL computes search vectors; do not write an invented vector value.
- Insert1000confirmed uploads/images referencing real inspected local bytes.
  Upload/confirmation/expiry are actual load audit times, because the schema's
  attachment window must be valid at insertion; they are separate from logical
  content times/fingerprint. Do not bypass expiry/owner/image triggers.
- Force all deferred constraints before commit. Any inconsistency rolls back
  the SQL batch; retain only the newly owned local files as failed-run evidence.
  A second load refuses a nonempty target rather than upserting/resetting it.
- Verify actual counts/distributions, all FKs/regular owners, Handle uniqueness,
  absence of reference-user expiry, exactly800current discoverable listings, current sensitivity
  calculations, tied pagination, stored positional vectors and actual indexes.
  Compare safe logical row projections to the generated input fingerprint.
- Verify1000byte hashes/references plus public/owner/hidden image-authorization
  cases through the real Listings handler/service with an explicit isolated
  eligibility/caller fixture only in an isolated reproduction. The accepted
  NEXT-06 review records the actual session/media checks; this local recipe is not
  a substitute for or a fresh run of those receipts.

## Normal publication and pipeline dependency

Use a separate fresh probe database/fixture so normal app-created random IDs,
images or user state do not alter the1000listing reference snapshot. Exercise the
actual upload-intent/byte inspection/confirmation/create handlers, not bulk SQL
as a substitute for publication. Probe current queues/source state after creation.

The actual new-listing-to-vector/search check needs a prepared active pipeline.
Retain this original Step3subcheck as pending until Step4prepares the real pinned
helper/worker/pipeline; repeat the normal publication check there and return to
close this Step3obligation. Do not claim it passes merely because an intent/job
exists, copy a vector, or silently mark the whole step complete. Mohit must
verify this staged checkpoint dependency before advancing.

## Original real/cloud gate list (historical)

The2026-10-29inventory records stopped shared ECS/RDS, Hybrid/worker disabled and
remaining DNS/HTTPS/runtime/role work. It is historical, not a live check. Do not
start resources, grant roles, read secrets or load an existing database now.

Before cloud operations, prepare and separately approve the exact account/role/
region, isolated database, accepted source revision/migrations, active runtime
threshold/config, S3 bucket/prefix/IAM, upload/load/rollback route, storage/request
cost and caps, stop conditions, duration and cleanup/retention. Consume reviewed
shared resources; do not duplicate infrastructure. Recheck physical object bytes,
real owner-bound upload confirmation and authorized read for every reference,
real Identity capabilities/sessions and normal create/edit vector freshness.
Keep final cloud media/normal-workflow acceptance pending until actual checks.

No source-photo rewrite, comparison-window extension or data mutation is implied.
The benchmark cutoff is2026-12-01T00:00Z; both configurations must finish before
it. Material changes still require revalidation/rebinding; fresh temporary-user
fixtures retain their real14day lifetime outside the reference snapshot. Step4
vectors, Step5human judgments, Step6reset/reload/freeze and DATA-READY remain.

## Implemented local command

`data/generators/reference_load.py` owns real-byte materialization, guarded bulk
SQL and logical-projection checks. `scripts/evaluation/reference_local.py` owns
only a new private cluster, fixed tools, bounded lifespan and isolated real-handler
checks. Its explicit caller/eligibility and file-backed signed-object fixture is
not real Identity/S3 acceptance. `data/tests/test_reference_load.py` covers target,
media, overwrite and opt-in refusal cases without a database.

```sh
CLIP_ENVIRONMENT=test .venv/bin/python -m scripts.evaluation.reference_local --name next06-transfer-42-20261030-a --image-root /Users/mohitmahapatra/Desktop/clip-dataset-images --isolated-local-reference
```

This command is local-only. It refuses ambient AWS/DB/libpq overrides, enforces
at least2GiB free disk and a ten-minute rehearsal deadline plus bounded shutdown.
It accepts no existing target URL/socket/bucket argument. Every invocation creates
a new private target, stops only its PGDATA and retains logs/media/receipts. The
transport guard reads public server identity/version and verifies actual connection
Unix host/port; it does not grant read-all-settings or superuser privileges.

### Step4 local pipeline extension

Mohit verified the Step3 local result and authorized Step4. Add `--embeddings`
to the command above for the actual installed pinned offline helper. The new
`reference_embeddings.py` adapter uses existing operator prepare/queue/activate
and real durable workers for1000sources, refusing any missing/stale/failed parts.
Activation is local and cannot affect an external target. Six engineering search
cases verify actual Keyword/Hybrid HTTP, availability, stable unique pagination
and keyword inclusion. They are not human relevance judgments or Success@5.
The actual dispatcher processes normal HTTP creation in a separate cloned DB;
require1001current vectors and the created ID in real Hybrid results. This closes
the staged Step3 local semantic subcheck while real session/S3/cloud checks remain.
The helper has production limits plus a finite work budget, is always closed,
and baseline rows/1000vector coverage are rechecked after the probe.


### Step6 local owned-target reset

The approved Step6 increment adds `--rebuild-check` (requires `--embeddings`).
The runner prepares1000real vectors, closes its helper/connections, and drops
only the fixed DB created within this invocation's freshly owned Unix-only cluster.
It checks ownership/start/path/actual DB-login-transport identity first; no force,
if-exists, external target or source-input deletion is available. Recreate with
all29migrations, reload the same actual photo bindings, then encode again. Require
identical logical record/media/source-vector/index fingerprints; random durable
job IDs/audit times are excluded. A separate normal-flow probe still checks the
real dispatcher/new-listing vector path. Owned services stop; receipts retained.
The ordinary loader's nonempty refusal is unchanged. See the data guide for the
exact command and Step6 freeze-candidate evidence; actual cloud/final gates remain.


### Prepared cloud implementation (not live acceptance)

`reference_cloud.py` now provides offline planning and explicitly activated loading
using reviewed target JSON and a private create-only ledger. `reference_rows.py`
shares actual schema insertion/projection checks; `reference_load.py` preserves
its original local-only target guard. Cloud guards enforce the project account/
region/non-root identity, owner-bound bucket/run prefix, strict TLS DB identity,
exact migrations, restricted login and empty row/registry state. Every create-only
upload is GET/hash verified before confirmed SQLmetadata; post-upload guards and
transaction locks close target races. Existing row constraints remain active.
No resource creation/migration/grants/reset/deletion/retry route exists. Failures
retain fsynced attempted keys for separately approved operator inspection/cleanup.
See the cloud handoff and pre-cloud review package. Stubber/negative guard checks
and native shared-SQL rehearsal do not accept real cloud/Identity behavior.
