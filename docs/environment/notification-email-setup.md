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

The sender requires an explicit test or production profile; test is limited to
up to five configured recipients, and production rejects injected provider/SSM
test doubles. No profile is enabled by this file. Actual account preferences,
templates, worker scheduling, general-recipient runtime permissions and bounded
cloud/inbox verification remain later CN-03 checkpoints. A provider exception
can be ambiguous; fallback and later retries may cause duplicate delivery.
