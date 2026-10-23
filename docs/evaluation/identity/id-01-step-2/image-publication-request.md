# ID-01 Step 2 — exact built-image publication request

2026-10-23 07:16:45 UTC. [Build evidence](builder-build-result.md) passed; publication
is not yet approved. This is not deployment, task registration or email approval.

## Exact action
From only approved builder `i-086dd4b9830033682` before its 08:10:00 UTC expiry,
using its reviewed repository-scoped role and non-persisted registry token:
- Source `52186a0466feb24ffb855d9f019c78cd5a17aa39`.
- Local image `sha256:e630678ecb23c3e027b55147a6be4741586e69d22521f1e8b536d212ba7de2c8`,
  `clip-api:id01-amd64-52186a0466fe`, Linux AMD64, non-root, local checks passed.
- Push one new immutable tag to
  `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api:id01-amd64-52186a0466fe`.
  Existing repository confirmed IMMUTABLE; tag absent before approval.
- Recheck operator/builder role, image ID/architecture, repository/tag and expiry.
  Execute [reviewable publication script](builder-proposal/publish.sh.proposed)
  once (ten-minute push cap, no automatic retry). ECR token only in stdin/private
  `/run` Docker config; logout/remove config on exit. Never emit/store token in
  repository, logs, shell arguments or source layers.
- After upload, read manifest with operator profile, verify config digest equals
  the approved local image ID, record immutable registry manifest digest and
  actual compressed size, and recheck target tag. Stop if any mismatch.

## Limits and cleanup
One image, existing repository only; no repository/policy/lifecycle/role change,
no Git push/merge, app deployment, task start or SES send. Fits the current one-hour
builder / USD 1 incremental window; upload incurs NAT processing and subsequent
ECR storage. Keep this one image only for the Step 2 runtime test and until
separately reviewed image cleanup; no automatic deletion of other images.

After validated handoff, terminate only owned builder `i-086dd4b9830033682` and
verify root volume `vol-0125a996fffc44f69` deleted, under the already approved
cleanup authority. On failure, stop without retry/push substitution and perform
owned VM/disk cleanup; hard timer remains as fallback. Do not extend the window.
Temporary IAM/profile/group cleanup remains a separate reviewed removal plan.
Do not claim termination or email-delivery evidence before actual checks pass.

Approve the exact one-image publication above. Existing builder cleanup approval
remains valid; publication does not approve any application runtime/email action.
