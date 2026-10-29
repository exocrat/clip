# Identity test Terraform root

Current state: builder resources are removed; smoke definition :1 is registered.
The initial ECS send failed and its owned compute/root disk were removed. Local
operator SES delivery is confirmed; application-role diagnosis remains pending.
The source and historical plan descriptions below do not authorize another apply
or run. Review current prerequisites in [ID-01 setup](../../../../../docs/environment/identity-provider-setup.md);
any diagnostic needs a new exact approval. Older plans are recoverable through
the [evaluation history guide](../../../../../docs/evaluation/README.md), but are
not current approvals.

ID-01 Step 2 owns the temporary AMD64 image builder and separate one-shot email
task definition. Aditya approved its concrete
design and one non-applying plan; that temporary builder was removed. Any future
resource or permission change needs a new reviewed plan. Historical plan details
are available through the [evaluation history guide](../../../../../docs/evaluation/README.md).

Use Terraform 1.15.9, locked AWS 6.69.1, default workspace, existing state bucket
and exact key `domains/identity/test/terraform.tfstate`. No backend migration.
`builder_enabled` and `email_smoke_task_enabled` are both required. The first
true proposes the approved builder; false removes
owned builder resources and requires its own reviewed cleanup plan. Neither
selection is a harmless default against existing state. The task flag registers
or deregisters only the Identity smoke task; it never starts one.

`versions.tf` pins target/backend/provider and tags. `main.tf` creates only the
Identity builder role/policy/profile, dedicated security group, and one private
t3.small with one-hour shutdown timer and delete-on-termination root disk.
Existing shared subnet/NAT/ECR are consumed through explicitly reviewed IDs; no
shared role/network/service or database is mutated. No application secrets or
SES access on the builder role. ECR capability is not image-push authorization.

Run `make terraform-check` with the pinned binary before cloud planning. Cloud
init/plan uses the approved profile/account and explicit variable, private saved
plan and exact review workflow from [Terraform instructions](../../../README.md).
Stop on any plan scope other than the approved five creates. No source upload,
remote build, registry publication or email follows automatically from apply.

## Post-build registration and temporary-resource cleanup proposal

`email-smoke.tf` consumes the reviewed shared task/execution role ARNs and
`email-smoke-container.json`, which pins the verified image digest, non-root UID,
no port mappings, disabled email provider and no approval
or recipient values. Logs reuse the existing shared group. A run needs separate
explicit overrides/approval; registering a task neither starts compute nor sends.

The proposed next full plan explicitly selects `builder_enabled=false` and
`email_smoke_task_enabled=true`: remove only the four remaining temporary builder
role/policy/profile/group resources and register one task definition. The builder
VM/root disk already have verified cleanup evidence. Review that exact expected
scope instead of the historical five-create builder scope above; stop for shared
changes or any launch/replacement. The old planning request is recoverable
through the [evaluation history guide](../../../../../docs/evaluation/README.md),
but is not approval to recreate these resources.
