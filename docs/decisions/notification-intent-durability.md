# Atomic notification intent and asynchronous delivery

**Date:** 2026-10-18
**Origin:** PD-08 Step 1.

## Question
How is notification work retained without making email delivery determine message success?

## Options considered
- Persist intent atomically with its originating conversation/message write; deliver asynchronously.
- Dispatch only after commit without durable intent, risking lost work, or send email in the write transaction, coupling success to the provider.

## Selected choice
Persist notification intent atomically with the originating conversation/message write. Deliver asynchronously with duplicate suppression. External provider delivery is outside that write transaction; its failure does not reverse the successful primary action. This is not an exactly-once email guarantee.

## Rationale
Committed primary actions retain their notification work without depending on provider availability.

## Implications
PD-08 proposes intent relationships/constraints. DL-00/CN-01/CN-03 must jointly review producer transaction ownership and the public delivery/read-state boundary; no private cross-domain transaction access is granted. Mohit approved the [notification timing/retry policy](notification-delivery-policy.md) and [finite terminal retention](private-data-retention.md) during Step 2. Exact atomic episode/lease/replay behavior and provider idempotency limits remain implementation/review gates; read-before-due suppression remains required.

## Approver
Mohit (C), explicit approval in the execution session. The user later confirmed the PD-08 producer/notification-owner gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). Future producer and worker implementation checks remain in CN-01/CN-03.

## Supersedes
None; selects the persistence direction under the shared async-failure convention.
