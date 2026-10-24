# ID-01 Step8 — capability policy and scoped public eligibility

Recorded2026-10-24 06:15:10 UTC. Aditya(A), task/id-01-identity at3da24db plus
uncommitted Step8. Aditya verified the capability matrix and generated runtime
binding before implementation. Aditya verified the local result and authorized
its checkpoint commit on2026-10-24 06:23:29 UTC. Full consumer FR-03 matrix/ID-READY remain incomplete.

## Audit and dependency state

Reviewed canonical Step8, FR-02/03 and wanted-response clarification, Identity/
combined/types contracts, source/generator/public declarations, boundaries,
actual Step7 session/HTTP/SQL and staging/contribution/checklist records. No
missing capability decision: both classes retain their approved activities;
temporary users cannot manage sale listings or initiate wanted responses.
Ownership/membership/consent/resource checks remain with owning domains.

Found the generated eligibility declaration still refused. The verified plan
approved a thin scoped technical dispatcher without business logic/private
imports in public.py. Preserve source refusal/signature, generated status for
other functions and the existing HTTP/schema/type/version surface. Actual
account/SQL/session implementations exist; synthetic signed Microsoft assertions
and mail provide controlled auth only, not real provider evidence. Other
marketplace routes on the deliberately isolated branch are not claimed or
mocked into production; full consumer integration stays Step14.

## Changed code/configuration paths

| Path | Purpose and important behavior |
|---|---|
| apps/api/app/domains/identity/capabilities.py | Code-owned Capability enum and explicit shared/regular-only allowlists; future unmapped categories deny. Both classes may browse/search/save, manage own wanted/profile/contacts, start listing conversations, use existing authorized conversations, submit offers/share selected own contacts. Only regular may manage sale listings/start wanted responses. PostgresCapabilities reads fresh lifecycle/class/profile fields under bounded own-domain SQL, checks caller expiry/class and rejects pending/expired/revoked/removed/future/missing/stale contexts. Caller construction is not authentication. Async boolean eligibility uses exact optional class, no session-online requirement, only eligible result and safe422/503; blocking reads run outside event loop. No resource ownership/membership is inferred. |
| apps/api/app/core/runtime_bindings.py | Trusted immutable callback snapshots in ContextVar scopes; no process-global mutable provider, environment selection or automatic import binding. Nested scopes replace/reset and concurrent tasks retain their own callbacks. Dispatch strictly validates reviewed model data, including revalidation of model_construct instances without private warnings; missing/wrong/dependency returns safe503, explicit reviewed PublicErrors preserved. No domain imports, policy or DB discovery. |
| apps/api/app/domains/identity/sessions.py | Construct the real capability provider from the existing trusted connection/clock, without startup I/O or new secrets/schema. Existing authentication/session behavior retained. |
| apps/api/app/domains/identity/http.py | Bind the real eligibility provider per request scope and restore it on exit. GET /me applies fresh READ_OWN_PROFILE enforcement after actual session authentication. No new HTTP lookup or marketplace endpoint; normal unconfigured main remains health-only. |
| contracts/source/identity.py | Explicit RUNTIME_BINDINGS selects only check_account_eligibility and imports its technical dispatcher alias. Source async callable still refuses; reviewed signature and boolean result stay unchanged. No provider import or discovery in source. |
| scripts/generate_contracts.py | Validate frozen binding metadata, selected refusing async function/supported signature/technical import and BaseModel return. Generate only that refusal-body replacement as typed dispatch with strict result validation. Reject unsupported metadata/signatures rather than invent wrappers. Format2 and all other outputs unchanged. |
| apps/api/app/domains/identity/public.py | Regenerated typed runtime wrapper for eligibility, preserving all arguments/default/return type and forwarding to the scoped core dispatcher. No SQL, business rule, private provider import or fake fallback. Other Identity/contact declarations still refuse; file was not hand-edited. |
| apps/api/tests/core/test_runtime_bindings.py |12 technical scope/failure cases: unbound503, immutable/nested restoration, overlapping task isolation, strict malformed/extra/coercible result rejection, safe failures, cancellation restoration, async/name validation and preconstructed-model bypass rejection. Generic test models are not domain provider evidence. |
| apps/api/tests/domains/identity/test_capabilities_postgres.py |40 actual SQL/RSA/OTP/session cases, including independent26-case regular/temporary matrix, lifecycle/caller mismatch, exact class/boolean shape, offline account versus authentication, unavailable/unbound503, fresh reads, invalid arguments and parallel real providers with distinct clocks. Temporary wanted-author/existing conversation policy retained. No consumer record authorization is simulated. |
| apps/api/tests/domains/identity/test_capabilities_http.py |3 actual session-backed HTTP cases: deny forged temporary sale/wanted-response claims, retain existing-thread policy, authorize regular class, ignore browser target IDs, call generated public provider within request scope, apply actual GET /me fresh policy and keep lookup endpoint absent. Extra policy routes are fixture-only; no Listing/Search/Conversation implementation is claimed. |
| tests/contracts/test_runtime_binding_generation.py |8 deterministic generator constraint cases: only selected refusal becomes exact typed dispatch; unchanged unselected source; reject mutable/unknown metadata, implementation bodies, missing import, unsupported args/returns. No provider or application import. |
| tests/contracts/test_domain_declarations.py | Preserve all reviewed names/signatures; assert exactly one typed adapter AST and original refusal bodies elsewhere. Normalize only that one body to prove no other source-derived AST change; other domain modules remain byte-for-byte source derivatives. |
| tests/contracts/test_identity_declarations.py | Recognize reviewed typed-runtime Identity header while other domains stay declaration-only. Canonical source declaration-only invariants remain enforced. |

Core/API/Identity README, canonical generation/contract/convention docs, command
registry and [approved decision](../../../decisions/identity-capabilities-and-runtime-binding.md)
explain the narrow extension. [Source hashes](source-hashes.json) pin13 code/test
files. No other domain public output, OpenAPI, TypeScript, shared model, default
main, dependency manifest/lock or database migration changed in this increment.

## Actual checks, corrections and limitations

- Actual policy/public/HTTP suite passed43 cases. Dispatcher suite initially had
 a test-only barrier deadlock: both tasks waited before either callback ran.
 Interrupted only the two owned matching pytest processes (2 cases each had run;
 neither interrupted run is a pass), replaced barrier with overlapping dispatch
 lookups, then all12 dispatcher cases passed. No production behavior was relaxed.
- Added strict revalidation against preconstructed Pydantic model bypass and
 explicit fail-closed allowlists for future categories. Combined dispatcher/
 policy suite passed55 cases; generator/declaration suite passed36 cases.
- Strict runtime/generated-public Mypy passed five files. Final full make check
 passed all11 gates:709 Python,63 data and16 web tests; Black112 files, CI parity,
 boundaries, eight current generated artifacts, contract types, web lint/types/
 build,35 wrapper safety cases, actual PostgreSQL18.6/dbmate2.36.0 migration/five
 SQL smoke/legacy-up/down checks and Gitleaks8.30.1 source snapshot.
- 208 changed/new local Markdown file targets and git diff --check passed before
 final evidence/status updates. Source/header/AST checks prove dispatch remains
 technical and unimplemented functions never fabricate success. No raw real
 identity/token/password/contact evidence or provider request was introduced.
 Actual storage route is Linux ARM64; no new native macOS/AMD64 claim.

Final evidence-inclusive Gitleaks scan passed;13 source hashes matched and211
changed/new local Markdown file targets resolved.

## Remaining gates / next checkpoint

Aditya verified the local result and authorized its checkpoint commit. Step9
still requires plan verification; no push/merge or enabled runtime/cloud job. Public
eligibility now has a usable explicitly scoped real implementation; workers
must install trusted scopes rather than import/discover a provider automatically.
Cross-domain callers must authenticate actors and derive target IDs from trusted
context/authoritative relationships. Bool eligibility does not authenticate a
session or authorize record ownership/participant consent.

The deployed app/runtime key/DB/TLS/proxy configuration, real provider/browser,
current-main migration reconciliation and independent peer acceptance remain
original ID-READY gates. Other contact declarations remain for Step9. Actual
marketplace endpoints/consumer matrix remain Step14 and cannot be replaced by
these helper/probe checks. No complete FR-03/NFR/readiness closeout claimed.
Relevant checklist privacy/ownership/fresh UTC lifecycle/real storage/scoped
failure/concurrency/local checks applied; task-wide integration/peer/browser
review remains open. No cloud/send/retained/shared database action occurred.
