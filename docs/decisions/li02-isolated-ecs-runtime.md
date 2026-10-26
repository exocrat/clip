# DEC-13 — Isolated LI-02 ECS runtime and RDS zone fallback

**Date:** 2026-10-25

**Origin:** LI-02 Step 2 resource-design revision for Step 12.

## Question

How should the isolated LI-02 cloud demo use ECS capacity and handle temporary
RDS Availability Zone capacity failures without changing shared ECS or RDS
resources?

## Options considered

- Add a dedicated ASG capacity provider to the shared ECS cluster. This shares
  the cluster control plane and requires a coordinated change in the shared
  Terraform root, which owns the provider association.
- Give LI-02 its own ECS cluster, capacity provider, and ASG-backed EC2 host
  inside the shared VPC. This leaves the shared ECS cluster/provider/ASG
  untouched, at the cost of one more cluster target to select during later
  integration.

## Selected choice

Use a dedicated LI-02 ECS cluster, capacity provider, and ASG-backed private
EC2 host. Reuse the shared VPC, private workload subnet, NAT, ECR repository,
and Terraform state backend; do not modify the shared ECS cluster, provider,
ASG, or host security group. Keep the LI-02 ASG at zero while the demo is off.
Terminate its host and delete its root EBS volume during stop. The empty
LI-02 cluster, provider, and ASG may remain for quick restart.

For the disposable Single-AZ RDS instance, try `ap-south-1b` first. Only after
AWS reports insufficient instance capacity may startup prepare a fallback plan
for `ap-south-1a`. Each distinct saved plan requires its own exact-hash review
and approval. If a failed apply leaves an RDS instance or ambiguous partial
state, stop and inspect instead of silently retrying.

## Rationale

The isolated rehearsal should not require modifying shared ECS configuration
or waiting for shared ECS tasks/capacity. A dedicated cluster still exercises
the ECS/EC2, ALB, private-RDS, and S3 application path; a later configuration
target can select the shared cluster/provider for real integration. The
cluster/provider/ASG definitions add no ECS compute charge while no instance is
running. Billing is limited to the EC2 host and retained EBS while present;
the stop procedure terminates the host and removes its root volume.

The existing private RDS subnet group spans the two reviewed AZs. An explicit
fallback preserves exact Terraform-plan approval while allowing the rehearsal
to recover from a transient capacity shortage.

## Implications

- Update the LI-02 Step 2 resource design and Step 12 requirements/runbook.
- Update only the LI-02 Terraform root, start/stop driver, lifecycle checks,
  and LI-02 command documentation to implement the selected target.
- Recheck the target AWS identity, budget, price, state, and live inventory
  before preparing any plan. No cloud mutation is authorized by this decision;
  every plan/apply and teardown keeps its existing exact-plan approval gate.
- The existing Terraform and driver still target shared ECS and pin RDS to
  `ap-south-1b` until the Step 12 implementation is completed and verified.
- Real shared integration remains a separate Step 13 check; the isolated
  rehearsal does not claim that the shared ECS target works.

## Approver

User, LI-02 domain owner, in the current session (`2026-10-25`).

## Supersedes

The LI-02 Step 2 design recorded on 2026-10-23 that reused shared ECS capacity
and pinned the disposable RDS instance to `ap-south-1b` without a fallback.
