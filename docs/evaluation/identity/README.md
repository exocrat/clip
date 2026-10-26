# ID-01 evidence and handoff

Owner: Aditya(A). Scope: ID-READY; ID-01 remains in progress.
Consolidated2026-10-24 from the reports at `890adb1`; decisions, acceptance
criteria and action approvals still come from their canonical sources.

| Read | Contents |
| --- | --- |
| [Cross-owner review](cross-owner-review.md) | What changed, why, affected paths, pending integration and checks for Suraj/Rahul/Mohit. |
| [Implementation](implementation.md) | Steps3–11 behavior, checks, corrections and source snapshots. |
| [Provider history](provider-history.md) | Completed SES/builder/runtime investigation, delivery outcomes and development cleanup gate. |
| [Integration handoff](integration.md) | Current Step12 result, email routing and remaining work for ID-READY. |
| [Hosted demo postmortem](id-01-step-12/demo-postmortem-20261026.md) | What worked/failed in the local and hosted demo, stale IISc DNS, cleanup results, and remaining shared resources. |
| [Live work log](../../status/work-log.md) | Verification state, exact dated outcomes, ownership and pending integration ledger. |

## Current state

- PR #14's local Identity/marketplace hardening is merged at main `3d6c270`;
  runtime follow-up is on `task/id-01-runtime-preparation`, integrating accepted
  main `d7afc8b` (PR #15). It includes runtime preparation, cleanup/state evidence
  and the locally human-verified Firefox origin fix. New source still needs its
  own peer/affected-owner review and current CI.
- Real local Microsoft/IISc and temporary email registration/sign-in/reset were
  human-verified. No human hosted account/image/Search journey was accepted.
- The original shared DB's17migrations and separate runtime roles/secure URLs have
  [recorded real results](id-01-step-12/demo-postmortem-20261026.md#database-preparation).
  Reusable migration defaults require fresh approval for another live window.
- AMD64 build switch, scoped runtime IAM and private S3 configuration are useful
  retained work. ECS runtime is opt-in with a private controlled-recipient input;
  no personal recipient or default auth bypass is retained.
- [Read-only cleanup verification](id-01-step-12/cleanup-verification-20261026T180723Z.json)
  at18:09UTC confirms RDS stopped, compute0and temporary ingress absent. Aditya
  later reports apex A removal; propagation is deliberately not rechecked.
  [Refresh-only service reconciliation](id-01-step-12/ecs-state-reconciliation-result-20261026T182852Z.json)
  is applied/verified: state serial18and live service both revision2, capacity0.
  No infrastructure changes or restarts were performed.
- ID-READY is **not accepted**. Durable HTTPS/proxy/runtime/provider checks and
  actual image/Search/browser integration remain; Hybrid needs its separate
  privileges/model/pipeline setup. Full Step14 stays outside this milestone.

Branch cleanup verification2026-10-26 14:02:52UTC: all11local gates passed
(1830Python/24optional skips,94data,289web/3opt-in skips), plus backend-free
Terraform4roots and offline review consistency. [Disposition and limits](id-01-step-12/demo-postmortem-20261026.md#what-belongs-in-the-branch).

## Canonical sources

[Task and acceptance checks](../../tasks/domain-task-list.md#id-01--implement-identity-eligibility-and-temporary-accounts),
[task index](../../tasks/project-task-index.md), [Identity contract](../../../contracts/identity.md),
[provider setup](../../environment/identity-provider-setup.md),
[secret references](../../environment/secret-handling.md),
[email routing decision](../../decisions/identity-email-routing.md),
[stub/integration gates](../../architecture/stubs-and-integration-gates.md).
Other Identity decisions stay under docs/decisions; this summary does not replace them.

## Evidence retention

JSON hashes/manifests, proposed policy/task/build inputs and the two offline-tested
diagnostic scripts remain at their original paths. They are historical evidence,
not current executable approval. Old hashes identify old source revisions and need
not match current code. Private recipient/key/OTP values are not part of evidence.

The44superseded narrative reports were combined here. Their exact contents remain
in Git at the archived revision; [archive-map.json](archive-map.json) records each
original path, SHA256, Git blob and replacement section. For exact old plan text:

```bash
git show 890adb1:docs/evaluation/identity/id-01-step-2/runtime-run-approval.md
```

Old approvals, prices and caps must not be reused for new cloud/provider work.

## Autonomous local preparation — 2026-10-25 11:48:05 UTC

Separate worktree `/tmp/clip-id-ready-local-hardening`, branch
`task/id-ready-local-hardening`, starts from85c4606; original worktree unchanged.
Offline review-consistency command committed17457d9; explicit real local runtime
command prepared/tested without live bootstrap. Full local gate passed all11checks:
1074Python/1existing DB-only skip,63data,118web; Black158files, actual PostgreSQL18.6
lifecycle and Gitleaks.

[Runtime preparation and concrete image CA finding](integration.md#explicit-local-runtime-preparation-and-image-trust-finding--2026-10-25-114606-utc):
the cached AMD64 base system store contains none of the3regional RDS roots.
Shared Dockerfile correction needs writer coordination/review; live setup and
updated-main integration remain pending. No ID-READY acceptance or deployment.

## Accepted main integrated — 2026-10-25 17:09:30 UTC

Latest implementation `42e9cd9` on `task/id-ready-local-hardening` contains accepted
main `6c86060` and both autonomous local commits. Combined17migrations through
20261025013000 checked:37tables/33functions/43triggers. Full11gates passed:
1791Python/21skip,94data,223web/2skip; separate real store21pass/3optional skips.
[Current merge paths/evidence and pending gates](integration.md#accepted-main-integration--2026-10-25-170710-utc).
Cross-owner and migration candidate metadata now reference the merged source;
review/image/live flags remain pending. Original worktree unchanged; no push.

## Local image trust fix — 2026-10-25 18:00:39 UTC

Ordinary native ARM64 image now installs pinned regional RDS roots and selects
the actual OS CA file for bundled libpq. Four actual-image checks and17runner
regressions passed; all11aggregate gates passed (1792Python/24skip,94data,
223web/2skip). [Evidence/limits](id-01-step-12/image-trust-local.json) and
[implementation result](integration.md#rds-image-trust-correction--2026-10-25-180039-utc).
AMD64/Hybrid and live TLS/peer/provider/browser/retention gates remain pending.

## Shared browser transport — 2026-10-25 19:00:23 UTC

Local Listings/Search CSRF headers and normal Identity /api routing are integrated
through one shared technical helper. Full11gates passed:1800Python/24skip,
94data,257web/3skip. Real TS/HTTP/SQL writes/denials passed with synthetic upstream
ports; no actual browser/device/provider acceptance. [Result](integration.md#shared-browser-transport-result--2026-10-25-190023-utc)
and [exact source/check evidence](id-01-step-12/browser-transport-local.json).
Aditya verified this local result. Affected-owner review and current deployed/
runtime/image gates remain.


## PR #14 merged — shared runtime pending

Aditya confirms Suraj reviewed/merged PR #14; main is `3d6c270`.
[Post-merge shared runtime plan](integration.md#post-merge-shared-runtime-plan)
records the remaining schema/credentials/IAM/image/HTTPS and real-runtime gates.
This merged implementation is not ID-READY acceptance. Authentication uses
Microsoft or email OTP; there is no SMS/phone-number verification.
