# CN-03 terminal notification cleanup proposal

**Status:** approved by Aditya and implemented locally; disposable PostgreSQL
checks passed. Shared/cloud execution remains separately gated.

Implement a Conversations-owned, bounded asynchronous cleanup operation. It
uses PostgreSQL's clock and selects at most 100 terminal `sent`, `suppressed` or
`failed` intent IDs whose `completed_at` is at least 30 days old and whose
original `expires_at` has passed. The operation defaults to dry-run; a caller
must explicitly select `apply=True`. It installs no scheduler, CLI, cloud job,
or automatic execution.

For each candidate, use one transaction and lock the owning thread, recipient
member and intent in the same order as delivery. Recheck terminal state, cutoff
and original expiry while locked; then delete only that intent row. Limit lock
and statement waits, report aggregate counts only, and safely resume after a
partly completed batch. No content, account, read-state or origin rows change.

Do not add a separate deduplication table: source-derived keys and due times are
immutable, the database rejects an inserted intent after its original 24-hour
delivery window, and member episode state survives terminal-row deletion. A new
conversation retry reuses the existing thread. Tests must demonstrate all these
replay guards, exact cutoff, live/leased exclusion, concurrent state changes,
dry-run, batch bounds and rollback on a disposable synthetic database. If those
guards prove insufficient, stop and review a bounded guard before deletion.

This approval is for the local implementation and synthetic tests only. Any
shared/cloud deletion, scheduler installation or deployment requires a separate
exact plan and approval. Rahul reviews Conversations state and producer effects.

An offline [role proposal](../../database/roles/conversations-notification-retention.sql.proposed)
grants SELECT and row-lock permissions on the three required tables and DELETE
on intents. Its narrow key-column UPDATE grants also permit key changes; this
residual capability needs review. The DELETE grant covers the whole intent
table; the reviewed cleanup code, rather than SQL privileges, enforces the age
and terminal-state restrictions. Disposable PostgreSQL checks prove locks,
denial of unrelated writes, and successful dry-run and deletion under that role.
No role, scheduler or cleanup was deployed.
