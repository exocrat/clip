# ID-01 Step6 — private temporary activation and current eligibility

Recorded2026-10-23 20:07:32 UTC. Aditya(A), task/id-01-identity atf9d33eb plus
uncommitted Step6. Aditya verified the Step6 plan and directed implementation.
Private increment performed/checked; Aditya verified the result and authorized
its local checkpoint commit on2026-10-23 20:16:11 UTC.

## Audit and dependency state

Reviewed canonical ID-01 Step6, Identity activation input/lifetime/retention
contracts, actual schema/integrity guards, Step5 consume transaction and approved
password parameters. Existing real schema/OTP boundary are ready; no migration
or improvised account contract is needed. No new task-definition gap blocks this
private increment. The reviewed public activation operation returns SessionView;
its session/cookie/CSRF/lifetime design and issuance belong to Step7 integration,
so no fake session or public success endpoint is introduced here.

Staging guide permits isolated Steps1–11. Actual Argon2id and PostgreSQL are used;
synthetic email capture only supplies controlled OTPs. Original Step4/5 provider,
nonce/public/session/runtime and current-main integration gates remain pending.
This does not accept ID-READY or the full consumer capability matrix.

## Code/configuration changes

| Path | Purpose, behavior and relationship |
|---|---|
| apps/api/app/domains/identity/temporary_passwords.py | TemporaryPasswords accepts SecretStr inputs of15–128 Unicode characters including spaces, without trimming/normalization. Reject invalid surrogate encoding safely. Explicit Argon2id19MiB/t2/p1,16-byte independent random salt and32-byte hash; safe422 validation and503 hashing failures. Hash only, no password login/reset implementation or raw-password persistence/logging. |
| apps/api/app/domains/identity/temporary_accounts.py | TemporaryActivation composes Step5 consume: validate password policy, verify initial-purpose OTP, then hash and atomically insert active user/protected credential/enrollment guard, binding consumed OTP to its new account. Activation is proof time, expiry exactly336 hours later. Every mutation/consumption rolls back on failure; no session/CallerContext issued. TemporaryAccount is minimal private result only. PostgresTemporaryAccounts.require_current uses fresh trusted DB/time and bounded SQL waits to check current class/status/profile/lifetime plus already-trusted caller expiry; cached caller validity cannot extend expiry or hide revocation. It does not authenticate a caller or authorize a marketplace capability. |
| pyproject.toml, uv.lock | Pin argon2-cffi25.1.0 and lock native bindings26.1.0; reuse existing cffi. No previously locked package version changed. Library parameter/random-salt API checked against official documentation; real Linux ARM64 hashing passed. Other-platform/runtime image execution is not claimed. |
| apps/api/tests/domains/identity/test_temporary_passwords.py |12 real hash/policy cases:15/128 character boundaries, unchanged whitespace/Unicode, encoded parameters, independent salts, malformed/oversized/short/unwrapped inputs and safe failures. All passwords are synthetic. |
| apps/api/tests/domains/identity/test_temporary_activation_postgres.py |22 actual PostgreSQL cases using the existing private socket/SCRAM/tmpfs fixture and real Step5 service. First-success activation time, stable protected login, immutable lifetime/no reenrollment,16 concurrent callbacks yielding one account/credential/guard, rejected OTP/password, hash/credential/enrollment rollback and reusable unconsumed OTP after rollback, no hashing before proof, fresh-state failures, exact expiry and credential cleanup guard preservation. Synthetic callbacks/fixtures do not bypass production wiring. |

Root/API/Identity docs, temporary-auth decision and command registry explain the
actual behavior, reproducible checks and pending composition. Work-log status
and pending ledger retain original real gates. [Source hashes](source-hashes.json)
pin both runtime/test files and dependency manifest/lock.

## Actual checks

- Initial focused32 cases passed; added consumed challenge/account binding and
  proof-before-hashing/database-failure checks. Combined Step6/Step5 focused suite
  passed52 cases (12 password,22 activation,18 existing OTP DB).
- Changed-runtime strict mypy passed two files; uv sync --locked,
  uv lock --check --offline and uv pip check passed. Existing lock versions were
  compared programmatically: only Argon2 library/bindings added.
- Full make check passed all11 gates:597 Python,63 data and16 web tests;
  Black98 files, CI parity, boundaries, eight current generated contracts,
  contract types, web lint/types/build,35 wrapper safety cases, real
  PostgreSQL18.6/dbmate2.36.0 migration/four-smoke/upgrade/down checks and
  Gitleaks8.30.1 source snapshot. No skipped/failed required local gate.
- Changed-document153 local file targets and git diff --check passed before
  final evidence/status additions. Main/core auth/generated Identity declarations,
  contract sources, schema and migrations are unchanged in this increment.

The final evidence-inclusive scan initially flagged two source SHA-256 values
beside filenames containing password (generic-api-key). Verified each against
its source and separated manifest path/digest fields; no secret or scanner
allowlist change. The evidence-inclusive scan passed after that correction.

## Pending integration, verification and next step

Aditya verified the private result; original real integration remains pending.
Step7 still needs a reviewed
session/password-login/reset/revocation/cleanup design and implementation.
Bind the fresh eligibility gate to real trusted session/protected-operation
composition; verify actual expired/revoked marketplace denial and public
activation SessionView. Step11/12 must verify browser/API/real provider/runtime
configuration and current-main migrations; cloud sends/actions remain separately
authorized. Helpers/private service tests do not claim endpoint or full FR-03
acceptance. Existing Step5 OTP/public/send and Step4 Microsoft/nonce obligations
are not removed. No live send, shared/retained DB, new migration, cleanup worker,
cloud deployment/push/merge or Step6 commit occurred.

Relevant checklist review: owned boundaries, safe errors/privacy, actual
crypto/storage, UTC-controlled lifetime, concurrency/rollback and local quality
gates passed. Task-wide browser/provider/peer/integration review remains open.

Library reference: [argon2-cffi API](https://argon2-cffi.readthedocs.io/en/stable/api.html).
