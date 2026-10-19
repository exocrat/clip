# Evaluation Evidence and Manifest Index

**Canonical path:** `docs/evaluation/README.md`

This supplied index is documentation only; no measurements have been run. Actual evidence is created by its owning task and indexed in the work log and the [foundation requirement traceability map](../architecture/foundation-traceability.md), created by PD-01.

| Evidence home | Creator / contents |
|---|---|
| `docs/evaluation/foundation/` | PD tasks: clean-checkout/local/CI/cloud-readiness/approval results |
| `docs/evaluation/domain/<task-id>/` | Domain FR/local/cloud tests and privacy-safe results |
| `docs/evaluation/nfr/<nfr-id>/<run-id>/` | SE-01/CN-01/INT-01: manifests, safe raw outputs, calculations, settings/revisions, validity and cleanup |
| `docs/evaluation/experiment/<run-id>/` | EXP tasks: approved manifest/config A/B, data/workload/route versions, warm/measured intervals, raw metrics, validity/cost/analysis and cleanup |
| `docs/evaluation/closeout/` | CLOSE-00: final regressions/revalidation/cost/resources/report/demo/package proofs |

Evaluation tool source belongs under `scripts/evaluation/`; versioned workload
profiles and reviewed labels belong under `data/evaluation/` (the current label
template is `data/evaluation/query-labels.template.json`; SE-01's reviewed set
is `data/evaluation/query-labels.json`). Each owning task registers the exact
tool command in `docs/environment/commands.md` and the profile path. Per-run manifests and
results stay in the NFR evidence home above; measured values must not be
silently substituted by a static workload profile.

PD-13 local setup run: [commands, statuses, and outputs](foundation/pd-13/README.md).

Before every measurement create a manifest with actual values: task/NFR/run ID and owner; source/build/image/frontend/migration/configuration fingerprints; target account/role/region/resources/deployed path; generator seed/counts/labels/data fingerprint; exact commands/tools/version; workload/routes/request distribution/success checks; timing boundary/clock method/warm-up/measured duration/sample/repetition/run order/cold-warm policy; offered-rate/timeout/failure/drop handling; resource/concurrency/duration/cost caps and stop thresholds; human-approved version; telemetry/evidence outputs; rollback/cleanup/retention. Unknown consequential values require a question before the run. Register the command/tool creator task explicitly.

Preserve raw and invalid/incomplete results; keep calculations/interpretation separate. Expected status alone is insufficient when response meaning is wrong. Evidence excludes tokens/private keys/full contacts/private conversation plaintext/ciphertext. Use synthetic accounts and controlled approved recipients.

Affected changes invalidate earlier evidence until rerun or a documented equivalence review proves reuse appropriate. Do not average per-run p95s and call that a pooled p95. Measure offline NFR-04 with fixed human-reviewed labels; cloud latency/recovery evidence needs the normal deployed path. Final full-project budget belongs to CLOSE-00 after experiment costs, with billing delay/estimates identified.

## Dependency substitution restriction

Manifest mode records real versus test-double dependencies and contract/runtime/data revisions. Stub/local evidence is for isolated implementation only; it cannot establish deployed NFRs or real integrated acceptance. Offline NFR-04 still requires the final dataset/labels and real ranking path under SE-01. No deferred integration obligation may disappear from final traceability.
