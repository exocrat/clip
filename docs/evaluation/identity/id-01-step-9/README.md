# ID-01 Step9 — own profile, contacts, scoped sharing and retention

Recorded2026-10-24 07:08:51 UTC. Aditya(A), branch task/id-01-identity, parent c34db1d plus uncommitted Step9.
Plan verified before execution. Aditya verified the local result and authorized
its checkpoint commit on2026-10-24 07:23:42 UTC (recording time). No push, merge,
provider send, live cleanup or deployed scheduler is authorized here.

## Definition audit and dependencies

Canonical Step9 omitted explicit profile updates while the reviewed HTTP contract
already required PATCH /me/profile. Aditya verified the precise task-list correction
and its inclusion; no remaining material definition gap was found. Read Identity/
combined/source contracts, retention/private-contact/caller decisions, actual
sessions/HTTP/cleanup/schema, stub allowance, contribution/checklist/environment
and task/status records. Existing own Identity schema suffices; no migration.

Actual local PostgreSQL, activation/session and HTTP are used. Signed Microsoft
assertions, email capture and the server sharing grant are controlled synthetic
fixtures, not real provider delivery or actual Conversation participation/consent.
No reverse domain import or Conversation private-table access was introduced.
CN-02 owns actual membership/confirmation/client encryption checks; the final
consumer matrix remains Step14 outside ID-READY. Runtime/provider/browser/main
reconciliation and independent peer acceptance remain original readiness gates.

## Changed code and configuration

| File | Purpose and important behavior |
|---|---|
| apps/api/app/domains/identity/contacts.py | PostgresContacts locks the current user before source fields, freshly rechecks lifecycle/caller/capability, and trims/validates own display name/email/phone/UPI. Omission preserves name; null clears. Field-only idempotent upserts preserve other contacts and separate login; deletion immediately removes future retrieval. Async internal sharing reads off the event loop, requires a typed matching server actor/conversation scope, and requires confirmed fields for selected disclosure. Options are flags only; unselected fields null; missing requested values safe422. Dependency errors are safe503 without values. |
| apps/api/app/domains/identity/sessions.py | Constructs the real contact provider with the same explicit trusted connection and clock; no startup discovery or I/O. |
| apps/api/app/domains/identity/http.py | Implements reviewed own profile/contact routes with existing session/origin/CSRF/no-store controls. Uses generated runtime models for nominal consistency with services. Binds both real contact ports per request and clears ambient sharing claims; trusted Conversations composition must install an inner scope after its checks. No public sharing/directory route. Normal main remains health-only. |
| apps/api/app/domains/identity/cleanup.py | Adds bounded user candidates and user-lock/cutoff rechecks for contact deletion and display-name clearing/profile_removed_at marking at thirty days after earliest revocation/temporary expiry. Dry-run counts by default; apply only explicit owned target. Preserves users, enrollment/request/key records. No scheduler or retention deadline acceptance. |
| apps/api/app/core/runtime_bindings.py | Adds immutable snapshot runtime_claims scope and current claim lookup with explicit names, nested restoration and parallel isolation. Technical storage authenticates nothing; domain owns immutable record/preconditions. |
| contracts/source/types.py | Frozen internal ContactSharingContext validates UUIDv4 actor/conversation and optional nonempty supported frozen confirmed set; hides repr identifiers. It is no HTTP authorization model. |
| contracts/source/identity.py | Exports the context and selects the two contact ports alongside eligibility for existing typed dispatch generation. Canonical callable bodies remain refusing declarations; recipient resolution stays unimplemented. |
| apps/api/app/contracts/domain_types.py | Mechanically regenerated shared Python context/type output from canonical source. |
| apps/api/app/domains/identity/public.py | Regenerated typed contact wrappers forward exact reviewed signatures/results through scoped dispatch. No SQL/policy/private provider import or fake fallback. |
| pyproject.toml; uv.lock | Pin email-validator2.3.0 and its transitive dnspython2.9.0. Existing locked versions unchanged. Syntax-only use explicitly disables DNS/deliverability and preserves trimmed contact spelling; no mailbox/bank/payment verification. |
| apps/api/tests/domains/identity/test_contacts.py | Synthetic validation, actual own SQL/profile CRUD, separate login preservation, current lifecycle denial, selected subset/removal/redaction, missing/mismatched grants, frozen/non-wire context, parallel scope/update/delete-disclosure and unavailable dependencies. |
| apps/api/tests/domains/identity/test_contacts_http.py | Real session-backed regular/temporary HTTP CRUD, forged owner rejection, CSRF, malformed wire Unicode, safe errors, session privacy, expiry, absent directory and ambient-claim rejection. Fixture preparation proves Identity composition only, not actual CN authority. |
| apps/api/tests/domains/identity/test_identity_cleanup.py | Extends real retention tests for just-before/exact thirty-day temporary expiry or earlier revocation and regular revocation, dry-run/apply/repeat safety and marker preservation. Existing ten tests retained. |
| tests/contracts/test_domain_declarations.py | Structural assertions allow exactly the three reviewed typed adapters and normalize only their bodies when checking generated/source parity; all other refusals preserved. |

Canonical task, Identity/combined contracts, decisions, domain/core/API/root README,
document index and command registry describe this behavior and remaining gates.
OpenAPI, TypeScript, other domain outputs and database migrations are unchanged.
[Source hashes](source-hashes.json) pin all changed code/configuration/test files.

## Checks and corrections

- Initial runtime Black/strict Mypy passed. Existing generator/declaration/cleanup/
HTTP regression selection passed49 tests.
- Initial new-contact run had3 fixture/test expectation failures (incorrect login
column, malformed Unicode rejected by model before service). Corrected to actual
separate login schema/model boundary. HTTP run then had2 client-side surrogate
encoding failures; send escaped raw JSON to actually test server validation.
These failed runs are not counted as passes; no production safeguard was relaxed.
- Corrected focused own-contact/HTTP/cleanup suite passed53 tests with warnings
as errors. Strict Mypy passed all6 runtime files. Offline lock consistency and
installed dependency compatibility passed; only the two intended packages added.

- Full make check passed all11 gates:752 Python,63 data and16 web tests;
Black115 files; CI parity; zero boundary violations;8 current generated artifacts;
contract types; web lint/types/build;35 database-wrapper safety cases; actual
PostgreSQL18.6 clean/repeat/five-smoke/upgrade-down-reapply checks; Gitleaks8.30.1
source snapshot. This is Linux ARM64 local evidence, not native AMD64/macOS.
- All15 source hashes matched;288 changed/new Markdown local file targets
resolved and git diff --check passed before final log links were added.
- Relevant checklist authorization/ownership/privacy/UTC lifecycle/bounded SQL/
concurrency/generated-source/dependency and local check items applied. Task-wide
browser/provider/real consumer/peer acceptance remains open. No readiness claim.

## Pending real checks / next checkpoint

Step9 local result is human-verified. Preview only: Step10 audits/consolidates
deterministic auth fixtures, fake rejection and integrated security/retention
coverage. No Step10 implementation has started. Actual CN-02 membership/consent/
client encryption is still owned by Rahul(D); resume with its real reviewed
implementation. Actual runtime/provider/browser/key/DB/TLS/proxy wiring and
current-main/PR10 migration reconciliation remain required before ID-READY.
Cleanup deployment/scheduling/live apply needs separate exact-target approval
and observed run evidence. No FR/NFR/task/readiness closeout is claimed.
