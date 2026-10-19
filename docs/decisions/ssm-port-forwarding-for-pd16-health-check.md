# DEC-04 — Private API health access through SSM port forwarding

**Date:** 2026-10-19

**Origin:** PD-16 Step 4; verification procedure in Step 10.

## Question
How should a developer check the private API `/health` endpoint without exposing it publicly?

## Options considered
- SSM Session Manager port forwarding through the private ECS EC2 host.
- A separate test task inside the VPC, which would not provide a local browser or curl endpoint.
- Public HTTPS ingress, which requires a hostname, certificate, and access boundary not selected for this foundation.

## Selected choice
Use SSM Session Manager port forwarding from local port 18000 to ECS host port 18000. The ECS task uses bridge networking, mapping container port 8000 to fixed host port 18000. Add no inbound security-group rule.

## Rationale
This gives the team local access to the health-only endpoint over the managed instance channel while keeping the API and database private. The task uses no application credentials, and the SSM path adds no public listener. AWS requires SSM Agent 3.0.222.0 or later for port forwarding; the recommended ECS-optimized AL2023 AMI is resolved by its regional public SSM parameter at plan time.

## Implications
PD-16 must verify the managed instance is online and its SSM Agent is at least version 3.0.222.0, provide the instance role permissions, and review actual operator `StartSession` permissions under the approved [PD-16 broad-human-access exception](broad-human-operator-access.md). Instance and task permissions retain their reviewed scopes. The developer uses the AWS CLI and Session Manager plugin, starts a port-forwarding session, checks `http://127.0.0.1:18000/health`, then ends the session. See [AWS Session Manager prerequisites](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html), [ECS optimized AMI parameter](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/retrieve-ecs-optimized_AMI.html), [PD-16 requirements](../tasks/pre-domain-task-list.md#pd-16--review-and-provision-the-shared-cloud-test-foundation), and the [shared test foundation proposal](../environment/shared-test-foundation-proposal.md).

## Approver
User in the current session; name not recorded.

## Supersedes
None.
