# Web application guide

The web app is a runnable scaffold: it has the approved routes, shared shell,
and domain-owned placeholders. Identity temporary sign-in/registration is now in its first local UI checkpoint.
Other product surfaces remain placeholders; Microsoft callback/contact
editing and real provider/runtime acceptance are still pending.

Use Node.js 24 LTS and npm 11, as recorded in the
[workstation guide](../../docs/environment/development-workstation.md). Run
commands from the repository root; the root `package.json` and
`package-lock.json` are the only Node manifest and lockfile.

## Install and run locally

```bash
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The page header links to each approved route;
dynamic routes use the sample identifier `example`. Stop the foreground server
with Ctrl+C. Vite binds to loopback and fails if its configured port is busy.

## Run checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

`lint` runs Biome's recommended code checks on the web source, architecture
tests, and Vite configs. `typecheck` checks the app plus tests and Vite/Vitest configs.
`test` checks the route table used by the app and scans imports for violations
of the documented page/feature boundaries. The route tests deliberately check
paths and matching, not placeholder text or appearance. `build` type-checks the
app and creates production assets under ignored `apps/web/dist/`.

Run the same local suite with one command:

```bash
npm run check
```

## Preview a production build

```bash
npm run preview
```

Open `http://127.0.0.1:4173` and stop the foreground process with Ctrl+C. Build
first; preview serves only the generated local assets and does not deploy them.

These commands need no AWS credentials, external accounts, or production
endpoints. The current scaffold does not read frontend environment variables
or call an application API. `npm ci` downloads packages in the committed lockfile
from the configured npm registry.

## Identity first browser checkpoint — explicit local synthetic mode

From the repository root, in two foreground terminals:

```sh
CLIP_ENVIRONMENT=test uv run --locked python scripts/identity_ui_preview.py --synthetic-preview --seconds 1800
npm run dev -- --mode identity-preview
```

Open `http://localhost:5173/sign-in`. Both servers bind only to loopback. The
backend creates/migrates its own no-network disposable PostgreSQL container,
uses real Identity sessions/OTP/SQL and a reserved synthetic-only inbox; no SES
or Microsoft calls. Use only `preview@example.invalid` and a made-up password.
Create a temporary account, open Check test inbox, enter its transient code and
choose a8–128character password. Sign out and sign back in with those details.
The normal attempt/resend limits apply; code acknowledgements do not prove send
or eligibility. The preview code is only in local memory/browser, never logs or
evidence. Do not use real personal data or passwords in this mode.

The API expires after the chosen cap (default1800s, allowed60–3600s); Ctrl+C
also stops it and removes only its owned ephemeral database. Stop Vite separately
with Ctrl+C. A restart starts a new database, not the previous synthetic account.
The API port is8001 and Vite5173; busy ports fail rather than choose another.
The identity-preview mode is prohibited for builds/deployment. Normal builds
exclude the synthetic inbox; normal dev enables no proxy. Deployed runtime
wiring/cloud exposure and actual-phone access need their own reviewed plan.

Tests in `tests/identity.test.tsx` use jsdom/Testing Library and synthetic reviewed
HTTP results, covering forms, safe errors, duplicate/uncertain writes, session
expiry/stale reads and CSRF. The existing route/boundary tests remain. Full web
lint/types/tests/build uses `npm run check`. Human visual/device verification
follows the [browser procedure](../../docs/environment/browser-verification.md).

## Password recovery browser checkpoint

After creating the synthetic account above, sign out and choose **Forgot
password**. Enter the same reserved example email, request a reset code, and
read **Check test inbox**. Enter the code and a new8–128character password.
After reset, sign in explicitly with the new password; the old password and
sessions must fail. The shared OTP cooldown is60seconds from the previous send,
including registration, so wait a minute after registration before requesting
reset. Acknowledgement stays generic for unknown/ineligible addresses. Incorrect
or expired codes show a safe validation message; rate limits ask you to wait.

Uncertain reset outcomes guide sign-in with the new password rather than an
automatic retry. Passwords are never trimmed; UI and backend count Unicode code
points, with eight minimum and128maximum. Browser input permits the UTF-16 space
needed for128astral characters; the explicit character-count check remains the
client hint and backend authorization/validation remains authoritative.
This recovery increment awaits human browser verification; Microsoft callback
and own-contact UI remain pending Step11 increments.

## Private contact editor browser checkpoint

Open `http://localhost:5173/account/contacts` in the same capped local preview.
Sign in with the synthetic account you created (or register the reserved example
account again if the disposable database was restarted). Signed-out visitors see
a sign-in prompt and no contact request. Use synthetic contact values only.

Save email, phone and UPI one at a time; confirm a refresh shows the saved values.
Delete one field and confirm it disappears while the others remain. Blank fields
have an explicit empty state; clearing a draft does not delete a saved value.
Changing contact email does not change the sign-in email. Saving contacts does
not share them; actual Conversation selection/confirmation remains CN-02 work.
Copies already shared have separate retention. Errors/rate limits do not claim
success; uncertain writes require an explicit refresh before another attempt.

The page keeps drafts in memory, clears its UI on known logout/account changes,
and ignores old unmounted-editor responses. The session provider rechecks on
focus; ordinary focus changes preserve an unfinished draft for the same actor. Saving
one field also preserves unfinished edits in the other fields.
It uses no browser storage for contacts and never accepts an actor ID from the
URL. Human desktop/portrait/landscape and actual-device checks remain required.
Microsoft callback remains the next unimplemented Step11 UI scope.
