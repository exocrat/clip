# ID-01 Step13: bounded runtime verification preparation

Owner/operator: Aditya(A). Recorded2026-10-28 03:20:57UTC.
Source base1d24435; local proposal is uncommitted. [Safe preflight and hashes](preflight-and-proposal.json).
No resource start, SQL, app-domain DNS propagation check or provider send has
occurred. Aditya subsequently approved in-memory reads of the two existing DB
password inputs and non-applying shared/test planning. Two private stopped-state
drafts now exist; neither is approved for apply or deployment/ID-READY acceptance.

## First checkpoint result

The configured non-root identity is account335523638354, regionap-south-1. RDS is
stopped/private/protected; both shared and isolated Listings ECS clusters have
zero tasks/instances. ASG desired0/max1; no nonterminated EC2 instances were found
in this region. Existing API revision2uses512MiB and has no load balancer.
AMIami-0c10ee7b040aa465eis available x86_64. The proposed proxy address10.64.0.10
has no current interface; recheck before any apply. Existing ACM is issued/unused
but non-exportable, so a direct EC2 proxy cannot reuse its private key.

## Reviewable HTTPS configuration

The shared root adds an optional/default-off EC2/Caddy proxy with eight Terraform
resource addresses: node role, inline node policy, instance profile, security
group, source-SG ingress rule, EC2 instance, EIP and EIP association. AWS also
creates the instance's interface/root volume. The existing ASG supplies the
separate private ECS host; this proposal creates no RDS, VPC, NAT or duplicate
cluster. Sizing remains a per-run input; the shared c7i-flex.large default is
unchanged. No other domain's exclusive infrastructure is edited.

The proxy is t3.micro with Standard CPU credits,30GiB encrypted/deleting root,
IMDSv2 and no SSH. Its dedicated node role has agent/channel operations but no
Parameter Store/Secrets Manager reads; the AWS-managed SSM core policy was not
used because it includes GetParameter(s). Public TCP80/443only; outbound HTTPS
for image/ACME/SSM and TCP18000only to the ECS host group. Only the proxy group
may reach the API. Fixed proxy source10.64.0.10is the sole forwarded-header peer.

Caddy2.11.7is pinned by the official multi-platform image digest. It sets the
upstream Host/forwarded headers, disables request/internal raw logging and the
admin endpoint, and has no automatic credential-write retries. Caddy obtains its
own ACME certificate after the separately approved domain A record points to the
new proxy IP. The existing ACM certificate/validation CNAME remain untouched.
The API command suppresses raw access logs and trusts only the exact proxy IP;
without the proxy it explicitly disables forwarded headers. Default-disabled
Identity keeps its existing image command. The old unrestricted proxy workaround
is not restored. [Caddy header behavior](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy),
[SSM core permissions](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSSMManagedInstanceCore.html).

The proxy schedules an OS stop at240minutes; this ends only its compute. IP/disk
remain until separately approved teardown. The shared API/host/RDS still require
operator-managed safe stop. This is not a whole-account automatic spending cap.
No wildcard forward trust, public database, fake auth or provider bypass is added.

## Sizing and bounded cost proposal

Public Mumbai On-Demand rates effective2026-10-01: t3.micro Linux$0.0112/hour,
c7i-flex.large Linux$0.08479/hour, Single-AZ PostgreSQL db.t4g.micro$0.021/hour.
Two micros plus the database for4hours are$0.1736compute; C7i plus one micro and
the database are$0.46796. These exclude credits/discounts/tax, public IP, disks,
NAT/data, logs/images and T3 surplus credits. The existing NAT/storage continue
independently. Proposed later active window: at most4hours, with a conservative
$2incremental operating ceiling subject to human budget/headroom approval; no
window is active or approved by this file.

Micro is a test proposal, not full-app sizing acceptance. The API and DB helper
jobs each reserve512MiB, so run them sequentially on a1GiB host. Measure actual
allocatable memory/RSS and stop on placement/OOM/credit problems; do not resize
or add hosts automatically. Native AMD64 image-build memory needs and Hybrid
model/worker sizing remain unverified; do not promise a full build on Micro.

## Ordered next gates

1. **Planning only:** approve reading the existing shared/test backend and
   refreshing resources, a transient backend lock, and in-memory reads of exactly
   `/clip/test/database-master-password` and `/clip/test/database-probe-password`
   to supply unchanged ephemeral write-only version1inputs. No other secret is
   needed for this request. Existing Terraform requires these values even for a
   non-mutating plan; [DEC-11](../../../decisions/terraform-write-only-credential-inputs.md).
   Produce private saved stopped-state baseline/Micro-variant plans and redacted
   address/action summaries. Keep API/proxy off, phase=service, retained certificate
   flag/date and write-only versions; preserve actual image digest rather than
   stale stop examples. Stop on unrelated changes or destructive/rotation actions.
2. Review exact saved plan/source hashes before any apply. Resource starts,
   AMI/image build or ECR publication require their own reviewed scope. Never
   invent an upstream IP to bypass the proxy's required-input guard.
3. During a separately approved exclusive live window, start the retained RDS
   and one owned host, inspect the exact database baseline, and review the clean
   bootstrap/reset of project namespaces/tracker. Preserve instance, unrelated
   databases, stable auth keys and credential versions. No reset or incremental
   upgrade has been implemented/executed by this checkpoint. Review effective
   grants, current image and task/runtime configuration; discover the actual host
   address before preparing the enabled proxy plan.
4. Review/apply the enabled proxy/runtime plans. The human adds the new A record;
   do not repeat the declined DNS-propagation checks. Verify HTTPS, actual proxy
   source, secure cookies and Microsoft/email flows with approved accounts/sends.
5. Verify operational retention cadence and bounded cleanup. Stop app/tasks,
   release only owned protection/capacity, stop RDS when exclusive, and separately
   remove proxy/IP/SG/role/profile/root resources. Preserve shared network, buckets,
   secrets, images and certificate unless their own deletion was approved.

The email parameter still has version1and last-modified2026-10-24 14:15:25.735UTC.
That does not identify its key or contradict the human rotation confirmation if
the replacement was stored then. Location clarification was requested; no value
was read. New deployed configuration/delivery remain actual acceptance checks.

## Local checks and command

- Full12-gate make check:1938Python/153explicit skips,94data,433web/3skips,
  Conversations167, formatting/contracts/types/build, actual PostgreSQL18.6
  lifecycle, wrapper safety and Gitleaks passed.
- New exact-proxy Identity HTTP/SQL cases:6passed. They prove trusted/untrusted
  transport, exact/foreign/null Origin, request marker and Secure/HttpOnly cookies.
- Isolated Terraform mock plans:3passed (disabled default, enabled exact peer,
  missing-input refusal); enabled plan also rejects wildcard/secret-read node
  actions. The first mock fixture missed its required snapshot input; fixed.
- Pinned Caddy image validates its rendered configuration with networking disabled;
  bash-n passes for bootstrap. This is not an actual HTTPS or certificate test.
- Backend-free pinned Terraform format/schema validation passed all4roots.

Run mocks reproducibly with the pinned binary:

```sh
TERRAFORM_BIN=/path/to/terraform-1.15.9 uv run --locked python scripts/check_identity_https_proxy.py
```

The wrapper copies only the root to a disposable directory, removes the backend,
excludes state/plan/tfvars and AWS credential/config files, and requires the fixed
mock provider. It never accepts a live target. Terraform's public schema downloads
may occur; AWS resource APIs are not invoked. Logs are under
`/tmp/clip-id01-step13-*`; they are local evidence, not Git artifacts.

## Non-applying plan result — 2026-10-28 03:42:11 UTC

Aditya authorized the existing DB input/state planning scope. The fixed master/
probe parameter version1values were held only in process memory/ephemeral inputs;
plaintext values were not present in pulled state or rendered plan JSON. No auth
key, email-provider key, database connection, parameter write or resource start
was performed. Backend state serial18was read; no state apply/write occurred.
Plans/logs are owner-only outside the repository at
`/tmp/clip-id01-step13-plans-z3pe8zic`.

Both initial drafts keep API/proxy/Identity off, with no RDS/SSM/certificate action
or proxy creation. Both replace the stopped API task definition with the disabled
source configuration and include default-tag normalization. Most apparent tag
removals keep tags_all unchanged; the service's ExpiresOn23→27is a real metadata
alignment. The Micro draft additionally changes the launch-template host type;
no EC2 instance exists or starts. The unexpected SES policy difference is caused
by omitting its existing private sandbox-recipient input, not a requested sender
or sandbox-policy change. These drafts are not candidates for apply.

Correcting that input requires reusing the existing exact recipient ARN from
state in memory and protected plans, without printing it or adding a recipient.
Automatic approval review rejected this extra sensitive-input use because the
approved input scope named only the two DB passwords. Explicit human approval
was requested before that reuse; no indirect workaround or targeted/ignore-
changes plan was attempted. Regenerate both full plans after approval; old hashes
must not be approved/applied. SQL/reset, deployment, sends and resource starts
retain their separate gates.

Aditya reconfirmed that the replacement Resend key was saved correctly to the
configured parameter. The metadata date alone does not establish key contents;
no new rotation action is requested. Actual approved delivery remains later.
