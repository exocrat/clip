# CN-03 notification email setup

Aditya selected `updates@clip-iisc.site`, SES first, and Resend fallback. Local
code reuses the existing versioned email-route SecureString format and refreshes
it at first send and at most once per four hours. It reads the configured
`primary` field: the existing parameter must be reviewed and set to `ses` for
SES-first operation. Because Identity also uses that parameter, this changes its
provider order too. The value and current state have not been read in this step.

The existing API task-role record permits `verify@clip-iisc.site`; `updates@`
needs a reviewed SES FromAddress permission change. Confirm domain/sender
verification and current account/region before any real send. Resend domain
verification and delivery from `updates@` are not established by the earlier
`verify@` test. Confirm the existing SSM parameter reference, key access, rotation
and egress; never place the key or addresses in logs, source, fixtures or chat.
The SSM preference/key change, IAM permission, deployment and live provider send
require their own exact approved plans. No separate mailbox is assumed.

The sender requires an explicit test or production profile; test defaults to
up to five configured recipients. Aditya authorized an explicit test-worker
switch allowing other eligible notification recipients; it is not yet deployed.
For the next notification deployment, explicitly enable
`notification_allow_unlisted_recipients` so the worker has no recipient
allowlist, as Aditya directed on 2026-10-30. Rebuild and testing are deferred.
The image published at digest
`sha256:3faaeb2ebe160868d1e7b194e373051a1bde2fc5d84cef60959a028d3e8f3d00`
contains that feature, but predates the later Identity database-metadata checker
correction in the branch. It is not an exact image of the final branch; rebuild
or explicitly review that difference before any deployment.
Identity test email restrictions are separate. Production rejects injected provider/SSM
test doubles. The notification worker defaults off; explicit local settings can
start it only in the existing real Identity test profile with controlled
recipients. It uses one serial poller per API process, a 1–50 job batch and a
1–3600 second polling interval. Attempts remain capped at five, with database
leases across replicas. Production notification startup remains disabled.
The setting is not activated in the deployed runtime. General-recipient runtime permissions and bounded
cloud/inbox verification remain later CN-03 checkpoints. A provider exception
can be ambiguous; fallback and later retries may cause duplicate delivery.

## Step 10 integration preparation

The shared ECS definition can host the serial poller in the API task; the local
Terraform change adds a default-off enable flag. It references a separate Conversations
database secret and the Identity email parameter. Existing configuration records
show an API service and capacity at zero and a stopped RDS; these are historical,
not a current cloud inventory. A fresh read-only inventory and exact deployment
plan must establish resource state, cost, lifetime, and cleanup. Reuse one bounded
environment for grouped integration tests; avoid a separate worker service if
the existing API capacity is adequate. No scheduler/queue is needed by the local
poller itself, but no claim is made about other existing cloud resources.

At 2026-10-29 19:01:39 UTC, read-only AWS checks confirmed account 335523638354,
region ap-south-1, the shared ECS cluster and API service (desired/running zero),
its host group (desired zero), a stopped db.t4g.micro RDS instance, an available
NAT gateway, and SES sending enabled with production access and the domain
verified. No `clip`-prefixed Scheduler schedules, rules on the
default EventBridge bus or `clip`-prefixed SQS queues were returned. This limited
check does not establish the state of other buses, Scheduler, resources, or cost.

The Identity runtime must have the additive, separately reviewed
`database/roles/identity-notification-runtime.sql.proposed` grant after the new
migrations; its startup checker rejects missing or excessive rights. The API's
Conversations role deliberately lacks DELETE on notification intents. The
approved local retention operation therefore still needs a separate reviewed
least-privileged operator role and execution plan; it is not scheduled by this
change. Apply no database grants or retention operations without exact approval.
The worker also requires the dedicated Conversations DSN; a marketplace-only
connection cannot enable it. The local IAM change adds SES `updates@` while
retaining `verify@`; applying it requires a reviewed plan. Configure
SES-first in the shared SSM value only after approval and accounting for the
Identity provider-order change. Confirm sender verification, network access,
runtime secrets, recipient allowlist, monitoring and cleanup before live sends.

The local templates use generic new-conversation and unread-message copy with
only a fixed `https://clip-iisc.site/my/conversations/<conversation-id>` link.
Production sender composition accepts only that approved renderer; it does not
include message text, listing details, contact data or authentication codes.
