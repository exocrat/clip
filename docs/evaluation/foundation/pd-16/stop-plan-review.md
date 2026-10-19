# PD-16 Step 13 — requested compute shutdown

**Status:** User requested host/RDS stop. Non-applying service shutdown plan passed; exact saved-plan apply approval required by Step 13. Nothing stopped yet.

| Field | Value |
|---|---|
| Account/profile/region | `335523638354` / non-root `adityalaxmi1` / `ap-south-1`, shared test |
| Terraform/backend | 1.15.9, default workspace; existing bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, key `shared/test/terraform.tfstate`, serial 7 |
| Plan | `/tmp/clip-pd16-stop-plan-ch56ou4b/service.tfplan` (private) |
| **SHA-256** | **`07fb248e2f0fe130782e0d1c60dfc151b2f6578c9ebfbc15239fea1c82277df5`** |
| Exact change | `aws_ecs_service.api[0].desired_count`: **1 → 0**, in place; no other resource/attribute change, creation or deletion |

[Safe result/fingerprints](stop-plan-result.json). [Non-secret shutdown inputs](../../../environment/pd16-stop-plan-inputs.json) differ from approved run inputs only by `api_service_enabled=false`; phase stays `service`. Existing master/probe versions retrieved into memory only, counters unchanged, values absent from captured/saved/rendered artifacts. Lock released (404).

## Authorized sequence and limits

User explicitly requested compute shutdown ahead of Step 12 cost review; that review remains pending. Step 13 shutdown audit is coherent: apply only the checksum-matched plan after caller/source/state/credential preflight; let ECS stop API tasks and managed scaling drain/terminate the empty host. Do not stop EC2 or change ASG capacity manually. Observe cluster tasks and ASG desired/instances until zero. Allow up to 30 minutes observation with progress updates (15-minute scale-in reference is not a maximum); if stalled, stop and review instead of forcing termination.

After confirming zero running/pending tasks and zero hosts, use the already requested RDS stop against `clip-shared-test-postgres`, original resource ID `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, rechecking non-root caller/private/encrypted/protected target and operator use. User is the current operator; no other workload/session has been authorized and both SQL tasks finished. Issue stop once and poll read-only up to 10 minutes, stopping on unexpected status/error. No additional RDS-stop authorization is requested beyond the user's current explicit instruction. Retain DB storage, credentials, images, task definitions, network and PD-15 backend/state.

## Cost, rollback and cleanup

This avoids future host/RDS compute charges once stopped, with scale-in tail; NAT, DB storage/backups/logs, ECR and backend remain billable. Recorded idle reference approximately USD 6.21/96 hours before variable/tail costs, not a bill/cap. Last eligible estimated credits USD 179.49; budget actual USD 0.04/forecast USD 1.232. Actual cost review remains Step 12. Original run expiry **2026-10-19 19:17:08 UTC**, no extension or automatic shutdown installed.

On failed apply/scale-in/stop preserve state/artifacts and report actual running capacity; no retry, force termination, rotation or destroy. Resume needs separately authorized RDS start and a fresh reviewed desired-count-one plan; retain exact images. Existing 96-hour idle teardown requires its separate reviews/deletion-protection/destroy approvals. RDS can automatically restart after seven stopped days. Exact idle-clock/ownership-contact closeout remains pending; current cleanup review date 2026-10-23.
