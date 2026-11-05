# NEXT-06 dataset cloud handoff

**Current disposition (2026-11-05 15:26:56 UTC): Aditya confirms NEXT-06 complete. Pending gates and cloud handoff notes below are historical; they do not represent open NEXT-06 work.**

**Current checkpoint:** [Frozen release/task-wide review](task-wide-review.md). All six output/check groups are represented; Step3normal vector check is human-reported complete. Formal Step6human/current-headCI/peer/merge acceptance remains. Earlier broad hosted-runtime handoff statements are historical and do not create new NEXT-06implementation work.

Prepared for the contributor/operator who will load Mohit Mahapatra's reference
dataset into the shared project environment. This document is a procedure and
handoff, **not approval to deploy, start resources, upload, grant access or reset
an existing database**. Follow root AGENTS.md, CONTRIBUTING.md and the reusable
task prompt; retain each original NEXT-06 integration obligation.

## 1. Account restriction and starting state

- **Use only AWS account `335523638354`, region `ap-south-1`.** Mohit explicitly
  halted use of account `387743104934`; its root profile must not be used as a
  fallback. The earlier permission to use that identity has been revoked.
- On Mohit's machine `default` authenticated as root in `387743104934`. No ECS,
  RDS or S3 inspection was confirmed successful there: the proposed ECS command
  was interrupted. No load, upload, start or configuration change was performed.
- Use the receiving operator's authorized non-root project profile. Verify STS
  before any resource inspection; stop on the wrong account or unclear principal.
  Do not request credentials in chat, commit them or copy another person's profile.
- [Cloud inventory](../../../environment/cloud-inventory.md) is historical:
  the last recorded shared ECS/RDS were stopped and Hybrid/worker disabled.
  Refresh actual state under approved read-only scope. Do not assume these
  observations still hold or create replacement infrastructure automatically.
- Current task branch: `task/next-06-reference-dataset`; base revision
  `6edb52ba4e5a148386cd81e78b29c15b557193c7`. Mohit authorized committing/pushing this branch and creating its PR, including
  the complete tracked image/payload archive. Use the reviewed PR source; checking
  out the base commit alone lacks this work. Accepted merge remains a separate gate.

## 2. What is ready and what is not

The complete local sequence was performed and verified by Mohit:

| Item | Verified local state |
|---|---|
| Users | 5,000 active regular synthetic users; valid unique Handles; no temporary users in the benchmark |
| Listings | 1,000, with 1,000 distinct regular owners and one image each |
| Discoverability | 800 available, 100 explicitly unavailable, 50 future, 50 expired |
| Content | 9 categories, 45 item/synonym topics, 4 conditions; approved price/negotiability/proof distributions |
| Photos | 45 real source files, 1,000 distinct backed local object bindings |
| Semantic pipeline | Real pinned all-MiniLM-L6-v2, 384 dimensions; 1,000 current sources, 2,000 vector parts; zero missing/stale/failed parts |
| Rebuild | Same newly owned local DB reset, 29 migrations reapplied, input reloaded and text re-encoded; rows/media/vectors/65 indexes matched |
| Normal publication | Real Listings upload/confirm/create and background dispatcher generated a new vector and returned the new listing in Hybrid, in a separate clone |
| Judgments | Mohit accepted all 22 relevance groups and inclusion policy, without corrections |

Caller/eligibility and local file delivery in those tests are explicit fixtures.
They do **not** establish real Identity sessions, S3/IAM or deployed integration.
The registry still lists ID-READY/LI-CORE/SE-CORE/DATA-READY as not accepted.
Final source/contract/label binding and freeze remain pending; do not mark the
task complete from these local results.

## 3. Files to obtain and preserve

**Complete transfer is included in this PR:** [archive and instructions](../../../../data/transfer/README.md)
contain all45photos and both ignored payloads. No separate image download from
Mohit is needed. [Transferred judgments](transfer/accepted-judgments.json) rebind
the unchanged decisions to the publication-safe source fingerprint. The inventory
below also describes the original source locations.


Use [current transfer evidence](transfer/result.json) for the source-only rebind
and native verification. Historical local checks remain at [Step 6 evidence](step-06/result.json),
[freeze candidate](step-06/freeze-candidate.json),
[retained local receipt](step-06/local-rebuild-receipt.json) and the
[reviewed loading design](../../../architecture/reference-dataset-loading.md).

Obtain these inputs from Mohit's clone through a reviewed transfer:

1. The task source, tests and documentation, especially `data/generators/reference.py`,
   `reference_load.py`, and `scripts/evaluation/reference_local.py`,
   `reference_embeddings.py`, `reference_rebuild.py`.
2. `data/evaluation/reference-recipe.json` and `reference-image-inputs.json`.
3. Both `data/runs/next06-transfer-42-20261030-a/` and `...-b/`, including each
   `dataset.json` and `manifest.json`. **Payload JSON is ignored by Git**; a source
   checkout does not supply it. Never overwrite an existing named run.
4. The external source folder on Mohit's machine:
   `/Users/mohitmahapatra/Desktop/clip-dataset-images`. Transfer its **45 files**
   with category subfolders/relative filenames intact and verify every inventory
   hash. The original folder is external; its verified45photo copies are now included
   in the authorized transfer archive. Do not substitute photos.
   The explicit `mobile_phone/dual-sim-smartophone.jpg` spelling is an approved
   inventory alias, not a filename to silently fix.
5. [Accepted judgments](step-05/accepted-judgments.json),
   [candidate ID mapping](step-05/candidate-proposals.json),
   [catalogue](step-05/listing-catalogue.csv) and
   `data/evaluation/query-labels.draft.json`. The accepted-judgment sidecar is the
   authority for the human decisions; the canonical draft deliberately has null
   final metadata. Do not request the same unchanged judgments again.

Source photos total 41,861,658 bytes (44 JPEG, 1 PNG). They are reused across
distinct per-listing objects: the approved 1,000-object logical volume is
**925,881,224 bytes**, before storage/version/request overhead. Local hard-link
savings do not imply the same S3 storage volume. Retain originals until the
approved cloud objects and reproducibility artifacts have been independently checked.
Do not transfer the temporary local PGDATA or fake signed-file transport as a
production deployment.

## 4. Verify inputs and timing before cloud writes

The current local logical fingerprint is:

```text
sha256:7efd142e11c3e8555e1aa08603cbf8dff07de5d74412ccde3c39869b9334ab98
```

On the reviewed original source binding, validate both named inputs using the
receiving machine's repository-local Python and transferred photo root:

```sh
.venv/bin/python -m data.generators.reference validate --name next06-transfer-42-20261030-a --image-root /absolute/path/to/clip-dataset-images
.venv/bin/python -m data.generators.reference validate --name next06-transfer-42-20261030-b --image-root /absolute/path/to/clip-dataset-images
.venv/bin/python -m pytest data/tests -q -W error
```

The image path above is a placeholder to replace, not a cloud target. Validation
binds actual source/config/migration/photo state. A source revision/schema/config
change can invalidate the original binding: stop and review/rebind, never edit
hashes to silence the validator. Preserve stable IDs, content and human decisions
when unchanged; record any necessary new version/fingerprint transparently.

The benchmark comparison window ends **2026-12-01T00:00:00Z**. Future listings
start December 2; current/unavailable windows end December 31. This is not a
promise of permanent eligibility. Finish matched November runs before the cutoff;
afterward obtain a reviewed new window and revalidate. Temporary-account permission
fixtures are separate fresh fixtures with the unchanged real 14-day lifetime.

## 5. Approve the actual cloud plan

Before mutations, give the human a concrete plan identifying:

- Verified account, principal, region and reused shared resources; current
  readiness evidence and source/contract/migration revisions, with Identity and
  Listings owners reviewing their records and roles.
- Exact **isolated database**, restricted load/runtime roles, secure connection
  route, actual schema/runtime sensitivity threshold (local value was 500,000
  paise), and active taxonomy. Never load into a populated shared target or grant
  broad permissions to bypass a failure.
- Exact existing S3 bucket and run-owned prefix, authoritative upload-ID key
  mapping, IAM, encryption, CORS and owner-bound upload/inspection/delivery path.
  Do not invent a bucket or reuse an unrelated feature's prefix.
- Accepted runtime/model image and helper packaging, worker configuration,
  operator access and actual session/browser origin. Local `.tools` binaries
  are not portable runtime artifacts; follow the supported deployment build.
- Storage/request/compute cost estimate using current prices, explicit spending
  cap and time window, stop conditions, rollback, retention and cleanup owner.
  Resource starts, deployment, upload, SQL load and IAM changes retain their
  separate exact approvals. A read-only approval or this document covers none.

## 6. Review the prepared cloud adapter, then load

**The cloud adapter is now implemented and locally tested:**
`data/generators/reference_cloud.py`, sharing actual insertion/projection checks
in `reference_rows.py`. Live execution is not performed or accepted.
`reference_load.py` and `reference_local.py` retain native Unix-only guards;
never pass them RDS targets, weaken their guards or deploy fixture auth/storage.
`--rebuild-check` stays local-only.

Use the offline command before choosing/approving any cloud target:

```sh
.venv/bin/python -m data.generators.reference_cloud plan --name next06-transfer-42-20261030-a --image-root /absolute/path/to/clip-dataset-images
```

It validates local inputs and prints requirements; no SDK client/cloud/DB call is
made. Copy `data/evaluation/reference-cloud-target.template.json` to an approved
private operator configuration and replace every null using verified bindings.
The template is deliberately non-executable. `source_revision` binds the input's
base revision; separately review the exact deployed loader revision/content hashes
in the pre-cloud review package. Do not assume the input base contains this loader.
The TLS secret must exactly match host/port/database/role, use `sslmode=verify-full`
and an approved `sslrootcert`, injected only through `CLIP_DATABASE_URL`.

After separate exact target/cost/action approval, the implemented command is:

```sh
.venv/bin/python -m data.generators.reference_cloud load --name next06-transfer-42-20261030-a --image-root /absolute/path/to/clip-dataset-images --target /absolute/private/approved-target.json --ledger /absolute/private/new-run-ledger.jsonl --execute
```

These paths are placeholders, not live targets. The adapter accepts only project
account335523638354/ap-south-1, verifies non-root STS identity, enforces the approved
bucket owner, run-owned prefix, create-only PUT/checksum and bounded GET/hash for
every key. It checks exact TLS session/schema, restricted role and empty reference
rows/pipeline registry before upload; repeats checks after upload and checks
emptiness again under SQL locks before commit. SDK retries are disabled, per-call
connection/read limits apply and CLI work is capped at15minutes. It never starts,
migrates, grants, deletes, resets or automatically resumes. A create-only0600
fsynced ledger records each planned key before PUT, verified bytes and SQL planned/
committed state. Failure may leave attempted objects or an uncertain commit;
inspect evidence before any separately approved cleanup or retry. An existing key
is a refusal, not permission to overwrite. No real auth/S3/IAM acceptance is inferred
from local Stubber/guard tests or bulk success.

The receiving contributor must independently review the adapter and close the
original Step3 real integration obligation using the approved plan/contracts:

1. Verify all source/target bindings, fresh/empty target tables and actual roles,
   constraints, migrations and categories. Refuse drift and nonempty targets.
2. Upload actual bytes to 1,000 distinct authorized per-listing keys, preserving
   approved upload/image/operation IDs and owner mapping. Derive keys through the
   real Listings storage key builder; generated relative plans and
   `reference-local/...` keys are not cloud object keys. Reused topic photos still
   require every planned reference to resolve to actual inspected bytes.
3. Use reviewed real media inspection/confirmation semantics before inserting
   confirmed metadata. MIME/size/hash and owner attachment must agree; audit
   confirmation/expiry times must satisfy the schema at load time. Never fabricate
   ready rows, disable triggers/FKs or reuse expired confirmation windows.
4. Apply the reviewed bounded schema-aware bulk transaction, force deferred
   constraints and record a safe target/key mapping receipt. Generate no passwords,
   sessions, OTPs, real contact records or provider sends from bulk synthetic users.
5. Verify exact distributions/counts/relationships/Handles/eligibility, all 1,000
   image references and bytes, actual GIN index, and stable unique pagination of
   800 discoverable records. Verify actual owner/nonowner/anonymous image access
   with real Identity sessions and S3 signed delivery. Use actual authorized test
   identities without adding login secrets to every synthetic user.
6. Roll back only within the approved isolated scope on failure. SQL rollback does
   not undo S3 writes; retain a precise object ledger and use only the approved
   run-prefix cleanup. Never delete shared buckets or reset shared databases.

## 7. Process real embeddings and test deployed publication

Follow [pipeline bootstrap](../../../architecture/semantic-pipeline-bootstrap.md)
and the [operator command registry](../../../environment/commands.md#se-01-explicit-pipeline-statusbootstrapactivation).
The existing operator is `scripts/search_pipeline.py`; it requires approved
database-secret injection and exact non-secret host/port/database/role/pipeline
bindings. Do not put a credential-bearing URL in arguments, logs or this document.

Execute approved `status`, `prepare --execute`, bounded `queue --execute` and
then actual worker processing. Guardedly `activate --execute` only once coverage
is complete. The local pinned pipeline ID is
`4b43fc307151933bf5b0fa80ff4e10f8cb4266194905cd2b15a3d01b2386d9ca`;
verify it against the accepted manifest, not just this copied value.

Require all 1,000 non-retired sources current, including unavailable/future/expired
listings; zero missing/stale/pending/leased/failed/invalid parts at the checkpoint.
Do not copy unrelated vectors, silently reset failed jobs or replace another
serving space. Existing workers, source fences and retry rules remain authoritative.

With actual hosted auth/storage/worker wiring, publish and edit a listing through
the normal app; verify its current vector and Hybrid retrieval after both actions.
Keep smoke mutations outside the frozen baseline or use an approved separate
probe target, then revalidate the baseline. Check Keyword/Hybrid eligibility,
known typos and semantic matches; runtime failures must remain visible.

## 8. Bind labels, freeze and hand back evidence

Preserve Mohit's 22 included judgments and policy. Do not alter labels or drop a
query because retrieval fails. The exact earlier inspection timestamp is unknown;
the sidecar records actual confirmation time separately. Follow the label format
when recording final review/binding metadata; do not invent a historical time.

After accepted readiness/source/contract/corpus checks, produce the reviewed
`data/evaluation/query-labels.json` under the existing format and validate at least
20 included cases against the exact eligible IDs/context. Retain reviewer/date,
inclusion policy and accepted label revision. Do not claim the draft validator
alone attests human review or enables final scoring.

Return a retained manifest and safe evidence for account/target, accepted source
and schema/config, seed, requested/actual counts, logical fingerprint, key/object
mapping and byte checks, real auth/media journeys, pipeline/source freshness,
index state, normal create/edit propagation, label binding, isolated reproducible
reload and freeze. Recheck relevant state before each matched run. Record failed,
skipped or pending checks and cost/cleanup outcome, then obtain human verification
before accepting DATA-READY. NEXT-07 scoring/architecture measurements are separate.

Local checks: 142 data tests, repository Black (325 files), boundaries, contract
freshness and CI parity passed. Broader tests are not all green on Mohit's macOS:
Docker-dependent checks and two Linux `memfd` tests remain unavailable/failing;
the registered secret scanner also requires Docker. Receiving operator must run
applicable full CI/security gates in a suitable environment. Arrange independent
peer review using `docs/prompts/peer-review-prompt.md`; AI findings do not replace
human approval. Commit, push, PR merge and cloud actions remain separately gated.


## Browser-login and current preflight checkpoint

Mohit's named CLIprofilemohitmahapa1 now verifies as non-root in335523638354.
The cloud loader supports CLIbrowser-login profiles through an in-memory expiring
credential bridge (`reference_login.py`), without requiring access keys or a CRT
extra. CLI's normal login cache remains CLI-managed; no new profile is written.
The bridge was verified by a real SDKSTSidentity check. New source changes require
review/commit approval and accepted source binding; earlier snapshots stay historical.

Latest [load preflight](transfer/load-preflight-current.json) reads14scoped calls:
existing t3.microhost is stopped and noSSMmanaged-node record returned; role policy
listing denied (effective runtime permissions still unverified); id01bucket private,
SSE-S3/owner-enforced with projectHTTPSCORS. No grants were changed or required just
to authenticate. Inspecting IAMpolicy metadata is different from actual runtime
permission acceptance: obtain owner review/export or verify the real approved path,
without broadening IAM solely to silence this metadata denial. No SQL connection,
secret fetch, host/database start, upload or deployment occurred. The exact private
access and runtime/storage/load/cost/window/rollback plan still needs approval.

Prepared local-only [v2 probe diagnostics](transfer/probe-diagnostic-v2.md) supersede the proposed remote payload. Historical Phase A failed with both resources stopped. A retry is not authorized by local preparation; verify exact hashes and obtain separate cloud-window approval.

Latest Phase A v2 closeout (2026-10-30 18:20:36 UTC): [receipt and exact execution evidence](transfer/phase-a-v2-20261030/result.json). Both existing resources verified stopped. The runtime role reached the migrations query and was denied SQLSTATE42501; no grants or other repairs made. Real load/metadata gates remain pending.

The runtime migration denial is an intentional documented permission boundary. The next reviewed route is [private administrative read-only inventory](transfer/admin-inventory-plan.md), with repository-local signed Session Manager plugin and verified regional CA. No application-role grant widening, admin credential read or new cloud call has occurred in its preparation. Its exact window requires separate approval.

Latest NEXT-06 administrative inventory (2026-10-30 18:46:54 UTC): [executed receipt and binding comparison](transfer/admin-inventory-20261030/result.json). Read-only inventory passed;32migrations/four schemas; proposed NEXT-06 database and roles absent. Cloud adds three migrations beyond local/corpus29; reconcile accepted source before setup/load. Owned tunnel/session closed and both resources verified stopped. No grants, schema/data writes or uploads occurred.

Source/schema reconciliation: [upstream evidence and isolated setup sequence](transfer/schema-reconciliation.md). Remote main/local/corpus remain29; the shared database’s extra three migrations are in still-open Notifications PR21. Continue preparing the proposed new isolated database on accepted29source, leave shared32unchanged, and preserve later accepted Notifications/source/runtime/freeze rechecks. No source merge/rebind or cloud write is authorized by this reconciliation.

Exact [create-only isolated29database setup package](transfer/database-setup-plan.md) is locally rehearsed and awaits separate cloud approval. The native helper matches canonical dbmate and proves actual restricted bulk SQL/negative privileges. Proposed cloud setup creates the new database and two NOLOGINroles; it publishes no credential and uploads/loads no business data. Native-only activation is not a cloud/session/S3 acceptance. Keep original integration and freeze obligations pending.

NEXT-06 isolated setup (2026-10-30 19:20:00 UTC): [actual successful execution and stopped closeout](transfer/database-setup-20261030/result.json). New clip_next06_reference has29accepted migrations and explicit loader grants; clip_next06_loader/clip_next06_runtime remain NOLOGIN/no password, runtime no grants. Shared32database/service unchanged. No business rows, credential publication or S3objects yet. Owned access closed, both resources verified stopped. Next loader credential/S3/SQL load requires its exact prepared approval.

[Exact ephemeral-loader/S3/SQL package](transfer/cloud-load-plan.md) is prepared locally with native SCRAM and actual bulk/revocation proof. This now proposes one-window memory-only loader access and password clearing, no persistent loader parameter. The new local5432tunnel, planned1000objects/925881224bytes, call/deadline/owner/key limits and no-retry recovery are explicit. Storage-maintainer confirmation is not yet recorded, and controller's gate remains false. No AWS calls/uploads happened in preparation. Original real runtime/session/media/vector/final source/freeze gates remain pending.

NEXT-06 live load (2026-10-31 08:25:12 UTC): [actual S3/RDS execution, sources and ledger](transfer/cloud-load-20261031/result.json).1000images/925881224bytes verified in existing id01bucket prefix id01/next06-reference-42-v1;5000users/1000listings+image records loaded into isolated clip_next06_reference29schema,800discoverable; SQLprojection matches native. Loader password cleared/NOLOGIN, runtime inactive, owned access closed, host/RDSverified stopped. Shared32service unchanged. Retain objects/data; no retry/reset. Real app/auth/signed-media/cloud ML/source-label/reproducibility/freeze remain pending; DATA-READY false.

The human-verified staged vector route now has a [native-tested exact producer window](transfer/vector-window-plan.md). Dedicated proposed clip_next06_embeddings role has column-only listing-id row-lock rights, embedding-only mutations and short-lived credentials; loader/runtime remain inactive. Native actual model/worker published1000generations/2000parts and productionSQLdiagnostics passed. No actual cloud vector writes or Linux/ECS/auth/media acceptance yet; exact next cloud approval and original integration/freeze gates remain.

NEXT-06 actual vector publication (2026-10-31 09:46:20 UTC): [execution/coverage/cleanup evidence](transfer/vector-production-20261031/result.json). Isolated clip_next06_reference now has1000current ready generations/2000actual pinned384-dimensional parts and serving pipeline4b43fc30...; six actual keyword/HybridSQLcases match native and source corpus rows remain unchanged. Dedicated producer password cleared/NOLOGIN; model/access closed and EC2/RDSstopped. No S3or original runtime/service changes. Actual authenticated app/media/normal new-vector workflow and deployedLinuxruntime/source-label/rebuild/freeze acceptance remain pending; DATA-READY false.

Current dataset-evidence checkpoint: [plan and owner handoff](transfer/dataset-evidence-plan.md), [consolidated candidate](transfer/dataset-evidence-candidate.json). Current-fingerprint native reset/reload/media/vector/index parity passed;22accepted judgments unchanged and validated. Actual cloud load/vectors retained. Proposed read-only cloud/native hash comparison awaits separate approval; no second destructive cloud reset required by Step6. Hosted runtime remains with its owner per Mohit. Final labels/source/auth/media/new-vector/freeze gates remain open; DATA-READY false.

Actual read-only cloud/native comparison: [receipt and executed sources](transfer/dataset-snapshot-20261031/result.json). Current source projection,1000generations/2000parts and65index hashes match the fresh native rebuild. All dataset roles inactive; SQL/tunnel/session closed and both EC2/RDS verified stopped. No data/role/object changes or deployment. Candidate now includes actual cloud hashes; original owner integration and final acceptance gates remain open.

Mohit verified the actual cloud/native snapshot checkpoint. [Remaining owner and final-acceptance gates](transfer/remaining-integration-gates.md) give the next evidence needed; preserve existing S3images/RDSdata and leave deployment with its owner. Current dataset candidate records human verification; final DATA-READY remains false.

Current ordered status: Step3normal vector check is complete on Mohit's report of another executor; our local attempt remained incomplete/no objects. Step4actual pipeline evidence was reconfirmed. Step5now supplies [canonical reviewed label bindings](transfer/step-05-final-labels-result.json):22unchanged included judgments, exact source/contract and user-chosen recorded review time. Step6formal freeze/task-wide review remains next; DATA-READY false. Broad historical deployment/ownership statements do not add a hosted deployment requirement to this dataset task.
