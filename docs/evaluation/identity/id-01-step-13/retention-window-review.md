# ID-01 Step13 — final retention tick and cleanup approval

All hosted human flows now pass: Microsoft sign-in, temporary email registration/
verification/sign-in, reset/new-password sign-in, contact save/reload/delete,
logout and requested phone-browser check. Browser/version was not supplied and
is not inferred. User confirmed both the reset email and standalone SES test in
Gmail after checking phone. SES production access/sending is enabled, domain DKIM
SUCCESS and no account suppression; accepted standalone test was received. The
application provider preference/keys remain unchanged. No Resend key lookup ran.

## Exact proposed operating action

Account335523638354, profile `adityalaxmi1`, ap-south-1, same shared/test window
ending19:03:57UTC/$2. Only owned private host `i-012c79d8ef66d51f9`, API task6,
verified imagebfa7316. No new AWS resource, IAM change or image rebuild.
[Exact source hashes and safe dry-run](retention-window-review.json).

Install root-owned nonsecret launcher and unchanged reviewed cleanup CLI under
`/opt/clip-id01-retention` on that host only; install the two proposed units as
`clip-id01-retention.service/.timer`. First run the new launcher without --apply;
require successful target/source/image/privacy guards and the reviewed all-zero
eligible-category counts. Any drift/error stops before scheduling/deletion.

Then enable the proposed timer: first automatic tick1minute after activation,
next1hour after preceding activation. Service calls --apply with per-category
batch100. Existing unchanged cleanup policy rechecks cutoffs/locks: expired/used
OTP content after24h, terminal sessions after7d, permanent expired/revoked temp
passwords, stale protection metadata after24h, private contact/profile fields
under30day policy. Preserve users, lifetime enrollment/operation/key guards and
all other domains. No arbitrary test-account delete/cascade or synthetic data.

The launcher selects one container by exact task family/revision, verifies exact
image and cleanup source hash, and refuses after19:03:57UTC. Child retrieves only
fixed version1Identity DSN using existing task role, memory-only, verifies target/
TLS/privacy and emits safe counts.90second child alarm/105second client bound,
no automatic retry, no credential on host/config/command/output. Default CLI is
dry-run and files are inactive until this approval. Four offline safety tests,
strict typing/Black and host3.9/child grammar checks pass. No policy SQL changed.

Verify timer's actual first scheduled service run exit0/counts plus next hourly
firing time. Do not claim a second hourly run,24hour observation or production
scheduler outside this temporary window. Disable/remove owned timer/service/
launcher during cleanup; future deployment must explicitly reinstall cadence.
A failure preserves committed cleanup state; no automatic rerun/reset/restore.
Canonical write/scheduling gate: docs/decisions/private-data-retention.md and
identity-sessions-and-cleanup.md. Preparation has not applied/scheduled anything.

## Exact cleanup after evidence and human tests

Review/approve saved full teardown plan:
`/tmp/clip-id01-runtime-plan-sz7ld_se/runtime-cleanup.tfplan`, SHA256
`a3da1773dea736d90f70b21553cde814a1d3a247cc598966e6cbf5c2ef20887e`,
backend22. [Complete actions/source hashes](runtime-cleanup-plan-review.json).
It sets API0/updates its non-proxy task definition and deletes only the8owned
proxy resources (node/EIP/association/SG/ingress/role/policy/profile), including
node interface/encrypted deleting root. No database, secret, key, shared policy,
network/NAT/bucket/ACM/image or other-owner deletion/change.

After timer verification and completed human tests, disable/remove owned job,
apply only that exact approved cleanup plan, restore ASG min0/max1/desired0,
verify private host termination/root removal, stop retained private/protected RDS
when exclusive, remove owned deadline fallback. Keep migrated database/accounts/
roles and SSM keys for next restart. Verify API0/proxy resources absent/RDS stopped;
retain sanitized evidence only. No push/merge is included.

The domain A record must be removed after its EIP is released, or pointed only to
a new approved deployment; give human exact timing. No DNS polling. Keep website
off after cleanup; no unapproved retention of paid test resources.

This finishes only the remaining Step13 checks; human closeout acceptance and
required source peer review/merge remain distinct. ID-01 Step14/full consumer
matrix and other owners' features are outside this checkpoint.
