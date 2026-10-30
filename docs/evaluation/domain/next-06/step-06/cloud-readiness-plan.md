# NEXT-06 cloud readiness inspection proposal

**State: approved by Mohit; execution stopped at the identity gate.** This is the
next original Step3/4 integration prerequisite, following verified local Step6.
No final DATA-READY, accepted milestone, runtime or current AWS identity is assumed.

## Local handoff

Mohit verified the local reset/reload/freeze-candidate result. All22human judgments
are accepted without corrections and must remain unchanged. Source changes are
uncommitted; exact source hashes bind the local candidate, not an accepted revision.
ID-READY/LI-CORE/SE-CORE/DATA-READY remain not accepted in the work-log registry.
Missing real integration checks stay at their original Steps3/4/5/6.

## Exact proposed read-only scope

Use this machine's existing `default` AWS profile, explicitly select `ap-south-1`,
set no-pager and bounded CLI connect/read timeouts. No credential/token output or
secret reads. AWS CLI is available locally; only profile name/region were read.

1. STS `GetCallerIdentity`. Expected historical project account335523638354,
   non-root identity. If account differs, identity is root, authentication fails
   or the project role is unclear, stop before resource calls. Do not assume the
   historical Suraj/Aditya profile names exist here or switch credentials.
2. ECS `DescribeClusters` for `clip-shared-test`, `ListServices` within that exact
   cluster and `DescribeServices` only for returned shared-service ARNs. Stop if
   ambiguous or unexpectedly numerous; do not inspect unrelated clusters. Record
   deployment/task-definition identifiers and desired/running/pending counts.
3. RDS `DescribeDBInstances` for `clip-shared-test-postgres`: status, engine/version,
   private/public flag and encryption only. No connection or SQL/secret retrieval.
4. S3 `ListBuckets` for bucket-name metadata, filtered for project CLIP naming.
   Do not enumerate keys/read objects/change permissions. If listing is denied,
   report the missing metadata rather than granting access or trying other roles.

Maximum12API calls, no automatic retry or broad discovery. Retain sanitized
account/region/resource-status evidence only. No service start/stop/scale, Terraform,
IAM change, SSM/SecretsManager read, database connection, upload, email, provisioning
or resource deletion. Do not infer effective auth/storage permissions from metadata.
The2026-10-29 inventory is historical and cannot establish current readiness.

## After inspection

Prepare a separately approved concrete load/deployment plan using the verified
shared account/operator/resources, isolated database and accepted migrations/code,
actual runtime threshold, owner-bound S3 upload/confirmation/delivery, real Identity
sessions, pinned model/worker activation, bounded storage/request/compute costs,
window/stop conditions, rollback and retention/cleanup. The local1000object plan
has925881224logical bytes from45source photos. No exact live target/prefix/role/cost
is invented now. Refresh applicable price/cost evidence when preparing that plan.
Independent review/explicit commit/push/merge approvals and full CI/security scan
remain separate publication gates; missing Docker and Linux-only local tests are
recorded honestly. Final label/source binding follows accepted revisions and real
checks, without changing human relevance judgments to suit scores.


## Inspection outcome

At 2026-10-30 12:58:08 UTC, STS returned root account387743104934 for default, differing from intended project account335523638354/non-root identity. Stopped before ECS/RDS/S3 as required. Initial network sandbox failure was retried outside the sandbox. See cloud-inspection-result.json. A correct non-root project profile is required to resume; this result authorizes no use of the other account.


## Superseding human direction and handoff

Mohit halted the alternate-account attempt and explicitly restricted all future
work to account335523638354. The earlier default/root account387743104934 authority
is revoked. Its ECS inspection command was interrupted; no successful resource
inspection is established. Do not retry that account. See the parent
[cloud handoff](../cloud-handoff.md) for the next operator; this original default-
profile proposal cannot be resumed until the actual authorized profile resolves
to the intended project account. No cloud calls were made during handoff writing.
