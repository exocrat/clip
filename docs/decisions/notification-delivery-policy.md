# Conversation email and bounded unread reminders

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 notification behavior review.

## Question
Which conversation emails are required, when are reminders due, and how are failures bounded?

## Options considered
- New-conversation email plus one coalesced reminder per unread episode, with bounded asynchronous attempts.
- Immediate email for every message or repeated reminders while unread, adding unsolicited volume beyond the selected policy.

## Selected choice
- New conversation: email the other participant promptly after the durable intent commits.
- Unread-message reminder: due 15 minutes after the episode's first unread text message. Later messages join that reminder without postponing its due time.
- Suppress when all currently unread messages are acknowledged before dispatch; recheck authorized read state and recipient eligibility immediately before dispatch. Reads acknowledge actual client display, not polling alone.
- At most one reminder per unread episode. Another requires catching up, then receiving a new unread message. An already reminded episode must not restart because a worker/terminal record is cleaned up.
- At most five attempts, including the first. Four transient-failure delays are 1 minute, 5 minutes, 15 minutes and 1 hour after successive failures. Stop 24 hours after the immutable original due time; terminal failures stop immediately.
- Intent persistence remains atomic with the originating write and delivery asynchronous. Failure does not reverse the primary action. No exactly-once provider guarantee.

## Rationale
Provides event awareness and a bounded unread reminder without per-message email or repeated reminders during one unread period.

## Implications
The [schema](../architecture/mvp-database-schema.md) records episode/target/read state and deterministic keys; CN-01/CN-03 must review and implement producer/worker ownership, atomic state transitions, replay deadlines, safe outcomes and race tests. Addresses are resolved through authorized Identity interfaces, not copied into notification records. The [retention policy](private-data-retention.md) applies to terminal records; cleanup cannot reset an episode or trusted original delivery deadline. Public source replay must not recreate an expired delivery window.

Lease/claim fencing, exact provider setup/idempotency, operational clock handling and immutable-source enforcement remain A/D review gates. No immediate per-message/offer/contact-share email, optional digest/match alert, paid service, scheduler, cloud resource or live delivery is selected or authorized here.

## Approver
Mohit (C), explicit approval of the presented notification policy. Producer/notification/Identity affected-owner review remains pending.

## Supersedes
None; refines the existing durable-intent decision.
