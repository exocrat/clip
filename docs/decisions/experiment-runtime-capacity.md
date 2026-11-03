# DEC-EXP-01 — Two-task running baseline for the architecture experiment

**Date:** 2026-11-03

**Origin:** NEXT-07 Step 0 and bounded deployment planning.

## Question

Should two healthy ECS tasks be the actual running configuration or only a
special temporary configuration for NFR-06?

## Options considered

- One normal task, temporarily two for recovery: cheaper, but the recovery
  evidence would describe a different capacity configuration.
- Two normal tasks in both architectures: the accepted deployment matches the
  configuration used for recovery and the performance comparison.

## Selected choice

Run two healthy ECS tasks on two `c7i-flex.large` hosts in both A and B while
the app is active. B additionally uses Lambda for its selected read share.
Run NFR-06 separately under both; stop one ECS task and measure restoration to
healthy configured capacity plus request failures. Do not count Lambda as the
second ECS task. Budgeted shutdown outside active windows remains permitted.

## Rationale

The submitted PRD, page 4, explicitly begins NFR-06 with at least two healthy
serving instances configured. Suraj confirmed that the actual deployment must
provide the configuration supporting that requirement, not only the test.

## Implications

The [deployment plan](../evaluation/deployment-20261103/plan.md) and its public
input overlay set count two for A/B and NFR-01–03 as well as NFR-06. The isolated
NFR-07 helper uses 1 GiB with Hybrid disabled so both source tasks stay healthy
within the two-host limit. This decision approves the capacity choice; cloud
creation, task loss, restore and cleanup still need their exact approvals.

## Approver

Suraj, 2026-11-03: “We will do two then.”

## Supersedes

The agent's suggestion to use one normal task and two only during NFR-06.
