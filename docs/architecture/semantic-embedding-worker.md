# Private Listings embedding job bridge

SE-01 hybrid amendment checkpoint4 follow-up. `embedding_worker.py` connects the
reviewed [storage protocol](semantic-listing-storage.md) to the
[real helper client](semantic-helper-protocol.md). It is explicitly invoked and
has no polling loop, DB discovery, application startup or public route binding.
Constructing it performs no work. No new installation or migration is required.

## One-job operation

`EmbeddingWorker.run_one()` takes a process-wide nonwaiting worker slot, checks
an injected dedicated connection is autocommit/idle, and claims **one** due job
for its helper's exact pipeline/configuration. Other model spaces are untouched.
`EmbeddingStore.claim(spec)` retains unfiltered operation only for existing
explicit native maintenance checks. The worker always passes the helper spec.

Claim commits before source text goes to the shared helper. The worker neither
holds a transaction during inference nor creates a second helper, closes a
borrowed helper, registers/enables a pipeline, reconciles/backfills a corpus or
changes model state. Sources/vectors never enter worker results or diagnostic
messages. The real store refuses unsafe transaction nesting without committing
or rolling back the caller's work.

The work deadline is **20 seconds**, covering claim, helper queue/start/compute,
validation and publication. It may only be shortened. Cancellation of an active
helper request retains its separately bounded <=5-second kill/reap allowance;
async deadlines are cooperative, not an OS scheduling guarantee. Failure/deferral
recording has a separate <=3-second deadline. Each claim/complete/fail/defer
transaction uses local PostgreSQL statement_timeout3s and lock_timeout1s, restored
on commit/rollback. No lease heartbeat extends the server's30-second lease.
Server-side unexpired-token/generation/source/config/retirement checks still
control publication independently of local time or helper success.

Every output must have all canonical description ranges, valid unit vectors,
one title and contiguous complete description parts. Publication uses the existing
atomic transaction/deferred completeness constraints. A changed-away-and-back
source cannot publish an old generation; a price-only edit can preserve work.
Retirement removes the generation and rejects any in-flight publication.

## Outcomes and recovery

| Outcome | Meaning |
|---|---|
| `idle` | No due job in this helper's supported pipeline. |
| `published` | Real store confirmed atomic ready publication. |
| `stale` | Source/generation/lease/retirement changed; no replacement job altered. |
| `deferred` | Helper capacity was full; owned lease released,5s delay, claim attempt refunded. |
| `failure_recorded` | Fixed timeout/helper_unavailable/invalid_vectors recorded; existing bounded retry policy applies. |

`WorkerBusy` refuses overlapping worker invocations without queuing or DB work.
`WorkerUnavailable` contains only a fixed message when persistence is uncertain;
there is no immediate replay, raw driver text or fake success. On external
cancellation the task propagates cancellation, starts no background writes, and
leaves any committed lease reclaimable after expiry. On helper failure it records
only the matching source/generation/token. On a capacity race `defer` uses those
same fences, clears the lease, decrements the just-consumed attempt once and
retains no fake model failure. Repeating it against that receipt cannot refund
another attempt. Existing retry ceiling/backoff and explicit retry remain intact.

`JobStore` and `ListingEncoder` document the private injected interfaces; tests
script these operation receipts only. Test-only fault helpers have no production
selection flag. The production encoder implementation is `SemanticHelper`.

## Evidence and pending gates

Unit tests cover concurrency, deadlines, safe errors, wrong pipeline/output,
capacity and cancellation. Disposable native tests exercise actual SQL with fault
pipes, then the separately opted-in actual model: full903-token description/four
chunks, exact persisted vectors, no held claim lock/transaction, real owned-helper
crash and fresh-request recovery, ABA rejection, price-only changes and retirement.
The model probe is bounded to30 windows, ten minutes, one worker/one live helper
and512MiB sampled host/helper RSS. It uses fixed existing local model/interpreter
paths and guarded owner-private Unix-socket test databases only.

[Retained scoped result](../evaluation/domain/se-01/worker-bridge/result.json).
The first run skipped the model opt-in because the API isolation fixture clears
CLIP_ variables. A test-only LISTINGS_TEST_ name fixed that without weakening the
fixture. The next run exposed fixture-only lease-expiry SQL touching an unleased
second pipeline and a non-whole-rupee price; both inputs were corrected while
keeping production constraints. Earlier runs remain retained separately.

This does not accept a deployed worker dispatcher, bootstrap/backfill, Linux/
resource support, real Identity integration, public mode/sort/coverage/fusion,
final dataset/labels, Success@5, FR/NFR or SE-CORE/DATA-READY. No shared/existing DB,
cloud, hosting, global interpreter or dependency changes occur in this checkpoint.


## Subsequent bounded dispatcher checkpoint

The one-job bridge remains unchanged. The normal lifecycle can now explicitly
own a separate default-off dispatcher, sharing the helper with one dedicated
idle-autocommit worker connection. It processes only due existing jobs; no
register/backfill/serving switch. [Scheduling/cleanup and native edit-to-reindex
checks](semantic-embedding-dispatcher.md) describe this subsequent layer. Durable
retry, source/lease/retirement fencing and cancellation receipts remain here.
