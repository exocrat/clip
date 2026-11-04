# Deployed shared-pool functional checks — 2026-11-04

Checkpoint: 15:52 UTC. The public website is serving through ECS. Its known
photo, Saved, Wanted and Hybrid failures did not recur in the checks below.
Lambda activation failed its startup smoke and its selected-read rule was
removed under the approved rollback. No pilot, formal comparison or NFR pass
is claimed. The Lambda startup cause is not yet established.

## Deployment and retained failure

Accepted main is `b4d7419f532d8be354720c87118f8ff13ab39270` (PR33 reviewed head
`e6e3cb54a1cc6637805afbf01416c56cddaf4933`). Account 335523638354, Mumbai:
two existing API tasks at revision 14, each 1024 CPU units / 2048 MiB, use the separate
existing-host PgBouncer service at revision 3. No host/RDS resize was performed.
API image digest is `21214318f0aed3d2233f16949e5e45e190f8c34b0aa8a2a7f482ffaca83c10e1`;
pool image is `8c2321845214573815181c5391f07038efaee2feccbd9815b6369d5c4a576592`.

A became healthy at 15:14UTC after the existing 300-second ALB drain. Its website
checks passed before the approved B apply completed at 15:23:15. B's first read
timed out during initialization. At15:25:42 the operator deleted only B's
selected-read listener rule, explicitly restoring ECS routing. This was an
operator rollback, not automatic request fallback. The Lambda/support resources
remain temporarily for diagnosis; Terraform must be reconciled before another
apply. Do not replay the old B plan.

An additional direct Lambda read, while public traffic stayed on ECS, also
failed: `Sandbox.Timedout`, initial initialization approximately 10 seconds and
invoke initialization approximately 5 seconds. One log reported Hybrid startup
unavailable. These failures remain evidence; no successful B parity is claimed.
Read-only timing in the existing ECS container found application import 1.30 s,
Identity preparation 0.34 s, its 352 SQL calls 0.17 s, helper startup 0.46 s. Those are
component diagnostics on ECS, not Lambda measurements. The exact Lambda image's
offline helper also passed locally with read-only storage, no network/shared
memory and both the configured and unrelated unprivileged users. This rules
out those particular local restrictions, not AWS startup problems.

Suraj approved fixed-stage tracing under plan SHA256
`bad7664ac52c193d8a178652c404db538c28388c2d10e60b8b4e8080c9f47b72`.
Both bounded diagnostic invocations completed at16:16UTC and the original
command/five-second timeout were restored. Public routing stayed on ECS.

## Startup correction prepared at16:27UTC

The five-second traced attempt failed after the initial ten-second deadline and
another five-second initialization attempt. Identity preparation took about0.4s;
the Hybrid database pool was ready in22–30ms. The trace reached model-helper
startup before interruption. With the temporary30-second timeout, initialization
completed in4990.03ms, helper ready at4489.53ms, and the browse request returned
20items/page1 in100.67ms invocation time (5.44s observed direct-call total).
This establishes successful real Lambda initialization and one browse response,
not complete Hybrid/parity or capacity. The initial cold helper delay and its
variation are not fully explained by those two observations.

The proposed repair preserves the five-second function and client deadlines.
Set `AWS_LWA_ASYNC_INIT=true` so the pinned adapter can continue initial startup
instead of restarting it when the initial window expires. It still waits for
application readiness before forwarding a request. A cold request that exceeds
the client's five-second deadline still counts as a failure; no timeout is
relabelled or excluded. Platform invocation duration may include the remainder
of asynchronous startup; do not label absent Init Duration as proof of warmth.
See [AWS lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)
and the [pinned adapter configuration](https://raw.githubusercontent.com/aws/aws-lambda-web-adapter/v1.1.0/README.md).

An isolated fake Runtime API exercised the **real pinned adapter binary**:
12-second app startup failed the initial deadline with async disabled; it
returned200 with async enabled, requesting its invocation at9.81s and finishing
at12.03s. A30-second unready app still hit the five-second invocation deadline
at14.82s and was never forwarded a request. The first async harness attempts
omitted required synthetic Lambda metadata and exited; those receipts remain,
and the corrected harness results are separate. No local result proves the
proposed AWS setting works until its new smoke checks pass.

Changed code/configuration and checks:

- `infra/terraform/shared/test/exp03-lambda.tf`: enable the adapter's async startup;
  keep memory, function timeout, concurrency, image, roles and database unchanged.
- `infra/terraform/shared/test/pgbouncer.tf`: explicitly retain ECS's empty
  capability-add list, preventing an unchanged pool from being replaced by
  unrelated plans. Drop-all capability restrictions are unchanged.
- `scripts/evaluation/k6/real_target_preflight.py`: before B measurements, require
  async startup, successful configuration update, five-second timeout and no
  diagnostic command/entrypoint/working-directory override. A remains unchanged.
- `tests/evaluation/test_lambda_startup_preflight.py`: accepted normal settings
  and rejection of diagnostic/deadline/configuration drift; the Lambda Terraform
  mock also checks async startup with the unchanged deadline.

Focused Python checks45passed; Terraform Lambda/pool mocks19passed. The broader
evaluation suite initially reported431passed/11skipped/6failed due to missing
Node on PATH; after adding the pinned Node, five passed and the remaining local
HTTP-server check passed outside the loopback-restricted sandbox. Formatting and
diff whitespace checks pass. No application business code or images changed.

Full saved Terraform plan SHA256
`40afb20d2a4f2a0f68de8b9aac44e48b41ef10fe89864bc2c98bf49687f45eb5`
has exactly two actions: update the existing Lambda environment (and normalize
its already-empty image override), and recreate the approved selected-GET rule
at100%Lambda. **No pool/API restart, resize, SQL, image or permission change.**
Source publication/integration and this changed cloud plan remain separately
gated. If smoke fails, delete only the recreated rule to restore ECS routing and
restore the captured Lambda configuration. The existing smoke budget applies;
this is not permission to begin the pilot.

## Actual website results

Both authorized regular accounts remained signed in. Two complete website
smoke passes each passed 16/16 recorded checks. Each pass downloaded and decoded
20 photos for each account and rendered Discover three times with20/20 photos,
zero photo errors and zero Saved warnings. Each rendered page used one photo
batch and one Saved-state batch, with no old per-card requests. Owner/peer hidden
photo rules, keyword/Hybrid search, browse pages, Saved, Wanted, inbox and unread
reads passed. Desktop overflow was absent. These are bounded samples, not an
exhaustive claim about every object, browser or load level.

After the explicit B rollback, the following ECS workflows passed:

| Evidence group | Result |
|---|---|
| Main controlled flows | 44/44 assertions: filters/order/price, image upload/confirm/decode, create/read/save/unsave, conversation deduplication, offer creation, Wanted creation/edit/matches and invalid/unauthorized requests |
| Follow-ups | 17/17 explicit assertions plus rendered-page and two composer observations: Hybrid after insertion, owner edit, stale revision 409, foreign edit denial, offer revise/withdraw and Wanted closure |
| Visibility and cleanup | 17/17: unavailable peer 404 / owner 200, image visibility, Saved unavailable reference, test-save removal, existing-thread access, preference toggle/restore, missing-CSRF 403 and invalid-image 422 |
| Deliberate encrypted contacts | 3/3: controlled fictional phone set, explicitly shared/displayed, original value restored |
| Selection and Wanted conversation | 15/15: owner select/clear, peer 403, temporary reopening of the controlled Wanted Request, owner self-response 403, responder create/retry same thread, author read and restored unavailability |

Visible two-client chat submitted and displayed synthetic messages in both
directions: 2545.58 ms and 1524.98 ms. The entry projection contained no plaintext
field. These are **not NFR05 results**. Earlier attempts failed to observe display
while diagnostic tabs were hidden/frozen; those receipts remain. The successful
check kept both dedicated tabs visible using browser focus emulation. Both
successful observations are within NFR05's five-second limit, but two diagnostic
messages do not establish its required 95% success rate under the frozen normal
workload. Keep the earlier observations as well.

One new listing and one Wanted Request were created and marked unavailable.
The listing selection is cleared; test Saved state, phone and notification
preference were restored. Controlled conversations and their attached image
remain recorded in the private fixture registry; no personal listing was edited.
Read-only inventory shows 1,003 listings, 900 available, all 1,003 embeddings ready.
The new listing's embedding completed in one attempt with no failure code.

## Remaining limitations and blockers

- Both controlled accounts lack an Identity notification destination. Their
  notification preference is enabled, but the worker has no address to resolve.
  Therefore these accounts do not establish real email delivery. Actual mailbox
  receipt and temporary-account activation/reset remain unverified.
- Read-only API logs since15:14 contained one 503 at 15:21:31 during the B apply
  window, which restarted the unchanged pool. Correlation alone is not a proven
  cause. No clean-smoke assertion is substituted for this retained503.
- Passive browser accounting retained439API request starts and seven transport
  failure events across the Lambda failure, navigation and diagnostic tab
  lifecycle changes. It did not retain per-failure causes, so those seven must
  not all be attributed to cancellation or classified as server failures.
  Status/header events and transport failures can overlap; this is not a valid
  formal success denominator. The bounded smoke assertions above are separate.
- Normal workstation DNS still differs from the actual ALB. AWS-side lookup
  matches the public domain and ALB. The dedicated browsers use their documented
  DNS override with normal domain TLS verification. Normal-target preflight
  correctly refused the mismatched answer; no formal parity capture exists.
- B startup/parity, stable normal generator DNS, complete run bindings, exact
  traffic approval and all formal measurements remain pending. The short local
  capacity checks do not accept deployed NFRs.
- Quiet database snapshots used three/four application backends, not proof of
  peak capacity. Original role limits and the 36-backend pool budget remain.
  CloudWatch's ordinary-traffic window 15:14–15:54 shows database CPU averaging
  4.61% (maximum one-minute average 5.55%), at most 10 connections, minimum freeable
  memory 139,583,488 bytes and zero surplus CPU credit balance. Both ECS targets
  remain healthy; account Lambda concurrency remains ten. These are not load
  measurements or a justification to skip the pilot.

## Exact evidence locations

All private evidence is under
`/home/suraj/src/.clip-private/pgbouncer-20261104/`. It contains identifiers and
must remain outside Git; credentials/message bodies are not part of these reports.

- `activation-a/apply-receipt.json`, `activation-b/apply-receipt.json`,
  `activation-b/manual-rollback.json`.
- `website-a-checks/2026-11-04T15-14-44-310Z.json` and
  `website-a-checks/2026-11-04T15-50-37-765Z.json`.
- `functional-b/flows.json`, `followups.json`, `contacts.json`, `cleanup.json`,
  `selection-wanted.json`, `controlled-fixtures.json`, `chat-visible-04.json`.
  **Despite its directory name, this functional-b group ran on ECS after rollback.**
  Earlier chat diagnostic receipts are retained alongside it.
- `background-health-1548.json`, `background-health-notifications.json`.
- `cloud-posture-1555.json`, `local-dns-recheck.json`.
- `browser-b-request-accounting.json` (passive observer stopped at15:56UTC;
  includes ECS after rollback, not439Lambda invocations).
- `browser-parity-a.json` (diagnostic override only), `parity-preflight-failures.json`,
  `aws-public-dns-check.json`.
- `lambda-first-smoke-log-summary.json`, `lambda-direct-read-diagnostic.json`,
  `cloud-startup-timing-03.json`, `cloud-helper-startup-timing.json`,
  `lambda-local-restricted-helper.json`, `lambda-startup-diagnostic-plan.json`.
- `lambda-startup-diagnostic-receipt.json`, `adapter-async-init-local.json`,
  `adapter-async-init-local-v2.json`, `lambda-startup-repair/provision.tfplan`,
  `lambda-startup-repair/provision-plan.json`.

The dinner checkpoint changed documentation and private diagnostic scripts;
the subsequent startup correction adds the configuration/preflight changes above.
No commit, push or unapproved deployment has been performed. The existing pool
24-hour / USD2 and B120-minute / USD1 bounds still apply.
