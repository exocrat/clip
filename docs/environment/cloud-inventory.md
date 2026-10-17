# Cloud environment inventory

Non-secret status record. Update only from approved plans and verified outputs. Never record credentials, tokens, or secret values here. This is an observed snapshot, not an authorization to use existing resources or create/change/delete cloud infrastructure.

## Account and access

| Fact | Observed value | Evidence/qualification |
|---|---|---|
| Account | `335523638354` | `aws sts get-caller-identity --profile clip-project` returned the intended account. |
| Account alias | Not available to Rahul's caller | IAM account-alias listing was denied; do not infer an alias. |
| Account owner | Aditya (human-reported) | No account ownership change was made. |
| Caller | `arn:aws:iam::335523638354:user/rahulkoyye` | Read-only STS identity check using `clip-project`. |
| Region | `ap-south-1` (Asia Pacific — Mumbai) | Selected and confirmed by Rahul; CLI profile configured for this region. |
| Available AWS credits | USD 140 (human-reported) | Not independently verified in this inventory. Cost reconciliation across accounts is intentionally deferred. |
| Access policy context | All four team members retain `PowerUserAccess`; Aditya reported `IAMFullAccess` removed | Human-reported. Rahul's IAM policy/group listing calls were denied, so the policy attachment for all four was not independently verified. Least-privilege checks are explicitly deferred by the team. |

## Observed resources in `ap-south-1`

Read-only service inventory checks found no CLIP-specific resources. Existing resources observed were identified as unrelated course/test resources and are not approved for this project. Do not adopt, modify, or clean them up as part of CLIP work.

| Service/resource group | Observed result | Ownership/limitations |
|---|---|---|
| EC2 instances | 0 instances | No CLIP instances found. |
| VPC networking | 1 VPC, 3 subnets; security groups/rules, an internet gateway, and a route table were also present | Existing course/test environment; individual owner not established. |
| Elastic IPs | 0 | — |
| RDS | No DB instances or clusters | — |
| ECS | No clusters | — |
| ECR | No repositories | — |
| Lambda | No functions returned by the current inventory call | Older Lambda-related CloudWatch log groups exist; this does not prove no historical functions/resources. |
| S3 | One bucket, `ds252-w4-bucket-adityamedhe`, tagged `Course=DS252` | Unrelated course resource; individual accountable owner not established by the observed tag. Do not use for Terraform state. |
| Other indexed resources | CloudWatch log groups for Lambda/EKS/course workloads; an EventBridge rule/default bus; ElastiCache users; an Athena catalog/workgroup; X-Ray defaults; and Resource Explorer index/view resources | Resource Explorer returned 33 indexed resources, of which 4 were tagged in the queried Region. Index and tag results are not a complete account-wide inventory; ownership is unknown unless explicitly shown by a tag. |

The Resource Explorer and Resource Groups Tagging API results are not exhaustive. The service-specific checks above are the limits of this snapshot; unqueried AWS services may contain additional resources. No existing resource was identified as CLIP-owned. The Resource Explorer index/view itself is account tooling, not a CLIP workload resource.

## Observed service quotas in `ap-south-1`

These are observed quota values only. No architecture-approved service/size plan exists yet, so this snapshot does not establish that the quotas are sufficient for deployment.

| Quota | Observed value |
|---|---:|
| EC2 On-Demand Standard instances (vCPU quota) | 8 vCPUs |
| Elastic IP addresses | 5 |
| VPCs per Region | 5 |
| Subnets per VPC | 200 |
| RDS DB instances | 20 |
| RDS DB clusters | 40 |
| RDS total storage | 100,000 GB |

ECS API throughput quota values were also queried, but are omitted because they are request-rate limits rather than deployment-capacity limits. Review service quotas against an approved infrastructure plan before any plan/apply approval.

## Cost and approval notes

The live account has a USD 200 `COST` budget for actual costs, starting 2026-10-17 and ending 2027-10-17. Actual-cost notifications use `GREATER_THAN` thresholds of USD 50, 80, 100, 120, and 130. All four team members (Aditya, Mohit, Suraj, and Rahul) are subscribed at each threshold; their email addresses are omitted from this repository record. These notifications are not a hard spending cap and do not stop resources.

The user discussed USD 120 as a planning marker but said it may be irrelevant; it is not a hard cap. No reserve is selected, and the team intends to change accounts if the available credits are exhausted. Reconciliation of project spend across accounts is deferred. USD 140 in available AWS credits is human-reported, not independently verified here. Credits are not separately monitored as consumed; the current budget has `IncludeCredit=false`. The team accepted cost alerts without a separate credit-consumption monitor.

### Infrastructure authority and cleanup

- Anyone on the four-person team may approve and apply infrastructure plans (Rahul-confirmed).
- Aditya owns billing alerts (Rahul-confirmed).
- Everyone shares cleanup responsibility; the person who started resources has first responsibility (Rahul-confirmed).
- These are team procedures, not AWS-enforced controls. Each cloud action still requires its own exact-plan approval and safety review.

### Coding-access exception

- Aditya reported that all four team members retain `PowerUserAccess` and that `IAMFullAccess` was removed. This is human-reported; Rahul could not independently inspect the policy attachments for all four.
- Rahul intentionally chose to retain `PowerUserAccess` and defer least-privilege checks. Record this as an accepted broad-access exception, not as a passed least-privilege check. No IAM policy was changed by this PD-14 work.
- The team should request additional service-specific access only for a reviewed task need. This record does not claim effective SSM, S3, or other service permissions were tested.

Refer to the work log for the dated verification record.

## Snapshot provenance

Recorded by Rahul (D) on 2026-10-17 from prior read-only checks using the `clip-project` profile, selected Region `ap-south-1`, AWS STS, service inventory APIs, Resource Explorer, Resource Groups Tagging API, and Service Quotas. No cloud resource, billing setting, permission, or account setting was changed by this inventory. See `docs/status/work-log.md` for the verification checkpoint and limitations.
