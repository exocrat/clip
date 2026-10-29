# Evaluation Evidence and Manifest Index

**Canonical path:** `docs/evaluation/README.md`

Past task check results are summarized in the task status and work log; they do
not establish final integrated NFR acceptance. Historical setup and domain run
receipts have been removed from the checkout and remain recoverable from Git
history. To locate an older receipt, list the evaluation files at
`f36ce3d^` with `git ls-tree -r --name-only f36ce3d^ docs/evaluation`, then read
one with `git show f36ce3d^:<path-from-repository-root>`. Historical output does
not prove current cloud state or authorize an action.
No ECS-only versus ECS+Lambda measured comparison has been run. The
[FR/NFR owner and evidence map](../architecture/foundation-traceability.md)
links requirements to their remaining checks.

The task-specific handoffs still needed by NEXT-03/NEXT-04 remain available:
[CN-01 integration](domain/conversations-integration.md),
[CN-02 offers](domain/conversations-offers.md), and the
[ID-01 demo postmortem](identity/id-01-step-12/demo-postmortem-20261026.md).
Use them as dated context; check current code, accepted revisions and live cloud
state before relying on their status. Other completed setup and branch-specific
reports were removed and remain recoverable from Git history.

| Evidence home | Creator / contents |
|---|---|
| Routine domain checks | Concise result and open gates in the owning task status/work-log entry; keep raw output only when an open acceptance gate requires it |
| `docs/evaluation/nfr/<nfr-id>/<run-id>/` | SE-01/CN-01/INT-01: manifests, safe raw outputs, calculations, settings/revisions, validity and cleanup |
| `docs/evaluation/experiment/<run-id>/` | EXP tasks: approved manifest/config A/B, data/workload/route versions, warm/measured intervals, raw metrics, validity/cost/analysis and cleanup |
| `docs/evaluation/closeout/` | CLOSE-00: final regressions/revalidation/cost/resources/report/demo/package proofs |

The early architecture experiment design is in
[`ecs-only-vs-ecs-lambda-task-list.md`](ecs-only-vs-ecs-lambda-task-list.md);
its required method is in the
[`experiment-definition guidelines`](ecs-lambda-experiment-guidelines.md).
The [reference dataset recipe](../../data/evaluation/reference-dataset-design.md)
and [NFR measurement procedures](nfr/measurement-design.md) are design inputs,
not generated data or measured results.

Evaluation tool source belongs under `scripts/evaluation/`; versioned workload
profiles and reviewed labels belong under `data/evaluation/` (the current label
template is `data/evaluation/query-labels.template.json`; SE-01's reviewed set
is `data/evaluation/query-labels.json`). Each owning task registers the exact
tool command in `docs/environment/commands.md` and the profile path. Per-run manifests and
results stay in the NFR evidence home above; measured values must not be
silently substituted by a static workload profile.

Before every measurement create a manifest with actual values: task/NFR/run ID and owner; source/build/image/frontend/migration/configuration fingerprints; target account/role/region/resources/deployed path; generator seed/counts/labels/data fingerprint; exact commands/tools/version; workload/routes/request distribution/success checks; timing boundary/clock method/warm-up/measured duration/sample/repetition/run order/cold-warm policy; offered-rate/timeout/failure/drop handling; resource/concurrency/duration/cost caps and stop thresholds; human-approved version; telemetry/evidence outputs; rollback/cleanup/retention. Unknown consequential values require a question before the run. Register the command/tool creator task explicitly.

Keep raw per-operation results for final NFR and architecture measurements, and
retain failed/incomplete results when they support an unresolved check or are
needed to interpret the outcome. For completed local setup and diagnostic checks,
a concise record of command, revision and result is usually enough; retire verbose
transcripts once no current decision or check relies on them. Git history retains
the prior files when historical detail is needed. Keep calculations separate
from interpretation. Expected status alone is insufficient when response meaning
is wrong. Evidence excludes tokens/private keys/full contacts/private conversation
plaintext/ciphertext. Use synthetic accounts and controlled approved recipients.

Affected changes invalidate earlier evidence until rerun or a documented equivalence review proves reuse appropriate. Do not average per-run p95s and call that a pooled p95. Measure offline NFR-04 with fixed human-reviewed labels; cloud latency/recovery evidence needs the normal deployed path. Final full-project budget belongs to CLOSE-00 after experiment costs, with billing delay/estimates identified.

## Dependency substitution restriction

Manifest mode records real versus test-double dependencies and contract/runtime/data revisions. Stub/local evidence is for isolated implementation only; it cannot establish deployed NFRs or real integrated acceptance. Offline NFR-04 still requires the final dataset/labels and real ranking path under SE-01. No deferred integration obligation may disappear from final traceability.
