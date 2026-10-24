# ID-01 Step11 — gated Microsoft sign-in/callback UI

Recorded2026-10-24 13:17:13 UTC. Aditya(A), task/id-01-identity atb3fe7aa plus uncommitted Microsoft increment.
Aditya verified/authorized committing contacts and directed continuation. This
local Microsoft UI increment was human-verified by Aditya, with explicit commit/
continuation authorization recorded2026-10-24 13:28:17 UTC. Real provider/
runtime/browser acceptance and ID-READY remain incomplete.

## Definition audit / prerequisites

No material task-definition gap against canonical Step11, reviewed provider,
session/nonce/caller rules, Identity/combined/source/generated contracts, frontend
map and browser/stub/contribution/checklist requirements. Existing actual backend
Microsoft validation/account/attempt/session/CSRF logic and reviewed public client,
common authority and callback records are present. Actual provider verification
remains original Steps4/11/12/13 work; controlled SDK responses do not prove it.
Aditya keeps the existing Identity/shared-page reservation, extended to HTML
referrer metadata, test URL and SDK manifest. No other feature private code.

## Changed code/configuration and important behavior

| Path | Purpose and behavior |
|---|---|
| apps/web/src/features/identity/microsoft.ts | Lazy real MSAL5.26.0 controller with exact registered origins, disabled-by-default public flag and unconditional synthetic-preview block. Fresh server nonce/cookie precedes SDK code/PKCE/state redirect. Own bounded session marker stores only random state/public nonce/expiry and is consumed before response handling. State/nonce/expiry/required assertion checks precede one server exchange. Only in-flight work is coalesced for StrictMode; consumed markers reject later replay and settled login results are not reused. Explicit SDK-init retry is possible; concurrent starts/callback cannot overwrite one another. Requests SDK cache cleanup before new starts, before assertion exchange and finally on initialized callback paths; no silent/cached token acquisition or Microsoft global logout. URL response material is removed; provider errors become code-owned messages. Backend remains full authentication/eligibility authority; actual SDK artifact erasure/live wire behavior remains unproved. |
| apps/web/src/features/identity/MicrosoftSignIn.tsx | Disabled/enabled provider button and pending/success/safe-error callback screen. No raw claims/assertions/URLs are displayed. Explicit Check sign-in status uses only the generation-fenced session refresh, never a second assertion exchange, and describes existing CLIP session rather than new IISc proof. Inactive callback effects ignore late UI results. |
| apps/web/src/features/identity/api.ts | Typed nonce-attempt and assertion exchange endpoints from generated models; validate nonce/expiry, regular-only result and expired-session rejection. Existing same-origin cookies/custom headers/no-store/10s request bound apply; no automatic auth write retry. Extra result fields are not exposed. |
| apps/web/src/features/identity/session.tsx | Refresh now returns only the current fenced SessionView or null. Older reads after logout/account change cannot be used by explicit recovery to revive stale UI. Existing consumers may ignore its return; server remains authoritative. |
| apps/web/src/features/identity/SignIn.tsx | Adds private Microsoft button under the existing shared submit/ref guard, updates sign-in guidance and maps Microsoft failures safely. Other temporary/recovery flows remain. |
| apps/web/src/features/identity/index.ts | Exports MicrosoftCallback for public page composition, preserving prior feature exports. |
| apps/web/src/pages/ScaffoldPages.tsx | Connects only the existing AuthCallbackPage to public MicrosoftCallback; no new route or other feature/private composition change. |
| apps/web/src/features/identity/identity.css | Adds feature-owned spacing/layout for the Microsoft action and hint. |
| apps/web/index.html | Adds no-referrer metadata to prevent redirect material entering subsequent Referer headers. No page/provider configuration activation. |
| apps/web/vitest.config.ts | Sets jsdom test URL to the recorded localhost callback origin; Node architecture tests remain unchanged. |
| apps/web/tests/identity-microsoft.test.tsx | Thirty-one controlled SDK/DOM checks cover config, disabled/preview/exact-origin guards, server nonce/state metadata, start deduplication, invalid/expired markers/results, one-shot exchange/replay/deadline, cleanup/init/provider/backend/uncertain failures, StrictMode, no displayed/logged provider payloads, safe explicit recovery and logout fencing. SDK method stand-in is test-only, not cryptography/provider evidence. |
| package.json; package-lock.json | Pin runtime @azure/msal-browser5.26.0 and resolved @azure/msal-common. Existing dependency versions unchanged; actual SDK types enforce public method configuration. SDK is lazily loaded, not auto-selected by any fake/runtime discovery. |
| .env.example | Documents public VITE_MICROSOFT_SIGN_IN_ENABLED=false; no secret, actual environment change or server authority. |

Provider decision, canonical Identity/browser docs, root/web README, frontend map,
command registry and work log describe this implementation and pending real gate.
[Source hashes](microsoft-source-hashes.json) pin changed code/configuration/test.
No backend/schema/generated HTTP shape/tenant/domain policy or cloud change.

## Actual checks and limits

- Initial strict types caught an older SDK configuration pattern: in5.26.0 the
navigateToLoginRequestUrl option belongs to handleRedirectPromise, not constructor
auth options. Adapted to installed public types. Also narrowed generic claim shape
and replaced unsafe finally throwing with explicit post-cleanup outcome handling;
removed one unused test import. No checks disabled or casts bypassing SDK config.
- First86web cases passed; added SDK-init retry/cleanup/null/overlap and recovery-
after-logout cases, plus expired session arrival rejection. Final92web cases,
lint/types/production build passed. Controller/component filenames differ beyond
case so case-insensitive filesystems do not resolve a controller as a view.
- Source audit confirms browser client ID equals backend CLIENT_ID and callbacks
match reviewed provider records. Dependency audit confirms exactly2new SDK packages
and no existing version changes. Actual SDK source preserves supplied nonce/user
state and defaults fragment responses; its standard OIDC defaults include
 offline_access. No Graph data scope, client secret or provider account change.
- Official SDK cache guidance requires session storage for redirect. CLIP's own
marker holds public metadata only; SDK cache cleanup is explicitly requested.
No claim of crash/backup/browser-memory erasure. Actual artifact/consent/PKCE/
redirect checks remain live-provider gates. References: [Microsoft SDK caching](https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/caching.md),
[initialization](https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/initialization.md).
- Final make check passed all11gates:771 Python/63data/92web, Black118,
CI parity, zero boundary violations,8current generated artifacts, contract types,
web lint/types/build,35wrapper safety cases, actual PostgreSQL18.6 clean/repeat/
five-smoke/upgrade/down/reapply and Gitleaks8.30.1. No failed/blocked check is
counted as a pass. Existing frontend regressions remain passing.
- Actual local headless Chromium inspected disabled sign-in and safe callback
states at1280x800/390x844/844x390: no horizontal overflow, no synthetic response
text displayed, clean callback query/fragment and no-referrer metadata. Page
network observation recorded zero Microsoft-provider requests. Portrait callback
screenshot inspected outside the repo without real identity/assertion/contact/
OTP values; owned browser closed. No real provider success/native device proof.
- Normal production bundle excludes synthetic-inbox markers. Fourteen source/
config hashes matched and178local Markdown targets resolved before final log
links. Final evidence-inclusive scanner/hash/link checks follow metadata updates.
- Relevant checklist exact contracts/ownership, server-only authority, fresh
nonce/state/deadline, duplicate/replay/recovery fences, privacy, SDK/dependency
pinning and controlled/local/browser gates applied. Task-wide real provider/
SDK cache/consent/device/current-main/peer/ID-READY review stays open. Linux ARM64
and headless observations are not native macOS/AMD64 or actual-phone evidence.
- Fresh explicit1800s loopback synthetic backend was started for human review;
Vite reuses5173, API8001, fixed example inbox only. Previous capped backend had
expired. Recreate the synthetic account to exercise current-session recovery.
No Microsoft/SES call, inbox send, paid/shared resource or deployment occurred.

## Human verification / remaining gates

Use the capped loopback identity-preview environment. On `/sign-in`, sign out if
needed to inspect disabled Continue with Microsoft. It must remain disabled even
with a browser build flag in this synthetic mode. Open `/auth/callback` and inspect
safe unavailable state, Back to sign in and Check sign-in status. An existing
synthetic temporary session may be recovered as current CLIP session only; no
IISc eligibility is inferred. Inspect desktop and phone portrait/landscape.

This local UI increment is human-verified and authorized for local commit. Actual
provider/PKCE/cache/consent/native phone behavior cannot be checked through the
synthetic preview and remains required before readiness acceptance. Next is the
Step11 local/task-wide audit and original pending Step12 real setup/integration
plan, each under the numbered verification loop; no Step12 implementation started.
Real server/key/DB grants/TLS/proxy wiring, current-main/PR10 migration reconciliation,
SES configuration, actual CN-02 sharing and independent peer/readiness acceptance
retain their owners/gates. Consumer matrix stays Step14 outside ID-READY.
No live enablement/send/deployment/cloud/push/merge/FR/NFR/ID-READY approval.
