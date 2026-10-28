# Isolated semantic-inference feasibility probe

SE-01 hybrid checkpoint 4. These tools prepare and measure a CPU model on this
Mac; they do not install into the API environment, activate HTTP search, implement
production helper IPC or create evaluation relevance labels. The
[feasibility plan](../../../docs/architecture/semantic-search-feasibility.md)
records limits, actual results, failed runs and pending native/Linux/production gates.

## Files and behavior

- `requirements.in`: three reviewed direct CPU-helper candidates.
- `requirements-macos-arm64.txt`: 24 fully pinned transitive packages with hashes,
  generated with uv for Python 3.13/macOS ARM64. It is not a Linux lock or security
  support assertion; the runtime/package support must be revisited before release.
- `model-manifest.json`: exact upstream revision, checked sizes/SHA-256 for seven
  model/tokenizer/config/card files; no weights or third-party code committed.
- `preflight.py`: metadata-only compatible-wheel selection, size bound, reported
  PyPI advisories and license metadata. Fixed public sources and fixed local
  output `.tools/semantic/preflight.json`; no credential lookup or inference.
- `fetch.py`: downloads those preflight-bound wheel/model artifacts to the ignored
  tree, verifies size and SHA-256 (small model metadata also bound to Git blob),
  reuses only matching files, and rejects mismatches or budget overflow. A failed
  partial remains for diagnosis; no arbitrary cleanup or unverified reuse.
- `probe.py`: offline real ONNX CPU inference; single thread/batch, explicit
  attention-mask mean pooling/L2 normalization, complete bounded token windows,
  repeat/padding checks and synthetic controlled matching examples. Blocks Python
  network/child-process audit events, emits only phase timings and safe metrics.
- `supervise.py`: starts only the local helper child with a minimal environment,
  reads its/identified preview-API RSS using `ps`, checks phase/overall deadlines,
  enforces the 512 MiB aggregate ceiling, and kills only its own child on failure.
  Every supervised run retains logs/metrics under `.tools/semantic/probes/`.
- `tests/evaluation/test_semantic_probe.py`: root-environment portable chunk,
  overflow, fixture-size and artifact-integrity regression checks. No ML imports.

Model execution reads verified local files; Hub/tokenizer download methods are
never used. Neither Python audit hooks nor metadata advisory queries constitute
an OS security boundary or comprehensive security audit. Run only these fixed,
reviewed artifacts and synthetic probe inputs. The hard stop watchdog is separate
from model execution and remains active during imports/inference.

## Reproduce within the verified local probe scope

Use the existing repository-local uv/root Python and fixed artifact tree. This
procedure documents the completed bounded Mac feasibility probe; it is not an
NFR or release workflow. Use the current task and approved measurement design
before planning any new run. No system installer, global executable link, shell
activation or project Python change is needed. The original local run used
Python 3.13.12 from uv's
20260211 managed build with `--no-bin`; that older probe pin is not the deployment
patch selection.

1. Create `.tools/semantic/` and copy the committed helper lock to
   `.tools/semantic/resolved-mac.txt`. Do not silently re-resolve newer packages.
2. Run `preflight.py`; verify target/artifact sizes/advisories/license terms. Stop
   on any missing wheel, advisory, binding failure or budget overflow.
3. Install the fixed helper Python with explicit local paths and `--no-bin`, create
   its separate venv, run `fetch.py`, then sync packages offline with required
   hashes and only the verified local wheels.
4. Identify the existing isolated preview API process; pass that PID explicitly
   to `supervise.py`. No process is guessed from an arbitrary default. This Mac
   sandbox requires process-read approval for `ps`. No command signals that API.
5. Inspect the unique retained run's `result.json`/`supervisor.json`, keep tooling
   failures, and copy only safe metrics to the existing SE-01 evidence directory.
   Root interpreter/lock must still match the pre-probe values.

The approved envelope is 300 MiB downloaded artifacts, 1 GiB added disk, 30
inference calls/queries, ten-minute probe duration, 30-second startup/preparation,
five-second individual inference and 512 MiB combined local helper/API resident
memory. The actual run used 14 calls, about 147 MiB artifact bytes and 528 MiB
on disk. No final data, human labels, HTTP latency or cloud acceptance follows.

## Real IPC follow-up

`ipc_probe.py` uses the API3.14 private client and actual helper3.13 model via
owned local pipes. Unlike the original single-process arithmetic/model probe,
it tests process handshake, serialization, repeated output and child crash/restart.
The supervisor requires an explicit opt-in and identified preview PID; it never
guesses which API process to inspect. Its watchdog samples the probe
host/helper/preview API RSS within512MiB and stops only owned helpers. No
DB/worker/public route is created. See the
[protocol](../../../docs/architecture/semantic-helper-protocol.md) and current
[evaluation task](../../../docs/evaluation/README.md) before planning further work.

## Development calibration follow-up

`calibration.py` validates separate synthetic development fixtures, measures
actual English/expanded FTS and native cosine through the real local helper in
the explicitly opted-in disposable native test, then compares90predeclared
aggregation/threshold/fusion/cap settings. Its CLI only reanalyzes a captured,
strictly bound matrix. It does not implement production ranking or use final
labels. Eight listings/eleven queries use exactly30model windows in the retained
run; one helper,10min and512MiB host/helper bounds apply. A preserved failure
shows that full long-source coverage does not ensure semantic relevance.
[Proposal and limits](../../../docs/architecture/hybrid-search-calibration.md).
This development calibration is distinct from the approved NEXT-01 comparison
and later NEXT-07 measurement runs.
