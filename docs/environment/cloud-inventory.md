# Cloud environment inventory

Non-secret handoff of the last recorded cloud state. This is not a live view or
permission to create, change, or delete resources. Before any cloud operation,
verify the caller and refresh AWS and Terraform state; review and approve the
exact operation separately. Never record credentials, tokens, or secret values.

## Experiment readiness identity check — 2026-11-03

Read-only STS verification found that the default shared-credentials profile is
root in account `484394572488`, which is not the project account; do not use it
for project work. The existing `surajs2` profile resolves to non-root IAM user
`surajs2` in project account `335523638354` and region `ap-south-1`. The
documented operator profile `adityalaxmi1` is not configured in this environment.
Suraj then directed using `surajs2` for read-only project inspection. Later
dated entries below record that refresh. No resource was changed.

## Experiment deployment readiness refresh — 2026-11-03 11:17 UTC

Suraj explicitly directed read-only project inspection with profile `surajs2`;
STS confirmed non-root IAM user `surajs2` in project account `335523638354`.
The default profile remains root in unrelated account `484394572488`; it was
not used for project inspection. No resource was created, changed or deleted.

| Area | Read-only observation |
|---|---|
| ECS | `clip-shared-test` is ACTIVE, with Container Insights disabled, one active service, zero running/pending tasks. `clip-test-api-ap-south-1-pd16` is ACTIVE at task-definition revision 11, desired/running/pending 0, with no load balancer attached. The task uses image digest `sha256:97482cb4fb697eee230e66d134c165e557dac7d71a165e6034c88747f1738245` (tag `cn03-b95a7a50ecf8`, pushed 2026-10-30), which predates the integrated EXP-03 PR #27/#28 merge on 2026-11-03; a current immutable application image must be built and reviewed. |
| ECS host | ASG `clip-shared-test-ecs-host` reports min 0/desired 0/max 1 and all listed scaling processes suspended. It lists `i-086045c48487471de` as InService/Healthy, while EC2 reports that instance STOPPED (`t3.micro`). Do not start or terminate it directly. This capacity is not usable now. |
| Database | `clip-shared-test-postgres` is stopped, private, encrypted, PostgreSQL 18.6, `db.t4g.micro`, 20 GiB gp3, deletion-protected. Five available automated snapshots were listed; the newest is 2026-10-30. No manual snapshot was listed. |
| Ingress and Lambda | No load balancers and no Lambda functions are currently present. The only issued `clip-iisc.site` ACM certificate is valid until 2027-05-11 but `InUse=false`. The account has no Route53 hosted zones; any public hostname update belongs to the external DNS operator. No public DNS record was checked in this refresh. |
| Network and Terraform | VPC `vpc-04b0cc01cbf93cd17` (`10.64.0.0/20`) and NAT `nat-0d7fefbad586f4bce` are available. The versioned, AES256-encrypted shared/test state object was last modified 2026-10-30 and has Terraform serial 31. A streamed state inspection printed only resource addresses/metadata, not attributes or secret values; it includes the retained Identity HTTPS proxy/EIP, shared database/network, and ECS service, with no EXP-03 ALB/Lambda resources. No Terraform refresh or plan ran. |
| Costs | The AWS cost budget is account-wide, unfiltered, and configured for 2026-10-17 through 2027-10-17; its USD 200 target is not the project's experiment-period cap. Suraj clarified that the project USD 200 limit applies through experimentation. For 2026-10-17 through 2026-11-03, AWS Budgets reports USD 26.526 gross actual and USD 1,217.222 forecast; its `IncludeCredit=false` setting explains why this differs from the near-zero Cost Explorer net view. Cost Explorer's `RECORD_TYPE` breakdown is USD 26.525958 Usage and approximately -USD 26.525958 Credits, so credits offset the gross usage in that period. The budget has no project/resource filter and its forecast is not an experiment estimate. Cost Explorer service totals for the same period are account-level and do not identify exact resources; the largest are EC2-Other (about USD 20.92), VPC (USD 2.28), RDS (USD 1.64), and EC2 compute (USD 0.98). Suraj reports NAT is about USD 1.56/day; that rate is not confirmed by the queried service-level totals. The separate USD 10 experiment credit limit remains; current remaining credit balance and experiment-only allocation are unverified. |

The stale `ExpiresOn=2026-10-27` tags on retained PD-16 state/resources are
past due; do not retag or clean them up without the separately reviewed plan.
These observations prove the target is not presently deployed and its cost
headroom is unresolved. They do not authorize starting RDS/EC2, resuming ASG
processes, changing DNS, applying Terraform, or deploying A/B.

## CN-03 test shutdown — 2026-10-30 10:27 UTC

Aditya directed stopping the test resources while preserving them. The API ECS
service has desired/running/pending count zero. Its protected host
`i-086045c48487471de` and HTTPS proxy `i-0d1947299024cae06` are stopped, not
terminated; the retained RDS was verified stopped at 2026-10-30 10:34:06 UTC. All Auto Scaling
processes on `clip-shared-test-ecs-host` are suspended to prevent replacement or
termination and must be deliberately resumed for later use. The existing proxy
EIP and DNS record remain; the site is offline. NAT, EIP, RDS storage, logs,
monitoring and other retained resources may still incur charges. No AWS resource
was deleted. The independently built unlisted-recipient image is retained locally, on
the host disk, and in ECR at digest
`sha256:3faaeb2ebe160868d1e7b194e373051a1bde2fc5d84cef60959a028d3e8f3d00`;
it is not deployed. Recheck all state before future work.

## NEXT-06 approved Phase A closeout — 2026-10-30 17:51:24 UTC

Conditional guards passed in non-root335523638354; ASGprocesses includingLaunch/
Terminate were already suspended. Existing RDSand EC2host started for the one
reviewed metadata probe; SSMbecame Online. Probe exited1with genericRuntimeError,
no usable DBmetadata; exactfailurestage/secret-or-SQLprogress not established.
No upload/schema/grant/runtime/ASGchange. Both named resources verified stopped
by2026-10-30 17:48:00 UTC. Servicecalls48within160cap; no retry/repair performed. Rawreceipt's
failure label did not rename after cleanup, but actual flags/events confirm both
stops. [Closeout](../evaluation/domain/next-06/transfer/phase-a-20261030/result.json).
Further cloud attempts require separately reviewed diagnostic payload/approval.

## NEXT-06 SDK and route/storage preflight — 2026-10-30 17:02:49 UTC

One approved max18call batch used14requests; actual SDKlogin bridge verified
non-root project identity without access keys/CRTextra. EC2i-086045c48487471de is
stopped/t3.micro in the existing appSG; priorASGInService did not establish running
compute. SSMmanaged-node filter returned no records. IAMtask-role inline/attached
policy listing was AccessDenied; effective runtime permissions remain unverified,
not repaired. Current id01bucket metadata passes owner/region/private/SSE-S3/
public-block checks; CORSmatcheshttps://clip-iisc.site, ownershipBucketOwnerEnforced,
no versioning config returned. No object/secret/SQL access or resource changes.
[Sanitized receipt](../evaluation/domain/next-06/transfer/load-preflight-current.json).

## NEXT-06 configuration refresh — 2026-10-30 16:48:55 UTC

Approved16operation scope completed using non-root profilemohitmahapa1 in project
account335523638354. Shared ECSrevision11 is x86_64Linux/256CPU/512MiB/bridge and
uses id01imagebucket/prefix, with Hybrid and worker false; only nonsecret allowlist
and SSMreference names were read. RDS18.6db.t4g.micro/20GiBgp3/singleAZ remains
stopped/private/encrypted; port5432ingress permits only appSG. Related private
subnets have no automatic public IP. Existing ASGdesired0/max1 returns one healthy
InServicehost; actual EC2state/type/SSMreachability not inspected. li02bucket is
Mumbai/SSE-S3, all public blocks enabled, nonpublic policy status, owner enforced;
CORS onlyhttp://127.0.0.1:5173; versioning call returned no configuration content.
These are metadata observations, not working auth/media/SQL/model integration.
No secrets/objects/SQL/session/remote commands or resource changes. [Evidence](../evaluation/domain/next-06/transfer/cloud-config-current.json).

## NEXT-06 bounded read-only refresh — 2026-10-30 16:12:47 UTC

Mohit's browser-login CLIprofile `mohitmahapa1` now verifies as non-root IAMuser
`arn:aws:iam::335523638354:user/mohitmahapa1` in Mumbai. The approved six scoped
inspection calls found `clip-shared-test` ACTIVE with one service and zero tasks;
`clip-test-api-ap-south-1-pd16` uses taskrevision11 with desired/running/pending0
and rolloutCOMPLETED. `clip-shared-test-postgres` is stopped, PostgreSQL18.6,
private and encrypted. Project bucket names include the id01 and li02 images
buckets and retained Terraform state bucket. No object/secret/SQL access or
resource change. Current task config/capacity/network/effective permissions and
pricing were not inspected; prior revision10/NAT/DNS/settings observations below
remain historical, not reverified. [Evidence](../evaluation/domain/next-06/transfer/cloud-readiness-current.json).
Next configuration scope requires separate approval; no cloud load authorized.

## NEXT-04 read-only refresh — 2026-10-29 12:08 UTC

Using the renewed `surajs2` profile, STS confirmed non-root user `surajs2` in
project account `335523638354`, region `ap-south-1`. SES reports production
access and sending enabled. The shared ECS service is task revision 10 with
desired/running/pending all zero; its host ASG is at desired zero with no
instances. Shared RDS is stopped and private. One NAT gateway remains available
and may incur charges. No `clip` EventBridge rules were returned; this does not
prove that every other scheduler or retained resource was inventoried.

The stopped task is configured for the test Identity profile, dual email and S3,
with both Hybrid search and the worker disabled; its browser origin is exactly
`https://clip-iisc.site`. The Identity image bucket blocks all public access, its
bucket policy is not public, and CORS permits GET/HEAD/PUT from that HTTPS origin.
The API task role's inline policy lists SES send, SSM parameter read and S3 object
operations. Its sender condition includes `verify@clip-iisc.site`, its three SSM
references match the documented Identity test parameters, and its S3 scope is
the ID-01 object prefix; effective permissions and secret values were not tested. An ACM
certificate for the domain is issued. Route53 returned no exact hosted zone for
the domain in this account. Google and Cloudflare public DNS returned no A record;
public NS records point to `launch1.spaceship.net` and `launch2.spaceship.net`.
The hostname did not resolve from this environment; IISc resolver behavior and
the current DNS operator remain unverified.

NEXT-03 adds a participant projection used by Conversations: its dedicated runtime
role needs reviewed `USAGE` on the Identity schema and `SELECT` on that view.
The local role fixture verifies the narrow grant, but no shared grant or migration
was applied. Current Terraform state/drift, Identity's real general-recipient
production path, Hybrid model/worker and automatic vectors, trusted ingress,
retention scheduling, budget and hosted end-to-end behavior remain deployment
gates. The user deferred the broader SES production source change. No resource
was started, changed or deleted and no email was sent in this refresh.

Source inspection confirms that product discovery defaults to Hybrid, whose SQL
accepts eligible original/expanded keyword matches or semantic matches without
duplicating listing rows. Listing insert/text-edit triggers invalidate old
embeddings and enqueue generations for active pipelines; the configured helper,
model, serving pipeline and worker are still required to process them. These
source paths do not establish a working hosted vector pipeline.

## Shared foundation — historical inspection 2026-10-26

An approved read-only inspection finished at **2026-10-26 18:09:02 UTC**. A
refresh-only Terraform apply at **18:29:50 UTC** reconciled state serial 18 with
the live API service at revision 2; it changed no cloud resources. The newer
dated records in this inventory supersede this snapshot where they differ.

| Area | State at that inspection |
|---|---|
| Account and region | Account `335523638354`, `ap-south-1` (Mumbai). Aditya is the named operator by user direction; verify the actual caller before an approved action. |
| ECS | Shared cluster `clip-shared-test` remains. API service is revision 2 with desired, running and pending task counts at zero. Capacity provider/ASG has desired zero and no host. |
| Database | `clip-shared-test-postgres`, resource ID `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, was stopped, private, encrypted and deletion-protected. Database data, storage and automated backups remain. No SQL or secret values were read during the cleanup inspection. |
| Network and state | The retained foundation includes its dedicated VPC/NAT and versioned Terraform backend. The 2026-10-19 inventory recorded VPC `10.64.0.0/20`, NAT `nat-0d7fefbad586f4bce`, and backend bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`. Refresh before relying on these identifiers. Preserve the backend and its state versions. |
| Identity demo cleanup | Temporary proxy, released EIP, demo security group and target group were removed; temporary API revision 3 is inactive. Certificate `a9775d00-2af5-4b12-990d-1ce9795f1859` is issued and validated but has no listener. Identity parameter metadata was version 1; values were not decrypted. |
| Domain | Aditya reported removal of the apex A record at 18:20:44 UTC. At his direction, DNS propagation was not checked. Preserve the ACM validation CNAME. |
| Retained resources and possible costs | Shared VPC/NAT, RDS storage/backups/data, ECS cluster, ECR, private image bucket, IAM roles, SSM parameters, logs, Terraform state and ACM certificate were recorded as retained. They may continue to incur charges. |

The **ID-01 demo postmortem** has the detailed deployment and cleanup outcomes.
It records that hosted sign-in, listing publication/photo upload and Search were
not accepted. ID-READY remains incomplete. Check current state before reusing any
of its resource details.

## Separate LI-02 demo

The last recorded post-stop inventory, from **2026-10-25**, found its disposable
RDS, load balancer, service, host/root volume, run S3 objects, URL parameter and
log streams absent. Two ECR run images remain by user direction
(105,624,604 bytes total, about 101 MiB). The shared RDS and ECS cluster remain
separate resources. Recheck before relying on this older snapshot.

## Cost and future work

DEC-12 accepted approximate cost estimates for the bounded PD-16 runs; they are
not an invoice or the final NFR-08 result. The account's USD 200 budget reference
is not a spending cap. Track later cloud spend and reserve, and complete the
project-wide reconciliation in CLOSE-00.

NEXT-04 directly uses this inventory and the [ID-01 demo postmortem](../evaluation/identity/id-01-step-12/demo-postmortem-20261026.md).
For current provider references, see [secret handling](secret-handling.md) and
[ID-01 setup](identity-provider-setup.md). Existing resource naming exceptions
are covered by the [resource naming decision](../decisions/cloud-resource-naming-and-tags.md).
The [shared/test Terraform README](../../infra/terraform/shared/test/README.md)
describes that module; it does not replace a fresh plan or approval.

| Account or project | `335523638354` — last checked 2026-10-19 20:27:40 UTC as IAM user `adityalaxmi1` with the approved non-root profile; account alias not determined |
| Region | `ap-south-1` (Asia Pacific — Mumbai), selected for the project and used by identity and inventory checks |
| Contributor CLI sign-in | Current operator Aditya used `adityalaxmi1`; verify the caller with STS before each approved action. The older `clip-project` profile observation below is historical; see [AWS CLI sign-in](README.md#aws-cli-sign-in). |
| Resources | PD-15/16 project resources were freshly checked read-only through 2026-10-19 20:37:27 UTC; see the live reconciliation below. October 17 observations remain historical; unrelated untagged resources are not adopted. |
| Service quotas | Selected applied/default limits recorded below; utilization/headroom unavailable from the quota-utilization report |
| Cost | Budget alerts configured for account `335523638354`; a read-only Cost Explorer query on 2026-10-17 returned estimated October unblended cost `-0.000000003 USD` through 2026-10-18. This near-zero estimate is not final or a project-wide/cross-account total. |

## PD-15/16 live resource reconciliation — 2026-10-19

Read-only resource checks were completed through **2026-10-19 20:37:27 UTC**. STS identity at 20:27:40 UTC confirmed profile `adityalaxmi1` in account `335523638354`. Project-tagged resources and the documented RDS, ECS, ASG, ECR, log, Parameter Store, network, IAM-role, and state-bucket records were checked against the approved PD-15/16 scope. All returned `Project=CLIP` resources were owned by PD-15 or PD-16; no domain-specific resource appeared. CloudTrail returned no non-read-only management events from the last confirmed shutdown at 18:23:35 UTC through 20:27:40 UTC. No Terraform plan/apply or cloud mutation ran. This is a scoped live check, not a scan of unrelated untagged account resources or a refresh-only Terraform plan.

| Component | Current observed status |
|---|---|
| State backend | Bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, Mumbai; versioning enabled, SSE-S3 (`AES256`), all S3 public-access blocks enabled, policy non-public and denies insecure transport. Both expected objects exist: `bootstrap/terraform.tfstate` and `shared/test/terraform.tfstate`. PD-15 owns the backend; preserve it and its versions during PD-16 cleanup. |
| Private network / NAT | Dedicated VPC `10.64.0.0/20` with the approved public/NAT subnet `10.64.0.0/24`, workload subnet `10.64.1.0/24` in `ap-south-1a`, and RDS-only subnet `10.64.2.0/24` in `ap-south-1b`. NAT `nat-0d7fefbad586f4bce` and the attached internet gateway are available. No default VPC adoption. |
| ECR / ECS capacity | Immutable, scan-on-push repository `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api` contains the approved image tag `68d6179db03dcf983278b290d22a939af625bba1`, digest `sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed`, 49,476,193 bytes. Cluster `clip-shared-test` is active with zero running/pending tasks. Its one approved API service is active but desired/running/pending counts are all zero. Capacity provider `clip-shared-test-capacity`; ASG min/desired 0, max 1, no instances. API revision 1, setup revision 3, and probe revision 1 task definitions are active; older setup revisions 1–2 are inactive. Tag lookup still returns the previously terminated host; it is not current capacity. |
| RDS / retention | `clip-shared-test-postgres`, resource ID `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, is stopped, private, encrypted, protected from deletion, PostgreSQL 18.6, `db.t4g.micro`, 20 GiB gp3, one-day automated-backup retention. The only returned snapshot is an available **automated** backup (`rds:clip-shared-test-postgres-2026-10-19-10-30`), not a manual final snapshot. No restart or teardown ran. |
| Credentials / IAM / logs | Master and probe parameters exist as SecureStrings, version 1; values were not read. The seven Terraform-owned `clip-shared-test-*` IAM roles exist. `/ecs/clip-shared-test` retains seven-day log retention and reports zero stored bytes. This check does not validate effective permissions or inspect state/log contents for secret leakage; see [secret references](secret-handling.md). |
| Tags / ownership | Read-back confirms PD-16 resources use `Project=CLIP`, `Environment=test`, `Task=PD-16`, `Owner=shared-team`, `ExpiresOn=2026-10-23`, as approved. The PD-15 state bucket has its named owner tag and `ExpiresOn=2026-10-26`. Existing naming exceptions remain as approved; no rename/retag was needed. Aditya is the current operator by explicit user direction. |
| Cost / holding period | Approximate base reference remains USD 61.66/720 hours with RDS running, before variable charges; this is not a current bill. RDS is stopped and ECS capacity is zero, but NAT, database storage/automated backups, ECR, logs, parameters, and backend remain retained and may incur charges. The accepted idle anchor/deadline is **2026-10-19 18:23:35 UTC → 2026-10-23 18:23:35 UTC**; cleanup still requires separate exact approvals. See [stop/resume plan](shared-test-rds-operations.md). |
| Acceptance | User confirmed the previously pending PD-08/09/12/13/15 upstream/platform/owner/peer gates on 2026-10-19. PD-16 operational closeout was accepted for now; the combined PD-17–19 review/merge and PRE-00 remain pending. |

The following October 17 inventory and PD-14 closeout are historical snapshots. This read-only update authorizes no cloud operation and does not replace an exact reviewed Terraform plan.

### Step 8 prerequisite refresh — 2026-10-19 16:49:57 UTC

User selected a two-hour test window and volunteered previously as operator. Official ARM64 Session Manager plugin 1.2.896.0 is installed locally. Approved root read-only billing returned five enabled eligible credits: USD 179.54 remaining / USD 179.49 estimated, expiry 2027-08-14; see [summary](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/step8-credit-summary.json). Root was not used for provisioning or IAM review. Current operator IAM metadata, read with `adityalaxmi1`, shows direct IAMFullAccess and developer-group PowerUserAccess/CLIPParameterStoreTeamAccess; no inline/attached policies exist on the three application task roles. This updates historical reported-policy facts for this operator only. The user resolved the Step 8 mismatch by approving [DEC-10 broad-human-operator access](../decisions/broad-human-operator-access.md); no additional human role or policy change is proposed; [preparation record](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/environment/pd16-service-plan-preparation.md). No service plan, IAM change, RDS restart or live SSM session ran.

## Step 4 read-only inventory — 2026-10-17 UTC

Checked the selected architecture services and networking dependencies in `ap-south-1`, plus the account-wide S3 bucket listing. This is not an exhaustive scan of every AWS service. No resource was created, changed, or deleted.

| Service/resource | Observed resources | Owner/use status |
|---|---|---|
| EC2/VPC | Default VPC `vpc-0b2b0d6d7a6f26ad8` (account owner `335523638354`); 3 default subnets; attached internet gateway `igw-0332ced57934b2681`; no NAT gateways; no EC2 instances | VPC/subnets/gateway are account-owned; no project-specific tag/name observed on the VPC. Security groups: `default` (`sg-0aefab8f97f8cebb7`) and `week8-lab-sg` (`sg-06f99fead30a15bc5`), both in the default VPC; individual owner/project use not established. |
| ECS | No clusters | — |
| Lambda | No functions | — |
| RDS | No DB instances or clusters | — |
| ECR | No repositories | — |
| Load balancing | No Application/Network Load Balancers or Classic Load Balancers | — |
| S3 | Bucket `ds252-w4-bucket-adityamedhe`, created 2026-09-11, located in `ap-south-1` | No owner/project tags; owner and purpose are unknown. Do not treat it as a CLIP project bucket without separate approval. |

The account-alias query was denied with `AccessDenied` for `iam:ListAccountAliases`; therefore no alias value is inferred. The Service Quotas utilization report completed but returned no utilization records for the queried project services, so remaining headroom/current usage is not established by these checks.

**Resource-use direction (Rahul, 2026-10-17):** Do not adopt or use the existing resources listed above for CLIP. Leave them untouched and create dedicated project resources only through the reviewed infrastructure workflow. Apply the project naming/tagging policy to every resource type that supports it; document exceptions because [AWS tagging support varies by resource type](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/what-are-tags.html). This direction does not approve provisioning or any other cloud change.

## Step 7 project resource naming and tagging — latest verified convention

Use this convention for future CLIP-owned resources; it does not authorize creation or modification. AWS resource naming and tag capabilities vary, so adapt only to service-specific character/length rules and record any exception in this inventory.

**Name format:** `clip-<environment>-<resource>-ap-south-1-<unique-suffix>` where the service permits it. Keep every component non-sensitive and comply with service-specific character and length rules. Do not include account IDs, personal email addresses, secrets, or user/listing data in names or tags. This convention does not authorize creating resources.

Apply these exact tag keys and meanings wherever the resource type supports tags:

| Tag key | Required value |
|---|---|
| `Project` | `CLIP` |
| `Environment` | Approved environment name, such as `dev`, `test`, `staging`, or `prod` |
| `Owner` | Named accountable person |
| `Task` | Owning task ID or domain |
| `ExpiresOn` | ISO `YYYY-MM-DD` expiry/cleanup date |

Tag keys are case-sensitive; preserve the spelling shown above. If a resource cannot be named/tagged or an expiry tag is not supported/applicable, record its exact resource identifier, unsupported field(s), reason, accountable owner, and expiry/cleanup handling here. Keep exceptions narrow and do not treat existing untagged account resources as project resources. Apply tags consistently to child resources and cost-bearing dependencies where supported.

Rahul verified this updated convention on 2026-10-17. It supersedes the earlier Step 7 convention recorded in this file; see [DEC-03](../decisions/cloud-resource-naming-and-tags.md).

### Observed quota values

Values below are applied limits unless marked as AWS defaults. These are limit values, not remaining capacity; the CLI returned unit `None` for these entries.

| Service | Quota | Observed value |
|---|---|---:|
| EC2 | Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances | 8 |
| EC2/VPC | Elastic IPs | 5 |
| ECS | Services per cluster (AWS default) | 5,000 |
| Lambda | Concurrent executions | 10 |
| RDS | DB instances | 20 |
| RDS | DB clusters | 40 |
| RDS | Total storage for all DB instances | 100,000 |
| Elastic Load Balancing | Application Load Balancers per Region | 50 |
| Elastic Load Balancing | Target Groups per Region | 3,000 |
| Elastic Load Balancing | Target Groups per Application Load Balancer | 100 |
| Elastic Load Balancing | Listeners per Application Load Balancer | 50 |
| S3 | Directory buckets (AWS default) | 100 |

No applied ECS or S3 quota rows and no quota-utilization records were returned for the queried service set. This is not evidence that usage is zero or that every quota is available; quota values/usages not listed here remain unverified.

## Step 5 cloud responsibility and access policy — 2026-10-17

These role assignments were directed by Rahul. They define responsibility, not blanket approval for a cloud change; each operation still requires the task's exact-target/plan/cost/rollback/cleanup approval.

| Responsibility | Assigned policy | Status/constraint |
|---|---|---|
| Approve infrastructure plans | Any team member: Aditya, Suraj, Mohit, or Rahul | Approval applies to the exact reviewed plan; approval is not permission to apply a changed plan. |
| Apply an approved plan | Any team member may apply | Name one human operator for each shared cloud-change window to serialize changes, per [CONTRIBUTING.md](../../CONTRIBUTING.md). |
| Billing alerts | Aditya | Rahul reports Aditya has billing visibility; this was not independently checked. |
| Cleanup | Shared across the team; the person who created/started the resources is first responsible | Cleanup scope must be tied to the approved project resources and exact cleanup plan. |
| AWS permissions | All four members intentionally retain `PowerUserAccess`; no least-privilege check is required for the current project phase | Aditya reported that `PowerUserAccess` remains for all users and `IAMFullAccess` was removed. This update is human-reported and not independently verified for all four identities. Rahul explicitly deferred least-privilege checks. Older read-only IAM observations and simulator results below remain historical evidence, not proof of current attachments/effective access. Aditya's root identity has not been exercised. |

Actual apply credentials/permission scopes and the selected per-window operator remain to be established before any apply. No standing access or cloud change is authorized by these role assignments. The user accepts the broad PowerUserAccess grants as intentional for now; additional service-specific access can be revisited when an approved plan identifies a need.

## Step 6 account-wide budget alerts — 2026-10-17

AWS Budgets API verification confirmed the following budget in account `335523638354`:

| Setting | Verified value |
|---|---|
| Name | `CLIP-Account-Actual-Spend-From-2026-10-17` |
| Period | Custom, 2026-10-17 through 2027-10-17 (one year; API timestamps correspond to midnight UTC / 05:30 Asia/Kolkata) |
| Reference amount | USD 200; notification reference only, not a hard spending cap |
| Cost basis | Actual incurred cost; `IncludeCredit=false` |
| Alerts | Email when actual cost is greater than USD 50, 80, 100, 120, or 130 (absolute thresholds) |
| Recipients at every threshold | All four team members (verified in the AWS subscriber query; addresses retained in the historical verification entry below) |
| Status at verification | Budget healthy; actual spend USD 0.00, forecast USD 1.223 |

Configuration and all five sets of subscribers were verified with read-only AWS Budgets API calls and human-verified by Rahul. These are five thresholds on one account-wide budget, not five separate budgets. The API endpoint is `us-east-1`, which is the billing-service endpoint used here; project resources remain in `ap-south-1`. This budget is account-wide but applies only to account `335523638354`; costs in another account are not aggregated. Rahul reports USD 140 in credits available and no near-term expiry; the amount and expiry were not independently checked, and Aditya does not need to reconfirm these user-provided facts. The selected alert basis is actual incurred spend, not remaining credit balance. No reserve or hard limit is set; do not wait until credits are exhausted before pausing or switching accounts. The alerts notify recipients and do not prevent spending. Cross-account project-spend reconciliation is deferred.

**Cost/credit safety direction (Rahul, 2026-10-17):** The team does not wish to pay out of pocket. Rahul reports USD 140 in credits available with no near-term expiry; do not ask Aditya to reconfirm those reported facts. For any proposed resource plan, check that its charges are eligible for these credits and that no out-of-pocket charge is expected; ask Aditya only if eligibility is unclear. Treat the existing USD 50 actual-cost notification as an immediate pause-and-review point for new billable work with Aditya, not as a hard stop or proof that charges are credit-covered. AWS applies credits only to eligible charges ([AWS credit application rules](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-credits.html)); AWS Budgets notifications can lag usage and arrive after thresholds are exceeded ([AWS alert timing](https://docs.aws.amazon.com/cost-management/latest/userguide/bcm-lite-view-budget.html)). Existing running-resource costs may continue. Do not wait for credits to be exhausted before stopping or considering another account. The exact shutdown/switch procedure and any numeric safety buffer remain undecided. No AWS configuration was changed by this direction.

## PD-14 task-wide closeout review — 2026-10-17 UTC

Read-only recheck on 2026-10-17 confirmed STS identity `arn:aws:iam::335523638354:user/rahulkoyye` in account `335523638354`. `describe-budget` confirmed the configured one-year USD 200 reference budget, actual-cost basis with credits excluded, and the documented period. The five actual-spend thresholds (USD 50/80/100/120/130) and all four email subscribers at every threshold were re-confirmed. Cost Explorer was queryable from Rahul's profile; October 1–18 unblended cost was `-0.000000003 USD`, marked estimated. This does not verify Aditya's separate billing visibility or aggregate total project spend across accounts.

Read-only `iam:GetUser`, `iam:ListAttachedUserPolicies`, and `iam:ListGroupsForUser` calls were denied. Therefore IAM attachments, effective least privilege, and all-four SSM/KMS access are not verified; this is not proof that the reported administrator access is absent, but the report cannot be independently confirmed from this profile. A Parameter Store name-only query returned no `/clip/` parameters, and the `alias/aws/ssm` KMS alias is present in `ap-south-1`; no values were retrieved and no parameters, keys, policies, or other AWS resources were changed. Repository review found no credential-signature matches in the environment/work-log records, and `git diff --check 4754e97..HEAD` passed.

**PD-14 closeout snapshot (2026-10-17): documentation decisions complete; cloud configuration was intentionally unimplemented at that time.** Account identity, approved region, one account-level budget with five alert thresholds, project conventions, and team approval/cleanup responsibilities are recorded. Cross-account spend reconciliation is deferred. Current all-four `PowerUserAccess` and removal of Rahul's former `IAMFullAccess` are reported by Aditya but have not been independently rechecked; least-privilege checks are intentionally skipped. Parameter Store remains a selected future access method, not a configured service. Alerts are not a cap or credit-balance monitor. Rahul reports USD 140 in credits with no near-term expiry. Check credit eligibility for each proposed plan; do not require Aditya to reconfirm the reported balance or expiry.

### Current IAM/SSM permission recheck — 2026-10-17

Historical read-only IAM inspection on 2026-10-17 succeeded for Rahul's identity. At that time the account had IAM users `rahulkoyye`, `surajs2`, and `mohitmahapa1` in `DS252-Project-Developers`, whose attached policy was AWS-managed `PowerUserAccess`. Rahul additionally had AWS-managed `IAMFullAccess`; Suraj and Mohit each had AWS-managed `IAMUserChangePassword`. None of those three users had an inline user policy or permissions boundary. Policy simulation allowed the checked project-path SSM read/write/delete/history/tag actions and selected-key KMS encrypt/decrypt actions for these three identities. No `/clip/` parameter existed, so no live parameter value operation was tested. Aditya later reported that all four retain `PowerUserAccess` and `IAMFullAccess` was removed. The newer attachment state has not been independently checked; Rahul accepted the grants as intentional and waived least-privilege checks. Aditya's root use remains user-reported and no root sign-in was attempted.

### Step 9 service apply — 2026-10-19 17:18:01 UTC

Approved checksum applied after commit `2978461`: seven resources created (API service, three task definitions, probe SecureString and two execution-role policies), no changes/deletions. [Result](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/service-apply-result.json). RDS still stopped; immediate API snapshot desired 1/pending 1/running 0, ASG desired/hosts 0 while managed scaling starts. This supersedes the base-only capacity/credential inventory above. Window ends **2026-10-19 19:17:08 UTC**; no automatic shutdown. Actual runtime readiness and SSM/SQL remain pending.

### Step 10 live database check — 2026-10-19 17:36:32 UTC

User authorized RDS start and fixed setup/probe sequence. Original RDS now available (start 17:30:03 UTC, available 17:34:25); one host/API still running. Setup revision 2 failed its logging guard before mutation; probe skipped. [Execution](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/database-action-result.json). This supersedes prior stopped status. Compute/NAT/storage remain billable; original window expires 19:17:08 UTC, no automatic shutdown. No logging changes or automatic repair; await decision.

### Step 10 successful database verification — 2026-10-19 17:51:23 UTC

[Setup revision 3 and probe revision 1 passed](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/database-retry-result.json); restricted `clip_test_probe` login and test DB ACL hardening now exist. Transaction-local logging checks/suppression succeeded without global parameter changes. Both one-shot tasks stopped; API/one host and RDS remain running. Initial revision-2 failure is historical. Web hosting needs a separately approved target/access; no domain/NFR acceptance. Window expires 19:17:08 UTC; no automatic shutdown.

### Current compute status — 2026-10-19 18:24:12 UTC

**Compute off:** API desired/running/pending 0, cluster tasks 0, ASG desired/hosts 0; original host terminated 18:17:10 UTC. Original RDS resource `db-PYRRZJPVKPGHIXDAHUWATXGH7A` verified stopped **18:23:35 UTC**. [Shutdown evidence](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/compute-stop-result.json). Supersedes preceding running snapshots. DB storage, ECR images, task definitions, network and state retained; NAT/storage/backups/logs remain billable. Resume needs separate RDS-start and fresh service-enable-plan approvals. Cleanup review date 2026-10-23 and unresolved exact idle-deadline/contact gates remain unchanged; RDS may auto-restart after seven stopped days.

### Step 12 read-only budget/utilization review — 2026-10-19

Five USD 50/80/100/120/130 alerts and all four historical subscriber routes reverified; no email sent. Budget actual USD 0.04/forecast USD 1.232 was last updated at 13:42:11 UTC, before the run; run-charge reconciliation awaits refreshed billing. [Review and utilization limits](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/foundation/pd-16/step12-cost-review.md). No Cost Explorer request/root fallback or resource change; compute remains off. Corrected period timezone description: actual API boundaries are midnight UTC, 05:30 IST.

### Accepted operator and idle deadline — 2026-10-19 UTC

User named **Aditya** as current operator and accepted a 96-hour idle clock from verified full shutdown **2026-10-19 18:23:35 UTC** to **2026-10-23 18:23:35 UTC** (23:53:35 IST). This supersedes earlier unaccepted exact-deadline proposals and unnamed-operator notes. `Owner=shared-team`/date-only expiry tag remain approved. No automatic deletion is installed/authorized; Aditya initiates separately reviewed cleanup if still idle. New approved runs update the clock.

### Cost precision accepted — 2026-10-19 UTC

User accepted approximate recent bounded PD-16 run costs and negligible run impact for closeout; exact delayed-charge reconciliation is no longer a blocker ([DEC-12](../decisions/foundation-cost-review-precision.md)). Earlier dated billing-follow-up notes are superseded on that point. Estimates remain estimates, not a measured zero or bill. Retained NAT/storage/other costs, USD 50 pause/review point, USD 25 reserve and project-wide budget still apply. No billing/resource action occurred.

### ID-01 SES sender policy applied — 2026-10-23 06:17:00 UTC

Aditya approved/applied exact saved plan `baa80880c96c379289a90a482a888aac9cc5d087aba40e211a17677a18695e9a`
in the existing shared test root/state. Added inline policy
`clip-shared-test-identity-email` to `clip-shared-test-api-task`, allowing only
SendEmail for verified `clip-iisc.site` with exact From `no-reply@clip-iisc.site`.
Role-policy JSON/state verified; state serial 9 and lock absent. Compute remains
off: original RDS stopped, ECS/ASG zero. No deployment or email send; actual
runtime delivery unverified. Existing idle clock/retained costs unchanged;
policy retained until separately reviewed removal. [Evidence](../evaluation/identity/provider-history.md#setup-and-permissions).

### ID-01 temporary AMD64 builder running — 2026-10-23 07:11:04 UTC

Aditya approved the exact builder plan plus one bounded native build and owned
VM/disk cleanup. Five-resource apply succeeded in Identity state (serial 2):
private t3.small `i-086dd4b9830033682`, encrypted root `vol-0125a996fffc44f69`,
security group `sg-00f275fda4e0f5104`, dedicated builder role/policy/profile.
No public IP/ingress and exact role policy verified. OS shutdown terminates and
root DeleteOnTermination true. Launched 2026-10-23 07:10:15 UTC; operator hard
expiry 2026-10-23 08:10:15 UTC, USD 1 incremental cap. SSM online; bootstrap timer
verification pending. Source remains `52186a0`; no build/push/send yet. Shared
RDS/ECS/ASG remain off; original shared idle deadline unchanged. Temporary IAM/
profile/group removal retains separate exact cleanup-plan approval.

### ID-01 builder image validated; cleanup scheduled — 2026-10-23 07:16:45 UTC

Supersedes pending bootstrap/build state above: timer/SSM/Docker/native checks and
one committed-source build passed. Exact image/source and checks are in
[build evidence](../evaluation/identity/provider-history.md#builder-and-image).
Builder remains private/running; approved absolute shutdown timer verified for
08:10:00 UTC (earlier than one-hour operator expiry). No image publication or
application email. Termination/root-volume deletion remain unverified until
actual cleanup; temporary role/profile/policy/group require later removal plan.

### ID-01 image published; builder VM/disk removed — 2026-10-23 07:23:06 UTC

Supersedes the preceding running-builder snapshots. Exact committed-source image
published/verified under approved tag `id01-amd64-52186a0466fe`, immutable digest
`sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`
in existing `clip-shared-test-api`. Size 68,148,997 registry bytes; retained for
runtime-test handoff, image removal separately reviewed. Builder
`i-086dd4b9830033682` terminated and root `vol-0125a996fffc44f69` absent verified
07:22:28.116194 UTC. No builder compute/disk retained. Dedicated builder role,
inline policy, profile and group `sg-00f275fda4e0f5104` remain pending approved
Identity-root removal plan. RDS stopped/ECS/ASG zero confirmed; original shared
idle deadline unchanged. No application runtime task/email. [Evidence](../evaluation/identity/provider-history.md#builder-and-image).

### Concurrent RDS start observed during Identity preflight — 2026-10-23 09:12:58 UTC

Supersedes the RDS-stopped observation above for the latest snapshot only:
original RDS resource `db-PYRRZJPVKPGHIXDAHUWATXGH7A` reported `starting` at
09:11:20 UTC. CloudTrail records IAM user `surajs2` starting it without error at
08:49:32 UTC, after two capacity errors. This Identity session made no DB change;
concurrent operator/task approval/window not established here. ECS cluster and
ASG remained at zero in the snapshot. [Evidence](../evaluation/identity/provider-history.md#builder-and-image).

### ID-01 smoke definition registered; temporary builder fully removed — 2026-10-23 09:27:10 UTC

Approved Identity saved-plan apply registered
`arn:aws:ecs:ap-south-1:335523638354:task-definition/clip-test-identity-email-ap-south-1-id01:1`
with exact verified image/shared roles and disabled-by-default email controls.
No task launched. Temporary builder role/policy/profile and security group now
verified absent, superseding their retained status above. VM/root cleanup already
verified; Identity state serial 3 contains no builder resources and lock is absent.
ECS/ASG capacity stays zero; no RDS calls/change under approved concurrent-work
exclusion. Image retained for test, task definition retained for separately
approved run/cleanup; no email. [Evidence](../evaluation/identity/provider-history.md#builder-and-image).

### ID-01 first runtime invocation: no compute observed — 2026-10-23 09:49:29 UTC

Approved one CLI RunTask invocation failed; no task ARN/matching task or host
observed. At 09:48:44.053417 UTC cluster/ASG capacity remained zero. Image/task
retained, builder fully removed, no RDS calls/change. No owned resource required
cleanup, no automatic retry. [Result](../evaluation/identity/provider-history.md#delivery-diagnostics).

### ID-01 corrected single runtime request accepted — 2026-10-23 09:55:32 UTC

Aditya explicitly approved one corrected idempotent request under the same
one-message/one-host/45-minute/USD1 scope. Original marker/token reused; prior
task/audit reconciliation and fresh preflight passed; memory-file input validated
offline. Task `f5352e809bfb4d5e87f1d72f6aff8e6f` accepted PROVISIONING using
registered :1 and existing capacity provider. Exact window starts
09:55:23.140122 UTC, expires 10:40:23.140122 UTC. No RDS calls; API service remains
disabled. Monitoring/cleanup in progress; email submission/receipt not yet proved.

### ID-01 runtime stopped; owned ECS capacity removed — 2026-10-23 10:14:29 UTC

Supersedes the corrected-request provisioning snapshot. Exact :1 task ran and
exited1; no delivery accepted, human reports no email. Existing managed scale-in
terminated only test host `i-06514fe65a4232752` and deleted root
`vol-028a4fa0eea059363`, verified 10:14:07.756278 UTC before the run expiry.
Cluster/service/ASG zero, no manual backstop or other workload interruption.
No RDS calls; concurrent DB use remains untouched/unverified here. No new live
retry. Image/definition/content-free logs retained for approved diagnostic handoff;
builder remains fully removed. [Evidence](../evaluation/identity/provider-history.md#delivery-diagnostics).

### ID-01 diagnostic ECS host promptly removed — 2026-10-23 16:57:21 UTC

One approved diagnostic task8d59687bbf7f446d84591adf7a81f1e6 ran and exited1
with SES AccessDeniedException; no resend. Sole owned host i-093fdd05f7b394ef5
and root vol-07e5d27895688b25a removed after guarded prompt SetDesiredCapacity(0),
verified16:57:09.886355 UTC; ECS tasks/registered hosts and ASG desired/instances
zero. No managed alarm/scaling/draining configuration change or other workload
interruption. RDS calls0; concurrent database state remains outside this record.
Image/task/log proof retained; [diagnostic evidence](../evaluation/identity/provider-history.md#delivery-diagnostics).

### ID-01 sandbox recipient permission and real delivery verified — 2026-10-23 17:17:30 UTC

Shared inline SES policy now permits the sender domain plus one privately supplied
controlled-recipient identity under the unchanged exact sender condition. Exact
reviewed single-update plan36e9738a7120549a9541f0571fb3b213994ebba8efc04edad1566115a11e3d47
applied; state serial10/lock release/attached policy verified, no other managed
change. Shared-root refresh read RDS metadata without a DB change.

Enhanced diagnostic host i-01edad09fd8c5e4d4/root vol-0dd35ab2e3a7797c4 removed
17:10:41.527682 UTC. Corrected verification task403eba24a7d2428394d76272148ab882
accepted actual SES submission and human inbox receipt. Its host
i-0bbef51578c9e5ecf/root vol-04f1705171090cf51 removed17:17:09.706322 UTC.
Both used guarded prompt cleanup; ECS/ASG zero, runtime RDS calls0, no other
workload interrupted. Normal managed scaling/draining unchanged. Images/task
definition/log evidence retained. SES sandbox/production access pending.
[Evidence](../evaluation/identity/provider-history.md#delivery-diagnostics).


### ID-01 private database preflight cleanup — 2026-10-24 21:59:41 UTC

Aditya explicitly approved the1hour preflight window anchored21:40:05 UTC, account
335523638354/ap-south-1. Original RDS resource db-PYRRZJPVKPGHIXDAHUWATXGH7A
started and is now confirmed stopped. One existing Identity definition:1 task ran
with sleep-only overrides, no secrets or exposed ports. Verified private SSM tunnel
and hostname-verified TLS; metadata inspection failed UndefinedTable before a
complete safe snapshot, likely public.schema_migrations absent, not independently
confirmed. One approved master-secret read requested privately; no DB writes or
key/email-secret reads. No schema/role/grant/URL/provider readiness claimed.

Cleanup confirmed: task/tunnel stopped, cluster hosts/tasks0, API desired/running/
pending0, ASG desired0/empty, owned i-00c9b68c7757c8da2 terminated and root
vol-0161f12c2748b1dc7 deleted; no active SSM sessions. Guarded early scale-in initially
rejected ScalingActivityInProgress, later accepted with honor-cooldown and fresh
idle checks. NAT/data/SSM/IAM/task definitions/state retained; ongoing retained
costs continue. No network or shared-policy change. [Sanitized record](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/identity/id-01-step-12/database-preflight-result.json).


### ID-01 renewed metadata and cleanup — 2026-10-24 22:27:20 UTC

Approved one-hour window22:13:36→23:13:36 UTC, account335523638354/ap-south-1,
collector9bfb607. Verified private tunnel/TLS and completed read-only catalog
inspection: public.schema_migrations absent, all14expected Identity tables absent,
Identity login absent; PUBLIC ACL counts0. One effective logging mismatch and
catalog SET flagsfalse require review, not automatic grants/global changes.
One approved private master-secret read; no role/schema/grant/logging/data writes,
key/email-secret read, send, deployment, network or IAM change.

Cleanup verified within window: original RDS resource db-PYRRZJPVKPGHIXDAHUWATXGH7A
stopped; sleep task1f26b751601944c4a0fcf7d88e179f32 stopped; SSM session closed;
ASG0/empty; cluster hosts/tasks0; API desired/running/pending0. Owned host
i-09708de46c0fa931a terminated and rootvol-00c3b7f86b1613fed deleted. Guarded
scale-in accepted with cooldown honored. NAT/data/parameters/state/IAM/task
retention unchanged; existing retained costs continue. [Sanitized report](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/identity/id-01-step-12/database-preflight-followup-result.json).


### Logging probe start rejected — 2026-10-25 04:06:31 UTC

Authenticated operator/idle guards passed under explicit logging-only approval.
Original RDS start rejected: InsufficientDBInstanceCapacity for db.t4g.micro in
ap-south-1a. Resource db-PYRRZJPVKPGHIXDAHUWATXGH7A rechecked stopped. No task,
host, session or secret read was started; no SQL, IAM/network/class/AZ change or
cleanup operation. Existing retained NAT/storage/etc. remain unchanged. [Result](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/identity/id-01-step-12/logging-probe-start-result.json).


### Logging retry startup/cleanup pending — 2026-10-25 04:37:19 UTC

Supersedes the preceding stopped observation: Aditya explicitly requested retry,
original RDS start accepted with recovery event04:16:15.760UTC. Resource
 db-PYRRZJPVKPGHIXDAHUWATXGH7A remains starting after20minute readiness bound.
No host/task/tunnel/secret read/probe SQL. Approved stop request rejected
InvalidDBInstanceState (requires available); cleanup pending. Shared API/ASG/tasks/
sessions rechecked zero/empty. No class/AZ/role/grant/IAM/network/schema change;
no automatic retry or unapproved wait extension. Original window ends05:05:35UTC.
[Retry record](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/identity/id-01-step-12/logging-probe-retry-result.json).


### Logging-only retry stopped baseline restored — 2026-10-25 04:53:05 UTC

Supersedes prior startup/stopping observations. AWS accepted the explicit retry,
then aborted recovery for insufficient db.t4g.micro capacity in ap-south-1a
(event04:37:55.153UTC) and put the original RDS into stopping. Our cleanup stop
call had been rejected InvalidDBInstanceState; do not attribute shutdown to it.
Original resource db-PYRRZJPVKPGHIXDAHUWATXGH7A now confirmed stopped. Cluster
hosts/tasks0, API desired/running/pending0, ASG0/empty and active sessions0. No
child resources launched, credential retrieved, SQL probe/data/schema/role write,
class/AZ/IAM/network change or alternative infrastructure. Retained NAT/storage/
parameters/state unchanged; their ongoing costs remain. [Final record](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/identity/id-01-step-12/logging-probe-retry-result.json).


### Live logging probe passed; stopped baseline restored — 2026-10-25 05:41:05 UTC

Aditya explicitly requested same-scope retry; new05:22:29→06:22:29UTC/1USD window.
Original class/AZ/private target and idle guards matched. RDS available, one exact
sleep-only task, verified private host/SSM and verify-full TLS. Committed ca935b9
logging probe returned completed/rollback_verified true, no failure phase;6local
settings and6NOLOGIN defaults accepted, then role absent/original baseline verified.
One private master-secret read; no permanent role/data/default changes, migrations,
auth-key/email-secret reads or provider operation. No class/AZ/IAM/network changes.

Cleanup verified: original RDS resource db-PYRRZJPVKPGHIXDAHUWATXGH7A stopped;
owned task8d71d4f672504d10b94c713c647b0fce stopped, tunnel closed; cluster hosts/tasks0,
API desired/running/pending0, ASG0/empty, no active sessions. Owned host
i-0be3743fe59a127bf terminated and rootvol-0806db641df31317b deleted. Guarded
scale-in accepted with honor-cooldown. NAT/data/parameters/state retained; baseline
retention costs continue. [Successful probe record](https://github.com/exocrat/clip/blob/a60c83f21f285ec0d32d72108035c9d159194b24/docs/evaluation/identity/id-01-step-12/logging-probe-20261025T052229Z.json).

### ID-01 Step14 stopped consumer wiring — 2026-10-28 19:54:52 UTC

Account335523638354/Mumbai, shared/test backend25; approved plan1ae7c926…5636
applied. API `clip-test-api-ap-south-1-pd16:8` has separate Conversations DSN
injection; execution-role policy `clip-shared-test-api-conversations-secret`
reads only `/clip/test/conversations/database-url`. Service desired/running/
pending0, ASG0/empty/max1, RDS stopped/private/protected. Prior image and
256CPU/512MiB retained; Hybrid off. No resource starts/new compute, bucket, DB,
network or data changes. Role/parameter provisioning remains separate; new
parameter metadata absent. Retain stopped definition/policy for next reviewed
window; removal/rollback requires a fresh reviewed plan. Aditya owns cleanup;
existing retained NAT/storage charges continue.
[Exact plan/result](../evaluation/identity/id-01-step-14/stopped-config-result.json).

### ID-01 Step14 role window stopped — 2026-10-28 20:31:28 UTC

User-requested cleanup complete: i-036a77b684c9ba694 terminated,
vol-083ee1bd19529468f absent, ASG0/empty/max1, API0, RDS stopped; owned deadline
and tunnel removed. New parameter absent; provisioning blocked in preflight
before any master/SQL/SSM operation. Retain task8/scoped policy and shared
NAT/network/storage/data/keys/images. Existing retention charges continue.
[Resume/result](../evaluation/identity/id-01-step-14/provisioning-window-result.json).

### ID-01 Step14 role retry cleanup — 2026-10-29 04:14:41 UTC

Approved retry created the reviewed Conversations login and SecureString v1.
Owned i-0fecb5c82b2569f92/root, tunnel and fallback removed; API/ASG0, RDS
stopped. Role/parameter retained for integration; shared NAT/storage remain.
[Result](../evaluation/identity/id-01-step-14/provisioning-window-retry-result.json).

### ID-01 Step14 real integration cleanup — 2026-10-29 05:10:26 UTC

Approved teardown complete: API0/task10, ASG0, RDS stopped; owned private/proxy
hosts and roots, EIP, tunnel and fallback removed. User confirmed DNS deletion.
Synthetic listing/image and narrow catalogue grants retained; Suraj review and
durable grant restoration pending. Shared NAT/storage continue accruing charges.
[Result](../evaluation/identity/id-01-step-14/s3-conversations-teardown-result.json).

Latest Phase A v2 closeout (2026-10-30 18:20:36 UTC): [receipt and exact execution evidence](../evaluation/domain/next-06/transfer/phase-a-v2-20261030/result.json). Both existing resources verified stopped. The runtime role reached the migrations query and was denied SQLSTATE42501; no grants or other repairs made. Real load/metadata gates remain pending.

Latest NEXT-06 administrative inventory (2026-10-30 18:46:54 UTC): [executed receipt and binding comparison](../evaluation/domain/next-06/transfer/admin-inventory-20261030/result.json). Read-only inventory passed;32migrations/four schemas; proposed NEXT-06 database and roles absent. Cloud adds three migrations beyond local/corpus29; reconcile accepted source before setup/load. Owned tunnel/session closed and both resources verified stopped. No grants, schema/data writes or uploads occurred.

NEXT-06 isolated setup (2026-10-30 19:20:00 UTC): [actual successful execution and stopped closeout](../evaluation/domain/next-06/transfer/database-setup-20261030/result.json). New clip_next06_reference has29accepted migrations and explicit loader grants; clip_next06_loader/clip_next06_runtime remain NOLOGIN/no password, runtime no grants. Shared32database/service unchanged. No business rows, credential publication or S3objects yet. Owned access closed, both resources verified stopped. Next loader credential/S3/SQL load requires its exact prepared approval.

NEXT-06 live load (2026-10-31 08:25:12 UTC): [actual S3/RDS execution, sources and ledger](../evaluation/domain/next-06/transfer/cloud-load-20261031/result.json).1000images/925881224bytes verified in existing id01bucket prefix id01/next06-reference-42-v1;5000users/1000listings+image records loaded into isolated clip_next06_reference29schema,800discoverable; SQLprojection matches native. Loader password cleared/NOLOGIN, runtime inactive, owned access closed, host/RDSverified stopped. Shared32service unchanged. Retain objects/data; no retry/reset. Real app/auth/signed-media/cloud ML/source-label/reproducibility/freeze remain pending; DATA-READY false.

NEXT-06 actual vector publication (2026-10-31 09:46:20 UTC): [execution/coverage/cleanup evidence](../evaluation/domain/next-06/transfer/vector-production-20261031/result.json). Isolated clip_next06_reference now has1000current ready generations/2000actual pinned384-dimensional parts and serving pipeline4b43fc30...; six actual keyword/HybridSQLcases match native and source corpus rows remain unchanged. Dedicated producer password cleared/NOLOGIN; model/access closed and EC2/RDSstopped. No S3or original runtime/service changes. Actual authenticated app/media/normal new-vector workflow and deployedLinuxruntime/source-label/rebuild/freeze acceptance remain pending; DATA-READY false.
