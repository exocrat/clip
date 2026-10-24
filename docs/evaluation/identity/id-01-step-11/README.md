# ID-01 Step11 — first temporary-authentication UI checkpoint

Recorded2026-10-24 09:08:21 UTC. Aditya(A), task/id-01-identity, parent1175d12 plus uncommitted Step11 work.
Plan verified. Aditya verified the first visible increment and authorized its
checkpoint commit on2026-10-24 09:15:28 UTC (recording time), then requested
a minimum password length of8instead of15. No specific browser/device viewport
observations were supplied; actual-device checks remain open. This
is a partial Step11 checkpoint, not whole-Step11 or ID-READY acceptance.

## Audit, ownership and scope

No material Step11 task-definition gap: reviewed frontend map matches the actual
scaffold. Canonical Step11, HTTP/Identity/source contracts and generated writable
request types, shared conventions, caller/session/provider/stub rules and browser/
contribution/checklists guide implementation. Actual local Steps3–10 and PRE-00/
DL-00 are available. Provider/browser/deployed/current-main/peer gates remain.

Aditya reserved the Identity feature/public exports, App/session shell connection,
bounded Identity page composition and web tooling/preview/docs as sole current
writer. Only SignInPage is wired so far; callback/contact pages and all other
feature private files stay as before. IdentityPlaceholder remains exported for
marketplace compositions. No approved route added or removed.

First usable-screen checkpoint: temporary sign-in, personal-email challenge,
OTP/password activation, session summary/logout and safe error/loading states.
Microsoft PKCE/callback, forgot-password/reset, contact editor/profile UI and
remaining integrated UI/privacy cases remain Step11 work after human inspection.
Actual-phone keyboard/provider behavior is not proved by responsive emulation.

## Changed code/configuration and purpose

| Path | Purpose and important behavior |
|---|---|
| apps/web/src/features/identity/api.ts | Same-origin cookie/no-store requests with10s bound, custom unsafe header, protected CSRF lookup and no automatic write retry. Uses generated writable credential types. Validates approved session/challenge result fields, excludes unrelated contact/token fields and maps failures to code-owned messages without raw payloads. |
| apps/web/src/features/identity/session.tsx | In-memory summary provider, initial/focus/visibility session reads, expiry deadline and stale-read generation fencing around explicit login/logout. Server cookies remain HttpOnly and protected operations remain server-authorized; no token/contact storage. |
| apps/web/src/features/identity/SignIn.tsx | Responsive temporary login/register/verify screens, labeled inputs/autocomplete, loading/validation/rate-limit/unavailable/uncertain states, duplicate-submit guard, current-form-only secrets and explicit session/logout controls. Initial/uncertain challenge reuses operation ID; deliberate acknowledged resend uses a fresh ID and cooldown. Successful activation returns the form to login so logout cannot reveal stale verification state. |
| apps/web/src/features/identity/identity.css | Feature-owned responsive two-column/stacked forms, bounded controls, wrapping, focus-compatible and error/notice/test-preview styling using existing shared tokens. No shared visual-system rewrite. |
| apps/web/src/features/identity/PreviewMailbox.tsx | Development-preview-only lazy-loaded synthetic inbox. Fixed reserved example recipient; transient code stays in local browser/memory and never logs/files. Normal production bundle removes the module and endpoint marker. No real recipient/code is used. |
| apps/web/src/features/identity/index.ts | Public provider/session/SignIn exports for page/shell composition; preserves existing placeholder/props exports. Removes only Identity's .gitkeep at its first implementation. |
| apps/web/src/App.tsx | Supplies the public Identity provider around the existing router. |
| apps/web/src/app/AppShell.tsx | Composes public session/logout controls and corrects the scaffold status note; preserves all existing navigation/routes and other feature code. |
| apps/web/src/pages/ScaffoldPages.tsx | Replaces only SignInPage's Identity placeholder with the public SignIn component. Other pages retain their original connections. |
| apps/web/vite.config.ts | Explicit identity-preview serve-only mode proxies fixed auth/me/test-inbox paths to loopback8001; normal dev has no proxy; rejects preview-mode builds. Hosts/ports remain loopback/fixed/strict. |
| apps/web/vitest.config.ts | Evaluates the Vite configuration in ordinary test mode and includes .test.tsx files; individual UI test opts into jsdom, existing architecture tests remain Node-based. |
| package.json; package-lock.json | Pins test-only Testing Library React16.3.3/user-event14.6.8/jsdom30.1.3 and resolved dependencies. No Microsoft/runtime JS dependency added at this first checkpoint. |
| apps/web/tests/identity.test.tsx |16 DOM/API/config cases: activation/logout/CSRF, safe HTTP errors, ambiguous request-key reuse/no auto resend, duplicate submits, expiry/focus/stale-read fencing, malformed results/extra-field stripping and preview build/proxy isolation. Synthetic reviewed fetch results are not real-provider evidence. |
| apps/api/tests/domains/identity/postgres_fixtures.py | Extracts existing no-network disposable PostgreSQL/migration lifecycle into a reusable context manager; fixture retains identical owned-resource behavior. Preview never accepts an external DSN or retained target. |
| scripts/identity_ui_preview.py | Explicit test-environment, loopback-only fixed-port/time-capped harness using real sessions/OTP/SQL and synthetic-only transient mailbox; never SES/Microsoft. No raw code/body/credential logging. Timer/Ctrl+C removes only its owned DB. Script/tests excluded from actual API image; ordinary main remains health-only. |
| apps/api/tests/domains/identity/test_ui_preview.py |3 checks: refuse production before DB/listener; subprocess-isolated health-only normal composition; actual synthetic registration/cookie/SQL/no-store plus non-loopback denial. |

Root/web README, frontend map, command registry and work log describe this exact
partial checkpoint. [Source hashes](source-hashes.json) pin changed source/config.
No production API/domain authorization/schema/contract/generated output changed.

## Checks, failures and correction record

- First web suite found a real logout UI bug: after activation, logout revealed
stale verify mode. Corrected the successful-activation transition and kept its
full form/logout regression. Corrected uncertain resend operation-key handling.
All32 web cases then passed with lint/types/build.
-3 local preview safety/SQL tests passed. Actual headless Chromium showed the
sign-in screen/test labeling with no page-wide horizontal overflow at1280x800,
390x844 and844x390. Mobile screenshot inspected outside repository, without an
OTP/inbox/account secret. Human visual/device verification still pending.
- Initial full aggregate failed one existing health test (769 passed): a new
preview test imported app.main before environment selection. An intermediate
rerun was deliberately interrupted after384 passes because moving the import
inside the earlier-running test still risked caching local settings. Isolated
that startup assertion in its own bounded subprocess. Affected tests passed4
in reverse order. Failed/interrupted runs are not accepted as passes.
- Early one-off formatter attempts failed due nested root config/disabled
formatter/unsupported generic flag. Used existing web-local config with explicit
language-specific formatter options; no global config was changed. Ordinary
lint/types/build remained the actual required web checks.
- Final full make check passed all11 gates:770 Python/63data/32web tests,
Black118, CI parity, zero boundary violations,8 generated artifacts current,
contract types, web lint/types/build,35 wrapper safety cases, actual PostgreSQL18.6
clean/repeat/five-smoke/upgrade/down/reapply and Gitleaks8.30.1 source snapshot.
Existing Node lock versions unchanged; only new DOM-test dependencies resolved.
Normal production bundle scan found no synthetic-inbox endpoint/recipient/code
markers. All17 source/config hashes written;160local Markdown targets checked
before final log metadata links. Final evidence-inclusive scan follows below.
- Relevant checklist source ownership/public boundaries, actual local SQL/HTTP,
controlled provider isolation, no automatic auth writes, private output/credentials,
session/CSRF and responsive checks applied. Task-wide browser/provider/current-
main/peer/ID-READY review remains open. Local Linux ARM64/headless Chromium is
not actual-phone/native macOS/AMD64 or deployed/provider acceptance.

The explicit preview API/Vite were observed running at2026-10-24 09:08:21 UTC;
API is capped1800seconds from its launch and cleans up its owned database on
shutdown. Vite remains a foreground process to stop separately. The owned
headless inspection browser was closed after safe layout inspection; no real
provider or email operation occurred.

## Human verification / remaining Step11 and readiness gates

Open `http://localhost:5173/sign-in` while the explicit capped preview is running.
Use only the documented reserved example address and a made-up password; create,
read the local synthetic inbox, verify, sign out and sign back in. Test incorrect
credentials/code and inspect desktop plus phone portrait/landscape layouts.
Record actual browser/viewport and observations; emulation is not device evidence.
A real phone cannot use workstation localhost; do not expose the server without
an approved access plan. Aditya verified this first checkpoint. Its eight-character password correction
is checked by the updated boundary/API/UI tests.

After verification, resume the next Step11 UI increment (Microsoft callback/
password reset/contact editing and remaining tests) under the original approved
plan and browser-check loop. No Step12 action or commit is authorized here.
Provider/runtime/SSM/DB/TLS/proxy/current-main migration reconciliation, actual
Microsoft/SES/browser checks, real CN-02 sharing consent/encryption and independent
peer acceptance remain original gates. Full consumer matrix stays Step14 outside
ID-READY. No cloud, send, deployed cleanup, push, merge or readiness claim.

## Verified password correction

Aditya changed the minimum from15 to8characters and authorized committing the
corrected checkpoint. `temporary_passwords.py` now enforces8–128 Unicode
characters for activation/reset/login verification; hashing parameters and exact
password preservation stay the same. `test_temporary_passwords.py` covers eight/
128, seven/129 and Unicode/whitespace boundaries. `test_identity_http.py` adds
real OTP/SQL activation/reset/login at eight characters while seven is rejected
without consuming valid proof. The registration UI/help/example docs match eight;
the UI integration test verifies eight-character activation. Updated current
Identity contract and authentication decision; original Step6 evidence retains
its historical boundary. No existing longer password is invalidated.

Corrected checkpoint checks completed2026-10-24 09:20:33 UTC: full make check
passed all11gates,771 Python/63data/32web, including eight-character HTTP/UI/hash
boundaries. The original770-case result above belongs to the initial screen.
Human verification and explicit commit authorization cover this corrected
checkpoint. Remaining Step11 work still needs its visible-increment review.

The subsequent [password recovery checkpoint](reset-checkpoint.md) builds on
verified first UI/8-character commit4d56101. Its separate hashes/results do not
replace this historical first-increment evidence.

The later [private contact editor checkpoint](contacts-checkpoint.md) has its
own source hashes and pending browser verification; the first UI evidence above
remains tied to its original corrected checkpoint.
