# ID-01 Step 2 — approved builder apply and native image validation

2026-10-23 07:16:45 UTC; Aditya (A). Exact plan apply + one bounded native build
and owned VM/disk termination were explicitly approved. No image push or email
sending was included or performed.

## Applied resource verification
Plan SHA-256 `c4367471d67ad0fd90873484e01a5688a31c62f738c135087e4117cec9c7442d`
applied once after exact source/lock/account/backend/idle-capacity/budget checks.
Five creates succeeded in the Identity root/state; serial 2. Owned resources:
- VM `i-086dd4b9830033682`, private t3.small / Amazon AL2023 AMD64.
- Root disk `vol-0125a996fffc44f69`, 20 GiB encrypted gp3, DeleteOnTermination.
- Group `sg-00f275fda4e0f5104`, verified zero ingress and only HTTPS egress.
- Dedicated builder role/policy/profile, policy exactly matches reviewed plan.

No public IP/SSH key; IMDSv2, terminate-on-OS-shutdown verified. SSM agent
3.3.5390.0 online. Cloud-init completion, active bootstrap timer/Docker/SSM and
native x86_64/amd64 checks passed through command
`c3dda312-3ada-43cf-b0ef-10ed2882725d`. The boot-relative timer started after boot;
added and verified an earlier absolute cleanup timer for **2026-10-23 08:10:00 UTC**,
within the operator's 08:10:15 UTC one-hour limit. Command
`65aec954-84fc-42a8-8a5c-868d122c17ce` succeeded; original timer retained as fallback.
Actual shutdown/volume deletion still require verification, not assumed.

## Exact image and checks
Reviewed app source `52186a0466feb24ffb855d9f019c78cd5a17aa39`. Allowlisted archive
only; gzip SHA-256 `34f1404bec5c4971ed022ed3e4ba4ba0d2599b8d12f7b05032913b76e855deb0`.
Seven bounded source chunks plus final checksum/script transfer succeeded through
SSM. No credentials/recipient/.env/local caches uploaded. One native build command
`f4b5b104-5be0-4edd-8070-3d8f62af51fe` completed successfully.

- Local image tag `clip-api:id01-amd64-52186a0466fe`.
- Image ID `sha256:e630678ecb23c3e027b55147a6be4741586e69d22521f1e8b536d212ba7de2c8`.
- Linux AMD64; configured user `10001:10001`, runtime UID 10001 checked.
- Image size 163,822,161 bytes (local, not compressed registry size or cost).
- Python 3.14, boto3 and actual Identity smoke module imports passed.
- Default-denied smoke command exited 1 with only fixed `failed_or_uncertain`
  output; network disabled, no recipient/credentials/approval passed.
- Normal API process became Docker-healthy with network disabled and no host
  ports; owned test container removed by script trap. No container remains.

Safe result/private command checkpoint files are in
`/tmp/clip-id01-builder-transfer-_24umv5r/`; apply artifacts in
`/tmp/clip-id01-builder-plan-aa0f7ct5/`. Raw remote build output retained privately
on the disposable VM, not repository. Source/body/recipient/credential output is
not included in evidence. No SES call or application task-role use occurred.

## Pending publication and cleanup
Builder remains running temporarily within approved one-hour / USD 1 cap; hard
termination scheduled 08:10:00 UTC, regardless of delayed publication approval.
No ECR login/push yet. Proposed tag was verified absent in the existing immutable
repository. Exact publication approval requested separately; if absent before
expiry, allow termination and report the unpublished image lost, not silently
push or extend runtime. IAM/profile/group removal requires reviewed cleanup plan.
Step 2 remains partial: real ECS task-role delivery and production access pending.
