# PD-16 Step 7 — validated image handoff and publication preparation

**Checkpoint:** `task/pd16-image-publication`, based on main `68d9da922e4501b94b784da5752ce547087d0b91` (PR #7). User subsequently authorized upload; exact OCI image published and verified on 2026-10-19 16:41:18 UTC. See [publication evidence](../evaluation/foundation/pd-16/ecr-publication.md). The preparation/approval-input sections below describe the prior checkpoint; no Step 8 action is authorized.

## Ordered-step audit and status

The purpose remains one private shared test foundation. The remaining order is coherent: repository exists before upload, digest is fixed before the service plan, live SSM/SQL checks follow service apply, and required lifecycle/evidence checks precede acceptance. No additional task-definition gap was found in this preparation. Missing image access/manifest digest are concrete Step 7 inputs, not passing results. DEC-07 permits bounded staging; original upstream/owner/platform acceptance remains required.

| Step | Output / gate | Recorded state |
|---|---|---|
| 1 | Inspect target, architecture, budget, quotas and skeletons | Performed; refresh action-specific facts before cloud operations. |
| 2 | Minimal private resource architecture | Recorded and reviewed. |
| 3 | Ownership, cost, retention and cleanup | Recorded; exact holding deadline/operator contact still open. |
| 4 | Terraform/image artifacts and local checks | Local checks recorded; native AMD64 image now verified. Original platform matrix remains open. |
| 5 | Exact base plan and approval | Recorded; earlier saved plans cannot authorize changed configuration. |
| 6 | Apply base and verify zero host capacity | Recorded; RDS separately stopped and verified. |
| 7 | Publish verified AMD64 image and record remote digest | Performed: exact source-commit tag/OCI manifest uploaded and remotely verified; human result verification pending. |
| 8 | Digest-pinned service/setup/probe plan | Pending Step 7 and separately approved plan preparation/review. |
| 9 | Apply approved service plan | Pending exact checksum approval. |
| 10 | Live SSM health, private SQL setup/probe, privilege/log checks | Pending service; local SQL tests do not accept cloud integration. |
| 11 | Bounded foundation smoke | Pending; no NFR claim. |
| 12 | Alerts, actual cost and utilization | Pending real deployment checks. |
| 13 | Verified stop/start/scale/retention/cleanup lifecycle | RDS stop verified; restart/ECS lifecycle and exact window remain open. |
| 14 | Inventory, evidence, outputs and closeout | Partial; final verification and acceptance remain open. |

## What is already verified

- Build source `68d6179db03dcf983278b290d22a939af625bba1`, accepted through squash merge `68d9da9`. Comparing its `pyproject.toml`, `uv.lock` and `apps/api/` against merged main shows no differences.
- Native Linux AMD64 build and health passed; see [durable evidence](../evaluation/foundation/pd-16/native-amd64-image-validation.md).
- Local tag `clip-api:pd16-amd64-68d6179db03d`; image ID `sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed`.
- Archive transfer completed on 2026-10-19 16:32:21 UTC; current Linux ARM64 engine loaded the exact `linux/amd64` tag without running it. Its config user is `10001:10001`; no emulation/rebuild was needed.
- PR #7 merged at `68d9da9`; final head `61dd7674` passed [hosted CI](https://github.com/exocrat/clip/actions/runs/39280676449). GitHub returned no formal review entries; the merge is established, independent human approval is not inferred from it.

## Completed archive handoff — 2026-10-19

The user supplied the archive and checksum. Checksum validation passed before load and after relocation; every outer archive SHA-256 blob matched its name. The archive manifest digest matches the committed native-build evidence. Local artifact directory: `/home/mainberry/.local/share/clip/artifacts/images/` (0700); archive and checksum files are 0600. Neither file remains in the repository.

- Archive: `clip-api-pd16-amd64-68d6179db03d.tar.gz`, SHA-256 `b899cbd6fc2551eb11cd310d1de856c08779cbd4c6a56caa5e6e4ed30f5ff188`.
- OCI manifest: `sha256:8f07c52fdfd5a15c29eedae5b7189e6923e5ab0c622459568f70f6d7581a2bed` (matches Docker 29 native-evidence image ID).
- Image configuration: `sha256:bcf4588afe87e681415f51b7581f99f627df04c6b39882022339a06e8c58f38c` (reported as image ID by the current Docker 26 engine).

These identifiers describe different objects in the same verified archive; do not reject this exact artifact because the daemons display different IDs. At archive-load time no image was run, tagged for ECR or uploaded; publication subsequently completed under separate explicit authorization. The original builder export instructions below are retained for repeat handoffs; they are not pending work. Do not copy AWS credentials or contact the builder automatically.

For an archive handoff, the builder first inspects the tag and requires the exact image ID/platform above. They can then export it locally:

```sh
docker image inspect clip-api:pd16-amd64-68d6179db03d --format '{{.Id}} {{.Os}}/{{.Architecture}}'
docker save --output /tmp/clip-api-pd16-amd64-68d6179.tar clip-api:pd16-amd64-68d6179db03d
sha256sum /tmp/clip-api-pd16-amd64-68d6179.tar
```

The builder supplies the archive through the team's chosen file channel and its checksum separately. Keep the archive outside Git. The receiver must verify its checksum, compare the archive manifest/configuration identities and inspect the loaded `linux/amd64` platform before relying on it. Loading an AMD64 image into an ARM64 daemon is an artifact transfer, not a new runtime validation. These are instructions, not commands executed in this preparation.

## Upload package — approved and executed on 2026-10-19

The exact source tag/manifest below was published unchanged using ECR layer/manifest APIs. Repository and identity checks passed; budget refreshed, but current credit balance was unavailable to this IAM user. Refer to publication evidence for the actual result and budget limits. These retained requirements do not imply Step 8 approval.

- Account `335523638354`; Region `ap-south-1`; private repository `clip-shared-test-api`, expected URI `335523638354.dkr.ecr.ap-south-1.amazonaws.com/clip-shared-test-api`.
- Proposed immutable commit-derived tag `68d6179db03dcf983278b290d22a939af625bba1`; recheck repository/tag existence, caller identity/permissions and immutable-tag behavior before approval. Do not overwrite an existing tag with different bytes.
- Artifact is the exact validated image above. Its archive OCI manifest digest is known, but the actual uploading tool may change manifest media type or layer representation. Establish the exact publishable representation/digest before requesting approval; do not assume a legacy Docker push preserves the archive manifest digest, or substitute the configuration digest.
- Refresh current billing/credit reserve, repository settings and existing image storage. Existing proposal reference is USD 0.10/GB-month; actual compressed incremental bytes and bounded upload window remain to be established. Keep the USD 25 reserve and pause/review thresholds.
- Scope: upload only this artifact to the exact repository/tag/digest. No service/RDS restart, IAM change, Terraform apply, image deletion or unrelated resource change. Use an approved non-root profile on the actual uploading machine, not an assumed contributor-wide profile name.
- Failure: preserve safe diagnostics and report partial publication; do not overwrite/delete/retry against changed inputs automatically. Any cleanup/delete has separate exact approval. Retain restart/rollback images and follow DEC-09 manual cleanup.
- Success: read back the remote manifest digest/platform, map it to the tested source, and record the immutable ECR URI for Step 8. An upload approval authorizes neither the service plan nor its apply.

No secret values, registry tokens, saved plans or image archive bytes belong in this document. Checksum/archive/load checks above ran at the user’s request; no runtime test, rebuild, cloud call or upload ran. The user then confirmed the builder had not uploaded and explicitly authorized this operator’s upload. It completed without a competing upload; next await result verification before Step 8. No service/RDS operation is authorized.
