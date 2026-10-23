# ID-01 Step 2 — one-shot runtime test preparation result

2026-10-23 06:39:31 UTC; Aditya (A), `task/id-01-identity` based on `44cd8ff`,
uncommitted worktree. Preparation authorized by Aditya's continue instruction;
result awaits human verification. No live send or cloud mutation in this increment.

## Changed behavior
`apps/api/app/domains/identity/email_smoke.py` adds an explicit Linux ECS command,
separate from HTTP/API startup. Requires explicit approval/test mode/SES/exactly
one controlled recipient, verifies container-role credentials and signed STS
account/role, then calls the existing Identity sender for one fixed generic
message. No database, OTP or account writes. No static AWS credential overrides.
Library logging suppressed during the run; only fixed accepted/uncertain outcome
printed. Command deadline 45 seconds; transport remains one attempt with bounded
socket timeouts. Provider acceptance does not establish inbox delivery.

`apps/api/tests/domains/identity/test_email_smoke.py` checks denial before sender
construction, one submission, redacted failure/no retry, invalid credential/role
responses, local-runtime rejection and positive expected-role acceptance. All
provider/role responses injected offline; no credentials or live recipients used.

Task-definition JSON is a proposal with unresolved image digest, not registered.
It reuses shared cluster/roles/logging with no ports or default send approval.
Runtime recipient/approval are separately gated overrides, not committed values.
Identity-exclusive task registration needs reviewed Identity-root ownership/plan;
shared service stays disabled. See [runtime plan](runtime-test-plan.md).

## Checks
- `uv run --locked pytest apps/api/tests -q -W error`: 264 passed before one final
  positive-role test was added; no runtime code changed afterward.
- Final `uv run --locked pytest apps/api/tests/domains/identity -q -W error`:
  18 passed (nine transport, nine smoke-command cases).
- Black formatting/check on the two new Python files passed.
- Changed-runtime mypy passed (one source file).
- Python domain boundaries: zero violations.
- Gitleaks 8.30.1 source snapshot passed; not a Git-history scan.
- `git diff --check` passed.

## Remaining gates
No image build/publication, task registration/start or application email send.
Exact reviewed source commit/image digest, bounded role-based run approval,
controlled inbox observation and compute-return-to-zero evidence remain pending.
SES production access remains pending. No step advance, ID-READY or task acceptance.
