# Shared browser session transport

**Date:** 2026-10-25
**Origin:** ID-01 Step12, Aditya's authorized Listings/Search CSRF integration.

## Question
How do feature-owned browser APIs use the reviewed cookie/CSRF contract consistently
without importing Identity-private code or changing marketplace authorization?

## Options considered
- Keep separate feature transports implementing the same session contract.
- Share technical HTTP/session behavior while retaining feature payload validation,
  safe errors, operation keys, UI and resource policies with their owners.

## Selected choice
Use `src/shared/http/sessionFetch.ts`. Each protected unsafe request fetches a fresh
session-bound token from GET /auth/csrf, then sends X-CLIP-Request:1 and the returned
X-CSRF-Token. Missing/failed/malformed preflight prevents that write. No token cache,
persistent storage, automatic replay or fallback to unprotected transport.
Only the reviewed public login/activation/reset operations may omit CSRF; they
still send the marker. The backend remains authoritative for session/class,
Origin, CSRF, resource ownership and current account state.

Requests use same-origin credentials/mode, no-store and redirect:error. Foreign,
protocol-relative and traversal targets fail before I/O. A linked ten-second
abort/deadline covers preflight and complete response receipt; bounded JSON/204
API responses are buffered through a clone before returning the original Response
for each feature's own parser. This transport is not for streams or upload bytes.
Failures expose safe status and whether the business request might have run.

API preflight and business requests explicitly use `referrerPolicy: "origin"`.
The document keeps its `no-referrer` policy for other activity. In fetch mode
`same-origin`, inheriting `no-referrer` serializes the write's Origin as `null`
under the [Fetch Standard](https://fetch.spec.whatwg.org/#append-a-request-origin-header),
causing the existing exact-Origin guard to reject legitimate writes. The API
override sends only the site origin as Referer, excluding path, query and fragment
(including login callback material), and preserves the browser's real Origin.
It is fixed after caller options so features cannot accidentally restore the
conflicting policy. Same-origin mode still prevents foreign destinations and
redirects remain rejected. Server Origin/CSRF validation continues unchanged.

Normal Identity uses the existing /api proxy like marketplace features. Explicit
Identity preview retains unprefixed routing; its existing build guard remains.
Listings/Search adopt only the shared transport, preserving their public exports,
request/response schemas, validators and owner-controlled operation retry rules.
Presigned S3 byte uploads keep their existing separate headers/transport.

Existing isolated browser demos expose the reviewed CSRF response double under
their current transport/profile guards. The shared app exposes it only for the
already-guarded dedicated synthetic Listings profile, before SPA fallback. Normal
and production startup never gain synthetic authentication or a CSRF bypass.
These doubles are not evidence of real session protection or readiness.

## Rationale
The old feature helpers lacked required headers, and normal Identity paths did not
use Vite's /api proxy. Fresh preflight avoids cross-account token caches; a cookie
change between stages is rejected by the server. No automatic replay is safe for
ambiguous mutations. Shared behavior prevents feature-private coupling.

## Implications
A coordinates the bounded technical helper; Suraj(B)/Mohit(C) retain their feature
logic and must review adapter/test-fixture changes. There are no page/route/UI or business-contract changes. ID-01 and affected
marketplace task status is recorded in the work log. This decision is not a current
proxy/TLS/provider-state assertion.

## Approver
Aditya(A) authorized the integration. Human/owner acceptance is recorded in the
work log; this does not approve any future push or deployment.

## Supersedes
None; implements the existing reviewed session/CSRF extension across feature APIs.

## Firefox origin compatibility — 2026-10-26 19:31:52 UTC

Aditya verified the API-only referrer-policy correction. Both CSRF preflight and
business fetches pin `referrerPolicy: origin`, overriding caller options. The page
retains `no-referrer`; Firefox otherwise sends `Origin: null` for these same-origin
POSTs. Firefox 148 reproduced and verified the correction locally, and Aditya
confirmed real local Firefox sign-in on 2026-10-26 19:36:18 UTC. Later task
acceptance is recorded in the work log; no current browser session is asserted.
