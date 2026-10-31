# NEXT-06 current PR update — actual cloud dataset evidence

This update supersedes the pre-cloud publication summary for the uncommitted
increment. Mohit explicitly requested local branch `images` and authorized committing the
prepared update. PR22 still points to the old remote branch until a separately
approved publication action resolves the renamed head. Push and merge are not
authorized by this local rename/commit.

## Proposed PR title and description

**Load and verify the reference dataset, images and serving search vectors**

Generate reproducible5,000-user/1,000-listing data with real images. Add guarded
account-specific operator tooling and retain actual S3/RDS load, serving vector
publication and read-only cloud/native rebuild comparison receipts. The live
reference data and1,000images remain retained; owned compute/access is stopped.

Current local checks:281data tests passed; Black50data/evaluation files unchanged;
Python domain boundaries0; previous actual native schema/permissions/SCRAM/model/
media/reset/reload checks and actual cloud receipts retained. Final secret scan
and file manifest accompany this package. Full current-head CI is pending publication;
Docker/Linux aggregate checks are not claimed locally. No global installs.

DATA-READY remains incomplete. Owner-managed real auth/media/create-edit/new-vector
and deployedLinuxruntime checks, accepted source/readiness/final label metadata,
independent human review and final freeze remain gates. No deployment, additional
cloud action or merge is authorized by publishing these receipts.

## New or changed executable code

| File | Behavior and relationship |
|---|---|
| data/generators/reference_login.py | Bridges the explicit AWS browser-login profile to SDK credentials in memory; bounded CLI export, safe failure diagnostics, no secret output. Actual account/role checks remain with callers. |
| data/generators/reference_cloud.py | Uses that login bridge and verifies AES256 on downloaded image objects as well as exact bytes/type/hash. |
| scripts/evaluation/reference_db_inventory.py | Fixed-resource bounded inventory, private connection/source/session checks and aggregate evidence; no arbitrary database target. |
| scripts/evaluation/reference_admin_inventory.py | Read-only private administrative schema/role inventory without widening application permissions. |
| scripts/evaluation/reference_database_setup.py | Create-only isolated29migration target and inactive restricted roles; refuses existing target/adoption. |
| scripts/evaluation/reference_load_access.py | Fixed-target admin guards, ephemeral loader activation/revocation, owned listener validation, storage safety and bounded load outcomes. |
| scripts/evaluation/reference_setup_local.py | Fresh Unix-only native database/permission/SCRAM rehearsal with optional real vector checks and owned shutdown. |
| scripts/evaluation/reference_vector_access.py | Dedicated fresh producer with narrow grants/column-only lock rights and OID-bound password clearing; app/loader remain inactive. |
| scripts/evaluation/reference_vector_pipeline.py | Runs real pinned supported embedding operator/worker and production query diagnostics; preserves source projection and bounded outcome evidence. |
| scripts/evaluation/reference_vector_local.py | Native permission/negative mutation checks around the real producer/model pipeline. |
| scripts/evaluation/reference_freeze_snapshot.py | SELECT-only stable vector/index fingerprint; excludes random generation/audit fields and returns no raw coordinates or source text. |
| scripts/evaluation/reference_local.py | Checks that reader against actual native reset/reload snapshots. |
| data/tests/test_reference*.py additions | Failure/privilege/authentication/storage/budget/cleanup controls for the new helpers; native/cloud receipts provide real integration evidence beyond doubles. |

Proposed/executed controllers under transfer are exact scoped operator artifacts,
not general runtime CLIs. Executed create/load/vector windows are consumed and
must not be replayed against the populated target. Tool binaries, credentials,
local clusters and caches remain outside publication. Hash references bind local
tools; the existing approved photo/payload transfer archive remains unchanged.

## Independent review

Primary peer Suraj(B), with Identity/Listings affected-owner review. Use
[the peer-review prompt](../../../prompts/peer-review-prompt.md). Review target,
source/schema guards, ephemeral privilege lifecycle, no-retry/partial-failure
receipts, cleanup, preservation of judgments and explicit pending integration.
AI preparation is not human peer approval. Exact commit/push and later exact
reviewed merge remain separately approved under CONTRIBUTING.md.

[Verified candidate](transfer/dataset-evidence-candidate.json) and
[remaining gates](transfer/remaining-integration-gates.md) are the current handoff.
