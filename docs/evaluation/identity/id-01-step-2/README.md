# ID-01 Step 2 isolated provider setup evidence

2026-10-23 05:26:05 UTC; Aditya (A), Linux ARM64;
`task/id-01-identity` based on `44cd8ff`, uncommitted worktree.
Human result verification and affected-owner review pending.

## Changes
Identity private SES transport and offline tests; shared disabled-by-default
sandbox configuration; boto3 1.43.116 manifest/uv lock; canonical provider
decision, setup/access instructions, command registry and task/docs links.
The [IAM JSON](ses-send-policy.proposed.json) is a proposal, not applied policy.

## Checks
- Focused configuration/transport suite: initially 37 passed.
- Full API regression suite: 255 passed before the additional SDK serialization test.
- Final Identity suite: nine passed, including real SDK request validation through
  botocore Stubber, synthetic credentials, and no network delivery.
- Changed runtime files: `uv run --locked mypy --no-incremental apps/api/app/core/config.py apps/api/app/domains/identity/email.py`: passed.
- `make check`: all 11 gates passed; Black 73 files, 430 Python tests,
  63 data tests, Python boundaries, eight current generated artifacts,
  representative contract-double mypy, 16 web tests/lint/type/build,
  35 simulated database-wrapper safety cases, PostgreSQL 18.6 clean/repeat
  migrations and both smoke suites, Gitleaks 8.30.1 snapshot.
- `git diff --check`: passed.

## Limits and pending gates
No external email or AWS mutation occurred. Offline accepted responses prove
request shape and local safeguards, not SES permission, mailbox delivery,
Microsoft authentication, account lifecycle, or ID-READY. See the
[setup record](../../../environment/identity-provider-setup.md) for exact
remaining permission, controlled-recipient/send and production gates.
Shared provider config/dependency changes need affected-owner review.

## Final transport safeguard follow-up — 2026-10-23 05:27:18 UTC

After the full aggregate passed, configured the SDK to ignore ambient endpoint
URL overrides. The first metadata-based assertion failed because the SDK does
not preserve that flag on client metadata; replaced it with a behavioral check
that an injected override is ignored and the regional AWS endpoint is used.
Final focused suite: nine passed; changed-runtime mypy, Black check and
`git diff --check` passed. The full aggregate was not repeated after this bounded
transport safeguard; its recorded pass precedes that final change.

## Shared-role Terraform proposal — 2026-10-23 05:40:36 UTC

Aditya verified the isolated provider increment. The
[proposed patch](ses-shared-role.proposed.patch) would add one inline policy to
the existing shared API task role, gated by the root's existing base/service
phase. `git apply --check` passed; it has not been applied to source or cloud.
This is a source proposal, not a saved Terraform plan. Shared owner review and
writer reservation precede editing the shared root. Preserve the deployed
`service` phase, idle compute settings and all other approved inputs during
later planning; reject unrelated changes/replacements/deletions. No resource
startup, live test, credentials or secret-value retrieval is authorized here.
