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
The Conversations routes now compose the adapter and session/history helpers
through `ConversationPageRuntimeProvider`. Identity must mount that provider
with the authenticated user ID and its session/CSRF-aware API adapter; no such
provider is mounted by the current app shell yet. Until then, live routes show
an explicit sign-in/session-unavailable state and never invent an actor. Real
Identity auth, browser IndexedDB reload/concurrency and two-browser integration
remain pending. In particular, `readOwnKey()` maps the approved authenticated
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

The returned `{crypto, relay, history, sendText, receiveText, stop}` provides the existing crypto
boundary, the transport, browser-local history and explicit shutdown. Use the
session's `sendText(request)`, not the low-level `crypto.sendText`, to durably
stage the sender's text before encryption. `relay.retrySend(operationId)` reuses
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
Page wiring and those real checks remain pending.

### Browser-local history

For a selected thread, `session.receiveText(context)` verifies that the receive
context matches the selected thread and supplies `session.history` to the crypto
helper. Verified incoming text is saved before SDK receive completion.
`history.read()` returns detached,
sequence-ordered received messages and outgoing records with their exact send
request and optional server confirmation. It does not fetch or acknowledge reads.
Registration-only sessions have null history and cannot send text.

The relay records a validated server confirmation against staged sender text.
After an unknown network outcome or local confirmation failure, retry the exact
prepared ciphertext through `relay.retrySend`; the returned confirmation repairs
local history without encrypting again. Reusing `session.sendText` with the same
operation is rejected. A staged record alone does not prove ciphertext was
prepared or the server accepted it. If encryption failed before preparation,
there is no prepared retry; never silently encrypt it again under the same UUID.
The pending record remains visible to composition code for explicit resolution.

`history.ts` stores versioned account/thread-bound plaintext snapshots in the
same SDK-local store (IndexedDB in the browser factory). Atomic compare-and-set
merges concurrent writes, rejects conflicting sequence/message identities and
bounds contention retries. Storage/quota/corruption failures fail closed with
generic diagnostics. It rewrites a thread snapshot per write: large-history
paging/performance has not been established. This cache is browser-local, not a
backup, server plaintext store or key recovery. Same-origin script compromise
can read it, just as it can read local keys; clearing/eviction can lose it.
It must only be used after the validated session/key startup boundary, not as
an offline authentication bypass. No changes to retention or backup policy are
implied. The memory-store history tests and real-SDK/HTTP-double tests do not
prove browser reload, eviction/quota, multi-tab durability or real sign-in.

### Conversation route composition

`ConversationInboxPage` loads the caller-scoped inbox and opens the selected
conversation. `ConversationDetailPage` first asks the API for the route's
summary and confirms the authenticated caller is one of its participants,
then opens the account/thread-bound IndexedDB session, resumes a pinned peer
session or establishes one from the member-scoped prekey endpoint, and displays
decrypted server entries alongside browser-local sender/recipient history.
It advances the entry cursor only after a page has been processed, retries
ambiguous sends using the same operation ID and prepared ciphertext, and sends
read acknowledgements only when the thread UI reports messages visibly
displayed. The shared route scaffold imports these controllers through the
Conversations public `index.ts` only. Offer, selection and contact-sharing
sections remain explicit placeholders for CN-02/Identity work.

The provider is an injection point, not an authentication implementation.
Until Identity supplies and mounts it, the production routes stay unavailable;
do not wire a browser-provided user ID or demo identity into this boundary.
