# Live functional audit — in progress

This is a diagnostic inventory, not an experiment, NFR pass or claim that all
features work. Preserve user-created content. The user asked to find issues
before starting further repairs; the proposed embedding grants remain unapplied.

## Findings and evidence

The [requirement coverage ledger](coverage.md) identifies tested, sampled and
pending paths. The [connection budget](connection-budget.md) records the proposed
pool configuration and pilot gate. Existing image-only redeployment approval
does not authorize SQL grants, larger resources or formal workloads.

- **Intermittent image and saved-state failures:** reproduced during a single
  Discover-page-style set of 20 concurrent requests. One run had six of 20
  image-link requests return 503; all 14 that received links got an S3 200.
  Another run had one image-link and two saved-state 503s; the three request
  IDs matched logs showing rejection before routing. At that minute PostgreSQL
  recorded three `clip_test_identity_app` connection-limit failures. That role
  has a shared limit of ten across both hosts; each request opens a fresh
  connection and authenticates the session. A third reproduction had five image
  API 503s. These observations strongly implicate session capacity; they do not
  prove the cause of every user-observed image error.
- **Photo bodies:** a separate 20-photo run downloaded complete bodies and
  decoded all 20 successfully. The earlier photo checks read only initial bytes;
  they did not establish full downloads. There is no S3 failure in the sampled
  successful-link requests; browser rendering and every object remain unverified.
- **Saved and wanted:** the final database initially lacked Search schema
  privileges due to an incomplete deployment grant copy. The user approved a
  narrow correction, which was applied; user confirms both pages now load.
  Intermittent per-card saved checks still reproduced 503 after the correction.
- **Hybrid search:** an authenticated keyword query returned 200; the same
  query in Hybrid mode returned 503. One available listing has a pending
  embedding. The running worker repeatedly logged dependency unavailability,
  and a read-only EXPLAIN under its role returned SQLSTATE42501 for the
  generation row lock. Worker UPDATE/INSERT column grants were not in the old
  deployment either; the worker was disabled there. Proposed limited grants are
  documented separately and deliberately held pending the user's audit-first
  instruction. Other causes and final Search behavior remain to be tested.
- **Email:** the active provider is SES, and SES account sending and production
  access are enabled, but the test app restricts recipients to its configured
  list. The user privately confirmed their personal address is not on that list.
  No provider response or inbox evidence for their failed attempt has been
  obtained. Treat signup/email delivery as unverified and blocked for that
  address; do not send email or change the list without a reviewed test setup.
- **Own item:** the implementation rejects starting a conversation with oneself;
  the reported denial is expected. This does not test peer conversations.
- **Notifications recipient restriction:** current task metadata has the enabled
  notification worker with `CLIP_NOTIFICATION_ALLOW_UNLISTED_RECIPIENTS=false`.
  The old hosted composition therefore also restricted required event mail.
  General required-user delivery is included in the hosted repair; individual
  real notification/inbox outcomes remain unverified. This is distinct from
  provider account production access and from the user preference/suppression.
- **Data:** the original accepted reference projection was verified before
  user inspection. Since then a user signed in and created an additional listing
  and image. Preserve them; freeze/record the resulting fixture state before any
  measurements. Do not silently delete them or claim the entire live database
  still exactly equals the original 5,000/1,000-row snapshot.

## Read-only samples

[Semantic sample](read-semantics.json): two pages returned available listings
without overlap; sampled category/negotiable filters and price sorting matched;
catalogue, own listings, saved, wanted, inbox, unread count, profile, preference
and conversation-key reads returned 200. These are individual samples, not full
functional acceptance. [Page reproduction](page-reproduction-1.json),
[request correlation](failure-correlation.json), and [full image decode](full-photo-decode.json)
contain only aggregate statuses/counts. Older files describe the GET requests as
read-only/no mutation: more precisely, they made no business-data changes, but
normal authenticated GETs update the user's session idle timestamp.

## Remaining functional coverage

### Controlled-account pass — 2026-11-03 evening

[Controlled API flows](controlled-flows.json),
[owner/offer/browser checks](controlled-followups.json),
[actual encrypted chat](browser-chat.json),
[deliberate encrypted contact sharing](encrypted-contact-share.json), and
[visibility/fixture retirement](visibility-and-cleanup.json) retain safe results.

Two distinct regular Microsoft test accounts were used. Actual browser S3 upload,
confirmation, full image decode, zero-price listing creation, owner edit,
nonowner denial, stale-revision conflict, save/unsave, conversation uniqueness,
offer creation/revision/withdrawal, wanted creation/edit/closure, notification
preference toggle/restore, and unavailable-listing/saved/photo rules passed the
specific checks recorded. Two real browser messages were submitted, encrypted and
displayed in opposite directions. A fictional phone value was deliberately
selected, encrypted and displayed on the other client; its source value was then
restored. These samples are not NFR measurements or full security acceptance.

The browser Discover reproduction had11photo placeholders and14saved-state
warnings. Hybrid returned200 before a new available test listing,503 after its
creation/edit, and200 after that listing was marked unavailable. Thus prior
successful search must not be treated as recovery of indexing: newly visible
unindexed content reproduces the failure. The worker's missing row-lock/update
permission was independently rechecked by EXPLAIN and still returns42501.

A buyer key-setup gate occurred during navigation after the noisy Discover page;
after reload both composers became ready without changing keys. Message exchange
then succeeded. Preserve this as a transient observation to recheck after the
connection repair; do not call it lost keys. The follow-up script's GET
`/me/profile`404 is an invalid audit operation: that path supports PATCH, while
current account data is GET`/me`. It is not a confirmed product failure.

The single listing and wanted fixture have been marked unavailable. Their opaque
IDs and cleanup status are stored in the private fixture registry, outside Git;
test conversation/history remain. No personal listing was changed. Normal URL
access briefly timed out because the workstation resolver returned an old IP;
the two dedicated audit browsers now map only the app hostname to the existing
ALB DNS name while preserving TLS. This is a diagnostic workaround, not a frozen
experiment network configuration.

The first live pass is sufficient to start the coordinated repair batch below;
coverage still requires the remaining checks and post-repair live rechecks.

### Repair scope selected after the first live pass

1. Bounded Identity pooling, bounded existing async-pool queues, and a shared
   ECS/Lambda/worker/admin budget. Preserve current role limits for A/small B
   smoke; prepare any pilot role-limit change for exact separate approval.
2. Bounded per-page saved-state lookup and image-link batching. Keep existing
   Listing collection/detail responses and measured route behavior unchanged.
   Each image must still pass its listing visibility check; unavailable IDs get
   no link. Responses are private/no-store and links expire within five minutes.
3. Enable intended general recipient delivery for the already explicit real
   hosted app, retaining controlled standalone/local adapters and OTP limits.
   Keep provider order/keys, TLS, sender restrictions and notification policy.
4. Prepare the missing worker grants and recheck claim/encode/publish/search
   once the exact SQL is approved. Do not silently apply permission changes.
5. Run focused regressions and required gates, prepare image-only rollout and
   rollback, then repeat the known failures and affected workflows live. Check
   generated contracts, both runtime paths and experiment tooling before pilot.

- Login/logout, session expiry/revocation, origin/CSRF and temporary signup/OTP
  need a real controlled account matrix; do not expose credentials or OTPs.
- Listing create/edit/availability, image upload/confirmation/invalid upload,
  wanted create/edit/close/respond, save/unsave and ownership denial require
  controlled fixtures and user-safe cleanup. Existing personal listings must
  not be edited/deleted by the audit.
- Two separate controlled accounts and actual browser keys are needed for
  end-to-end encrypted chat, display, unread position, offers and deliberate
  contact sharing. Inbox/key HTTP200 alone proves none of these.
- Notification delivery/reminder/suppression, provider failures and recipient
  allowlist need a specifically controlled recipient and approved send scope.
- Hybrid correctness/quality, all filter/sort/pagination cases, accessibility,
  desktop/phone visual behavior and failure handling remain partially sampled.
- A/B routing, authenticated parity, pilot and all eight NFR results remain
  unmeasured. No diagnostic results here may be reported as an NFR pass.

## Friday comparison

At 2026-10-30 16:00 IST, `main`'s latest preceding commit was `6edb52b`. The
prior cloud API image `cn03-b95a7a50ecf8` was pushed at 14:32 IST, and ECS task
revision11 using its digest was registered at 14:44 IST. The user identifies
this as the working cloud image; we have not independently proved exactly what
was serving at 16:00. Its source commit is `b95a7a50ecf8f9015dfe89f33f9d1d3b5ccfb12b`.
The photo adapter and photo-card implementation are unchanged from that commit;
its task definition had Hybrid search and indexing worker disabled. The old
`clip_test` database currently contains four listings/images, while the final
reference database currently contains 1,001 of each after user inspection.
Do not infer the exact historical database row count solely from current counts.
