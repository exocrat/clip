# DEC-10 — Broad human-operator access for PD-16

**Date:** 2026-10-19

**Origin:** PD-16 Step 8 operator-permission audit.

## Question
Must the four-person team maintain an additional scoped runtime operator role for PD-16's shared test environment?

## Options considered

- Add a scoped SSM/ECS runtime operator role, retaining the creator identity for Terraform.
- Accept the existing broad non-root human-operator access as an explicit PD-16 exception and maintain procedural action gates.

## Selected choice
The user selected the existing broad non-root human-operator identity for the PD-16 shared test foundation, citing the four-person team's capacity to maintain roles/resources. Do not add a dedicated human runtime operator role or change existing human permissions for this decision.

Read-only review found direct IAMFullAccess and developer-group PowerUserAccess/CLIPParameterStoreTeamAccess on the current operator. Record those broad permissions honestly; they are not a least-privilege result. Root authorization remains limited to the separately approved read-only billing exception in DEC-06.

## Rationale
A separate human role adds configuration, assumption steps and ongoing maintenance for this small team. The user accepts the broader authority of its trusted human operator for this bounded foundation work.

## Implications

- Step 8 reviews and records the actual human operator identity, attachments and approved invocation scope under this exception; a new narrow human role is not a prerequisite.
- The existing API, setup and probe application roles remain without attached/inline AWS permissions; execution roles retain the narrow image/log/parameter scopes in DEC-05. Shared instance permissions remain separately reviewed. Preserve these machine-role boundaries.
- Approved invocations use the fixed task definitions without command/image/environment overrides. This is a procedural rule, not a claim that broad human IAM permissions prevent overrides, direct secret reads, role administration or unrelated changes.
- Each plan, apply, upload, session/task execution, RDS operation and cleanup retains its specific action approval and target/window controls. This decision does not authorize an AWS mutation or Terraform plan.
- Review this exception at PD-16 closeout and when environment/team scope changes. Any future permission changes require separate review; the decision itself neither removes nor grants IAM policies.

## Approver
User in the current session; personal name not recorded. Explicitly selected broad human-operator access as a PD-16 exception after the scoped-role recommendation.

## Supersedes
PD-16's narrow-human-operator prerequisite for this shared test environment. Application/execution/instance role requirements, privacy rules and cloud approval gates remain in force. See [the service-plan audit](../environment/pd16-service-plan-preparation.md), [DEC-04](ssm-port-forwarding-for-pd16-health-check.md), [DEC-05](private-postgresql-probe-login.md) and [DEC-06](terraform-planning-identity.md).
