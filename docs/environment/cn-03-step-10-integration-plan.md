# CN-03 Step 10 integration preparation

Status: draft for completing preparation, not a cloud or SQL approval. Aditya
reported that Rahul approved his part on 2026-10-30; retain separate Identity,
platform and privacy review gates. Candidate source revision is
`0e87f3f9f6fc6561f9737a029bd48b1812583479`; any later code revision requires a
new image and review. The existing migrated database's actual head and grants
are not known until privately inspected.

## Target and present evidence

Account `335523638354`, `ap-south-1`, approved IAM user `adityalaxmi1`, and
Terraform root `infra/terraform/shared/test` with backend key
`shared/test/terraform.tfstate`. On 2026-10-30, read-only checks showed the
shared API desired/running zero, shared host group desired zero/max one,
PostgreSQL 18.6 RDS stopped (`db.t4g.micro`), and the existing Conversations
DSN parameter at version 1. Prior inspection found SES production sending and
domain verification enabled, and an available NAT gateway. Confirm all state
again before a plan; do not expose parameter values.

## Work to make an executable plan

1. **Migration:** inspect the private database head and schema/grants through an
   explicitly approved bounded tunnel. Compare exact checksums with the current
   32 migration files using the [unreviewed candidate manifest](cn-03-candidate-migration-manifest.json).
   The historical Identity migration runner deliberately
   pins a 23-file chain and refuses upgrades; it is not an upgrade tool. A local
   disposable rehearsal applied the nine-file suffix transactionally and checked
   the resulting ledger/schema; it did not exercise dbmate or a live target. Prepare
   and review an additive, exact-baseline upgrade manifest and procedure before
   applying migrations. Do not infer the database head or reset data.
2. **Permissions:** after migrations, propose only the separately recorded
   `identity.notification_destinations` grant to the existing Identity role;
   verify the Conversations role can operate the new state and has no cleanup
   DELETE. Preserve existing roles and credentials. The cleanup operation locks
   thread and member rows, so a retention role also needs sufficient PostgreSQL
   row-lock rights. The [candidate retention grants](../../database/roles/conversations-notification-retention.sql.proposed)
   passed an isolated PostgreSQL lock/denial check; their key-column UPDATE rights
   also allow key modification and need review; DELETE covers the entire intent
   table and relies on trusted cleanup code for the cutoff. The dry-run and deletion
   passed against synthetic rows using that role in disposable PostgreSQL. Live
   role provisioning and scheduling are not verified. Do not broaden the API role.
3. **Build:** build and validate the exact candidate AMD64 image and obtain its
   immutable ECR digest. The local machine's architecture cannot be assumed to
   build this image. Any temporary build host, image publication and cleanup need
   their own exact cloud approval, sizing and deadline.
4. **Runtime:** prepare a saved Terraform plan with `deployment_phase=service`,
   existing approved state and variables, one shared API task/host, Identity and
   Conversations enabled, the notification flag enabled and an exact controlled
   recipient allowlist. Preserve other owners' resources and existing secrets.
   The local policy adds `updates@` to the existing SES sender allowlist; retain
   `verify@`. Set the existing shared email parameter's `primary` to `ses` in a
   separately reviewed change, preserving its existing secret and acknowledging
   that Identity email uses the same provider order. No new DNS verification is
   expected for straightforward sends from the verified domain.
5. **Grouped verification:** keep the same environment running across the Step 10
   producer/read-state checks and the separately approved Step 11 provider tests.
   Check real message/intent transaction independence, read-before-due and both
   preferences, then controlled SES/Resend delivery and privacy-safe telemetry.
   Do not claim real-provider success from synthetic tests. The real test needs
   confirmed recipient accounts and an explicit cap on duration, concurrent
   tasks, sends and cost before starting.
6. **Cleanup:** prepare and separately approve the exact stop plan and owned
   temporary-host cleanup. Restore API desired count and host capacity to zero,
   stop the retained RDS, and remove only resources created for this run. Do not
   remove the shared NAT, database, secrets, state or another owner's resources.
   Existing NAT, storage and other retained components can continue charging.

Before asking for approval, resolve the live migration baseline, image digest,
private access, exact recipient list, cost estimate, caps and deadlines, and
inspect the complete saved Terraform plan for drift, replacements and exposure.
Any changed plan needs a fresh checksum and approval. No cloud mutation, SQL,
secret read, real provider send or cleanup is authorized by this draft.

## Step 11 proposed test bounds

Propose one grouped test window of at most two hours, at most one API task and
one shared host, no more than two explicitly approved recipient accounts and
10 provider submissions. Use a USD 3 incremental-spend stop threshold, not a
guaranteed billing cap; obtain current rates and include NAT data, storage,
images, email, logs and any temporary host before presenting the final plan.
Set an actual UTC deadline and establish the owned fallback before starting;
stop new work early enough to complete approved cleanup within that deadline.
These provisional bounds are not approval to start a resource or send mail.

Offline failure-injection tests cover SES failure and Resend fallback, both
providers failing, redacted provider errors, and worker startup bounds. Existing
disposable PostgreSQL evidence covers provider failure without undoing message
creation and read-before-due suppression. For live checks, verify the deployed
revision/configuration, controlled recipients, sanitized fixed-code logs and
intent outcomes; never record plaintext or addresses in evidence. Notification-
specific monitoring is locally prepared behind a default-off Terraform flag. It
proposes four failure/ambiguity metrics, a dashboard and four actionless alarms; an alert
destination and actual operational monitoring still require review and approval.
Validate deployed monitoring before claiming the Step 11 check has passed.
