# PD-16 Step 10 — proposed database actions

**Status:** User verified the guarded revision and approved continuation of this exact sequence on 2026-10-19 17:30:27 UTC. RDS start requested; see [execution result](database-action-result.json). No later lifecycle action is implied.

## Target and sequence

Use non-root profile `adityalaxmi1`, account `335523638354`, region `ap-south-1`, shared test only. Recheck STS and all target IDs immediately before mutation.

1. Start only RDS `clip-shared-test-postgres`, original resource ID `db-PYRRZJPVKPGHIXDAHUWATXGH7A`, and poll boundedly for availability. No instance, network, parameter-group, protection, credential or retention changes.
2. Run exactly one fixed setup task `arn:aws:ecs:ap-south-1:335523638354:task-definition/clip-test-db-role-setup-ap-south-1-pd16:2` in cluster `clip-shared-test`, existing capacity provider `clip-shared-test-capacity`, count 1, no overrides. Verify available CPU/memory on the existing host first; no new capacity/configuration authorized. Runtime logging guard must pass before ACL/role/password changes. The transaction revokes PUBLIC CONNECT/TEMP on `clip_test` and PUBLIC CREATE on `public`, creates restricted login `clip_test_probe`, sets its stored probe credential and checks privileges. No application tables/data are changed. Distinct execution role can retrieve master+probe references; task role has no attached/inline AWS policies.
3. Only after setup exits 0 with safe success output, run exactly one fixed probe `arn:aws:ecs:ap-south-1:335523638354:task-definition/clip-test-db-probe-ap-south-1-pd16:1` with the same cluster/provider/count/no-override constraints. It receives only the probe secret, authenticates, executes SELECT 1 and checks restrictions. Inspect safe exit/log status; never print secret-bearing diagnostics. Stop on failure, unavailable resources or timeout; no automatic reruns, logging changes, password rotation or repair.

Both SQL clients retain connection 10s, SQL/lock 30s and complete-client 60s + at most 5s forced exit. Allow at most 20 minutes for RDS startup and 5 minutes per task scheduling/completion within the original window; return status rather than silently extend it. Check progress between bounded calls. Ordinary PostgreSQL logging defaults may make setup fail safely; do not bypass the guard. A failure before its guard passes performs no ACL/role/password changes; an unknown timeout/late failure still needs investigation before retry.

## Cost, security and cleanup

Existing one-host cap, private bridge/routing/security groups and zero public ingress retained. RDS restart resumes compute charges within the existing two-hour window ending **2026-10-19 19:17:08 UTC**; no automatic shutdown/extension. Existing full-active reference approximately USD 0.35 per two hours before variable/tail/NAT/storage charges. Last recorded eligible estimated credits USD 179.49 and budget actual USD 0.04/forecast USD 1.232; no fresh cost claim here.

No full teardown or source rollback authorized. On failure retain artifacts/state, leave resources for diagnosis and report continuing cost. After checks/window, service shutdown still needs its reviewed desired-count-zero Terraform plan; verify tasks/hosts zero and separately authorize RDS stop. Preserve ECR images, DB data and PD-15 state/backend. This action approval does not approve those later lifecycle plans.

## Continuation after local-logging correction — approved and executed

Initial approved sequence above stopped on revision 2's logging guard, before ACL/role/password mutation; probe did not run. RDS is already available; do **not** start it again.

User approved the exact continuation; [setup and probe both passed](database-retry-result.json). The approved sequence used exactly one setup task using `arn:aws:ecs:ap-south-1:335523638354:task-definition/clip-test-db-role-setup-ap-south-1-pd16:3`, then the unchanged probe revision 1 only on setup exit 0 and expected safe success log. Account/profile/region/cluster/provider/count, existing single-host capacity and all no-override/timeout/security/cost/cleanup constraints above remain the same. Use a new client token for this distinct authorized invocation. The new script conditionally suppresses logging only within its transaction and verifies the guard; no global settings/grants/fallback. On denied SET privileges or any failure, stop without another retry or probe. No runtime support is inferred from successful registration. Window still expires **2026-10-19 19:17:08 UTC**.
