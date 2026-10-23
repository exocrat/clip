# ID-01 Step 2 — runtime test preparation

Current checkpoint: permission apply verified by Aditya; controlled recipient
verification passed; one-shot command and [runtime plan](runtime-test-plan.md)
prepared with offline checks. No test send, image
publication, deployment or task startup is authorized by that verification.

## Findings
The existing published API image predates the Identity SES adapter and boto3
runtime dependency. Existing ECS task definition is x86_64, bridge network,
uses the approved application task role, and defaults to production mode.
Current sandbox configuration rejects SES in production mode. Therefore a valid
adapter/runtime test needs a reviewed updated immutable image and an explicit
controlled test-mode one-shot task. Do not silently enable sending on the live
API service or count a personal-profile CLI send as task-role evidence.

## Proposed preparation sequence
1. Select one controlled recipient inbox and inspect its SES identity status
   read-only. If verification is needed, separately approve its verification
   message; the human clicks the link without sharing tokens or codes.
2. Prepare a bounded one-shot entry point using the actual Identity adapter and
   generic synthetic content, explicit test mode/one-address allowlist, no retry,
   no database, no credential/content logging, one-message cap and safe outcome.
   Review/test locally and identify exact source revision/build inputs.
3. Prepare separate image build/publication and task-definition/run plans for
   x86_64 using the existing repository/cluster/task/execution role boundaries.
   Resolve shared-root writer/review and ownership before changing task resources.
4. Obtain exact resource/time/cost/cleanup approvals before image publication,
   task registration/start or email. Running on ECS may start the existing EC2
   host through its capacity provider; RDS and API service stay off. Bound startup,
   one send, task stop and host return-to-zero, and review the existing AMI before
   any launch. No unreviewed provider or additional scheduler is implied.
5. Execute only approved actions; verify role/adapter submission, human inbox
   receipt, redaction and cleanup separately. Keep failures/uncertain delivery
   explicit; do not automatically resend.

An SES simulator can establish provider acceptance without a verified real
recipient, but does not establish actual inbox delivery. Production access still
pending; no general-recipient delivery or Step 2 completion is claimed.
