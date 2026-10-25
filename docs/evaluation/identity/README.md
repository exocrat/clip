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
| [Live work log](../../status/work-log.md) | Verification state, exact dated outcomes, ownership and pending integration ledger. |

## Current state

- Local Identity schema/services/API/UI are implemented and human-verified.
- Main/PR10 reconciliation is committed as `890adb1`; checkpoint `7a9b4a4`
  contains dual-provider email preparation. Latest local composition gate:976Python passed,
  one DB-only skip covered separately,63data and118web passed; all11gates passed.
- Resend `verify@clip-iisc.site` delivered to Gmail and IISc, human-confirmed.
  SES sandbox task-role delivery and owned cleanup passed; production access is
  pending. No new current cloud state is inferred from historical snapshots.
- Explicit local API composition is verified and committed at `fad1e2f`;
  [result/remaining work](integration.md#local-api-composition).
- [Secure runtime preparation](integration.md#secure-runtime-preparation) is locally
  implemented and human-verified; live secrets/grants are pending.
- Normal application composition still lacks real Identity runtime wiring.
  Microsoft sign-in is disabled. ID-READY is not accepted; no final FR03 claim.

- Real RDS logging/default probe passed with rollback and stopped/zero cleanup
  verified on2026-10-25; [live evidence](integration.md#live-logging-probe-passed--2026-10-25-053326-utc).
  Shared migration apply and Identity login/URL provisioning remain pending.

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
