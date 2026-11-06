# Identity test Terraform root

This optional Terraform root contains the Identity test image-builder and
one-shot email-task definitions. **ID-01 is complete** in the
[work log](../../../../../docs/status/work-log.md). The plans and outcomes below
are historical; they are not current approval or evidence that any resource is
running. Check current state before a future operation and create a fresh reviewed
plan.

## Scope and safeguards

The root uses Terraform 1.15.9, AWS provider 6.69.1, the default workspace, the
existing backend, and state key
`domains/identity/test/terraform.tfstate`. It consumes reviewed shared subnet,
NAT, ECR, and task-role identifiers; shared infrastructure is not owned here.
The `builder_enabled` and `email_smoke_task_enabled` inputs independently control
owned builder resources and task-definition registration. Registering a definition
does not start compute or send email.

`versions.tf` and `main.tf` constrain account, region, provider, and resources.
The builder design used a private AMD64 instance, dedicated security group and
role, one-hour shutdown timer, and delete-on-termination disk. The task definition
pins an image digest, runs non-root, has no port mapping, and does not contain
provider credentials, recipients, or approval values. None of these settings
proves the current deployed configuration.

For any future use, run the pinned offline Terraform checks, verify account and
state identity, inspect the exact saved plan, and stop if it changes shared
resources or proposes an unreviewed launch/replacement. See the shared
[Terraform guide](../../../README.md), the
[Identity setup guide](../../../../../docs/environment/identity-provider-setup.md),
and the [evaluation history index](../../../../../docs/evaluation/README.md).
