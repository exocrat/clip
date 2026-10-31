-- Support English-normalized keyword search over open, visible Wanted Requests.
-- migrate:up
CREATE INDEX wanted_open_text_search
    ON search.wanted_requests USING GIN (
        to_tsvector(
            'pg_catalog.english',
            coalesce(title, '') || ' ' || coalesce(description, '')
        )
    )
    WHERE retired_at IS NULL
      AND status = 'open'
      AND retirement_pending_operation_id IS NULL;

-- migrate:down
DROP INDEX search.wanted_open_text_search;
