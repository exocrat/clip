# NEXT-06 dataset cloud handoff

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
