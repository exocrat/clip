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
| [Step13 live preparation](id-01-step-13/README.md) | Verified native AMD64 image, successful23-migration bootstrap, hosted human auth/email/HTTPS checks, retention tick and cleanup evidence. |
| [Step14 permission matrix](id-01-step-14/README.md) |47business API operations, source-bound evidence, reconciled merged providers and user-reported owner acceptance with exact revision/runtime gaps; no Step14 test run yet. |
| [Live work log](../../status/work-log.md) | Verification state, exact dated outcomes, ownership and pending integration ledger. |

## Current state

- On2026-10-28 13:47:50UTC the approved corrected live bootstrap passed: all23
  migrations/head20261027112205,40tables/36functions/46triggers, explicit runtime
  grants, preserved roles and existing-password TLS logins before/after. Approved
  old database records discarded; credentials/SSM/S3 preserved.
  [Success and cleanup receipt](id-01-step-13/bootstrap-retry-result.json).
  Hosted HTTPS/actual-provider/human auth/contact/browser checks and the first
  automatic retention run and resource cleanup now pass; Step13 human verification is recorded;
  remaining source review/publication is tracked in
  [the Step13 review](id-01-step-13/closeout-review.json).

- Accepted main `5e8d264` includes Identity PR14/16 and Conversations PR17/18.
  Our branch `task/id-01-runtime-preparation` merged that exact tree at479a09c.
  PR16's hosted quality gate passed; its publication is no longer pending.
- Real local Microsoft/IISc, temporary email registration/sign-in/reset and the
  Firefox origin correction are human-verified. The new Identity/Conversations
  session/contact paths have actual local SQL/HTTP checks with controlled
  external signer/mail/storage boundaries; they do not prove deployed delivery.
- Step12's current migration candidate pins23unchanged accepted SQL files through
  20261027112205and40tables/36functions/46triggers. New runner/manifest changes
  are human-verified and committed at39bfb4b; source binding passes. New source
  review/CI/merge remain. The original candidate retains its historical pending
  flags; the separately approved Step13 execution manifest/receipt records the
  actual23-file bootstrap. The earlier17-file apply is historical evidence.
- Local preparation checks pass at2026-10-27 18:33:45UTC:12aggregate gates,
  1932Python/153skips,94data,433web/3skips, Conversations167 and focused32.
  At2026-10-27 19:17:44UTC the separate source-binding audit passes9/9checks
  against39bfb4b, with12regressions passed; ready_for_live remains false.
- At2026-10-27 18:25:58UTC Aditya confirmed exposed Resend-key revocation and
  replacement in SSM. The provider key was not read or delivery-tested after that confirmation.
  SES production access is not a blocker to approved Resend active-provider use.
- Step13 read-only catalog inspection confirms the17-version prefix with37tables/
  33functions/43triggers; no app rows or DDL. Exact clean bootstrap/grants remain
  separately gated. Native AMD64 image from2b292ad is verified/published after
  the build-only heap correction; no C7i fallback was needed. [Live receipt](id-01-step-13/preflight-and-proposal.json).
- Fresh cleanup2026-10-28 09:04:45UTC: owned host terminated, ASG/API counts0,
  private protected RDS stopped, owned scheduled fallback/tunnel removed. API
  service remains revision4/disabled; the new image is not deployed. DNS
  propagation is not rechecked.
- ID-READY is **not accepted**. Remaining real acceptance is Step13's approved
  HTTPS/runtime/provider/browser and operational retention checks, plus the final
  Step12 reviewed/merged handoff. Full image/Search/Hybrid/Conversations feature
  acceptance and Step14's exhaustive consumer matrix are separate obligations.

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
