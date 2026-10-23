# ID-01 provider setup and verification

Status: Step 2 partial. Local operator SES inbox delivery is human-confirmed
on 2026-10-23 10:26:07 UTC; ECS application-role delivery failed and needs
diagnosis. Production access remains pending. Historical snapshots follow.
The [decision](../decisions/identity-provider-setup.md) and
[work log](../status/work-log.md) distinguish approved direction from evidence.

## Microsoft
Client `ab3a63e3-d4db-4c3c-b4bf-ac5f7573ffbb`; registration tenant
`19d07278-f040-4722-8202-b1174cf3a4d3`. The tenant is registration metadata,
not an IISc sign-in tenant allowlist. Human-confirmed SPA callbacks:
`http://localhost:5173/auth/callback` and `https://clip-iisc.site/auth/callback`.
Public-cloud v2 common discovery and client-ID audience are the Step 4 validation
inputs. PKCE/state/nonce/replay handling must be implemented and checked there;
registration alone does not prove successful authentication. No client secret
or Graph permission is needed for this selected flow.

## SES runtime setup
Account `335523638354`, region `ap-south-1`; domain `clip-iisc.site` and DKIM
were verified in the recorded 2026-10-23 04:48:31 UTC inspection. Sandbox remained
active. Those observations do not establish current permission or delivery.

The pinned boto3 SDK uses the normal AWS credential chain. Local operators use
the existing approved interactive AWS profile; ECS uses its task role. Never
copy access keys into config. No SMTP password or new Parameter Store secret is
required for task-role SES sending; existing database secrets are unrelated.
Keep boto3/botocore wire/debug logging disabled: payloads contain private codes
and recipients. No SDK exception or payload should enter evidence.

The initial configuration is disabled by default. Explicit `ses` selection is
restricted to local/test mode and a JSON list of at most five controlled
recipients via `CLIP_SES_TEST_RECIPIENTS`. List membership is case-sensitive and
does not verify ownership or authorize a send. Addresses must be SES-verified
while in sandbox, except approved SES simulator destinations. Do not commit
real recipient addresses. `CLIP_SES_REGION` and `CLIP_SES_SENDER` are fixed to the
reviewed region/sender proposal. No API route currently constructs this sender.

The transport only submits one bounded plain-text message. Provider acceptance
is not inbox delivery. An uncertain failure is not automatically retried; Step 5
must handle that outcome without activating an account or claiming delivery.
Blocking calls must run outside the async event loop. Application challenge and
rate-limit controls remain Step 5 outputs.

## Reviewed and applied IAM sender permission

Proposed target: shared test application task role `clip-shared-test-api-task`.
The [JSON proposal](../evaluation/identity/id-01-step-2/ses-send-policy.proposed.json)
permits only `ses:SendEmail` for the verified domain and exact From address.
It grants no identity management, raw-email action, secret access or wildcard
resource permission. It does not limit recipients; recipient restrictions in
the controlled test plan and application allowlist remain necessary.

Aditya reviewed and approved the source proposal; the matching Terraform resource
now exists in `infra/terraform/shared/test/identity-email.tf` under his recorded
writer reservation. Local pinned Terraform checks passed. Aditya separately
approved the exact saved plan; apply and attached-policy/state verification
passed. See [apply evidence](../evaluation/identity/id-01-step-2/permission-apply-result.md).
No runtime sending was tested. Future permission changes/removal require a fresh
reviewed plan and approval. CN-03 worker permission remains a later separate scope.

## Remaining real checks and approval package

1. Completed: Aditya reviewed/approved the sender/role policy and exact plan.
2. Completed: approved exact-plan apply and attached-policy/state verification;
   effective task-runtime delivery is still unverified.
3. Completed: Aditya selected a controlled inbox; SES verification SUCCESS was
   checked on 2026-10-23 06:30:46 UTC. Recheck before dispatch; no address is
   recorded here. The [runtime plan](../evaluation/identity/id-01-step-2/runtime-test-plan.md)
   and offline-tested command are prepared; build/publication/task/run gates remain.
4. Approve a live test: account/region above, one generic synthetic message,
   one recipient, one attempt, maximum one minute, no resource creation, sending
   cost cap USD 0.01 excluding pre-existing environment costs. Stop on any error
   or uncertainty; do not retry automatically. No account activation or real OTP.
5. Execute from the intended application-role path after its deployment/run
   approval; a human-profile send alone cannot establish runtime permission.
   Record only UTC time, approved revision/role, accepted/failed outcome, and
   human delivery observation; no recipient, body, OTP or raw provider error.
6. Production-access approval is still pending. Refresh SES account status
   before general delivery and review removal/replacement of sandbox guards.

No live test is authorized by this written proposal. Any compute startup or
redeployment requires its own exact environment/resource/cost plan. Keep Step 2
partial until required real setup checks and human result verification pass.

## Offline checks

`uv run --locked pytest apps/api/tests/domains/identity/test_email.py apps/api/tests/core/test_provider_settings.py apps/api/tests/test_config.py -q -W error`
uses injected clients and synthetic `.invalid` destinations, without AWS calls.
The full API suite and repository format/type gates remain applicable. Commands
are recorded in the [registry](commands.md#identity-provider-offline-checks--id-01-step-2).

## Runtime image available — 2026-10-23 07:23:06 UTC

The [published image record](../evaluation/identity/id-01-step-2/published-image.json)
pins the approved `52186a0` AMD64 artifact and verified registry/config digests.
Native image validation and publication passed; temporary builder VM/root disk
removed. Dedicated temporary IAM/profile/group cleanup and actual smoke task
registration/run remain pending. No email-delivery evidence yet.

## Runtime task registered — 2026-10-23 09:27:10 UTC

Identity-owned smoke definition
`arn:aws:ecs:ap-south-1:335523638354:task-definition/clip-test-identity-email-ap-south-1-id01:1`
is registered and verified against the immutable image/expected roles/disabled
controls. All temporary builder resources removed; no task launched or message
sent. [Apply evidence](../evaluation/identity/id-01-step-2/runtime-registration-apply-result.md).
Current SES read-only snapshot remains sandboxed/healthy, sending enabled,
200/day and 1/second. Exact one-email run, inbox observation, owned test cleanup
and production access remain pending. Leave concurrent RDS activity untouched.

## Real runtime result: failed, cleanup verified — 2026-10-23 10:14:29 UTC

Corrected request launched exact :1 task; signed identity audit matches the
application role/task, but transport returned only `failed_or_uncertain` and
exit1. Human reports no test email. Do not count provider delivery as verified.
Owned task/host/root cleanup passed via managed scale-in; ECS/ASG zero, RDS
untouched. No resend. Exact transport cause still needs safe code/stage diagnosis;
current sandbox/production-access gate remains. [Result](../evaluation/identity/id-01-step-2/runtime-corrected-result.md).

## Local delivery confirmed — 2026-10-23 10:26:07 UTC

One explicitly requested local AWS CLI SendEmail call under the approved operator
was accepted at 10:24:06 UTC; Aditya confirms inbox receipt. Sending enabled,
sender and controlled recipient verification passed; sandbox remained active.
No address/content/provider payload recorded. This verifies local operator
delivery only, not the application task-role path. No ECS resources started.
The local pinned SDK lacked optional login-provider CRT support before any send;
CLI used the existing login successfully without changing dependencies. This
local credential-provider issue is not evidence of the earlier ECS root cause.
Required remaining setup gates: safely diagnose and verify real application-role
delivery, production-access decision/configuration review, then human Step 2
result verification. Microsoft real token/callback behavior and OTP/account flows
remain later implementation/integration checks, not missing Step 2 services.
