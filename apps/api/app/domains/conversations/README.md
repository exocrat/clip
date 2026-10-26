# Conversations domain

Owner: D — Rahul for CN-01/CN-02; A — Aditya owns CN-03 notifications, with D reviewing producer/read-state integration. Required implementation belongs to the [domain task list](../../../../../docs/tasks/domain-task-list.md), after the required foundation and contract gates.

`origin_retirement.py` implements the internal `get_origin_activity` and `mark_origin_retired` database operations. `thread_creation.py` implements internal Listing and Wanted Request thread creation through trusted origin contexts and Identity's eligibility interface. Both providers are tested directly and await real origin-owner composition.

`routes.py` is the public HTTP adapter mounted by the application. `messages.py` stores opaque encrypted messages and explicit read acknowledgements. `queries.py` supplies membership-scoped inbox/summary reads, deterministic filtering/paging, and unread text counts without loading origins or message bodies. `key_directory.py` registers typed public SDK bundles, preserves referenced historical versions, publishes public one-time prekeys, and atomically reserves peer prekeys. Per-account locks serialize rotation/publication/reservation; durable caller/operation records replay the exact result or reject changed requests. Public bundle bytes use the reviewed typed JSON representation in `public_key_material`; incompatible legacy material fails closed. Private keys remain browser-local. The directory migration creates only Conversations-owned storage and keeps consumed key IDs to prevent reuse.

All HTTP routes still require Identity to supply trusted `CallerContext`; no production test identity is installed. Real-session and origin-owner acceptance, deployed retention scheduling, and notification delivery remain pending. The future `notifications/` subtree is reserved for A; other conversation/offer implementation remains D-owned. Shared primitives belong in `app.core`; cross-domain calls use reviewed public interfaces.

`cleanup.py` implements the approved90-day thread-content purge. It defaults to
count-only inspection, locks/rechecks activity, and removes payloads and offer
history atomically per thread while preserving ordering, operation and reference
guards. `scripts/conversations_cleanup.py` supplies explicit target checks;
scheduling, real apply and independent30-day contact-share cleanup remain pending.
See the [mechanism and deletion order](../../../../../docs/decisions/conversation-content-cleanup.md).
