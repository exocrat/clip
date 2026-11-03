# Deployed parity, Lambda initialization and isolated restore tooling

These tools complete the code paths identified by Step 0. None of the templates
or commands authorizes a cloud action. Real input freezing, exact deployment and
run approvals, live smoke and Suraj's website inspection precede pilot traffic.

## EXP-04 live response checks

Prepare separate A/B manifests from
`data/evaluation/workloads/live-parity-manifest.template.json`. Bind the exact
shared target plan and the same reviewed ten-case corpus by SHA-256. Supply a
reviewed hidden listing UUID to test its 404 response. The normal corpus has
five browse, three search and two detail cases. Browse/detail retain independent
expected results; search checks the product response shape and filters, then
A/B equality. NFR-04 independently evaluates relevance.

Use `docs/evaluation/live-parity-approval.template.json` for an expiring approval
of each exact manifest. Supply the regular test-user cookie through the existing
secure handoff into `CLIP_SMOKE_SESSION`; never put it in command arguments,
files committed to Git, terminal output or logs. With the applicable configuration
deployed, run:

```sh
python -m scripts.evaluation.k6.live_parity capture MANIFEST APPROVAL --execute --output NEW_RECEIPT
python -m scripts.evaluation.k6.live_parity compare A_RECEIPT B_RECEIPT --output NEW_PAIR_REPORT
```

The capture validates all paths locally, checks the live AWS target and user,
issues exactly ten case GETs plus one anonymous and one hidden-detail GET,
with five-second timeouts, no retries and no redirects. Bodies stay in memory;
receipts contain canonical response hashes, status and correctness results.
Each file is new and owner-readable only. A nonpassing capture/pair returns a
failure exit code and preserves the receipt. Keep these under
`docs/evaluation/experiment-runs/<RUN_ID>/`. Review target-group metrics alongside
these receipts: response equality does not identify each weighted request's
backend. Save A before switching the deployment, then capture B from identical
inputs. Auth/session preflight makes additional bounded read requests.

## EXP-06/07 Lambda initialization evidence

```sh
python -m scripts.evaluation.k6.lambda_initialization TARGET_PLAN RUN_WINDOW --output NEW_INIT_REPORT
```

Use the same exact target plan and actual run-window schema as
`cloudwatch_capture.py`. The read-only collector verifies the AWS caller and
Lambda image, derives the actual configured log group, and reads at most 100
pages/200,000 events from that run window. Only platform REPORT fields survive:
hashed request/stream IDs, timestamps, runtime duration and explicit init duration.
Text and JSON platform reports are supported. Application messages, credentials,
message contents and arbitrary provider prose are never written.

Save `lambda-initialization.json` alongside CloudWatch evidence for each B run
and the separate cold-observation cohorts required by the protocol. Record its
hash in the run evidence and link it in the human EXP-07 report. Explicit Init
Duration proves observed initialization; a missing field does not establish a
warm invocation because suppressed initialization may lack that field. The tool
does not claim client-to-platform request correlation. Keep service initialization
observations separate from client latency unless independently correlated.
Missing reports return failure with a `no_data` receipt; log delivery may be
late, so preserve that receipt and use a new output file for any approved later
collection. Review report counts against invocations before claiming completeness.

## NFR-07 isolated application provisioning and timed handoff

`infra/terraform/shared/test/nfr07-smoke.tf` adds an opt-in isolated application
service to the existing reviewed experiment ALB and ECS cluster. It uses the fixed
`restore.clip-iisc.site` host, a separate target group, host port 18001 and three
dedicated SSM SecureStrings for the existing Listings, Identity and Conversations
database roles. It copies the
reviewed app container, redirects its database secrets to that dedicated
parameter and disables Hybrid/notification background workers. The source
service and its database parameters retain their bindings.

Run this shared-database restore check with A selected. Its isolated host rule
precedes the experiment routing rule, so the infrastructure guard refuses
weighted B while these smoke resources are enabled. Remove the smoke resources
before switching to B. The restore evidence can cover unchanged B when the same
database/backup procedure and relevant revisions are verified.

Before the timed restore, review and provision with `nfr07_smoke_enabled=true`,
`nfr07_smoke_running=false`, the reviewed isolated hostname and an issued
certificate covering it. DNS, its certificate and Microsoft callback registration for
`https://restore.clip-iisc.site/auth/callback` are explicit deployment-plan
dependencies. The new `CLIP_NFR07_RESTORE_SMOKE_ENABLED` app profile allows only
that exact origin, test mode, real Identity and disabled background writers. It
selects the fixed isolated Identity parameter; the ordinary app retains its
existing origin and parameter. Provisioning creates a
placeholder database parameter and zero tasks. Do not point it at the source DB.
The smoke task uses 256 CPU units/1,024 MiB and disables Hybrid search as well
as background workers. Keep both 2-GiB source tasks healthy on their two hosts;
the basic smoke task can share a host only after its actual free CPU/memory is
verified. Its reduced profile checks authentication and restored SQL reads, not
search performance.

Freeze `terraform output -json nfr07_smoke_bindings` into the observer's
`application_smoke_plan`, including the source application's immutable revision,
test-user ID and reviewed wanted fixture. Set `source_target_plan_path` and
`target_manifest_sha256` to the source's exact reviewed target plan. Record
`smoke_session_file` as an owner-only external file path for a fresh isolated-app
session. The initial `CLIP_NFR07_SMOKE_SESSION_COOKIE` is checked against the
source app before the restore; it is never assumed to exist in the backup.

During the separately approved restore, the observer verifies the new private
DB and integrity, then waits for app checks within the same original 30-minute
deadline. In a second operator terminal, obtain the new RDS endpoint and approved
restored DB credentials through the secret manager; supply the constructed URL
as ephemeral `TF_VAR_nfr07_restored_database_url`,
`TF_VAR_nfr07_restored_identity_database_url` and
`TF_VAR_nfr07_restored_conversations_database_url`, preserving each domain
role and reviewed database name on the restored instance. Record the Identity
and Conversations database names in the smoke manifest. Then increment
`nfr07_database_url_version` to at least 2 and apply the separately reviewed
activation plan with `nfr07_smoke_running=true`. The SSM values are write-only and
does not enter Terraform state. Never print the URL or place it in tfvars or Git.
Changing the endpoint requires publishing a new parameter version and restarting
only the smoke task; ECS does not refresh an already injected secret.

Sign in normally to the isolated app with the approved test account and put
its new session cookie into `smoke_session_file` through the secure handoff
(mode 0600, current owner, regular file, no symlink). The observer verifies all three database parameter endpoints and database
names, the service/image/TLS routing, user and wanted fixture. Restore,
parameter publication, task startup and real login all count toward 30 minutes.
A missing session, failed integrity check or late startup cannot produce a pass.

After collecting evidence, the separately approved cleanup scales the smoke
service to zero, removes its opt-in resources/parameter and restores host caps;
delete or retain the restored DB only as approved. Preserve source resources,
the backup and raw receipts. Account for ALB, logs, extra compute, restored DB
and retained storage in NFR-08. This document supplies no apply/restore/delete
approval and records no live NFR result.
