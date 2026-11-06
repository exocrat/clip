# Listings API guide

This guide maps the Listings implementation to its contracts, persistence boundary,
and focused tests. Task completion is tracked in the [work log](../../../../../docs/status/work-log.md);
this file is not a deployment or live-integration status report. Historical
checkpoint detail formerly kept here is represented by source history and the
linked task/evaluation records.

## Implementation map

- `routes.py` mounts listing, browse, saved-summary, image-upload/delivery,
  availability, selection, and offer endpoints.
- `service.py` owns request validation, seller/owner checks, image lifecycle,
  optimistic revisions, and the listing-side offer/availability rules.
- `browse.py` and `browse_store.py` implement public discovery and SQL filtering;
  `browse_validation.py` preserves raw input types before coercion.
- `search_access.py` is the public adapter used by Search. Search must use these
  operations and must not query Listings tables directly.
- `postgres_store.py` and the focused store modules implement Listings-owned SQL.
  `s3_storage.py` signs private-bucket upload and short-lived delivery requests.
- `cleanup.py` contains bounded object cleanup; it is an internal worker operation,
  not an HTTP endpoint or an installed schedule.

## Behavior and boundaries

Discovery excludes retired, unavailable, future, and ended listings before paging.
Ordering is stable for a fixed database state; it does not promise a snapshot across
concurrent changes. Search text is bound plain text. Catalogue codes are read from
the current database catalogue, and money/page inputs are validated before integer
coercion. Public image access uses short-lived links and checks retained listing
visibility; object keys stay private. Confirmed uploads are owner-bound and listing
attachment is transactional. Removed images are retired and cleaned asynchronously.

Listings calls Identity and Conversations only through their public adapters. It
owns its rows and does not read another domain's private tables. Replacement,
availability, selection, and offer operations enforce the reviewed revisions and
serialization rules at the persistence boundary. See the [API contracts](../../../../../contracts/README.md),
[database migration guide](../../../../../database/README.md), and the
[domain task index](../../../../../docs/tasks/project-task-index.md) for canonical
interfaces and task status.

## Focused verification

`test_browse.py` covers HTTP/auth/privacy behavior with scripted pages;
`test_browse_postgres.py` covers real SQL browse, filtering, ordering, and paging
when run through the registered disposable database checker. Store and image tests
cover adapter behavior and upload/cleanup rules. A unit or isolated SQL pass does
not establish current AWS, Identity-provider, Conversations, or browser integration.
Run the repository's documented checks when changing these paths; do not infer a
cloud or deployment result from local tests.
