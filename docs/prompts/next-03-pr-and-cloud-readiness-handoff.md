# Quick handoff: NEXT-03 integration and cloud readiness

Continue in `/home/suraj/src/clip-planning-main`. The product goal is a working
Campus Marketplace at `https://clip-iisc.site`, with Notifications as the known
exclusion.

Read `README.md`, then `AGENTS.md` and `docs/prompts/reusable-task-prompt.md`.
Use the [NEXT-03 change summary](../tasks/next-03-change-summary.md) for scope,
the [visual-feedback plan](../tasks/next-03-visual-feedback-plan.md) for settled
behavior, and [NEXT-04](../tasks/remaining-project-plan.md#next-04--completion-audit-and-integrated-https-cloud-app)
for the cloud-readiness route. The implementation report has prior checks and a
file inventory.

Work quickly and stay focused:

1. Inspect the full dirty diff and branch. Preserve it. Fetch and inspect current
   `origin/main` (the user says it is slightly ahead), then safely reconcile the
   changes. Check especially for migration conflicts/order changes. Do not reset
   or discard work.
2. Fix only concrete integration or PR-blocking issues. Run pinned full checks
   after integration and affected checks after fixes; report exact results.
   Update the work log and handoff docs. Reconcile the user's “we are done” with
   the work-log visual-review status.
3. Prepare the reviewable PR package under `CONTRIBUTING.md`, including affected
   owner and independent peer review. Do not merge without explicit approval of
   the exact PR revision.
4. Audit the deployment path read-only using NEXT-04 and the cloud inventory.
   Verify real auth/email/SES, migrations and grants, Hybrid model/vector flow,
   images/storage, HTTPS/DNS, cookies/CSRF, IAM and operations. Provide only the
   concrete blockers and deployment plan needed to run the app at the target URL.

No cloud deployment/apply, shared DB migration, DNS/permission change, real
email or paid usage without separate approval. The category and Handle
migrations have only passed disposable local checks; the Identity 17-migration
live package still needs separate owner review. Do not expand into Notifications,
chat-image attachments or optional relevance tuning.

Finish with PR readiness, exact verification results, remaining cloud gates and
the next action. Do not claim production readiness without real hosted checks.
