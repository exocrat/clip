# Conversation email and bounded unread reminders

**Date:** 2026-10-18
**Origin:** PD-08 Step 2 notification behavior review.

## Question
Which conversation emails are required, when are reminders due, and how are failures bounded?

## Options considered
- New-conversation email plus one coalesced reminder per unread episode, with bounded asynchronous attempts.
- Immediate email for every message or repeated reminders while unread, adding unsolicited volume beyond the selected policy.

## Selected choice
- Aditya selected one account setting for both conversation email types on
  2026-10-29. It defaults on; users may turn both emails off and back on.
  Recheck the current setting immediately before dispatch; suppress a claimed
  intent when disabled and do not replay it if the user later enables email.
  An unavailable preference check defers. This setting does
  not change Identity verification or password-reset emails.
- On 2026-10-29 13:30:07 UTC Aditya selected the address used for account
  creation and login as the notification destination. Identity must retain it
  encrypted and resolve it only for the authorized worker. Populate it from a
  validated Microsoft sign-in or authenticated temporary-account email flow;
  never substitute the editable, unverified contact email. Existing accounts
  acquire an address when they next authenticate or complete a verified flow.
  Local implementation uses AES-GCM with an HKDF-derived purpose key from the
  existing Identity target-encryption key, per-account associated data and key
  version. Resolver denies expired/revoked accounts immediately; the existing
  bounded Identity cleanup removes stored destinations within its 30-day
  terminal retention window. Key rotation/re-encryption and runtime role grants
  require review before deployment.
- On 2026-10-29 13:56:01 UTC Aditya selected `updates@clip-iisc.site` for
  conversation email, SES as primary and Resend as fallback. Use the existing
  four-hour configuration refresh and bounded real-provider fallback pattern;
  an uncertain first submission may produce duplicate mail. This sender requires
  separately approved runtime permissions and real delivery checks.
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

Aditya selected an independently configured, default-off bounded notification
  polling loop in the existing API lifecycle on 2026-10-29 13:14:28 UTC. The
delivery logic remains separable from the loop; database leases and fencing
coordinate API replicas. Jobs wait while the API is stopped and remain subject
to their original deadline. Polling interval, lease/claim details, exact
provider setup/idempotency, operational clock handling and immutable-source
enforcement remain implementation and owner-review gates. This choice does not
authorize a cloud resource, deployment, live delivery, or paid service.

## Approver
Mohit (C), explicit approval of the presented notification policy. The user later confirmed the PD-08 producer/notification/Identity affected-owner gate complete on 2026-10-19; see the [work-log reconciliation](../status/work-log.md#resolved-integration-evidence). CN-01/CN-03 still own implementation, provider, and race checks.

## Supersedes
None; refines the existing durable-intent decision.
