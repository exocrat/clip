# ID-01 Step13 — runtime activation and HTTPS window

Owner/operator Aditya(A), account335523638354, profile `adityalaxmi1`,
ap-south-1, existing shared/test root/state. Source `c82dc28`; no new image build
or migration/reset. [Exact saved plan and source hashes](runtime-stopped-plan-review.json).

## First approval: stopped configuration and bounded startup

Apply only `/tmp/clip-id01-runtime-plan-sz7ld_se/runtime-stopped.tfplan`, SHA256
`b531b9bad72885a99f1003f21533e2de2471dab824ebc9c2c75dba8f45042159`,
prepared from backend serial19. It replaces only `aws_ecs_task_definition.api[0]`
and updates `aws_ecs_service.api[0]` to that definition. Verified immutable image:
`335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:bfa7316c26f683654f5c4b3f40e9817876db5afd79f8f13af978a8841fbde8f8`.
Identity profile and real S3 wiring are configured, but API tasks stay0 and HTTPS
proxy stays absent. No IAM/SSM/RDS/network/storage change. Existing recipient
input preserved plus the approved IISc test address; private values stay outside
Git. Existing provider/authentication/DSN secrets are not changed or printed.

After exact-plan approval/apply, start retained private/protected RDS and exactly
one private t3.micro ECS host, Standard credits, ASG min1/max1/desired1. No app task
or proxy yet. Fresh exclusive operator window maximum4hours/$2 incremental stop
threshold (not an AWS billing cap); stop new work by3hours, startup limit20minutes.
Install owned host scale-down fallback for the deadline before starting; preserve
retained NAT/storage and unrelated workloads. Read actual private host IP and
registration; never reuse a terminated host address. Prepare full enabled runtime/
HTTPS proxy and rollback/teardown plans using that IP, preserving backend secret
versions and existing SES recipient input. Previously approved master/probe reads
may be used once per preparation, memory only for unchanged write-only inputs.
No operator read of authentication/provider keys is needed for planning.

Stop before applying any new enabled plan: exact plan/source/action review and
separate approval remain required. Stop/clean up for unexpected resources,
workloads, permission/credential changes, capacity/OOM, startup failure, timeout
or projected cap breach; do not enlarge/resize without approval.

## Next plan: HTTPS/runtime and controlled verification

Expected scope, to be confirmed against the saved plan: existing API service to1;
source proxy configuration creates one public Standard-credit t3.micro, encrypted
30GiB deleting root, EIP/association, dedicated secret-free SSM node role/policy/
profile, proxy SG and source-SG-only ingress to private API18000. Only public80/443;
no SSH/public DB/direct API. Existing pinned Caddy image, fixed proxy10.64.0.10,
exact observed upstream; no ACM export or auth/header bypass. No extra RDS/NAT/
cluster or other owner's resources. Proxy has240minute OS stop; operator must
clean up the full window, including EIP/disk and private runtime/RDS.

The human updates `clip-iisc.site` A record to the new EIP. Do not poll DNS
propagation. Validate actual HTTPS/certificate/proxy/header/cookie behavior,
deployed image/revision/provider configuration and startup privacy/role guards.
Existing execution/task roles fetch only already-reviewed application DSN/auth/
provider references during approved runtime startup; no key/password rotation.

Human signs in with Microsoft and uses temporary email registration/reset directly
on the website. Proposed provider-send scope for approval with enabled plan:
`verify@clip-iisc.site`, only Aditya's recorded IISc/Gmail test addresses, maximum
6intentional messages total, no automatic manual resend loop. Do not persist
OTP/password/token/contact values. Check sessions/logout, contact privacy and
available consumer smoke paths; no full Step14 or performance/load campaign.
Inspect retention dry-run and prepare exact hourly operating/stop mechanism;
retention writes/scheduling require their reviewed target/count plan. Never fake
provider success or seed shared synthetic accounts to replace human sign-in.

## Cleanup/retention and completion

On success/failure/deadline: stop only owned app tasks; apply reviewed proxy-off/
API0 cleanup, release only owned capacity/protection, terminate private host/root,
stop RDS when exclusive, remove owned fallback, proxy/EIP/SG/role/profile/root.
Preserve shared network/buckets/keys/images/ACM and migrated database/roles. No
`terraform destroy`, blanket test-account cascade, unrelated S3 deletion or
rollback to an incompatible old image. A failed new runtime stays off; preserve
sanitized diagnostics and reviewed configuration. Retain usable task definition
at0 for restart unless separately directed.

Do not claim Step13 complete until real regular/temporary flows, hosted security/
browser checks, retention operation, evidence and human verification pass. Final
closeout and Git push/PR/merge remain separately gated. Current preparation
created no resources and did not repeat unaffected application test suites.
