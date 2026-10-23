# ID-01 Step4 — private Microsoft validation and account mapping

Recorded2026-10-23 18:22:07 UTC. Aditya(A), task/id-01-identity at382cac9 plus
uncommitted changes. Aditya explicitly directed implementation after reaffirming
Microsoft SSO plus exact signed-email domain eligibility. This isolated increment
is performed and human-verified on2026-10-23 18:29:16 UTC; Aditya authorized
a local checkpoint commit. Original real flow/session gates remain.

## Audit and execution scope

Read the canonical task/Identity operations, provider/domain decision, auth core,
Settings, actual Step3 schema, privacy/retention/provider safety and staging guide.
No gap blocks private signature validation and account storage: schema/contracts
are reviewed and actual tables exist. Public session transport, browser PKCE/
state, server-bound nonce-attempt lifecycle/redemption and production activation
remain explicit design/integration gates; they are not silently invented here.
No generated/public contract, main.py route wiring, frontend or PR10 merge changed.

This implements the selected Microsoft/domain policy, not an extra institutional
OTP, tenant allowlist or claim that signed email proves current mailbox control.
A required signed email must parse to domain exactly iisc.ac.in, case-insensitive
for the domain; reject absence/malformed/subdomain/lookalike/username fallback.
Provider/validated issuer/subject is the account key, never email.

## Code/configuration paths and behavior

| Path | Purpose and relationship |
|---|---|
| apps/api/app/domains/identity/microsoft.py | MicrosoftIdentity holds minimal private verified claims with hidden repr. fetch_document reads only fixed Microsoft discovery/JWKS origins over TLS, refuses redirects/ambient proxies and caps bytes/socket time. MicrosoftKeys coalesces lookups under a lock, validates issuer/key origin/RS256, caches five minutes, throttles refreshes to30 seconds and refuses expired-cache failure. MicrosoftTokenValidator validates RSA signature, issuer/key/tenant binding, scalar client audience, version/required/time claims and a trusted expected nonce before checking signed email; safe401/503, no values logged. |
| apps/api/app/domains/identity/microsoft_accounts.py | RegularAccount is not a session/CallerContext. PostgresMicrosoftAccounts accepts a fresh trusted connection factory, transactionally locks the deterministic provider tuple, reuses active regular records or atomically inserts user/mapping. Revoked/pending/wrong-class/profile-removed records are not reactivated. SQL is parameterized and Identity-only, with3-second lock/5-second statement timeouts. MicrosoftAccountService validates before accessing storage; token/email/nonce are not persisted and no session is created. |
| apps/api/app/core/config.py and .env.example | Add explicit microsoft local/test selector with disabled default and production refusal until real session integration; example stays disabled. Selection installs no routes or successful fake authentication. |
| apps/api/tests/domains/identity/conftest.py and microsoft_fixtures.py | Explicit synthetic fixture creates in-memory RSA keys, real signed test tokens and controlled discovery documents. No private key/token file or network user sign-in; never injected by application startup. |
| apps/api/tests/domains/identity/test_microsoft.py |53 actual-signature/claim/issuer/key/domain/nonce/cache/failure/configuration cases, including consumer/multiple tenants without an allowlist, no username fallback, untrusted jku, malformed data and expired-cache refusal. |
| apps/api/tests/domains/identity/test_microsoft_postgres.py |8 real storage cases with fresh tmpfs PostgreSQL18.6/dbmate2.36.0 and a SCRAM-authenticated socket under a private test directory.16 concurrent callbacks create exactly one user/mapping, stable tuple differs from email, distinct tenants/subjects stay distinct, ineligible mappings deny, invalid tokens never write, and mapping failure rolls back the inserted user. No host port/retained database or ambient DSN; finally removes its own container. Verified Linux ARM64 socket route only; Docker Desktop/macOS execution is unverified and must be reconciled before a platform-wide claim. |
| pyproject.toml and uv.lock | Pin PyJWT2.15.1 crypto and psycopg3.3.6 binary; locked transitive cryptography50.0.2/cffi2.1.1/pycparser3.12. No hand-written cryptography or alternate manifests. |

[Exact source hashes](source-hashes.json). Domain/API README, non-secret example,
provider setup/decision, command registry, root overview and own work-log state
explain selection, privacy, real test effects and pending activation.

## Actual verification

- Initial token suite47 passed, expanded suite53 passed. Initial PostgreSQL
  fixture failed readiness because its custom socket replaced the bootstrap
  socket; no application account operation ran. Kept the bootstrap socket plus
  private test socket, then all8 actual PostgreSQL tests passed.
- Combined token/DB/Settings suite90 passed. Changed-runtime strict mypy passed
  three files. An isolated actual app.main import with production/microsoft
  failed ConfigurationError before serving, confirming entry-point refusal.
- Public Microsoft discovery/JWKS read via the real transport passed: expected
  issuer template/fixed key URL,8 RSA signing keys, all issuer-bound, no duplicate
  kid. This is public metadata evidence only: no user authentication/token flow.
- uv sync --locked and npm ci passed (zero npm audit vulnerabilities). Full
  make check passed all11 gates: Black85 files,519 Python/63 data/16 web tests,
  boundaries,8 current generated artifacts, contract mypy, web lint/types/build,
  35 database safety cases, Step3 actual migration/smoke/upgrade/down checks and
  Gitleaks8.30.1 source snapshot.
- Private controlled inbox absent from all changed files; local links and
  git diff --check passed. main.py and generated Identity public.py byte-match
  the preceding commit. No raw real token, credential or contact in evidence.

## Pending original gates

Do not wire browser-provided expected_nonce into this service: the expected value
must come from a reviewed server-bound attempt. This increment compares it but
does not create, consume or persist such attempts. PKCE/state, nonce redemption/
replay/session replacement policy, cookies/CSRF/lifetime, actual SessionView/
CallerContext establishment, logout/revocation/session behavior and actual
Microsoft/browser/runtime DB-role checks remain before public activation.
Step7/11 wiring must return to the original Step4/12 real checks; no successful
private result or synthetic fixture accepts ID-READY. Notification verified
delivery-target persistence/resolution is not supplied by this account mapping.

No cloud account/permission/hosting action, SES send, app image build/publication,
deployment, retained/shared DB access, new commit/push/merge or PR10 integration.
Step2 production gate remains pending. Actual database test resources were
removed by fixture cleanup; no server listener/host port or app session left.
Applicable checklist items: approved exact-domain decision, scoped dependency/
shared Settings writer, no public/fake bypass, real cryptography/SQL transactions,
privacy/error behavior and explicit staged integration evidence. Independent
Rahul(D)/affected-owner review and task-wide acceptance remain later gates.

## Primary implementation references

- https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
- https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- https://pyjwt.readthedocs.io/en/stable/usage.html
- https://www.psycopg.org/psycopg3/docs/basic/transactions.html
