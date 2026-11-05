# Listings/Images isolated test Terraform root

This root defines resources exclusive to the LI-02 image/demo rehearsal. LI-02 is
marked complete in the [work log](../../../../../docs/status/work-log.md); this
guide describes ownership and safeguards, not current AWS state or reusable
approval. Refresh state and prepare a newly reviewed plan before any future action.

## Ownership and boundary

State key: `domains/listings/test/terraform.tfstate` in the existing PD-15 backend,
default workspace. This root owns the Listings image bucket, isolated disposable
database, dedicated ECS/ASG capacity and task roles/log group. It consumes shared
VPC, subnet, NAT, ECR and state infrastructure without managing them. It must not
change the shared ECS cluster/capacity provider, shared RDS or `clip_test` database,
shared security groups, or another domain's resources.

The selected runtime and RDS placement are described in
[DEC-13](../../../../../docs/decisions/li02-isolated-ecs-runtime.md). The exact
resource definitions and lifecycle driver are the executable source. Historical
run steps and review outcomes are in the [cloud inventory](../../../../../docs/environment/cloud-inventory.md).

## Safety properties

The rehearsal profile uses synthetic accounts/data, a fixed test caller, a
dedicated `clip_test_listings` database, a run-scoped S3 prefix, private bucket
access and bounded listing/image counts. Production configuration rejects the
test caller. The database setup task is separate from the application role. Object
reads use short-lived signed URLs; bucket objects are not public.

The start/stop commands are `make li02-demo-start` and `make li02-demo-stop`; see
the [command guide](../../../../../docs/environment/commands.md) for current
operator instructions. Review the exact saved Terraform plan and its hash before
applying. Stop must remove only the run-owned endpoint, host, disposable database,
run prefix and parameter, then verify teardown. Keep shared resources untouched.
No plan hash, DNS value, task definition, or old approval in this directory
authorizes a future run.
