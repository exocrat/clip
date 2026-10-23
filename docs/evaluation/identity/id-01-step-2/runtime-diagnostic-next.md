# ID-01 Step 2 — next diagnostic proposal after failed real send

Proposal only; no code, task, policy or provider change authorized/executed here.
The real :1 task exited1 with only `failed_or_uncertain`, same-task STS identity
succeeded, IAM simulation allowed sender-scoped SendEmail, no email received.
Exact transport exception remains unknown; do not guess or widen permissions.

Recommended next verified increment: prepare/test a small private diagnostic
wrapper that uses the same published image and actual Identity sender/role-check
functions. Emit only fixed stage labels and a strict allowlist of service error
codes; never provider message, exception repr/traceback, recipient, content,
credentials or raw response. Unknown classes/codes map to `unclassified`.
`EmailUnavailable` suppresses display of its exception context; Python retains
the context object in memory, allowing a reviewed wrapper to classify the SDK
code without exposing its message or changing the actual sender's behavior.
Test synthetic private-payload exceptions to prove redaction and no retry.

A separately reviewed command override could use the existing immutable image
without another build/publication. It must keep explicit approval/test mode,
verified one-recipient restriction, actual signed task-role check, one sender
call and total deadline. It is a different live request: requires new exact
approval and new idempotency token (the previous request was accepted/stopped).
Do not reuse an old token with changed command parameters or override commands
silently. A no-send local/offline test cannot claim real provider success.

Only after human verification of the current failed result/cleanup should the
next diagnostic implementation be selected. Its one-task/one-email/shared-host
window and cleanup remain gated. Keep Step 2 partial and leave RDS untouched.

## Local preparation completed — 2026-10-23 10:32:43 UTC

Aditya subsequently authorized preparation. The exact wrapper, offline regression
checks and new command/cleanup request are now prepared; see
[runtime diagnostic approval](runtime-diagnostic-approval.md) and the work log.
The proposal-only wording above describes the earlier checkpoint. No new live
action has run; human preparation verification and exact live approval remain.
