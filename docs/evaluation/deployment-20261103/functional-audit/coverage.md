# Functional coverage and remaining acceptance

This is a coverage ledger, not a claim that every defect has been found. All
known failures are rechecked after repair. Raw experiment measurements have not
started. Controlled fixture IDs stay in the private registry for later cleanup.

| Requirement | Actual deployed evidence in this audit | Remaining checks |
|---|---|---|
| FR01 regular identity | Human Microsoft login for two distinct regular test accounts; current sessions/Handles/keys verified; anonymous browse/photo401 | Post-repair sessions; expiry/logout/revocation have real disposable-DB regressions, not live clock alteration |
| FR02 temporary lifecycle | Confirmed hosted recipient restriction prevents intended general email; SES account production access verified | Repaired real mailbox receipt, OTP activation/login/reset and temporary browser journey;14day expiry has controlled-time tests |
| FR03 account-class permissions | Two regular accounts exercised; anonymous denial checked | Temporary account live journey; class matrix exercised by native/offline tests |
| FR04 listing fields | Actual browser S3 upload/confirm and zero-price create; valid owner edit and stale revision409 | Post-repair full UI create/edit; complete field matrix from local regressions |
| FR05 ownership/availability | Nonowner edit/availability403; owner hides listing; peer detail404, owner200 | Post-repair repetition and browser controls |
| FR06 browse | Available page1/page2, sampled filters/sorts; actual browser page rendered with11photo errors and14save warnings | Repaired desktop/narrow layouts, navigation, repeated page/image checks |
| FR07 search | Keyword populated/empty samples, category/condition/price/negotiability/order checks; Hybrid200->503 after new listing->200 after hide | Worker grants, real indexing, edited source invalidation, real reviewed-query retrieval and NFR04; no ranking inference from200 |
| FR08 wanted | Create with zero budget, edit to null, peer read, nonowner denial, close, hidden peer detail, draft matches | Wanted response conversation and browser workflow recheck |
| FR09 saved | Save/list/unsave, unavailable reference retained, original grant fix rechecked; intermittent browser state failure reproduced | New batch status endpoint, cancellation/account isolation and all live rechecks |
| FR10 conversation | Create/reopen deduplication; both participants read; real nonparticipant detail/entries404 | Repaired inbox/unread/group/pagination behavior; native uniqueness/ordering tests |
| FR11 offers | Actual create/revise/withdraw and seller read | Seller selection/clear and visible controls; native state/authorization tests |
| FR12 deliberate contacts | Fictional phone set, explicitly selected/reviewed, encrypted share displayed by peer; source restored | Post-repair recheck and local invalid/selected-field tests |
| FR13 notifications | Preference read/toggle/restore; actual task still had recipient restriction flagfalse | Hosted general-delivery repair; real controlled inbox/notification/suppression evidence. The Microsoft test accounts may have no deliverable notification destination |
| FR14 images | Real S3 upload, confirmation, full browser decode; hidden peer404/owner200; invalid type422; actual photo API503s reproduced | Batch links, retries/expiry, repeated rendered-page/body checks; local corruption/partial-upload/cleanup regressions |
| FR15 unavailable/no transaction claims | Controlled listing and wanted marked unavailable; existing thread retained | Repaired selection/availability UI, final human inspection |
| FR16 client E2EE | Actual opposite-direction submitted/displayed messages and encrypted contact share; API entry projection has no plaintext field | Post-repair persistence/reload checks; local tamper/key-change/loss tests; no private key extraction |
| FR17 sensitive declaration | Existing implementation inspected; catalogue/price behavior covered in local suites | Post-repair boundary/reclassification tests and visible declaration check |

NFR01/02/03 each require their own A and B profiles, real-target verification,
correct denominator and evidence. NFR04 requires reviewed Success@5 labels and
retrieval. NFR05 needs actual two-browser measured send/display under its bound
normal workload. NFR06 task loss and NFR07 isolated restore remain separately
approved actions. NFR08 ledger includes the approved runtime extension estimate;
gross billing and retained resources still need reconciliation.

New image and saved batches are browser functionality outside the planned
Listing-only API traffic. Listing collection/detail payloads are unchanged, so
their existing workload case shape is retained. Freeze the new application,
schema/contract and connection-setting revisions before any pilot, and verify
equivalent selected reads on both paths. Functional messages here are not NFR05.

Local normal-app integration now covers26workflow groups, including real
PostgreSQL batch photo/saved reads, missing/removed-image isolation, Hybrid
invalidation/reindexing, seller selection, wanted-origin conversations, logout,
temporary activation/permission limits and unread grouping. See
[integrated-local-sweep.json](integrated-local-sweep.json). These extend local
coverage and do not replace the deployed checks in the table. The worker-grant
regression proves the exact missing privileges in a disposable restricted role;
cloud SQL application and live indexing recovery remain pending.
