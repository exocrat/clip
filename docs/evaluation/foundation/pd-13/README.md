# PD-13 local setup evidence

Captured on 2026-10-18 UTC for PD-13 Step 6. The run logs and command/status manifests below preserve the executed output. The database command manifest redacts its private local `PGPASSWORD` value; no password is present in the saved output logs.
Raw `.log` and `.patch` files preserve their original trailing whitespace; Git whitespace checks are disabled for those evidence files only.

## Run provenance

- Environment: Linux `aarch64`, Bash 5.2.37, Python 3.14.3, uv 0.10.7, Node 24.22.0, npm 11.19.1. Version outputs are in `clean-clone/`.
- Clean setup started from revision `145ba97147794c9ef471caa46977d8e0c94c76b8`, with no project virtual environment or `node_modules` present. `clean-clone/commands.json` records the ordered commands and exit/HTTP/shutdown statuses; the neighboring `.log` files hold their output.
- The passing fresh-clone run used the exact six-file overlay listed in `clean-clone/tracked-changes.log`; its patch is `clean-clone/source-overlay.patch` (SHA-256 `ae8399fb987e54cb63d487571d14bb75983aad42ab55b0ce8aa58c77d07fcddf`). The final Step 4–5 commit is `3a652bd0f390a7467368dda2acd6835c5958615e`. The overlay did not include `database/README.md`, `database/tests/local-db-safety.sh`, `docs/environment/commands.md`, or `docs/status/work-log.md`; the changed safety test was checked separately on revision `3a652bd` and its output/status are in `source-safety.log` and `source-safety.json`.
- `initial-failure/` preserves the first clean-clone aggregate failure. Its output showed dbmate could not read the bind-mounted migration directory under the clone's private file permissions. The fix runs dbmate as the contributor UID/GID while retaining read-only mounts and dropped capabilities; the later clean-clone aggregate passed.
- `persistent-db/` records two start/seed/status/stop cycles against the existing local Compose project and retained volume. This lifecycle used the original clone because the project is clone-owned; it was separate from the fresh-clone empty-database check.

## Results

- Fresh `make setup`, hook installation/configuration, and all-files hook run passed. API and web each started twice and returned HTTP 200; preview returned HTTP 200 twice; each process stopped and released its port.
- Two deterministic preview datasets (seed 42, 3 users, 2 listings) validated to the same SHA-256. `make data-load` returned the expected exit 2 because DL-00 contracts, accepted ID-READY/LI-CORE schemas, and SE-01 adapters/loader validation are not available yet.
- Formatting, two contract generations, and contract freshness checks passed. The full `make check` returned 0: 387 API/core tests, 63 data tests, 16 web tests, boundary and contract checks, 35 simulated database-safety cases, PostgreSQL 18.6 migration/repeat/smoke checks, Gitleaks 8.30.1, and Black's 59-file check.
- The retained database stayed at migration head `20261018152702` (4 migrations), with 8 categories and 4 conditions after both seed cycles. The named volume remains present and the container was stopped.
- The separately captured committed-tree safety check returned 0 with 35 simulated wrapper-safety cases. The mock does not contact Docker Engine, a database, registry, or provider.

## Current handoff status

**Platform status update — 2026-10-20 (Asia/Kolkata):** The user confirmed that the previously deferred Linux AMD64 and macOS checks passed on other machine(s). The exact machine architecture, commands, and raw outputs are not retained in this repository, so this is user-confirmed status rather than an independently reproducible run record. Final domain dataset loading/validation remains assigned to DATA-READY; this does not imply domain readiness or NFR acceptance.
