# Listings private embedding helper boundary — protocol 1

**Origin:** SE-01 hybrid amendment, real-helper integration checkpoint after native
bootstrap/switch verification. **Status:** private helper and local HTTP/browser checks verified; normal API
opt-in read lifecycle is now implemented and checked, awaiting result verification.
No database job runner or production deployment is enabled. Public mode/sort
registration is implemented; default normal API Hybrid capability stays disabled.

## Ownership and files

- `embedding_protocol.py`: Python3.13/3.14-compatible stdlib JSON-lines framing,
  UUID/text checks, complete token-window ranges and strict offset validation.
- `embedding_helper.py`: fixed owned offline CPU executable. Verifies local model/
  tokenizer SHA-256 and exact runtime pins, uses only CPUExecutionProvider with
  one inference thread, and supplies normalized 384-float vectors.
- `embedding_client.py`: API-side async lifecycle owner; imports no ML packages,
  opens no database and discovers no ambient targets. Only explicit construction/
  start can launch the fixed sibling script with the supplied local interpreter
  and model directory. No fake-helper/environment switch or alternate script input.
- `embedding_types.py`: shared strict private vector validation, used for query
  output and complete listing parts; vectors/source are hidden from result repr.

One controller owns one child per API process. A process-wide lock rejects a
second owner until clean close, including startup/restart. Construct clients after
worker-process creation; inherited controllers refuse to signal a parent's helper.
`app.main` now creates a controller only through the explicitly enabled
Listings-owned [lifecycle context](normal-api-search-runtime.md); routes never
construct one. Explicit interpreter invocation
preserves its venv path: resolving that executable's symlink would bypass
`pyvenv.cfg` and its isolated dependencies. Root API remains Python3.14; this Mac
helper uses existing repository-local Python3.13/model artifacts.

The child receives isolated `-I -B` imports, a fixed code-directory import path,
minimal PATH/offline/thread variables and no inherited HOME/provider/token/DB
configuration. It uses local `Tokenizer.from_file`/ONNX files, never Hub loading
or remote code. Python audit hooks reject network connect/bind and child creation;
they are not an OS sandbox. Vendor stderr is discarded; stdout is protocol only.

## Frames and handshake

Each frame is one UTF-8 JSON object plus newline. Input <=64KiB, output <=2MiB.
Duplicate keys, malformed UTF-8/JSON, nonfinite JSON constants, extra/unexpected
fields or mismatched bindings are rejected. User text is JSON data, never code.
All IDs below are private correlation values, not authorization.

The ready frame has exactly:
`v`, `kind`, `pipeline_id`, `pid`, `python_minor`, `runtime`, `threads`, `offline`,
`peak_rss_bytes`. Require v1, kind ready, actual owned PID, expected pipeline hash,
Python minor3.13, exact NumPy/ONNX/tokenizers pins, one thread and offline true.
Artifact/runtime/pipeline mismatch never selects a substitute model. Resource
metadata must be a nonnegative integer below512MiB; combined application/helper
memory is separately measured in the local probe and remains a deployment gate.

## Requests

Common exact fields: `v`, new canonical UUIDv4 `request_id`, expected 64-hex
`pipeline_id`, `operation`.

| Operation | Additional fields | Bounds |
|---|---|---|
| query | `text` | Nonblank, <=120 code points; <=254 content tokens at inference |
| listing | `title`, `description` | Nonblank, <=120/5,000 code points; title one window, description <=96 windows |

No owner/listing/generation IDs, authentication values, contacts, source hash, DB
URL, model URL, arbitrary path or log instruction is sent. The caller retains
its trusted DB work receipt/fences. Preserve stored source text exactly; do not
silently trim/change it after fingerprinting. Caller authorization and approved
source retrieval remain owning-service responsibilities.

## Progress and results

Progress exact fields: `v`, kind progress, bound `request_id`/`pipeline_id`,
`part_kind`, `ordinal`, `peak_rss_bytes`. Query emits query/0 once. Listing emits
title/0 then contiguous description ordinals. Each progress starts a separate
inference read deadline; count is bounded to1 query or97 listing windows.

Result exact fields: `v`, kind result, bound IDs, `operation`, `parts`,
`title_tokens`, `description_tokens`, `query_tokens`, `ranges`, `peak_rss_bytes`.
Each part has only `kind`, integer `ordinal`, 384 finite normalized numeric
`vector` values. Booleans/NaN/infinity/zero/wrong norm or size are invalid.

Query returns one query/0 vector, typed0–254 query tokens, one `[0,count]` range,
and null title/description counts. Listing returns one title/0 vector, full
contiguous description parts and null query count. Description windows hold254
content tokens plus CLS/SEP with32-token overlap. Zero normalized content tokens
still produce one empty-content window. Root validates exact typed ranges for
all reported tokens and verifies progress/part/window counts before returning.
Overflow fails explicitly; no final window is dropped. Typed result objects
expose only private vectors/token metadata, never source text.

The CPU encoder mean-pools the all-one attention mask (including CLS/SEP), then
L2-normalizes. No padding or mixed batch exists in this protocol. It performs no
matching/ranking, vocabulary expansion, thresholding, filtering or SQL reads.
Those are separate integration stages; controlled vector comparisons are not
human relevance labels.

## Failures, deadlines and recovery

Fixed error frames contain `v`, kind error, bound IDs and code from timeout,
helper_unavailable or invalid_vectors. Startup/invalid-request fatal frames carry
only `v`, kind fatal and a fixed code. No raw exception, traceback, text or vector
is forwarded in a diagnostic. Parent maps timeouts/crashes/invalid output into
`HelperUnavailable.failure_code` using those same safe persistence codes;
`HelperBusy` remains separately distinguishable for future worker deferral.
Public `503`/error-envelope binding is still unimplemented.

- Explicit prewarm/start has30s maximum. A lazy start inside a request is also
  limited by that request's remaining20s budget.
- One request holds the exchange lock, with at most eight waiting requests;
  overflow fails immediately. Work deadline20s includes queue/startup/encoding.
- Each inference/read window has5s maximum; total progress cannot extend the
  overall deadline. Configured limits may be shortened, never exceed these caps.
- Timeout, invalid frame/result, crash or active cancellation kills/reaps only
  the owned child, discards that stream and never replays the failed request.
  Waiting cancellation does not kill somebody else's active request.
- Reaping has a separate <=5s cleanup allowance. A failed/uncertain reap latches
  the client unusable and prevents additional children. Cancellation during spawn
  retains ownership; an eventual late child is killed rather than untracked.
- A subsequent new request may restart/re-handshake after a bounded1s cooldown.
  It cannot overlap the old child. Close rejects queued/new work, interrupts its
  active child and releases process ownership only after clean reaping.

These are helper-request deadlines. The future DB generation orchestrator must
still enforce its overall20s claim-to-compute budget, lease/cancellation/failure
protocol and publication fencing; this increment starts no automatic worker and
performs no DB writes.

## Checks and real probe

`test_embedding_client.py` / owned `doubles/embedding_helper.py` inject protocol/
process faults only: incorrect handshake/IDs, malformed/duplicate/oversized JSON,
extra/private fields, invalid coverage/vector, timeout, queue overflow, waiting/
active/startup/spawn cancellation, close, crash/restart and competing owners.
The double supplies coordinate vectors, never model/relevance evidence.

`scripts/evaluation/semantic/ipc_probe.py` separately runs the actual pinned model
through real pipes, <=30 windows/10min, with an independent sampled512MiB combined
probe-host/helper/declared preview API watchdog. It checks controlled matching,
full long-description windows, concurrent serialization, exact repeatability,
owned-child SIGKILL/restart and absence of leftover helpers. The watchdog reads
only declared PIDs/PPIDs/RSS, not process arguments/environment. No database/cloud
access, dependency install, model download or public route is involved.

The historical result and source fingerprints identify the exact local probe;
see the [evaluation retrieval guidance](../evaluation/README.md). The initial
real startup exposed
the interpreter-symlink bug, fixed with a launch regression. Python3.13 compile
also caught Black's3.14-only multi-except syntax; shared/helper exception handling
now remains3.13-compatible without changing root formatter settings.

Local matching, memory and pipe timings are not deployed p95/concurrency,
Linux/cgroup/production support, final Success@5 or human-label acceptance.

## DB orchestration follow-up

The [private one-job bridge](semantic-embedding-worker.md) now combines the real
client with the Listings job store and overall20s budget. It borrows this client,
uses committed source receipts, defers full-queue work, records fixed failures
and leaves cancellation reclaimable. Real disposable SQL/model integration is
recorded separately; no app startup, background dispatcher or HTTP activation is
introduced. Helper request limits above remain independently enforced.


## Subsequent isolated HTTP/model lifecycle checkpoint

The test-only native Search harness now explicitly owns helper/pool/watchdog/
shutdown and invokes the actual collection service. It creates its own empty
native Unix-socket database and synthetic sources, publishes every generation
through EmbeddingWorker, then marks serving. The real application entry point
still never constructs this helper. One helper/100windows/30min and sampled512MiB
API/helper watchdog apply; native PG/Vite memory is separate. Headless closing/
503/keyword-independence/cleanup pass; browser and production lifecycle/platform/
actual upstream integration remain separately pending. No fake model is used.


The subsequent normal API lifecycle checkpoint supersedes the earlier statement
that the real entry point never constructs a helper: it can now do so only with
explicit/default-off settings. Existing pins/framing/capacity/deadlines remain;
no inference worker, automatic bootstrap or deployment is activated.


A subsequent separately enabled/default-off dispatcher now borrows the same
helper, adding no model process. It is cancelled/awaited before helper close.
The helper protocol/queue/deadlines do not change; automatic bootstrap/backfill
and deployment remain inactive. See [dispatcher contract](semantic-embedding-dispatcher.md).

The Step10 quality correction annotates helper functions and chunk ranges and
checks them using the dedicated Python3.13 dependency environment. The exact
no-install command and narrowly scoped untyped ONNX import are recorded in the
[command registry](../environment/commands.md#se-01-isolated-semantic-helper-typing-correction).
It leaves protocol frames, pins, pooling, deadlines and model math unchanged.
