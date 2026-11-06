# MVP database schema — current sources

The schema proposal created for PD-08 is no longer the executable schema or a
current review checklist. **The ordered SQL files in `database/migrations/` are
the source of the installed schema.** Check the current migration head and
status using the [database guide](../../database/README.md); do not rely on an
old branch-head statement or treat this page as migration approval.

## Read by purpose

| Need | Current source |
|---|---|
| Public API fields, ownership and authorization boundaries | [Identity](../../contracts/identity.md), [Listings](../../contracts/listings.md), [Search](../../contracts/search.md), and [Conversations](../../contracts/conversations.md) contracts |
| Executable tables, constraints, indexes and triggers | Ordered files in `database/migrations/` and the migration/schema checks in the database guide |
| Initial authentication, contact, catalogue and listing choices | [Temporary authentication](../decisions/temporary-authentication-storage.md), [discovery semantics](../decisions/listing-discovery-semantics.md), and [catalogue/limits](../decisions/catalogue-and-listing-limits.md) |
| Offers, contact sharing and origin ownership | [Offer lifecycle](../decisions/offer-lifecycle.md), [domain boundaries](../../contracts/domain-boundaries.md), and [origin retirement](../decisions/origin-retirement.md) |
| Retention, encrypted content and notification records | [Private-data retention](../decisions/private-data-retention.md), [conversation cleanup](../decisions/conversation-content-cleanup.md), and [notification policy](../decisions/notification-delivery-policy.md) |

These contracts and decisions explain intended behavior; the migrations show
what is installed. When they differ, stop and resolve the discrepancy through
the owning task and review workflow. Never hand-edit a migration already
published to a shared environment; create a reviewed forward migration.

## Historical design record

This proposal originated in PD-08 Step 2 on 2026-10-18. It helped define the
initial relational inventory and record the approved design choices. Later
Listings, Search, Conversations and Identity migrations added or refined that
schema. Git history retains the full proposal; the linked decision records keep
the choices that remain useful. The proposal's old pending-review statements,
branch heads and proposed migration ordering are not current task status.

For backup/restore boundaries, use the [backup and restore procedure](../../database/backup-and-restore.md).
