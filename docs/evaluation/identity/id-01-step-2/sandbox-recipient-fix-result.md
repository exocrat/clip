# ID-01 Step 2 — controlled-recipient scope diagnosed and fixed

Recorded 2026-10-23 17:13:37 UTC. Aditya explicitly approved the urgent
diagnostic/fix/verification sequence; no commit/push/merge authority inferred.

## Actual denied resource

Enhanced wrapper SHA256 d07bae8dfa0d9239db8f119e7c47a99697b55a47de84e0aa111b3fc25dc93871
passed37 focused offline tests. One approved :1 task
bbbd211646394427b5a0c97e1b704958 ran17:07:02.081698 UTC onward and returned
AccessDeniedException at ses_submission, resource_class controlled_recipient,
denial_reason unclassified. No raw SDK message/private address retained. This
identifies the actual denied identity; previous simulations alone did not.
Prompt guarded desired-zero cleanup removed host i-01edad09fd8c5e4d4/root
vol-0dd35ab2e3a7797c4, ECS/ASG zero verified17:10:41.527682 UTC. Runtime RDS calls0.

## Reviewed/applied exact correction

Writer Aditya's shared/test identity-email.tf now takes optional sensitive
ses_sandbox_recipient_identity_arn, restricted to one exact account/region email
identity with wildcards refused. Existing ses:SendEmail statement now lists the
sender domain and the one verified controlled recipient; exact FromAddress
no-reply@clip-iisc.site unchanged. No administrative/wildcard SES grant.
The private ARN is not in repository source/evidence; IAM/protected state retain
it, and normal plan rendering masks it. Future plans must preserve it while
sandbox delivery needs it; remove deliberately after production-access review.

[Plan scope/source hashes/checksum](sandbox-recipient-fix-review.json) and
[approved fix boundaries](sandbox-recipient-fix-plan.md). Exact saved-plan SHA256
36e9738a7120549a9541f0571fb3b213994ebba8efc04edad1566115a11e3d47.
Full refresh-enabled Terraform1.15.9/AWS6.69.1 plan showed exactly one inline policy
update, zero other managed changes. Rechecked plan/source/operator/idle guards
and applied that exact artifact once under Aditya's approval. Attached policy
exact two resources/action/condition verified; compute remained zero.

Shared-root planning refreshed RDS metadata but proposed/applied no DB change;
no database connection/schema/data operation/start/stop/credential rotation.
Existing approved version1 master/probe SecureStrings supplied only ephemerally
in child memory as required by unchanged provider write-only inputs; checked
absent from saved-plan members. No secret/payload logging. Terraform backend-free
format/validation passed all three roots; git diff --check passed.

## Verification preparation (historical)

One corrected actual-role test is separately executing under the approved
sequence, same :1/image/enhanced wrapper, new token/marker, one message maximum,
45-minute/USD1 window and prompt owned cleanup. No automatic resend. Do not
claim delivery or complete Step2 until its actual submission, human receipt and
cleanup pass. SES production access remains pending.

## Corrected real delivery and cleanup passed — 2026-10-23 17:17:30 UTC

One corrected run started17:13:50.377355 UTC, expiry17:58:50.377355 UTC,
task403eba24a7d2428394d76272148ab882, same exact :1/image/wrapper. Full preflight
verified the corrected policy, SES sandbox sender/recipient, current pricing and
empty ECS window. Actual role/adapter returned submission_accepted/stage complete,
no unexpected logs, exit0 at17:15:55.489 UTC. Aditya explicitly confirmed the new
message reached the inbox (observation recorded by17:16:58 UTC). This verifies
real application-role SES submission and inbox delivery, not just IAM simulation.

Repeated all-service/task/sole-owned-host guards passed; one prompt desired-zero
action removed host i-0bbef51578c9e5ecf/root vol-04f1705171090cf51. Verified
17:17:09.706322 UTC: host terminated, root deleted, ECS/ASG zero, no other
workload affected, runtime RDS calls0. No service/database/managed alarm change,
new image or automatic retry. Private sanitized checkpoint:
/tmp/clip-id01-fixed-verification-4zq309m5/.

Shared Terraform state serial10 and released lock verified after the policy
apply. Exact two-resource policy and original sender condition match reviewed
plan/source; no other managed resource changed. The fix therefore resolves the
observed SES sandbox recipient-identity authorization failure.

Final make check passed all11 gates: Black79 files,458 Python/63 data/16 web tests,
boundaries,8 current generated artifacts, contract mypy, web lint/types/build,
35 database-wrapper safety cases, PostgreSQL18.6 clean/repeat migrations and both
schema smokes, full-source Gitleaks8.30.1. Three-root pinned Terraform format/
backend-free validation passed. Changed-file JSON/local-link/private-inbox checks
and git diff --check passed. No app image rebuild needed. Code/config files:
- runtime_authorization_diagnostic.py: bounded SDK-context resource/reason
  classification with fixed output and unchanged actual sender/role/deadline.
- test_authorization_diagnostic.py:9 synthetic denial/privacy/single-attempt cases.
- runtime-authorization-run.proposed.json: exact wrapper command with private
  recipient placeholder; this run's actual destination/token stayed private.
- infra/terraform/shared/test/identity-email.tf: optional sensitive exact recipient
  ARN added to existing sender policy, wildcard inputs refused; preserve during
  sandbox plans and remove only through reviewed production transition.

Setup/decision/private-input/commands/inventory/work-log records reconciled.
No new commit/push/merge authorized or performed. Human inbox verification passes;
Aditya verified this complete fix/check/cleanup report and permitted staged
continuation on2026-10-23 17:23:48 UTC. Step2 stays
partial for production access/configuration review; later Identity implementation
and ID-READY acceptance remain pending.
