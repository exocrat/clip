# ID-01 Step12 — dual-provider email preparation

Recorded2026-10-24 14:01:17 UTC. Aditya(A), task/id-01-identity at29ab71a
plus this uncommitted increment. The Step12 merge proposal remains unexecuted.

## Authorized behavior and audit

Aditya approved Resend initially, SES later, configuration refresh every four
hours and one alternate attempt after any first failure. The
[canonical decision](../../../decisions/identity-email-routing.md) resolves the
prior no-cross-provider-retry rule without changing application-owned auth state,
public signatures or production fake refusal. Timeout fallback can deliver two
copies of the same code. No new challenge/expiry/attempt reset occurs. No new
material task-definition gap was found; runtime setup is an explicit pending
prerequisite, not simulated acceptance.

## Changed code and relationship

| File | Purpose and important behavior |
| --- | --- |
| `apps/api/app/domains/identity/email_routing.py` | Immutable provider snapshot plus RefreshingEmailSender: lazy first load,14400second monotonic cache, synchronized refresh, one primary/one alternate attempt, same message, private terminal failure. Each send keeps one snapshot. Failed refresh sends nothing with expired settings. |
| `apps/api/app/domains/identity/email_configuration.py` | Trusted SSM loader reads one explicit SecureString into route/key together; strict versioned JSON, fixed Mumbai SDK endpoint, one SDK attempt, redacted errors. SES adapter is explicitly injected and retains its own restrictions. No reads on import/construction. |
| `apps/api/app/domains/identity/resend_email.py` | Real HTTPS plain-text POST to fixed Resend endpoint; explicit at-most-five controlled recipients, private key, fixed sender, default TLS checks, no ambient proxy/redirect/retry, bounded envelope/response and socket timeout, safe errors. No live calls in checks. |
| `apps/api/app/domains/identity/temporary_delivery.py` | Documentation reconciles one logical dispatch with the router's approved two-provider attempt; executable OTP behavior is unchanged. Tickets remain transient, consumed once and not logged/persisted. |
| `apps/api/tests/domains/identity/test_email_routing.py` |44offline cases cover both orders/failures, four-hour exact boundary, snapshot credentials/order replacement, bad/expired configuration, concurrent load/OTP consumption, exact Resend wire shape/denials/privacy/redirect refusal, and SSM real SDK serialization through offline Stubber. |

Identity README, contract, docs index, provider/setup/safety decisions, secret
reference and Step12 plan explain selection, narrow policy supersession and gates.
No shared application/config/Vite, schema, generated surface or dependency change.
Proposed SSM path `/clip/test/identity/email-delivery` is not provisioned or verified.
Its private schema is version1, primary resend/ses and resend_api_key; no actual
credential/recipient/OTP is recorded. One parameter version avoids mixed route/key
reads. Existing environment selectors and SES production guards remain intact.

## Checks and evidence

- Focused new+existing email/delivery tests:60passed;44are new.
- Strict project mypy for3new source modules: success, no issues.
- Pinned Black: new modules/test formatted; final122Python files unchanged.
- `make check` exited0/all11gates:815Python (158.21seconds),63data,92web;
  boundaries,8generated artifacts current/format2, contract types, web lint/types/
  build,35wrapper safety cases, actual PostgreSQL18.6 clean/repeat/five-smoke/
  incompatible-upgrade atomicity and preserving upgrade/down/reapply, Gitleaks8.30.1.
- Full local log: `/tmp/clip-id12-email-routing-check.log`.
- [Five source hashes](email-routing-source-hashes.json) identify this exact code.
- Synthetic mocked provider failures and offline SDK serialization are not real
  Resend/SES/SSM permission, delivery or deployed-runtime evidence. No live DNS,
  account/API-key, cloud, send, hosting, shared DB, push or merge action occurred.

## Remaining gates

Human verification and explicit commit approval; then separately approved
current-main reconciliation, shared runtime/secret wiring and real setup. Resend
needs domain DNS and sending key/retention review, exact SSM/IAM plan and bounded
live recipient test. Keep SES sandbox limits until actual production acceptance.
SES fallback for a nonverified recipient can still fail while sandboxed.

Once both actual adapters, task-role permission and runtime loader are deployed,
editing the SecureString primary can switch without rebuild/restart; current
private components do not claim the website already does that. Each process
refreshes on its first send after four hours; a failed refresh sends nothing.
No background polling, bounce/webhook fallback or automatic permanent promotion.
CN-03 adoption remains separately owned. All original ID-READY/provider/browser/
peer/merge acceptance gates remain; Step14 stays outside current scope.

## Subsequent edge diagnosis — 2026-10-24 14:19:07 UTC

Human reported no delivery and authorized exactly one retry. It failed HTTP403/
edge1010, captured without private error text. Added explicit CLIP User-Agent in
resend_email.py plus request-header assertion in the routing tests; Black and
44focused tests pass. Source hashes updated for these two files. The prior full
gate predates this narrow header correction. No further live send; correction
remains unverified against actual Resend. No credential/domain failure inferred.

### Live correction result — 2026-10-24 14:22:05 UTC

Following official Resend 403/1010 documentation review and fresh human approval,
one actual adapter send with the explicit CLIP User-Agent received a valid
success response. No automatic retry/fallback. Provider acceptance verified;
inbox receipt and deployed/runtime checks remain pending. No sensitive values or
message identifier retained in evidence.

## Selected verify sender — 2026-10-24 16:15:52 UTC

Aditya selected verify@clip-iisc.site for Identity verification/reset messages,
avoiding generic no-reply/marketing-style senders. Resend delivery from verify
to his IISc inbox is human-confirmed in the setup record; exact filtering cause
for older messages remains unknown. Bounded shared ownership recorded before edits.

| Changed path | Important behavior |
| --- | --- |
| apps/api/app/domains/identity/resend_email.py | Fixed From is now verify@clip-iisc.site; request, validation, key and no-retry behavior otherwise unchanged. |
| apps/api/app/core/config.py | SES sender Literal/default permits only verify@clip-iisc.site, retaining controlled recipients and production refusal. Old environment sender overrides must be updated before running the new code. |
| .env.example | Documents the new SES sender; no local actual environment file is modified. |
| infra/terraform/shared/test/identity-email.tf | Desired exact IAM FromAddress condition now verify@; existing live role still permits no-reply until a separately approved plan/apply. No wider sender/domain permission. |
| apps/api/tests/domains/identity/test_email.py | Actual offline SES request/stubber assertions require the selected verify sender. |
| apps/api/tests/domains/identity/test_email_routing.py | Actual offline Resend envelope assertion requires verify; refresh/fallback semantics unchanged. |
| apps/api/README.md | Current sender setting and staging safety documentation updated. |

Canonical decision/setup/work-log explain this choice and desired-versus-live
permission distinction. No new route/dependency/OTP policy/secret/DNS/send or
deployed change. Focused email/routing/provider-settings/API config tests82passed
with warnings as errors; pinned Black4files unchanged; whitespace passed. Prior
full815/63/92 gate predates this literal-only sender change; not rerun or relabeled.
Source hashes updated/extended to9code/config/test paths. Terraform plan/apply
and revised runtime SES send remain pending separate approvals. Current local
increment awaits human verification and explicit commit approval.
