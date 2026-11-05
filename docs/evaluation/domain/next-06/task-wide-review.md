# NEXT-06 task-wide review — frozen data and reviewed labels

**Current disposition (2026-11-05 15:26:56 UTC): Aditya confirms NEXT-06/DATA-READY complete. The pending acceptance text below is historical and superseded; retained step evidence and stated limits remain unchanged.**

All six canonical output/check groups are represented in the current package.
Content is frozen; formal task/DATA-READY acceptance remains pending human Step6
verification, current-head CI and independent human review/authorized merge.
No new dataset feature/integration implementation is identified by this review.
Step3's remaining normal workflow check is accepted on Mohit's explicit report
that another person performed it, with no executor/raw receipt/revision invented.

## Canonical ordered-step audit

| Step | Required output/check | Result and evidence |
|---|---|---|
|1|Audit reusable generators/loaders/fixtures/labels and actual missing data|Completed; step-01/result.json and subsequent corrective/source audits retained.|
|2|5000users/1000varied listings, safe synthetic data, workload-required extras|5000regular users/1000listings/9categories/45topics/4conditions. Both full generated record sets identical. Other NFRmutation fixtures are separately assigned by the approved dataset design; no extra bulk-domain records needed by current browse/search corpus.|
|3|Reviewed real schema-aware load, relationships/counts/ownership/availability/indexes/media; normal new-vector behavior|Actual isolated RDSload and1000S3object PUT/GET receipts verified. Normal workflow check complete on Mohit's external-executor report. Our local five-minute attempt remained incomplete/0users/0listings/0object writes and stopped. Neither is rewritten as direct proof of the other.|
|4|Pinned supported prepare/queue/worker/activation, complete coverage and representative results|Actual1000ready generations/2000parts;0missing/stale/pending/leased/failed/invalid/conflicting serving; six production keyword/Hybridcases. Relevant current source/model bindings agree with retained execution.|
|5|20+human judgments with exact IDs/reviewer/date/policy and real bindings|22unchanged included queries;800eligible reference IDs; strict format/actual binding validation. Mohit explicitly chose recorded acceptance timestamp and a12f4a3dataset/6edb52bcontract revisions. No score-driven relabeling.|
|6|Seed/version/count/media/model/index/fingerprint, isolated reset/reload and freeze|frozen-dataset.json records exact fixed inputs/source/labels/model/index hashes. Real same-owned-target reset/reload and separate actual cloud/native snapshot agree. Both payloads and52transfer members verified. No second destructive cloud rebuild is required by the canonical step.|

No additional hosted deployment, RAM upgrade, full Listings feature campaign or
NFRmeasurement is invented as a NEXT-06 requirement. Real Linuxcapacity/latency,
Success@5, architectural experiment and broader domain acceptance retain their
own assigned procedures. A valid freeze is not permission to run them.

## Reproducibility and operational handoff

[frozen-dataset.json](frozen-dataset.json) is the immutable content manifest.
[The label adapter binding](transfer/final-label-binding.json) joins original
truthful generated-only manifests to real load/vector/rebuild evidence. Input
manifests, accepted judgment history,52member photo/payload archive and consumed
execution receipts were not overwritten. New source/schema/model/data/labels
need reviewed versioning/revalidation; never delete an existing release to force
`freeze` through its exclusive-create guard.

Revalidate using the retained/restored payloads/photos and pinned model:

```sh
.venv/bin/python -m scripts.evaluation.reference_labels validate --image-root /absolute/path/to/clip-dataset-images
.venv/bin/python -m scripts.evaluation.reference_release validate --image-root /absolute/path/to/clip-dataset-images --model-root /absolute/path/to/model
```

Restore the unchanged archive using data/transfer/README.md. A full clone with the
accepted Git objects is required. Archive and Git together contain all data/
images/labels/evidence/tooling; model retrieval/runtime pins remain in the existing
semantic runbook. No global dependencies or Docker install on Mohit's Mac.

The approved measurement window ends2026-12-01T00:00Z. No November5regeneration
is required for these unchanged inputs. Actual source/schema/config/model/data
changes or window expiry can require a newly reviewed version. Recheck the
actual deployed dataset/fingerprint/window before measurement; this local freeze
is not a new live inventory or a perpetual state guarantee.

Reference images/data/vectors remain retained in account335523638354/Mumbai.
Latest recorded stop of shared EC2/RDS:2026-10-31 10:33:47UTC; later metadata
confirmed stopped, and our local check started no cloud compute. Review stopped
RDS by2026-11-06 10:33:47UTC ahead of its possible seven-day restart. No scheduler,
policy change, new upload, reset or cloud cleanup occurred in Step6. Existing
storage/baseline charges remain outside this local step's cost claim.

## Applied checklist and source review

- Correct existing clone/Mohit/macOS/pinned repo-local Python/Node/native PG/model;
  no WSLassumption/global installation. Preserve current images branch/worktree.
- Changes stay in data/evaluation/operators/tests/docs; no product Listings,
  Identity, shared frontend, public contract or migration edits. Public API
  contracts and real source/labels are bound; generated artifacts remain current.
- Query/listing IDs are canonicalUUIDv4, money integer paise, dates UTC, contexts
  fixed page1/page-size20/relevance/Hybrid, exclusions unchanged. All22included;
  errors/empty judgments will not be dropped to improve later scoring.
- Corpus contains synthetic regular records, no seed credentials/sessions/contact
  payloads/provider sends. User photos remain unmodified. No local private SQL,
  tool binaries, credentials, assertions, cookies or signed URLs are published.
- Actual reset/model/SQL/image receipts are distinguished from doubles/native
  rehearsal/failed local browser attempts/human-reported completion. Failed
  attempts and consumed approvals retained; no unauthorized retry/adoption.
- Local workflow guard was corrected during closeout to check approval before
  macOSnative-path setup and to enforce the reviewed time limit before any SDK/
  native work; tests assert no guarded function was called. Standard temp receipt
  location makes this failure-path control portable to LinuxCI.
- Source-byte, archive-member, ledger, label, source-revision and output-overwrite
  checks pass. New release verifier reads only, never extracts archive members,
  encodes vectors, makes AWSrequests or changes the existing database/objects.

## Validation and remaining acceptance gates

Local results:453data/evaluation tests pass,1calibration measurement skipped;
496web tests pass/3explicit live-boundary skips; lint/typecheck/build pass with
existing chunk-size warning. Black355files unchanged; domains0violations;
8generated contract artifacts current; consumer mypy2files pass; CIparity12gates.
Full Docker-based API/database aggregate is not claimed locally. Existing real
native PG18.6/schema/model/media/permission/reset proofs are retained. Final
source secret-scan and byte manifest are in transfer/step-06-freeze-result.json.

PR23/a12f4a3has successful hosted Foundation quality gates (run41193787819),
but this does not cover the new uncommitted update. No submitted GitHub review
exists on that PR. Once the human verifies Step6 and explicitly approves the
concrete commit, publish images and replace PR23 as requested; new-head CI and
independent review remain necessary. Primary peer Suraj, affected Identity/
Listings review as appropriate, using docs/prompts/peer-review-prompt.md.
Author/agent checks cannot approve a PR; exact merge needs separate authorization.
Formal DATA-READY acceptance is recorded separately against this immutable
manifest/hash and accepted merge revision; do not hand-edit frozen metadata to
pretend that pending human/CI/peer gates have passed.
