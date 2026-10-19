# PD-16 evidence and AMD64 handoff

**Publication reconciliation — 2026-10-19:** PR #7 merged at main `68d9da9`; final head `61dd7674` passed [hosted CI run 39280676449](https://github.com/exocrat/clip/actions/runs/39280676449). The local/push-pending statements below describe evidence-capture time. Independent approval is not inferred from the merge (GitHub formal reviews were empty). Current checkpoint: [Step 7 image handoff/publication preparation](../../../environment/pd16-image-publication.md).

PR #7 local review corrections: [deadline tests, real lock failure check and manual ECR cleanup resolution](review-corrections.md). This evidence covers the tested correction worktree; Suraj verified the result and approved its commit. Publication and current hosted/independent review remain pending.

## Step 10 live verification — passed, human verification pending

[Revision-3 setup and revision-1 probe](database-retry-result.json) both exited 0 with expected safe logs. Role/ACL assertions, SELECT 1 and privilege checks passed. [SSM/API health](step10-health-result.json), [private network/log-stream checks](step10-network-result.json) and approved running digest/definition checks complete Step 10 execution. Web hosting deferred until target/access and approval. No domain/NFR acceptance; Step 11 and remaining PD-16 gates pending. RDS/one API host running; expiry 19:17:08 UTC unchanged.

## Step 10 transaction-local correction — applied

[Apply result](local-logging-apply-result.json): setup revision 3 active and source-matched, state serial 7, lock released; no SQL rerun. Await verification and [exact revision-3 execution approval](database-action-review.md#proposed-continuation-after-local-logging-correction--approval-pending).

### Approved correction plan

[New plan and checksum](local-logging-plan-review.md): setup-definition replacement only. Correction local; no apply/SQL rerun. RDS/one host running, original expiry unchanged.

## Step 10 database setup — safely blocked

[Database execution result](database-action-result.json): RDS started; setup revision 2 exited 1 because effective logging failed its guard. RDS error log confirms rejection before ACL/role/password changes. No probe or retry. [Private-network/log-stream checks](step10-network-result.json) passed. RDS and one host remain running; window ends 19:17:08 UTC. Await a reviewed logging decision before repair.

## Step 10 guard replacement — applied

[Apply result](logging-guard-apply-result.json): setup revision 2 registered, script matches source; one create/one deregistration, state serial 6, lock released. RDS stopped and no SQL task invoked. Await result verification and separate database-action approval.

### Approved plan

[Runtime guard plan/checksum and review](logging-guard-plan-review.md): only setup task-definition replacement; guard local and unexecuted, no apply/restart/task invocation.

## Step 10 SSM health passed — database precheck pending

[Health/session and registered-definition checks](step10-health-result.json): HTTP 200, expected body, session terminated. RDS stopped. Effective database logging is not proven by unset parameter metadata; await decision on runtime guard/diagnostic path before setup.

## Step 9 applied — human-verified

User approved the exact plan and commit first (`2978461`). Apply exited 0: seven creates, no changes/deletions; state serial 5, lock released, credential checks passed. RDS remains stopped. [Apply result and two-hour window ending 19:17:08 UTC](service-apply-result.json). Runtime/SSM/SQL checks remain Step 10.

## Step 8 corrected plan — approved and applied

Fresh authorized plan passed: seven creates, zero changes/deletions; both credentials absent from saved/rendered artifacts, versions unchanged. [Exact plan/checksum and deployment scope](service-plan-review.md). Applied in Step 9 as recorded above; RDS restart remains separately gated.

## Step 8 service-plan validation failure

The first authorized non-applying service plan failed: existing master write-only value/version pairs cannot omit the value. Saved plan is `errored=true`; no apply ran. [Safe failure evidence and pending correction](service-plan-failure.md).

## ECR publication — 2026-10-19

Step 7 upload and remote manifest verification passed and were human-verified. [Step 8 input audit](../../../environment/pd16-service-plan-preparation.md) is active; no service plan has run. The approved source-commit tag resolves to OCI digest `sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed`; [exact URI, identity, cost limits and evidence](ecr-publication.md). Service deployment and real integration remain pending.

## Current native AMD64 validation — 2026-10-19

Built and validated the API image from clean local commit `68d6179db03dcf983278b290d22a939af625bba1` on a native Linux AMD64 engine. Image `clip-api:pd16-amd64-68d6179db03d` reports `linux/amd64`; HTTP `/health` returned 200 with `{"status":"ok"}` and Docker health became healthy. The local image is retained; test container/context were removed. [Exact build/check provenance, commands, local image ID and logs](native-amd64-image-validation.md). This resolves the target-image build/health blocker only. ECR upload subsequently passed as recorded above; live service/SSM/SQL/lifecycle verification, current branch hosted/peer acceptance and full PD-16/PRE-00 acceptance remain pending.

## Recorded outcomes through `cc04a23`

This index preserves non-secret summaries from the [work log](../../../status/work-log.md) and [proposal](../../../environment/shared-test-foundation-proposal.md). It does not independently rerun those checks. Raw plans/state/credential files must not be committed.

| Check | Provenance and recorded result |
|---|---|
| Native API container | Linux ARM64, Docker 26.1.5, Python image 3.14.8 and uv 0.10.7; base `c51a000` plus dirty worktree. Allowlisted 172 KB context; `/health` returned `{"status":"ok"}`, Docker health became healthy. Container/image removed. This is not the exact committed AMD64 artifact. |
| Local Terraform | Pinned Terraform 1.15.9, backend-free format/schema validation recorded passed. Shared/test phase uses counted resources: `disabled` against populated state can plan deletion. |
| Base v4 | SHA-256 `25a31e3b74bd11dbfc14e91041f28d487f578ddb2685ac4a1807cd3fcb5af562`; 40 creates. Non-root apply created 39 resources; RDS failed with `FreeTierRestrictionError` for seven-day backup retention. |
| Rejected v5 | Missing `deployment_phase=base` proposed 39 deletions. Not applied. No destructive recovery success is claimed. |
| Recovery v6 | SHA-256 `932a9b62d067ffbb241d6f7cb275e5c0696e80710dc8f14f0a51ff1162345ad4`; one RDS create and 39 no-ops. Apply succeeded with one-day retention. RDS private/encrypted/Single-AZ, ASG zero, no ECS task/service. |
| AMD64 legacy attempt | Clean source `37f1d3d5c380e26eac5bb86499e888bdf4adbfd6`, credential-free staged context. ARM64 legacy builder first failed at `uv sync` with `exec format error`; temporary QEMU attempt segfaulted while downloading `pydantic-core`. |
| AMD64 BuildKit attempt | Same clean source; temporary Buildx 0.37.2 / BuildKit 0.33.1 reached `uv sync` and reported an empty PEP 508 entry in the dev group. Staged manifest hash matched source and TOML parsing passed. Root cause is unresolved; neither package incompatibility nor emulation-only failure is proved. |

At that historical checkpoint, no AMD64 image/upload, service deployment, SQL probe or lifecycle verification had been recorded. Original logs/contexts were retained under `/tmp/pd16-api-amd64-37f1d3d*`; their continuing availability is not assumed. Exact raw command invocations/exit statuses not retained in canonical Markdown cannot be reconstructed as verified evidence. Temporary builders, binfmt handler, helper images and plugin were recorded removed. See [bootstrap migration evidence](../../../../infra/terraform/bootstrap/state-migration-plan.md) separately.

## Native AMD64 developer handoff

1. Agree the exact reviewed source SHA after audit corrections. `37f1d3d` identifies historical failures; it is not automatically the final approved handoff revision.
2. Use a clean checkout of that SHA and record clean/dirty state, Linux AMD64 host/engine architecture and Docker/tool versions. Never copy AWS profiles, dotenv files, virtual environments, Git metadata or datasets into the image context.
3. Follow the [allowlisted local build and health procedure](../../../environment/commands.md#local-api-container-image--pd-16-step-4) on the native AMD64 host. The procedure builds the worktree, so first ensure it matches the agreed commit. Preserve the build command, exit result, image architecture/ID, HTTP/health result and cleanup outcome. This is the pending target image validation, not a macOS/Compose matrix pass.
4. If the build fails, retain sanitized output and the exact source/tool/architecture provenance. Do not change dependency pins merely to make the symptom disappear; explain and review the cause/change first. Do not publish credentials or unredacted diagnostics.
5. After a successful build, agree the exact ECR account/Region/repository and immutable commit-derived tag, determine the publishable manifest digest with the selected tooling, and obtain explicit upload authorization. A local Docker image ID is not necessarily the registry manifest digest. Verify the remote digest after the authorized push and pin the service plan to it. Building alone does not authorize upload, deployment or cloud changes.

The service plan/apply and real SSM/SQL/lifecycle checks remain PD-16 Steps 8–14. PRE-00, domain implementation, NFR results and independent human peer approval remain separate gates.
