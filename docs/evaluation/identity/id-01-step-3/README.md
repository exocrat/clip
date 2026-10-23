# ID-01 Step3 — isolated Identity schema checks

Recorded2026-10-23 17:41:45 UTC. Aditya(A), task/id-01-identity based on80abc52;
uncommitted source. Human verified the concrete Step3 plan before implementation;
Aditya verified the result on2026-10-23 17:45:34 UTC and authorized a local
checkpoint commit. No Step4 code or Identity readiness accepted.

## Audit and scope

Compared ID-01 Step3, reviewed Identity contract/typed requests, approved MVP
schema, UUID/UTC/migration/retention decisions and actual four-migration baseline.
The seven existing Identity tables already store user UUID, account class,
lifecycle/activation/expiry, provider tuple, contacts and authentication records.
No duplicate tables/fields/indexes are needed. Demonstrated gaps: storage lacked
contract display-name/contact upper bounds, paired chronological revocation
event and provider-mapping immutability. The verified plan covers those gaps;
no other schema prerequisite blocks this isolated account/profile increment.

The current upstream main defec38 contains PR10 and seven additional migrations,
known head20261022062357. Aditya explicitly deferred merging it until Identity
implementation is ready. New timestamp20261023173439 follows all known versions
and has no local collision; the branch chain remains four foundation migrations
plus this correction. It is not the combined accepted-main chain.

## Code and storage behavior

| File | Purpose and important behavior |
|---|---|
| database/migrations/20261023173439_identity_account_profile_integrity.sql | Adds nullable display-name max80 and nonempty-contact max254 code-point bounds, pairs revoked status with timestamp at/after creation, and adds guard_external_identity_history so mapping ID/owner/provider/issuer/subject/created time cannot change. No-op updates allowed. Validates existing data rather than trimming or inventing event times. Down removes only its own three checks/function/trigger and preserves every row/table/index. Uses existing transaction advisory lock and10-second lock timeout. |
| database/tests/identity-schema-smoke.sql | Rollback-only real SQL checks of Unicode/null/empty/bounds, paired revocation chronology, all six immutable mapping fields, duplicate provider tuple and invalid FK, aware time and original336-hour/activation/enrollment guards. Temporary helper accepts only literal synthetic statements and checks expected SQLSTATE without printing payloads. |
| database/tests/identity-upgrade-seed.sql | Seeds only a guarded disposable clip_test_ database with synthetic regular/temporary/provider/contact rows at the old schema. |
| database/tests/identity-upgrade-check.sql | Checks every seeded identity/profile/provider/contact value and original lifetime across upgrade/down/reapply without printing values. |
| scripts/check_database.py | Existing no-target local Docker gate now tests fifth migration/three smokes, rolls back only the new guards to exercise older-schema fixtures, verifies incompatible-data upgrade atomicity, and verifies successful upgrade/down/reapply preserves data. Network-none tmpfs database, ephemeral local password, no host ports/retained volumes; finally removes only its new container. |
| database/tests/native-checks.sh | Keeps the existing macOS-only route consistent with the new head/five migrations,21 functions/33 triggers and third smoke. Syntax checked; revised native execution is not claimed. |

Exact implementation hashes are in [source-hashes.json](source-hashes.json).
Existing unique provider tuple, user lookup and temporary-expiry indexes are
retained. Published migrations byte-match the preceding commit. No raw provider
token/password/OTP storage or verified-email destination design is introduced.
This is storage integrity, not authentication/security/NFR implementation.

## Actual checks

- uv run --locked python scripts/check_database.py: passed after correcting an
  ambiguous information_schema column reference in the new smoke test. Initial
  run failed at that test; disposable container cleanup still executed.
- Real PostgreSQL18.6/dbmate2.36.0: clean apply/head/repeat; all three SQL smokes;
  unchanged23 domain tables. An81-character pre-existing name causes upgrade
  failure with no migration version, partial constraints or data rewrite.
  Correcting only the synthetic test fixture then permits upgrade; upgrade,
  down and reapply preserve seeded accounts/mapping/contacts/original expiry.
- make check: all11 gates passed. Black79 files;458 Python/63 data/16 web tests;
  Python boundaries,8 current generated contracts, contract-double mypy, web
  lint/types/build,35 simulated DB-wrapper safety cases, new real database
  checks and Gitleaks8.30.1 source snapshot.
- bash -n database/tests/native-checks.sh and targeted Black check: passed.
- Published-migration byte equality, unique timestamp, changed-file private-inbox
  exclusion, local Markdown links and git diff --check: passed.

## Deferred gates and handoff

Real local PostgreSQL is used; no schema or provider stub substitutes for these
checks. No project Compose volume/shared/RDS database was migrated; no AWS calls,
provider send, deployment, commit/push/merge or other domain implementation.
Do not apply the isolated high-version chain to retained/shared data before
integrating current main: strict dbmate will reject later adding earlier
timestamped migrations. Before ID-READY, integrate/reconcile current main, run
the complete combined chain and affected-owner/API/UI/provider checks. Revised
macOS execution is unverified here; historical native results remain historical.

Relevant checklist application: scoped shared-file writer reserved, reviewed
contract and UUID/UTC conventions preserved, no cross-domain private queries,
forward-only published history, synthetic fixtures/no private diagnostics, real
transaction/rollback checks, full local checks, explicit pending gates. Rahul(D)
and affected schema/shared owners review the eventual exact handoff; no human
peer approval or milestone acceptance inferred. Step2 production access remains
pending under approved staged progression. Next human verifies Step3 result,
then reviews Step4 Microsoft validation/claim-security decisions before code.
