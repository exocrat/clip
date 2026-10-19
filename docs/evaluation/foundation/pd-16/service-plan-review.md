# PD-16 Step 8 — corrected service plan for review

**Status:** Non-applying plan succeeded on 2026-10-19. Human result/plan approval pending. No Step 9 apply, RDS restart or task invocation has run.

## Exact target and artifact

| Field | Reviewed value |
|---|---|
| Caller/account | IAM `adityalaxmi1`, account `335523638354`; non-root preflight matched. |
| Region/environment | `ap-south-1`, shared `test`. |
| Terraform/root | 1.15.9; `infra/terraform/shared/test/`, default workspace. |
| State | Bucket `clip-tfstate-335523638354-ap-south-1-20261019-0e51ca0`, key `shared/test/terraform.tfstate`; current lock absent after planning (HeadObject 404). |
| Plan path | `/tmp/clip-pd16-service-plan-t35ha1uc/service.tfplan` (0600; parent 0700). |
| Plan SHA-256 | `f02303878b94e7baa96d6f617ee7a8162c5fc25e1bda9890bee1ba787f29986a` |
| Input SHA-256 | `8faaa1d0722a0d2cd0077946686033785296520ef7698f4fd356b7c21c661ee2` |
| Result | Exit 2: **7 creates, 0 changes, 0 deletions**, `errored=false`; state serial before plan 4. No apply. |

[Safe result, reviewed attributes and source fingerprints](service-plan-result.json). Raw state/plan/rendering and retained probe credential stay in the private external directory, not Git. The earlier failed plan remains separately marked not for apply.

## Seven resources to create

| Resource | Purpose/boundary |
|---|---|
| API task definition `clip-test-api-ap-south-1-pd16` | Linux X86_64, CPU 256, memory 512; approved API ECR digest; bridge 8000→host 18000; existing API execution/task roles. |
| API service `clip-test-api-ap-south-1-pd16` | Desired count 1 using the existing capacity provider; reviewed ASG remains min 0/max 1. Applying may launch one private EC2 host/root volume; this is not an additional Terraform-managed instance resource. |
| Setup task definition `clip-test-db-role-setup-ap-south-1-pd16` | Fixed script, existing setup roles, references master and probe SecureStrings; bounded client/SQL execution. |
| Probe task definition `clip-test-db-probe-ap-south-1-pd16` | Fixed script, existing probe roles, references only the dedicated probe SecureString. |
| Setup execution-role policy `clip-test-db-setup-secrets-ap-south-1-pd16` | Only `ssm:GetParameters` on the two fixed credential references. |
| Probe execution-role policy `clip-test-db-probe-secret-ap-south-1-pd16` | Only `ssm:GetParameters` on the probe credential reference. |
| `/clip/test/database-probe-password` | Standard SecureString, write-only version 1, approved namespace and shared-team/expiry tags. |

The new probe ARN is computed at apply, so dependent policy/container JSON is partly unknown in the rendered plan. Fixed Terraform references/scripts and pinned input values were reviewed; the source fingerprints are recorded. Step 10 must verify actual rendered definitions/policies after apply. Do not describe source review as live policy/SQL acceptance.

## Images and security

- API: `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api@sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed`.
- Setup/probe client: `docker.io/library/postgres@sha256:9551dd5bf356409a21b31248f49b33bba9bb1877365f3a7e933aecd9af3cf52d` (Linux AMD64, packaged GNU timeout/psql inspected).
- No base network, RDS, master parameter, instance profile or ASG change/replacement/deletion. Existing private access and no inbound API rule remain.
- Human broad-access and `Owner=shared-team` exceptions are explicit in DEC-10/DEC-03; machine role restrictions remain. No new human operator role.
- Corrected plan used the same existing master version 1 only in memory, plus the retained generated probe credential; both write-only counters stayed 1. Neither value appeared in captured output, rendered JSON or decompressed saved-plan entries. The original ordinary SSM/RDS password state fields were empty. No master rotation or credential update is planned.
- Source change in `variables.tf` corrects when the ephemeral master must be supplied; resource logic/version counters remain unchanged. Steps 8/9/13 and the runbook now follow DEC-11.

## Cost, window, rollback and cleanup

The user selected a **two-hour** initial test window. Before a future apply/start, record the actual UTC start and expiry two hours later; no automatic shutdown is installed. One host/task is the capacity cap. The previous recorded fully active estimate is approximately USD 0.35 for two hours before variable usage, startup/scale-in tail and continuing NAT/storage charges. Credit refresh: USD 179.54 remaining / USD 179.49 estimated eligible credits, expiry August 2027; budget actual USD 0.04 and forecast USD 1.232. Conservative estimated credits minus forecast and the older 720-hour USD 125.45 reference leaves USD 52.808 before variables, above the USD 25 reserve. These references do not replace actual Step 12 cost verification.

This plan leaves RDS unchanged; it was verified stopped before planning. RDS start is a separately approved action against `clip-shared-test-postgres`, original resource ID `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, using the non-root profile. No restart was performed during planning.

On apply failure, stop and preserve state/artifacts; inspect partial results before repair. No automatic destroy, password rotation, permission expansion or manual ASG termination. Stopping a deployed service requires a newly reviewed `deployment_phase=service`, `api_service_enabled=false` plan with unchanged ephemeral credentials; verify zero tasks/hosts, then separately stop RDS. Retain images for restart. Full 96-idle-hour teardown retains its separate deletion-protection, manual ECR cleanup and fresh destroy approvals; preserve the PD-15 backend and state versions.

## Next gate

User must verify this result and explicitly approve this exact plan/checksum before Step 9 apply. Pre-apply recheck caller, checksum, source fingerprints, state/current conditions and unchanged master parameter version; re-supply both ephemeral values. A changed plan/source/target/state or unavailable credential requires review rather than reuse. No later deployment, SQL task, restart or cleanup is authorized by this review record alone.
