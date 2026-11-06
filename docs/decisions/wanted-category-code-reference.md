# Wanted-request category reference

**Date:** 2026-10-25

**Origin:** SE-02 Step3 pre-implementation audit; correction of Step2 schema handoff.

## Question

How can Search store wanted-request categories when its reviewed Listings
catalogue interface exposes immutable category codes rather than private UUIDs?

## Options considered

- Store the public code with a restrictive FK to the existing unique Listings
  code. Preserve the reviewed public interface and application ownership boundary.
- Add and review a new internal UUID lookup interface, expanding the contract
  and leaving existing public code-based inputs needing another mapping call.
- Read the private catalogue table or hardcode UUID mappings in Search. Rejected:
  the former violates domain boundaries; seeded UUIDs vary between databases.

## Selected choice

Use `search.wanted_requests.category_code text`, referencing
`listings.categories(code) ON DELETE RESTRICT`. Keep the reference nullable only
for retired content, with the same existing live/retired check and category index.
Search validates new assignments through `read_active_categories` and resolves
historical display labels through `read_category_display`. Inactive assignments
remain retained; new assignment still requires an active code.

Only the reviewed schema migration resolves existing UUID references and its
rollback resolves codes back to UUIDs. Transient conversion functions are dropped
inside each transaction. ALTER TYPE avoids request update triggers, preserving
content, revision, timestamps and pending state. No application code reads private
Listings tables. No public wire fields or category ownership change.

## Rationale

The stored reference should be usable through the already reviewed public
interface. Unique immutable catalogue codes provide referential integrity without
adding an implementation-only UUID dependency to Search.

## Implications

Migration `20261025012200_wanted_category_code_reference.sql` and its populated
rollback/reapply test correct the earlier storage-only no-gap conclusion.
Listings sale rows retain their existing category UUID reference. Shared database
wrappers and fixtures follow the new head; existing migrations stay unchanged.
The work log records SE-02 and the affected-owner review as complete. This dated
decision does not assert current cloud schema state or authorize a future migration.

## Approver

Mohit Mahapatra (Search owner), explicit approval in the SE-02 correction exchange
on 2026-10-25. This is not independent peer or cloud/deployment approval.

## Supersedes

The wanted-request UUID reference in the initial database schema design and the
SE-02 Step2 assertion that no category-boundary correction was needed. All other
[retirement](origin-retirement.md) and [domain-boundary](domain-public-boundaries.md)
rules remain applicable.
