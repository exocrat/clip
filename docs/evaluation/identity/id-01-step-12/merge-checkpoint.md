# ID-01 Step12 — local main reconciliation

Prepared2026-10-24 16:31:04 UTC. Contributor Aditya(A), branch task/id-01-identity.
Checkpoint source7a9b4a4; merging exact accepted main
`defec38f59d4acb683f7b51950860f458aacfdd1` with no merge commit. Aditya explicitly
authorized the checkpoint commit and local merge. Remote main matched the target
before action; PR10 acceptance was previously verified. No push/main PR merge,
cloud action, deployed change or readiness acceptance is implied.

## Scope and audit

No new material task-definition gap. Preserve the accepted Listings work and
Identity's reviewed implementations; fix shared composition/contract/migration
conflicts only. A is the current writer for the bounded shared reconciliation
specified in integration-plan.md. Suraj's private production backend/frontend/
Terraform and main application composition remain identical to accepted main.
The separately approved exception is a test-only clock fixture described below.
Affected-owner and independent peer review remain required.

The13predicted textual conflicts are resolved. Existing author histories and
Listings status rows are retained; current Identity row is maintained separately.
No original migration SQL was edited: all7Identity-parent and11main-parent files
match their parent bytes, with14distinct files in the combined chain.

## Changed code/configuration and important behavior

| Path | Resolution/result |
| --- | --- |
| apps/api/app/core/config.py | Combines Identity Microsoft/SES settings and verify sender with accepted Listings DB/S3/isolated-demo settings. Keeps both domains' production/fake/recipient/target guards. |
| apps/web/vite.config.ts | Normal mode preserves Listings `/api` rewrite to loopback8000; Identity synthetic mode retains only its explicit loopback8001 proxies and refuses build/deployment. It does not proxy SPA auth callback or enable real Identity. |
| pyproject.toml; uv.lock | Adds accepted psycopg-pool3.3.3 to Identity's manifest/lock; existing locked versions remain unchanged, including boto3 1.43.116. No downgrade to main's older boto3. |
| scripts/check_database.py | Unified optional Listings adapter mode and protected retirement/full rollback with Identity's guard/OTP/session upgrades, failure atomicity and data preservation. All operations target an owned disposable container only; no input DSN/shared data. Verifies14migrations/33tables/25functions/37triggers, five smokes and exact migration history. |
| database/tests/native-checks.sh | Combined head/inventory,14rollbacks, five smokes and reapply; Bash syntax checked. Actual macOS/native execution is not newly established. |
| tests/contracts/test_generation.py | Retains accepted Listings live-route schema comparisons and Identity's added nonce/CSRF declarations/53operation count. Removes obsolete health-only route-count assertion. |
| apps/api/tests/domains/identity/test_ui_preview.py | Inspects actual OpenAPI paths instead of assuming every FastAPI router wrapper has a path. Requires accepted health/Listings routes and absence of synthetic mailbox/unbound auth routes. |
| apps/web/tests/identity.test.tsx | Retains Identity preview isolation/build rejection while explicitly preserving normal Listings proxy; verifies synthetic mode cannot expose the normal API proxy. |
| apps/api/tests/domains/listings/test_image_upload_service.py | Human-approved module-scoped auth-clock fixture aligns existing caller expiry checks with its fixed synthetic service time. Restored after each case; no production clock or expiry comparison changed. |

Accepted canonical source changes retain optional pickup area, existing/new image
selection and retirement marker outcomes alongside Identity's nonce/CSRF/contact
context/runtime dispatch declarations. Generated artifacts are regenerated from
canonical sources, not hand-edited. Changes relative to Identity parent include
contracts/generated/openapi.json, contracts/generated/types.gen.ts and
apps/api/app/contracts/domain_types.py; incoming Conversations public declaration
is retained as generated. All8registered artifacts must pass freshness checking.
Shared ScaffoldPages retains both accepted Listings public components and Identity
callback/contact/sign-in components. No consumer private implementation import.
The incoming Listings main/lifespan/router/storage and isolated fixed caller are
preserved; actual Identity runtime remains unbound pending its next checkpoint.

Documentation resolutions combine API/web commands, catalogue/schema/migrations,
front-end ownership map, canonical contracts and author evidence. README explains
local reconciliation underway rather than claiming deferred integration complete.
The command registry preserves both supported database modes. Independent review
must include the complete merged diff, not only the13text conflicts.

## Checks and retained failures

Initial full check failed13cases: one obsolete Identity route enumeration and
12Listings image cases whose Oct22fixture session expiry was compared to actual
calendar time. The fixture expired Oct23. Failure log:
`/tmp/clip-id12-merge-check.log` (954passed/13failed/1skip). No product auth expiry
was weakened. Aditya explicitly approved the bounded Listings test-clock change;
focused rerun of image/Identity preview cases25passed. Separate contract/config
check102passed; complete web gate118tests/lint/types/build passed. Actual disposable
merged migration check and optional Listings workflow passed; the latter executes
the DB-only root-suite test separately rather than claiming a skip is a pass.

An initial attempt to select several check.py checks with --only was rejected by
argparse; corrected to its registered positional commands. Independently data63,
boundaries0violations, contract types,35wrapper safety and source Gitleaks passed.
No check was disabled. The final aggregate result is recorded below. Local logs use `/tmp/clip-id12-merge-*.log`; no private provider data.

## Remaining boundary

Human verification and separate explicit merge-commit authorization follow the
resolved diff/full gate. No remote push or main merge authorized. Runtime secret/
role/proxy/TLS/auth composition, provider live configuration, SES verify-sender
policy apply, key rotation and actual device/peer/CI readiness remain pending.
Step14 consumer matrix stays outside ID-READY. No local merge acceptance is a
claim that the website now supports real sign-in or that ID-READY is accepted.

The combined native inventory check initially assumed24functions/36triggers from
older parent harness counts; actual SQL measured25/37. The later accepted image
upload migration adds a function/trigger omitted from the older native inventory.
Corrected both harness expectations from measured SQL, without altering any
migration. Diagnostic failure log: `/tmp/clip-id12-merge-inventory.log`. Also fixed
one inherited relative-link depth in infra/terraform/domains/listings/test/README.md;
no private Listings runtime code changed. Final gate rerun follows this correction.

## Final result — 2026-10-24 16:39:37 UTC

`make check` exited0 with all11ordered gates passing on the final resolved source:
967Python passed/1DB-only skip,63data passed,118web passed, Black142files,
0boundary violations,8generated artifacts current/format2, contract mypy, web
lint/types/build,35wrapper safety, actual PostgreSQL18.6 combined migration/
upgrade/rollback/inventory/reapply and Gitleaks8.30.1. The skipped root Listings
PostgreSQL test passed separately through --listings-store (one actual DB workflow).
Final raw log: `/tmp/clip-id12-merge-verified-check.log`. Earlier failed full runs
and inventory diagnosis remain at their original local log paths above.

Locked setup `uv sync --locked`/`npm ci` completed. Lock audit proves only
psycopg-pool3.3.3 added; existing versions unchanged. Bash syntax passed for the
native harness; no actual macOS/device or cloud claim. All published migration
bytes match their two parents. No private Listings production code changed; only
the explicitly approved test fixture and one relative documentation link differ
from incoming main under its private paths. Actual main application source is
identical to incoming main. [32source hashes](merge-source-hashes.json) capture
resolved source/config/generated/migration files. Local Markdown targets and
whitespace checks passed.

All13Git conflicts are marked resolved. HEAD remains checkpoint7a9b4a4 and
MERGE_HEAD remains defec38f; staged merge is intentionally uncommitted. Aditya
verification and explicit merge-commit authorization are pending. No push, remote
main merge, live provider/cloud/shared-DB operation or ID-READY closeout.

At2026-10-24 16:41:58 UTC Aditya verified the result, explicitly authorized
its local merge commit, and requested stopping afterward. Runtime wiring and
all remaining acceptance gates stay pending; no push/deployment authorized.
