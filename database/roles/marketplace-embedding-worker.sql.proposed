-- Give the existing background worker exactly the columns its lease and
-- completion statements write; existing SELECT/INSERT/DELETE grants remain.
GRANT UPDATE (state, lease_token, lease_until, attempts, failure_code, updated_at, title_count, description_count, retry_after)
ON TABLE listings.embedding_generations TO clip_test_marketplace_app;
GRANT INSERT (generation_id, part_kind, ordinal, vector)
ON TABLE listings.embedding_chunks TO clip_test_marketplace_app;
