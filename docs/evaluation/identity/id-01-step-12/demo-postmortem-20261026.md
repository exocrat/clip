# ID-01 demo outcome and retained deployment handoff — 2026-10-26

Owner: Aditya(A). Source branch: `task/id-01-runtime-readiness`, based on
main `3d6c270`; last committed preparation `1bb0eb9`. This handoff consolidates
the local retrospective and emergency hosted demo notes. **ID-READY remains
incomplete.** Cloud facts include the read-only follow-up (historical receipt: `cleanup-verification-20261026T180723Z.json`) at2026-10-26 18:09:02UTC; older demo outcomes remain historical.

Exact JSON receipts cited below are preserved in the parent of cleanup commit `f36ce3d`; retrieve one with `git show `f36ce3d^:docs/evaluation/identity/id-01-step-12/<filename>`. They record past actions and state only; NEXT-04 must refresh current cloud state.

## Local demo outcome

Aditya verified real IISc Microsoft sign-in and non-IISc denial, plus Gmail
registration, temporary sign-in and forgotten-password delivery. The local demo
used disposable PostgreSQL and real Identity providers. Photo upload failed because
that launcher did not configure S3; it was not an S3 provider failure.

A temporary local no-photo path had 17 API/19 web focused tests but no human
browser acceptance. It was removed after the demo. No such flag, route, trigger
override or related test remains in source; the normal one-to-eight-image rule
is unchanged. Its temporary test results do not validate current image upload.
Local S3 support would separately need explicit adapter settings, narrowly scoped
short-lived credentials/prefix and reviewed localhost CORS, then real upload/
confirm/display/cleanup checks. No local S3 success is claimed.

## Database preparation

The original t4g.micro start initially hit capacity errors. Alternate-zone micro
restore hit capacity, small hit Free-plan restrictions, and t3.micro hit the account
instance quota. No replacement database was created and the account was not
upgraded. The original later started successfully. Keep these executed results,
rather than the expired planning requests:

- Original capacity failure (historical receipt: `shared-database-preflight-20261026T071912Z.json`).
- Micro restore rejection (historical receipt: `database-recovery-apply-20261026T073215Z.json`),
  small restriction (historical receipt: `database-recovery-small-apply-20261026T073928Z.json`),
  t3 quota rejection (historical receipt: `database-recovery-t3-apply-20261026T075358Z.json`).
- Original RDS start (historical receipt: `database-original-rds-start-20261026T090330Z.json`),
  real schema preflight (historical receipt: `shared-database-preflight-result-20261026T095424Z.json`),
  logging/session follow-up (historical receipt: `shared-database-followup-result-20261026T100459Z.json`).

The approved strict runner then applied all 17 migrations to original `clip_test`,
head `20261025013000`, with 37 tables/33 functions/43 triggers verified. Separate
Identity and marketplace logins/URLs were provisioned and checked:

- Migration result (historical receipt: `shared-migration-apply-result-20261026T102702Z.json`).
- Identity role/URL (historical receipt: `identity-runtime-role-result-20261026T103522Z.json`).
- Marketplace role/URL and precise privileges (historical receipt: `marketplace-runtime-role-result-20261026T104412Z.json`).

The marketplace role covers the reviewed Listings/Wanted/Saved operations but
has **no Hybrid embedding-table privileges**. Hybrid/pipeline/model/worker setup
still requires the Search owner's review. Keep Identity's private-table role
separate; do not reuse the isolated Listings database-owner bootstrap.

The exact applied manifest is archived byte-for-byte (historical receipt: `shared-migration-manifest-applied-20261026T102702Z.json`)
for checksum provenance, with a separate completed-run review receipt (historical receipt: `shared-migration-apply-review-executed-20261026T102702Z.json`). The canonical reusable manifest is reset to its unreviewed,
not-authorized state. The completed window's approval is consumed; the archive is
historical evidence and is not permission for a new live run.

## Hosted demo outcome

An AMD64 image with Microsoft sign-in enabled was published at digest
`sha256:50de5b7d8f27ca41c89b9617d8fc1d53e267110481648468c7cf48bb49c3f881`.
Health and bundled web-root smoke checks passed. The approved Terraform operation
retained scoped task IAM, the private ID-01 image bucket and API task revision2,
but AWS rejected load-balancer creation account-wide. See
deployment/partial-apply evidence (historical receipt: `demo-deploy-attempt-20261026T111441Z.json`).

A separately approved temporary EC2/Caddy HTTPS proxy and task revision3 served
the app after a forwarded-protocol correction. Public resolvers returned
`65.0.49.162`, while Aditya's IISc resolver returned stale `43.205.193.65`.
A direct HTTPS check to the intended IP succeeded. These observations are
consistent with stale IISc DNS; they do not validate the complete application.
No human hosted sign-in, listing publication/photo upload or Search journey
was accepted. Temporary proxy evidence (historical receipt: `demo-proxy-bypass-20261026T112213Z.json`).

## Recorded cleanup and remaining operator actions

| Resource | Last recorded result |
|---|---|
| Shared API | Desired/running/pending0 on revision2; temporary proxy-trust revision3 inactive. No permanent proxy bypass is retained in source. |
| Temporary proxy/EIP | Proxy i-0ddd52b8041114121 terminated; EIP65.0.49.162 released. |
| Temporary ingress | Target group, demo SG and cross-SG rules removed; five corresponding state entries removed. Failed NLB and unused recovery source removed. |
| Shared ECS host | i-0543832969d007de2 terminated/root removed; ASG0/empty. |
| Local demo DBs | Four verified disposable tmpfs PostgreSQL containers removed; no persistent volumes removed. |
| Original RDS | Read-only follow-up at18:09UTC confirms **stopped**, private, with deletion protection enabled. No SQL/data inspection was performed. |
| Domain | Aditya reports A removal at18:20UTC; propagation explicitly not rechecked at his direction. Earlier public answers remain historical. Preserve the correct ACM validation CNAME. |
| Terraform service state | Approved refresh-only apply verified at18:29UTC: state serial18and live service both revision2/desired0. Existing dependency metadata recorded; no infrastructure action. |

VPC/NAT/NAT EIP, RDS storage/backups/data, runtime roles/SSM URLs, ECR image,
private image bucket, IAM/log group and ACM certificate are deliberately retained.
They can continue incurring storage/network charges. Removing their Terraform
source would risk unintended deletion later; local Git cleanup does not remove
cloud resources or reconcile remote state.

## What belongs in the branch

Retain the Docker Microsoft build switch, scoped task/execution IAM, private S3
configuration and gated runtime composition: these support unfinished real
integration and describe retained cloud resources. This postmortem and the
work log keep the useful outcomes and limitations. Exact approval/result JSON
is recoverable from Git history, but does not establish current state or authorize
a new action. The cleanup removed expired restore/preflight proposals, superseded
runtime proposals, the duplicate local retrospective and verbose machine output
from the checkout. Keep concise current state in the work log.

| Retained source | Purpose and merge disposition |
|---|---|
| [Dockerfile](../../../../apps/api/Dockerfile) | Explicit Microsoft frontend build input, default false; needed to produce reviewed real sign-in images. |
| [base.tf](../../../../infra/terraform/shared/test/base.tf) | Execution role reads only the marketplace URL parameter for ECS injection. |
| [identity-email.tf](../../../../infra/terraform/shared/test/identity-email.tf) | Task role reads exact Identity references and image objects under id01/, preserving the verified SES sender scope. |
| [listings-images.tf](../../../../infra/terraform/shared/test/listings-images.tf) | Tracks retained private encrypted S3 bucket, HTTPS CORS, lifecycle and TLS-only policy; removing source would risk later deletion. |
| [service.tf](../../../../infra/terraform/shared/test/service.tf) | Opt-in real runtime connects the DB secret, Identity and S3 settings; default foundation profile stays disabled and valid. |
| [variables.tf](../../../../infra/terraform/shared/test/variables.tf) | Default-off activation and sensitive controlled-recipient input, maximum five; service precondition requires a nonempty list when enabled. |

Runtime activation must remain default-off and explicitly require a private
controlled-recipient list. The demo's removed personal recipient must not leave an
enabled, invalid email configuration. Fresh plans must preserve retained certificate
inputs and reconcile drift; no demo plan/checksum authorizes a future deployment.

Next: prepare a fresh full deployment plan after selecting durable HTTPS ingress,
choose supported durable HTTPS ingress/proxy trust, then verify real runtime/
provider/image/Search/browser behavior. Do not mark ID-READY complete from image
publication, a certificate or synthetic tests. Peer/affected-owner review and a
current exact CI revision remain required for the next PR.


## Local cleanup validation — 2026-10-26 14:02:52 UTC

Locked setup and all11local gates passed:1830Python/24optional skips,94data,
289web/3opt-in skips, Black261files, contracts/types/boundaries/build,35wrapper
safety cases, real PostgreSQL18.6 lifecycle and Gitleaks8.30.1. Backend-free
Terraform1.15.9 validates all4roots. All17main SQL files are unchanged; JSON,
relative paths/heading anchors and historical/reusable manifest hashes pass.
The focused offline audit has12passing tests and reports consistent=true,
ready_for_live=false. First aggregate exposed a reusable/historical manifest
reference mismatch; separating the executed receipt fixed it without changing
security checks or tests. Logs: /tmp/clip-branch-cleanup-check-final.log and
/tmp/clip-branch-cleanup-terraform.log. Historical failed log is retained privately.

Cleanup is ready for human/affected-owner review, not automatic deployment or
ID-READY acceptance. Changes remain uncommitted; no new AWS/state/DNS/SQL/secret
operation, push or merge occurred during the audit.


## Live cleanup verification — 2026-10-26 18:09:02 UTC

After Aditya renewed the expired operator session, read-only checks confirmed the
original RDS stopped, shared ECS/ASG0/empty, no owned EIP/demo SG/target group,
and proxy task revision3inactive. Exact proxy/host IDs return no retained instances.
ACM is issued/unused; fixed Identity parameter metadata remains version1. No
credential values or SQL were read. State was pulled in memory only; no refresh.
The two unresolved items are public apex resolution to the releasedIP and live/
state ECS service revision mismatch. No resources or DNS changed; application
journeys cannot be validated while stopped and require their separate approved run.
Sanitized evidence (historical receipt: `cleanup-verification-20261026T180723Z.json`).


User follow-up18:20:44UTC: released-IP apex A deletion reported complete; do not
recheck propagation at Aditya's direction. Refresh-only state plan (historical receipt: `ecs-state-reconciliation-review.json`)
was applied with explicit approval at18:29UTC. State/live service now both revision2,
shared compute remains0and RDS stopped. No secrets, DNS or infrastructure action.
Safe apply result (historical receipt: `ecs-state-reconciliation-result-20261026T182852Z.json`).
