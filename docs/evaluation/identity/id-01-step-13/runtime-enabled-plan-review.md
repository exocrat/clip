# ID-01 Step13 — exact HTTPS/API deployment approval

Account335523638354, profile `adityalaxmi1`, Mumbai shared/test, sourcec82dc28.
The approved stopped-runtime plan applied successfully (backend19→20), then the
approved private host/RDS window started15:03:57UTC. Actual host
`i-012c79d8ef66d51f9`, Standard-credit t3.micro at10.64.1.179 is ECS/SSM registered.
API remains0. [Exact plan/actions/source hashes](runtime-enabled-plan-review.json).

Saved plan `/tmp/clip-id01-runtime-plan-sz7ld_se/runtime-enabled.tfplan`, SHA256
`246c529444a63364c24e39ef6bd71c8e195b33ea6bb86d977321558064ef11f8`.
Apply has not run. Eleven changed addresses:

- Eight proxy resources created: EC2 t3.micro, EIP/association, dedicated IAM
  role/inline policy/profile, proxy SG and private API source-SG ingress rule.
  EC2 creates its interface and encrypted/delete-on-termination30GiB root.
- API task definition replaced to trust only proxy10.64.0.10, with raw access logs
  disabled; same verified immutable imagebfa7316, existing provider/auth/DSN/S3
  configuration. Service desired0→1 and new task-definition reference.
- ASG min1→0 returns to source policy; max1 and current desired1 retained. ECS
  capacity-provider owns desired scaling. Require API task on the exact observed
  host; any replacement/address drift invalidates this proxy upstream plan.

Public80/443 only; no SSH/public database/direct public API. Proxy role cannot
read secrets; Standard credits/IMDSv2/pinned Caddy and exact upstream checked.
No database/migration/reset, SSM/password/key, bucket, existing IAM policy, NAT,
ACM or other-owner resource change. Existing execution/task roles retrieve only
reviewed application parameters at runtime; operator does not print key values.

## Runtime checks and limits included in requested approval

Same active four-hour/$2 window: absolute deadline19:03:57UTC, stop new work
18:03:57UTC. Maximum one private Micro, one proxy Micro, retained RDS and one API
task. No load campaign or unapproved sizing change. Retained NAT/storage costs
continue outside this incremental operator threshold; no actual-billing claim.
Proxy240minute OS stop is secondary and never extends this window. Failure,
capacity/OOM, unexpected resources/permissions/workload or cap risk stops work.

After apply, validate task health and actual image/role/privacy/proxy configuration.
Give human the new EIP for `clip-iisc.site` A record; no DNS propagation polling.
Verify actual HTTPS/certificate and secure cookie/header behavior, then human
Microsoft login and temporary email registration/sign-in/forgotten-password/reset,
logout/session/contact checks on the website. Proposed send approval: at most
6intentional messages from `verify@clip-iisc.site` to Aditya's recorded IISc/Gmail
addresses only (private task allowlist). No raw tokens/passwords/OTPs/contacts in
logs/evidence/chat, no false provider success or automatic manual resend loop.
No SES production assumption; use existing reviewed dual-provider configuration.
No Step14 full matrix or complete Conversations activation added as a gate.

Retention dry-run/operating-cadence review is allowed; persistent retention writes
or scheduling need their exact target/count/mechanism approval. Human final
browser/regular/temporary acceptance remains required to complete Step13.

## Failure, rollback and cleanup

On failure/deadline stop the owned API service, close owned connections, restore
ASG0/max1 and terminate owned private host/root; stop retained RDS when exclusive.
Prepare/review the full proxy-off/API0 teardown to remove only these eight proxy
addresses plus their interface/root/EIP. No blanket Terraform destroy. Preserve
migrated DB/roles/keys, shared network/buckets/images/ACM, existing policies and
unrelated resources. Keep verified task configuration at0; do not roll schema back
or silently return to an incompatible historical image. Remove owned fallback
after cleanup confirmation. Record partial apply before any recovery decision.
Current saved plan and source changes need human approval before public creation,
IAM changes, API start or email sends. Existing startup approval alone is not that
approval; this document completes the concrete review package.
