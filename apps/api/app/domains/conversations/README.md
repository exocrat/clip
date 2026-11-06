# Conversations domain

Owner: D — Rahul for CN-01/CN-02; A — Aditya owns CN-03 notifications, with D reviewing producer/read-state integration. Required implementation belongs to the [domain task list](../../../../../docs/tasks/domain-task-list.md), after the required foundation and contract gates.

CN-02 Step7 implements the declared contact-options and contact-preparations
routes through `contacts.py`. Each checks Conversations membership and its local
write-disabled marker before installing Identity's actor/conversation scope.
Options expose flags; confirmed preparation returns only selected current own
values with no-store responses, entries, persistence or activity writes. The
normal Identity middleware supplies the real public providers; unbound calls
fail503. The UI keeps those values transient until the participant confirms
encrypted publication. Step8 stores only SDK-encrypted shares; `ciphertext` and
the SDK's encrypted first-send `prekey_bundle` are accepted, while protocol
controls are rejected. Independent30-day cleanup removes ciphertext/subtype
but preserves the ordered entry marker. It defaults to dry-run; no schedule or
persistent-target apply is enabled.

`origin_retirement.py` implements the internal `get_origin_activity` and `mark_origin_retired` database operations. `thread_creation.py` implements internal Listing and Wanted Request thread creation through trusted origin contexts and Identity's eligibility interface. Both providers are tested directly and await real origin-owner composition.

`routes.py` is the public HTTP adapter mounted by the application. `messages.py` stores opaque encrypted messages and explicit read acknowledgements. `queries.py` supplies membership-scoped inbox/summary reads, deterministic filtering/paging, and unread text counts without loading origins or message bodies. `key_directory.py` registers typed public SDK bundles, preserves referenced historical versions, publishes public one-time prekeys, and atomically reserves peer prekeys. Per-account locks serialize rotation/publication/reservation; durable caller/operation records replay the exact result or reject changed requests. Public bundle bytes use the reviewed typed JSON representation in `public_key_material`; incompatible legacy material fails closed. Private keys remain browser-local. The directory migration creates only Conversations-owned storage and keeps consumed key IDs to prevent reuse.

All HTTP routes require Identity to supply trusted `CallerContext`; no production test identity is installed. CN-01, CN-02 and CN-03 are marked complete in the [work log](../../../../../docs/status/work-log.md). This README records implementation boundaries; it does not claim a fresh live-session or cloud-state check. Persistent cleanup scheduling and applying the cleanup target remain separate operational work. Shared primitives belong in `app.core`; cross-domain calls use reviewed public interfaces.

`cleanup.py` implements the approved90-day thread-content purge and independent
per-share30-day cleanup. Both default to count-only inspection and preserve
ordering, operation and reference guards. The contact-share path locks and
rechecks each thread/entry, then removes ciphertext and subtype atomically while
retaining a content-free entry marker. `scripts/conversations_cleanup.py`
supplies explicit target checks and `history`, `contact-shares`, or `all`
scopes. Scheduling and persistent-target apply are separate operational actions,
not evidence of an incomplete CN task.
See the [mechanism and deletion order](../../../../../docs/decisions/conversation-content-cleanup.md).
