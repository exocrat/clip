# ID-01 Step11 — password recovery UI checkpoint

Recorded2026-10-24 09:29:11 UTC. Aditya(A), task/id-01-identity at4d56101 plus uncommitted recovery increment.
Aditya verified the first UI, requested8-character minimum, authorized its commit
and directed continued Step11 work. Aditya verified this recovery increment and authorized
its checkpoint commit on2026-10-24 09:33:04 UTC (recording time); no specific
browser/device measurements were supplied. No additional numbered step or Microsoft/contact UI work.

## Scope audit / real dependencies

No task-definition gap against Step11 and reviewed Identity/reset HTTP contracts.
The backend already implements real single-use OTP/reset/hash/session revocation;
verified771 Python/63data/32web/all11 gates support the first corrected commit.
The new UI uses those exact operations/generated writable types. Same reserved
Identity writer and existing `/sign-in` route; no cross-feature or shared-page
composition changes. Provider/browser/current-main/peer/ID-READY gates remain.

## Changed code and important behavior

| Path | Purpose and important behavior |
|---|---|
| apps/web/src/features/identity/api.ts | Extracts one safe acknowledgement validator shared by registration/reset and adds typed reset-challenge/reset-password operations. Generic acknowledgements reveal no eligibility/delivery. Reset is a single explicit write returning no replacement session; existing cookie/header/no-store/time bounds and no automatic retry apply. |
| apps/web/src/features/identity/SignIn.tsx | Adds Forgot password and reset states to the existing page, purpose-separated challenge/resend and recovery-specific labels/autocomplete. Explicit reset submits only challenge/code/new_password, clears password/code/email/session summary on confirmed success and requires normal sign-in. Expired challenge blocks submission. Unknown/dependency/incorrect/rate-limit errors remain safe. Uncertain outcome instructs sign-in with the new password; no automatic reset retry. Cancellation/email change clears proof/password and stays in recovery. Eight–128 Unicode code points are checked without trimming; native input permits enough UTF-16 units for128astral characters. Registration shares the same creation-password validation. |
| apps/web/tests/identity.test.tsx | Adds8 UI cases for reset-specific endpoints/generic ack, eight-character reset then explicit login, no implicit session, secret clearing, uncertain single attempt and recovery guidance, safe422/429/503, expired-code submission denial, seven/eight astral-character limits and changing email without entering registration. Existing32 web cases retained. |

Root/web README, frontend map, commands and work log describe this increment.
[Source hashes](reset-source-hashes.json) pin these3code/test files. No production
API/schema/generated/contract/dependency, page route or private feature change.

## Actual checks and observed recovery

- Initial web lint rejected an unannotated optional activation result; typed it
with generated SessionView|undefined and reran. No lint rule disabled. An initial
formatter command used root-relative paths from the wrong directory and processed
nothing; reran the registered exact web-local command successfully.
- All40 web tests passed, plus lint/types/normal production build. DOM providers
are controlled reviewed fetch results, not actual Microsoft/SES evidence.
- The previously owned preview backend was stopped with SIGINT and its context
manager removed only its disposable DB. Uvicorn emitted a standard interrupt
traceback/exit130; that is the requested stop, not a successful test run. Restarted
the same explicit capped harness with fresh ephemeral SQL/keys so the actual
server loads the committed eight-character policy. Vite reuses the existing
loopback5173 process; no live provider/send, credentials or shared database.
- Final full make check passed all11 gates:771 Python/63data/40web,
Black118, CI parity, zero boundary violations,8generated artifacts current,
contract types, web lint/types/build,35wrapper safety cases, actual PostgreSQL18.6
clean/repeat/five-smoke/upgrade/down/reapply and Gitleaks8.30.1 source snapshot.
- Headless Chromium rendered recovery entry/action with no horizontal overflow
and no visible errors at1280x800/390x844/844x390. Portrait screenshot inspected
outside the repo without OTP/account/secret values; owned inspection browser
closed afterward. Normal build excludes synthetic-inbox endpoint/address/code
markers. Human/device verification remains pending; emulation is not phone proof.
- Relevant checklist public contract/type/ownership, private input/output,
session/reset/uncertain retry, Unicode and local/controlled-provider checks applied.
Task-wide provider/device/current-main/peer/ID-READY review remains open. Local
Linux ARM64 results are not new native macOS/AMD64 or deployed acceptance.

## Human verification actions / remaining gates

Open `http://localhost:5173/sign-in`. This fresh disposable database has no prior
preview account. Use only the reserved example address and a made-up password,
create/verify the temporary account, sign out, wait60seconds from its last code
send and choose Forgot password. Request/reset via the transient test inbox,
choose a different password of at least8characters, then explicitly sign in.
The old password must fail. Also inspect incorrect code/safe errors and narrow
portrait/landscape layout. No email is sent; Microsoft is disabled in preview.
The API is capped1800s from restart and cleans its owned DB on timeout/stop.

Record actual browser/viewport observations; human layout/device acceptance is
not inferred from tests or this report. The first UI is already human-verified;
this recovery increment is human-verified and its checkpoint commit authorized. Next preview
only: private contact editor and Microsoft PKCE/callback remain Step11 work.
Actual-phone keyboard, provider/runtime/SSM/DB/TLS/proxy/current-main migrations,
CN-02 consent/encryption and independent peer/readiness gates remain open.
No cloud/send/retained cleanup/push/merge/deployment or ID-READY completion.
