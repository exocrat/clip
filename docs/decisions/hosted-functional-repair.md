# Hosted functional repair: connection and browser request handling

Suraj requested comprehensive functional diagnosis, coordinated repairs and
equivalent behavior for ECS-only and ECS/Lambda, then actual NFR measurement.
The initial [live catalogue](../evaluation/deployment-20261103/functional-audit/README.md)
and [connection budget](../evaluation/deployment-20261103/functional-audit/connection-budget.md)
record evidence and limits. Passing results must come from verification.

## Selected implementation

- Use a bounded synchronous Identity pool for ECS. Keep current account/session
  SQL, logout, expiry and revocation checks unchanged. Share that pool across
  sessions, capabilities, contacts and notification recipient lookup.
- Bound existing async queues. Keep Lambda leases bounded and release idle
  connections before an execution environment can freeze. Resource sizes remain.
- Add GET`/images/delivery?image_ids=...` and GET
  `/me/saved-listings/status?listing_ids=...`, each limited to100IDs. The browser
  coalesces requests from a render without caching results across navigation or
  account changes. Cancelled components cannot receive a later batch response.
- Photo batches resolve one authoritative database snapshot, then apply each
  image's listing visibility rule before signing. Hidden and missing images both
  receive null, and cannot break unrelated page photos. Links retain at most
  five minutes; responses are private/no-store. Old single-image reads remain.
- Saved batches read only the caller's requested saved pairs, without resolving
  every saved listing's content or paging through all saves for every card.
- Existing listing collection/detail payloads are unchanged. The new batch
  routes stay on ECS in both configurations; selected Listing GET routing and
  measured workload definitions remain. NFR01 still excludes image bodies.

## Intended email behavior

SES has production access; the short application allowlist was a staged testing
restriction. Suraj explicitly requested intended real-app delivery. The already
explicit hosted real Identity runtime now permits canonical destinations for
its purpose-bound verification/password-reset mail; its dual-provider fallback
uses the same recipient policy. Required notifications likewise use general
eligible-recipient delivery in that hosted runtime. User opt-out, suppression,
OTP limits, provider order/keys, bounded retries and sender/TLS rules remain.

Standalone/local provider probes retain controlled recipients. The existing
test environment label and its fake/debug/startup safeguards are not globally
replaced with a production switch. The legacy notification-unlisted setting is
not a restriction on the explicitly hosted real app's required delivery.
No generic arbitrary-mail API is added. Real inbox verification remains pending
until a controlled deliverable recipient is available; provider access alone is
not proof of delivery.

## Approval boundaries

Suraj approved image-only repair redeployments with checks, review, health
verification and a known rollback, within existing resource and cost bounds.
Database privileges/limits, new resources and upgrades require their separate
approval. Future PR merge retains its gate. There is no automatic NFR acceptance,
permission to alter scoring/labels, or authorization for formal/fault workloads.
