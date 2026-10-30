# NEXT-06 pre-cloud review and PR package

**State:** implementation and available local verification complete; dependency/
platform checks, independent human review and actual cloud integration remain.
Publication is authorized; independent peer/CI/cloud acceptance remains separate.

Owner: Mohit Mahapatra (C). Primary independent peer: Suraj (B), per the task
index/roster. Identity and Listings owners review their record/permission/media
assumptions. Use [the peer-review prompt](../../../prompts/peer-review-prompt.md);
author/agent findings cannot replace human approval. Review requested from GitHub user `suraj-username` (the existing Listings PR author).
The request is not human approval.

## Published PR

[PR #22](https://github.com/exocrat/clip/pull/22) is open and ready for review on the task branch. The
complete image/payload archive is included. Hosted CI and independent review
remain the merge gate; the user has not authorized merging.


Title: **Prepare reproducible reference dataset and guarded cloud loading adapter**

Base: `main`. Head: `task/next-06-reference-dataset`.
Mohit authorized committing/pushing these changes and opening the PR, including
the complete45photo/two-payload transfer archive. Current file hashes bind the
implementation; Git supplies its publication revision.
Publication and exact merge follow CONTRIBUTING.md and remain distinct from
permission to deploy or load a cloud target.

Suggested description:

> Generates a reproducible 5,000-user/1,000-listing reference corpus with real
> photo bindings and stable November availability. Adds guarded local loading,
> real-model coverage/publication/rebuild checks, 22 human-accepted relevance
> judgments, and an explicit cloud adapter with account/TLS/schema/role guards,
> create-only byte-verified objects and a private recovery ledger.
>
> Local validation: 177 data tests, native PostgreSQL/model/media reset/reload,
> formatting, boundaries, CI parity, consumer types and a checksum-verified native
> pinned Gitleaks scan pass. Full CI is not green locally: npm restoration needs
> authorized registry access; Docker/Linux-specific checks need a suitable runner.
> Actual S3/IAM/Identity/deployed integration and accepted source/label freeze
> remain pending. No cloud changes are included or authorized by this PR.

## Changed code/configuration

| File | Purpose and review focus |
|---|---|
| `data/generators/reference.py` | Deterministic exact distributions, lifecycle windows, photos, stable IDs and input/source validation; no credentials/sends |
| `data/evaluation/reference-recipe.json` | Approved seed42/45topics/counts and December cutoff; 5,000regular benchmark users |
| `data/evaluation/reference-image-inputs.json` |45actual byte/MIME/size/hash bindings and explicit filename alias; original photos external |
| `data/generators/reference_rows.py` | Shared transaction/locked emptiness/catalogue/FK/deferred constraints and exact row/image/index projections |
| `data/generators/reference_load.py` | Preserves fixed local Unix target/role/version guards and real-byte materialization; delegates SQL only |
| `data/generators/reference_cloud.py` | Offline planning or explicit guarded cloud load; account335523638354/non-root, bucket ownership, exact TLS DB/schema/restricted role, empty pipeline/rows; create-only PUT/GET hashes and fsynced uncertain-write ledger |
| `data/evaluation/reference-cloud-target.template.json` | Exact nonsecret operator target fields, null until verified; no invented live bindings |
| `scripts/evaluation/reference_local.py` | Owns isolated native PG/tools/media/app probe; opt-in real vectors and same-owned-target rebuild, process cleanup |
| `scripts/evaluation/reference_embeddings.py` | Supported actual model/operator/worker, complete coverage, bounded real search and automatic publication |
| `scripts/evaluation/reference_rebuild.py` | Compares stable actual vector/source/index fingerprints, excludes random job IDs/audit times |
| `data/tests/test_reference*.py` | Generation, local media/target safety, search failures/budget, reset refusal and cloud contract/bytes/ordering tests |

Documentation includes loading design, command registry, data guide, task status,
step evidence, [operator handoff](cloud-handoff.md), accepted judgments, the full
catalogue and [refreshed local freeze candidate](pre-cloud/freeze-candidate.json).

Keep both current a/b manifests. Historical reference/week/v1 manifests are marked
superseded diagnostics and must never be selected as the benchmark. The authorized tracked transfer archive is the explicit exception for45photo
copies/raw payloads; individual source photos, `.tools`, credentials, local
clusters and npm caches must stay outside the commit. The Git ignore rule deliberately omits `data/runs/*/dataset.json`;
use the included verified archive to restore them; see data/transfer/README.md.

## Review gates and failure semantics

1. Confirm exact account restriction and no deployed activation from imports or
   offline planning; root/wrong-account identities stop before S3/SQL.
2. Confirm unchanged local target guards, actual shared schema operations and
   no trigger/FK/expiry/owner bypass. Cloud config does not prove human approval.
3. Verify target and source bindings, strict TLS/session role, migration set,
   restricted role, empty rows/registry and final locked emptiness check. Reject
   concurrent writes/schema drift; never force a populated-target reset.
4. Inspect every attempted-object ledger entry before any retry/cleanup. A timeout
   may leave an object, and SQL commit may be uncertain; no automatic replay,
   object deletion, shared-bucket cleanup or overwrite is implemented. The CLI
   imposes15minutes; SDK attempts1, connect5s/read30s. Confirm these bounds suit the
   separately approved actual run before authorizing it.
5. Confirm uploaded real bytes precede confirmed SQLmetadata, authoritative
   prefix/uploadUUID mapping, owner attachments and audit confirmation windows.
   Cloud keys differ from local keys; compare logical content and the explicit
   target mapping, not a false identical-key assumption.
6. Preserve all22accepted judgments; no exclusions/relabeling to improve scores.
   Final revision/contract/corpus binding and review metadata are still gated.
7. Real Identity sessions, signed S3 delivery/IAM, deployed model/worker current
   coverage and normal create/edit propagation remain mandatory. Stubber and local
   caller/storage fixtures do not accept them or any cloud NFR.

## Validation and environment handoff

See [machine-readable results](pre-cloud/result.json) and the actual retained
native receipt. Owned services are stopped. Both named input runs still validate
with the unchanged fingerprint and accepted IDs.

The initial web run encountered a missing Signal SDK import (337 tests passed,
1failed and18test files failed loading). Restoring locked dependencies was attempted:
offline npm cache lacks `unique-names-generator@4.7.1`; sandbox registry DNS is
blocked. Escalated calls were interrupted; this is not recorded as Mohit refusing
his standing task approval. Dependency restoration is incomplete, so the receiving
authorized environment must run `npm ci` before current web/contract checks.
No package/lockfile or frontend source change was made to hide this failure.

On a suitable Linux runner with the registered Docker prerequisites and pinned tools:

```sh
uv sync --locked
npm ci
make check
```

The Linux-only private-AWS tests require `memfd`; Docker-backed root integration
tests and the registered scanner cannot pass on this macOS setup without their
prerequisites. A pinned Gitleaks8.30.1 native source snapshot scan was run locally
with the same config/default rules/no inline bypass and redaction; it does not
replace hosted full CI. Do not change shared CI/platform tests just to conceal
environment limitations. Human peer approval and a green applicable CI run remain
required before merge. Do not mark NEXT-06/DATA-READY/final freeze complete yet.
