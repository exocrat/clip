# Cloud environment inventory

Non-secret status template. Update only from approved plans and verified outputs. Never record secret values here.

| Fact | Current status |
|---|---|
| Account or project | `335523638354` — verified by read-only STS caller identity as IAM user `rahulkoyye`; account alias not determined because this profile lacks `iam:ListAccountAliases` |
| Region | `ap-south-1` (Asia Pacific — Mumbai), selected for the project and used by identity and inventory checks |
| Contributor CLI sign-in | Rahul's local `clip-project` profile; `aws login --profile clip-project`, then verify with `aws sts get-caller-identity --profile clip-project`; see [AWS CLI sign-in](README.md#aws-cli-sign-in) |
| Resources | Step 4 read-only inventory on 2026-10-17: see scoped findings below; resource ownership/project use is unverified for untagged resources |
| Service quotas | Selected applied/default limits recorded below; utilization/headroom unavailable from the quota-utilization report |
| Cost | Budget alerts configured for account `335523638354`; a read-only Cost Explorer query on 2026-10-17 returned estimated October unblended cost `-0.000000003 USD` through 2026-10-18. This near-zero estimate is not final or a project-wide/cross-account total. |

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

Rahul verified this updated convention on 2026-10-17. It supersedes the earlier Step 7 convention recorded in this file; see [DEC-03](../decisions/DEC-03-cloud-resource-naming-and-tags.md).

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
| Period | Custom, 2026-10-17 through 2027-10-17 (one year; API timestamps correspond to midnight Asia/Kolkata) |
| Reference amount | USD 200; notification reference only, not a hard spending cap |
| Cost basis | Actual incurred cost; `IncludeCredit=false` |
| Alerts | Email when actual cost is greater than USD 50, 80, 100, 120, or 130 (absolute thresholds) |
| Recipients at every threshold | All four team members (verified in the AWS subscriber query; addresses retained in the historical verification entry below) |
| Status at verification | Budget healthy; actual spend USD 0.00, forecast USD 1.223 |

Configuration and all five sets of subscribers were verified with read-only AWS Budgets API calls and human-verified by Rahul. The API endpoint is `us-east-1`, which is the billing-service endpoint used here; project resources remain in `ap-south-1`. This budget is account-wide but applies only to account `335523638354`; costs in another account are not aggregated. Rahul reports USD 140 in credits available; this balance is not independently verified. The selected alert basis is actual incurred spend, not remaining credit balance. No reserve or hard limit is set; if credits are exhausted, the team expects to switch accounts. The alerts notify recipients and do not prevent spending. Cross-account project-spend reconciliation is deferred.

**Cost/credit safety direction (Rahul, 2026-10-17):** The team does not wish to pay out of pocket. Do not approve or provision new billable CLIP resources until Aditya confirms the current credit balance, expiry, eligible services, and whether a stronger spend-control feature is available for this account. Treat the USD 50 actual-cost notification as an immediate pause-and-review point for new billable work with Aditya, not as a hard stop or proof that charges are credit-covered. AWS applies credits only to eligible charges ([AWS credit application rules](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/useconsolidatedbilling-credits.html)); AWS Budgets notifications can lag usage and arrive after thresholds are exceeded ([AWS alert timing](https://docs.aws.amazon.com/cost-management/latest/userguide/bcm-lite-view-budget.html)). Existing running-resource costs may continue. Do not wait for credits to be exhausted before stopping or considering another account. The exact shutdown/switch procedure and any numeric safety buffer remain undecided. No AWS configuration was changed by this direction.

## PD-14 task-wide closeout review — 2026-10-17 UTC

Read-only recheck on 2026-10-17 confirmed STS identity `arn:aws:iam::335523638354:user/rahulkoyye` in account `335523638354`. `describe-budget` confirmed the configured one-year USD 200 reference budget, actual-cost basis with credits excluded, and the documented period. The five actual-spend thresholds (USD 50/80/100/120/130) and all four email subscribers at every threshold were re-confirmed. Cost Explorer was queryable from Rahul's profile; October 1–18 unblended cost was `-0.000000003 USD`, marked estimated. This does not verify Aditya's separate billing visibility or aggregate total project spend across accounts.

Read-only `iam:GetUser`, `iam:ListAttachedUserPolicies`, and `iam:ListGroupsForUser` calls were denied. Therefore IAM attachments, effective least privilege, and all-four SSM/KMS access are not verified; this is not proof that the reported administrator access is absent, but the report cannot be independently confirmed from this profile. A Parameter Store name-only query returned no `/clip/` parameters, and the `alias/aws/ssm` KMS alias is present in `ap-south-1`; no values were retrieved and no parameters, keys, policies, or other AWS resources were changed. Repository review found no credential-signature matches in the environment/work-log records, and `git diff --check 4754e97..HEAD` passed.

**Closeout state: documentation decisions complete; cloud configuration remains intentionally unimplemented.** Account identity, approved region, account-level budget alerts, project conventions, and team approval/cleanup responsibilities are recorded. Cross-account spend reconciliation is deferred. Current all-four `PowerUserAccess` and removal of Rahul's former `IAMFullAccess` are reported by Aditya but have not been independently rechecked; least-privilege checks are intentionally skipped. Parameter Store remains a selected future access method, not a configured service. Alerts are not a cap or credit-balance monitor. Rahul has since confirmed a strict no-out-of-pocket intent; Aditya's credit eligibility/expiry and available spend controls must be confirmed before any billable provisioning.

### Current IAM/SSM permission recheck — 2026-10-17

Historical read-only IAM inspection on 2026-10-17 succeeded for Rahul's identity. At that time the account had IAM users `rahulkoyye`, `surajs2`, and `mohitmahapa1` in `DS252-Project-Developers`, whose attached policy was AWS-managed `PowerUserAccess`. Rahul additionally had AWS-managed `IAMFullAccess`; Suraj and Mohit each had AWS-managed `IAMUserChangePassword`. None of those three users had an inline user policy or permissions boundary. Policy simulation allowed the checked project-path SSM read/write/delete/history/tag actions and selected-key KMS encrypt/decrypt actions for these three identities. No `/clip/` parameter existed, so no live parameter value operation was tested. Aditya later reported that all four retain `PowerUserAccess` and `IAMFullAccess` was removed. The newer attachment state has not been independently checked; Rahul accepted the grants as intentional and waived least-privilege checks. Aditya's root use remains user-reported and no root sign-in was attempted.
