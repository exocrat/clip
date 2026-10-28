# Cloud environment inventory

Non-secret handoff of the last recorded cloud state. This is not a live view or
permission to create, change, or delete resources. Before any cloud operation,
verify the caller and refresh AWS and Terraform state; review and approve the
exact operation separately. Never record credentials, tokens, or secret values.

## Shared foundation — last inspected 2026-10-26

An approved read-only inspection finished at **2026-10-26 18:09:02 UTC**. A
refresh-only Terraform apply at **18:29:50 UTC** reconciled state serial 18 with
the live API service at revision 2; it changed no cloud resources. No later
cloud refresh is recorded here.

| Area | Last recorded state |
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
