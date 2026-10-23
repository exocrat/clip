# ID-01 Step 2 checkpoint commit review

Prepared 2026-10-23 06:47:00 UTC. Branch `task/id-01-identity`, parent `44cd8ff`.
Human verified the prepared runtime command/plan. No commit authorized yet:
CONTRIBUTING.md line 21 explicitly requires separate approval for every commit.

Proposed message: `ID-01: prepare sandbox SES setup and bounded runtime test`.
Scope: isolated Step 2 checkpoint, not ID-READY or task completion. Includes
verified provider setup records, sandbox transport/config/SDK pin, tests,
reviewed and applied IAM source, approved AMI preservation, bounded smoke command
and task/run proposals, access/inventory/status/documentation/evidence updates.
No credentials, recipient address, actual cloud state, saved plan, images or
runtime overrides are included. Task-definition image placeholder remains
explicitly unresolved, so it is not deployable input.

Full local aggregate passed: 439 Python, 63 data, 16 web tests and all 11 gates;
Black 75 files, contract freshness, boundaries, types/build, PostgreSQL checks,
wrapper safety and Gitleaks snapshot. Local Markdown paths resolve; recipient
absence and whitespace checks passed. This is local evidence, not hosted CI,
independent peer approval, email delivery or readiness acceptance.

After commit approval: commit this package locally only, record the exact source
revision, then prepare image build using that revision. No push, PR publication,
merge, ECR upload, task registration/start or email is authorized by committing.
Arrange designated independent review using `docs/prompts/peer-review-prompt.md`
at the appropriate PR handoff; AI/local checks do not replace human approval.

Builder prerequisite: Docker daemon 26.1.5 is ARM64; Buildx absent and no registered
binfmt handler. Prior native AMD64 validation was performed on another teammate's
machine. Select an existing AMD64 builder or review host emulation setup before
claiming an AMD64 build. No installation or cloud builder startup has occurred.

## Exact candidate paths

- `.env.example`
- `README.md`
- `apps/api/README.md`
- `apps/api/app/core/config.py`
- `apps/api/app/domains/identity/README.md`
- `apps/api/app/domains/identity/email.py`
- `apps/api/app/domains/identity/email_smoke.py`
- `apps/api/tests/domains/identity/test_email.py`
- `apps/api/tests/domains/identity/test_email_smoke.py`
- `docs/README.md`
- `docs/decisions/identity-provider-setup.md`
- `docs/decisions/shared-test-ecs-image-pin.md`
- `docs/environment/cloud-inventory.md`
- `docs/environment/commands.md`
- `docs/environment/identity-provider-setup.md`
- `docs/environment/secret-handling.md`
- `docs/evaluation/identity/id-01-step-2/README.md`
- `docs/evaluation/identity/id-01-step-2/checkpoint-commit-review.md`
- `docs/evaluation/identity/id-01-step-2/cloud-plan-request.md`
- `docs/evaluation/identity/id-01-step-2/cloud-plan-result.md`
- `docs/evaluation/identity/id-01-step-2/permission-apply-result.md`
- `docs/evaluation/identity/id-01-step-2/permission-plan-review.md`
- `docs/evaluation/identity/id-01-step-2/pinned-plan-result.md`
- `docs/evaluation/identity/id-01-step-2/plan-source-hashes.json`
- `docs/evaluation/identity/id-01-step-2/runtime-preparation-result.md`
- `docs/evaluation/identity/id-01-step-2/runtime-task-definition.proposed.json`
- `docs/evaluation/identity/id-01-step-2/runtime-test-plan.md`
- `docs/evaluation/identity/id-01-step-2/runtime-test-preparation.md`
- `docs/evaluation/identity/id-01-step-2/ses-send-policy.proposed.json`
- `docs/evaluation/identity/id-01-step-2/ses-shared-role.proposed.patch`
- `docs/status/work-log.md`
- `docs/tasks/domain-task-list.md`
- `infra/terraform/shared/test/README.md`
- `infra/terraform/shared/test/base.tf`
- `infra/terraform/shared/test/identity-email.tf`
- `infra/terraform/shared/test/locals.tf`
- `pyproject.toml`
- `uv.lock`
