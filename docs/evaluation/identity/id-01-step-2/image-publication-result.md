# ID-01 Step 2 — approved image publication and builder cleanup

2026-10-23 07:23:06 UTC; Aditya (A). Exact one-image ECR publication explicitly
approved; owned builder VM/disk termination already approved. Result awaits
human verification; no application deployment/task start/email is accepted.

## Published artifact
Source `52186a0466feb24ffb855d9f019c78cd5a17aa39`.
Local config/image ID `sha256:e630678ecb23c3e027b55147a6be4741586e69d22521f1e8b536d212ba7de2c8`.
Immutable tag `id01-amd64-52186a0466fe` in existing
`335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api`.
Registry manifest digest:
`sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`.
Deployable immutable reference:
`335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:3ef8b13d3b102dc97e67d79d91e43eb8d4b2cc02fbabb45cf6001c8a93eddd1d`.
Registry-reported compressed size 68,148,997 bytes, not a measured storage bill.

Preflight reconfirmed operator/builder identity, exact local image and AMD64
architecture, unexpired VM, immutable repository and unused tag. One publication
command `f6c0eb96-14ca-4c10-a840-40b6b4a84c67` succeeded, no retry. Registry token
passed only to login stdin; private `/run` Docker config logout/removal trap
completed. No credential value in command inputs, source, image or evidence.

Operator ECR manifest read verified schema 2 config digest equals the approved
local image ID; describe-images matched the same tag/digest. No other image tag
or repository/policy/lifecycle setting changed. Previously recorded runtime,
non-root, denied-smoke and isolated-health checks apply to this exact artifact.

## Actual cleanup
After manifest verification, terminated only builder `i-086dd4b9830033682`.
Termination requested 2026-10-23 07:21:41.633195 UTC; verified terminated and root
`vol-0125a996fffc44f69` absent on 2026-10-23 07:22:28.116194 UTC. Completed before
the approved 08:10:00 UTC deadline; no fallback-timer assumption needed.
No builder compute or root disk retained. Temporary role/inline policy/profile
and security group remain managed by Identity state until separately reviewed
removal; neither silently deleted nor claimed cleaned up.

Original RDS remains stopped; shared ECS running/pending tasks zero and ASG
hosts/desired zero. No application task started, no SES message sent, no DB
startup, no Git push/merge or additional local commit. Existing shared idle
cleanup deadline unchanged. One published image retained only for runtime test
handoff and separately reviewed image cleanup; ongoing registry storage retained.
Raw publication/cleanup checkpoints stay private in
`/tmp/clip-id01-builder-transfer-_24umv5r/`; no token/recipient/content evidence.
`git diff --check` passed. This does not prove task-role email delivery.

## Next checkpoint
Human verifies this publication/cleanup result. Then prepare the actual
Identity-owned smoke task definition pinned to the verified digest and the
removal plan for the four temporary IAM/profile/group resources. Task
registration/apply and any one-send compute/runtime window remain separate
reviewed approvals; production access still pending. Step 2 stays partial.
