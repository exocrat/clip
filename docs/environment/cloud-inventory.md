# Cloud environment inventory

Non-secret status record. Update only from approved plans and verified outputs. Never record credentials, tokens, or secret values here. This is an observed snapshot, not an authorization to use existing resources or create/change/delete cloud infrastructure.

| Fact | Current status |
|---|---|
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

User selected a two-hour test window and volunteered previously as operator. Official ARM64 Session Manager plugin 1.2.896.0 is installed locally. Approved root read-only billing returned five enabled eligible credits: USD 179.54 remaining / USD 179.49 estimated, expiry 2027-08-14; see [summary](../evaluation/foundation/pd-16/step8-credit-summary.json). Root was not used for provisioning or IAM review. Current operator IAM metadata, read with `adityalaxmi1`, shows direct IAMFullAccess and developer-group PowerUserAccess/CLIPParameterStoreTeamAccess; no inline/attached policies exist on the three application task roles. This updates historical reported-policy facts for this operator only. The user resolved the Step 8 mismatch by approving [DEC-10 broad-human-operator access](../decisions/broad-human-operator-access.md); no additional human role or policy change is proposed; [preparation record](pd16-service-plan-preparation.md). No service plan, IAM change, RDS restart or live SSM session ran.

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

Approved checksum applied after commit `2978461`: seven resources created (API service, three task definitions, probe SecureString and two execution-role policies), no changes/deletions. [Result](../evaluation/foundation/pd-16/service-apply-result.json). RDS still stopped; immediate API snapshot desired 1/pending 1/running 0, ASG desired/hosts 0 while managed scaling starts. This supersedes the base-only capacity/credential inventory above. Window ends **2026-10-19 19:17:08 UTC**; no automatic shutdown. Actual runtime readiness and SSM/SQL remain pending.

### Step 10 live database check — 2026-10-19 17:36:32 UTC

User authorized RDS start and fixed setup/probe sequence. Original RDS now available (start 17:30:03 UTC, available 17:34:25); one host/API still running. Setup revision 2 failed its logging guard before mutation; probe skipped. [Execution](../evaluation/foundation/pd-16/database-action-result.json). This supersedes prior stopped status. Compute/NAT/storage remain billable; original window expires 19:17:08 UTC, no automatic shutdown. No logging changes or automatic repair; await decision.

### Step 10 successful database verification — 2026-10-19 17:51:23 UTC

[Setup revision 3 and probe revision 1 passed](../evaluation/foundation/pd-16/database-retry-result.json); restricted `clip_test_probe` login and test DB ACL hardening now exist. Transaction-local logging checks/suppression succeeded without global parameter changes. Both one-shot tasks stopped; API/one host and RDS remain running. Initial revision-2 failure is historical. Web hosting needs a separately approved target/access; no domain/NFR acceptance. Window expires 19:17:08 UTC; no automatic shutdown.

### Current compute status — 2026-10-19 18:24:12 UTC

**Compute off:** API desired/running/pending 0, cluster tasks 0, ASG desired/hosts 0; original host terminated 18:17:10 UTC. Original RDS resource `db-PYRRZJPVKPGHIXDAHUWATXGH7A` verified stopped **18:23:35 UTC**. [Shutdown evidence](../evaluation/foundation/pd-16/compute-stop-result.json). Supersedes preceding running snapshots. DB storage, ECR images, task definitions, network and state retained; NAT/storage/backups/logs remain billable. Resume needs separate RDS-start and fresh service-enable-plan approvals. Cleanup review date 2026-10-23 and unresolved exact idle-deadline/contact gates remain unchanged; RDS may auto-restart after seven stopped days.

### Step 12 read-only budget/utilization review — 2026-10-19

Five USD 50/80/100/120/130 alerts and all four historical subscriber routes reverified; no email sent. Budget actual USD 0.04/forecast USD 1.232 was last updated at 13:42:11 UTC, before the run; run-charge reconciliation awaits refreshed billing. [Review and utilization limits](../evaluation/foundation/pd-16/step12-cost-review.md). No Cost Explorer request/root fallback or resource change; compute remains off. Corrected period timezone description: actual API boundaries are midnight UTC, 05:30 IST.

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
