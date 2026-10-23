# Web application guide

The web app is a runnable scaffold: it has the approved routes, shared shell,
and domain-owned placeholders. Product data, authentication, APIs, saving,
offers, and messaging are still implemented by later tasks.

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

## Conversations API boundary

`features/conversations` exports `ConversationApi` and `ConversationHttpTransport`.
The adapter implements the reviewed inbox, summary, entries, message, explicit
displayed-read and public-key/prekey HTTP mappings using generated contract types.
It validates successful response shapes, rejects malformed routing/cursors/key
material, and exposes only content-free error status/kind. It never automatically
retries a write; the caller must retain and reuse its prepared ciphertext and
operation ID after an ambiguous outcome. Fetching entries never acknowledges reads.

Identity must supply the authenticated request function, including session and
CSRF behavior. The adapter has no default transport or test-identity fallback.
It is not yet mounted by the scaffold pages. Real auth, page composition,
local history persistence and two-browser integration remain pending. In
particular, `readOwnKey()` now maps the approved authenticated
`GET /me/conversation-key`: only an explicit valid null means never registered.
Errors or malformed bundles never become a missing key.

## Conversations SDK relay

Use the public `openIndexedDbConversationSession(userId, conversationId, api,
options)` entry point to compose the real OpenE2EE SDK with the authenticated
HTTP adapter. The account ID must come from Identity's trusted session view.
Pass null for `conversationId` to publish keys before any chat exists; peer
operations require a selected authorized conversation. First key creation
requires `acknowledgeUnrecoverableHistoryRisk: true` after the user accepts the
existing warning. Existing directory keys with missing local keys fail closed.
The local store is atomically bound to an account; a different account cannot
silently reuse its private state. The factory refuses a failed SDK sync and
suppresses SDK logging rather than forwarding keys/content/error internals.
It preserves the SDK's required PQ/Braid policy and key maintenance defaults.

The returned `{crypto, relay, stop}` provides the existing crypto boundary,
the transport, and explicit shutdown. `relay.retrySend(operationId)` reuses
the persisted prepared ciphertext, timestamp and operation ID, including after
adapter recreation. Directory identity/registration changes block posting or
retrying the old ciphertext. Call `stop()` before replacing the active client;
the IndexedDB factory also closes its store. `createConversationSession` accepts
an explicitly supplied platform store for composition/testing; production does
not select the memory adapter or install test authentication.

`ConversationRelay` maps own/member identity reads, single-device discovery,
public bundle registration, batches of up to 200 public OTPs, and peer OTP
reservation to the reviewed API. Registration/publication requests and prepared
message writes are journaled using SDK-local metadata before HTTP submission.
The versioned journal contains public material or ciphertext, never HTTP
credentials. Inventory times come from matching actual SDK-local key records,
not invented server timestamps. Concurrent reservation calls use distinct
reservations; distinct SDK client instances never share a reservation intent.
A failed reservation retries within that client, while a restarted client may
reserve fresh keys, leaving the old unused reservation consumed server-side.

Retrieval remains CLIP entry polling and the existing receive helper. SDK local
delivery completion neither acknowledges reads nor deletes retained API entries;
the UI must still acknowledge actually displayed messages. Delivery receipts
are disabled to preserve the approved no-peer-receipts behavior. No socket,
presence, group, linked-device, sealed-sender or server device-set capability is
advertised. Unsupported operations, including stale-KEM clearing and implicit
own-identity replacement, throw rather than report fake success. Automatic
protocol-control receive/resend recovery still needs integration checks; this
increment proves prepared HTTP retry, not every SDK recovery path.

`tests/conversations-relay.test.ts` uses actual SDK clients/crypto and a reviewed
HTTP-contract double. This proves isolated client behavior, not real Identity,
PostgreSQL transport, browser IndexedDB reload/concurrency, or CN-CORE acceptance.
Application history persistence, page wiring and those real checks remain pending.
