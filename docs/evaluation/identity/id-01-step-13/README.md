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

## Corrected stopped-state plans — 2026-10-28 04:43:41 UTC

Aditya explicitly approved unchanged private SES recipient ARN reuse and requested
a commit first. Both full plans were then regenerated from state serial18 against
committed source3433ae7, without targets or ignored changes. The existing SES
policy is unchanged; no IAM policy, RDS, SSM parameter or ACM actions remain.
Both plans affect15resource addresses, chiefly default-tag normalization, stopped
API task-definition replacement/service reference and launch-template metadata.
The Micro plan additionally selects t3.micro for the future host. Capacity stays0;
API, Identity and proxy stay disabled. No apply, SQL, email or start occurred.
The old draft hashes are superseded and must never be applied.

Private baseline SHA256: `73694804e9b76abc2295b3274b2b616290714c96b8da7e1129ef3f7369d9d6d4`.
Private Micro SHA256: `927ac404dc4c48ed2566d6d6724d1bcab65682168181f11d68f726fbe30b1fb7`.
Artifacts remain owner-only in the previously recorded private directory. Existing
password versions1 are preserved; no provider/authentication key was read.
This clears the private-input planning blocker, not Step13 acceptance. Exact-plan
apply, resource starts and the later clean database bootstrap remain separate
approvals. Retained ExpiresOn dates are historical metadata, not permission for
a new operating window; refresh/review them before any active-resource plan.

## Approved stopped-state apply — 2026-10-28 04:46:45 UTC

Applied exactly the approved Micro plan SHA256
`927ac404dc4c48ed2566d6d6724d1bcab65682168181f11d68f726fbe30b1fb7`
in account335523638354/ap-south-1/shared/test. Apply completed; backend serial
18→19. Independent AWS reads verify launch template version3 selects t3.micro,
ASG desired/min0 with no instances, API task revision4 with desired/running/pending0,
and protected private RDS still stopped. No host/proxy was created or started,
no SQL connection/reset or email send occurred. The C7i comparison plan is now
stale and must not be applied. Private apply log and sanitized status remain in
the recorded private directory. No new operating window is authorized.

Next checkpoint is the separately approved bounded active window: retained RDS
and one owned host, observed sizing/address, current-image build/publication
review, and exact database baseline/reset review. Enabled proxy and actual
HTTPS/provider/browser/retention checks remain pending.

## Next bounded startup proposal — 2026-10-28 04:48:19 UTC

Aditya verified the stopped-state apply. Fresh read-only preflight confirms both
clusters idle, RDS stopped/private/protected, ASG min0/max1/desired0 and LT3 Micro
with encrypted30GiB delete-on-termination root. CPU credit mode is not explicitly
set in the template; set Standard on only the new host before any diagnostic load.

Requested window: account335523638354, adityalaxmi1, Mumbai shared/test, operator
Aditya, at most4hours/$2 incremental operating ceiling (an operator stop threshold,
not an automatic AWS billing cap). Start retained RDS and exactly one private
Micro host by temporarily setting ASG min1/max1/desired1. Min1 keeps the empty
diagnostic host from idle scale-in; restore min0 afterward. Before startup create
a named one-off ASG scale-down for start+4hours, min0/max1/desired0. This fallback
covers host capacity only; operator must separately stop RDS. No proxy or API task.

Read-only ECS/SSM diagnostics observe actual address, registration and allocatable
memory, plus uname/free/df, Docker version/info and ECS/SSM service status. No
SQL connection, credential/provider read, migration, reset, build/publication or
email is included. No ingress, IAM or other-owner resources change.

At most4hours host+RDS public compute estimate is$0.1288, excluding EBS, NAT,
storage/log/data/tax. Existing retained costs continue. Stop for drift, unexpected
workloads/hosts, registration/memory failure, extra-resource requirements, deadline
or projected ceiling breach. On completion/failure restore min0/max1/desired0,
verify owned host termination, stop RDS when still exclusive, remove only owned
scheduled action after cleanup confirmation. Preserve shared infrastructure,
images, keys and data. Full structured scope is in the adjacent proposal JSON.
Startup is awaiting its separate human approval.

## Approved startup diagnostic checkpoint — 2026-10-28 04:54:19 UTC

Started at2026-10-28 04:50:53 UTC after explicit approval. One private host
`i-03d4b9d603b260361` registered with ECS/SSM at10.64.1.247; Standard CPU credits
were verified. SSM diagnostic652dc658-e0b8-43e6-ad33-bfe3e3572091 exited0:
x86_64, Docker25.0.16, ECS/SSM services active, root28GiB free, no swap.
ECS advertises2048CPU units/916MiB available for task reservations. OS idle
available memory was537MiB. This supports a single512MiB scheduling reservation
only; no actual API process, memory/load acceptance or build suitability is proven.
Two512MiB tasks cannot fit. No new blanket Micro sizing acceptance.

Host diagnostics complete; cleanup restored ASG min0/max1/desired0 and the owned
EC2 host is terminated. Retained RDS startup was still transitioning; cleanup
continues until RDS can be stopped. The planned host address is historical after
termination and must never be reused as a future proxy upstream without a new
live observation. No SQL, provider/auth secret read, API/proxy activation, image
build/publication or email occurred. Pending cleanup/result verification.

## Diagnostic window cleanup verified — 2026-10-28 05:03:07 UTC

The approved window is complete. RDS reached available and accepted the stop
request; it is now stopped/private/protected. The owned host is terminated.
Independent final reads confirm ASG min0/max1/desired0 with no instances, API
desired/running/pending0, and absence of the owned one-off scheduled action.
The window began04:50:53 UTC and cleanup reached stopped05:02:50 UTC, within
the approved four-hour limit. No account billing was queried or actual charge
claimed. Shared network/storage/NAT and other-owner resources were preserved.

Gitleaks8.30.1 source-snapshot scan and whitespace checks pass; no application
source/configuration changed during this window. This checkpoint proves host
registration/sizing diagnostics and bounded startup/cleanup only. Human result
verification remains pending. Next prepare the reviewed current-image build and
read-only database-baseline inspection scopes before another live window; clean
bootstrap/reset, deployment, HTTPS/provider/browser and retention acceptance
remain pending. ID-READY and ID-01 remain incomplete.

## Next build/database preparation — 2026-10-28 05:10:38 UTC

Aditya verified the diagnostic result and selected t3.micro for a native AMD64
build. Prepared [the exact build/publication/read-only inspection window](build-and-database-window.md),
an allowlisted233file source archive bound to3433ae7, a loopback-only hash-checked
SSM transfer helper, and a sequential bounded native build helper. The latter
uses2GiB swap on the owned encrypted root,512MiB RAM/1536MiB combined per build
step, a45minute timeout, non-root/platform and default-runtime health/UI checks,
and image archive hashes. No host IAM or public port is added. Local ARM64 only
stores/pushes the resulting AMD64 image; it never executes that image.

Three real transfer boundary tests pass after correcting test-only connection
cleanup. Shell syntax, embedded Python parse, inert CLI help and formatting pass.
Source archive excludes local changes/caches/environment files. No new build,
AWS window, ECR publication or SQL ran. New master-secret use for read-only SQL,
source/image transfer, publication and bounded startup/cleanup need the exact
combined window approval. This prepares current-image and catalog findings only;
bootstrap/reset and all deployed acceptance remain separately pending.
