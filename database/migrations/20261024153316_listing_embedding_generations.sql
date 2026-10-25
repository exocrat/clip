-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Derived content remains entirely Listings-owned. Empty registry means this
-- additive migration starts no worker, backfill, inference or serving pipeline.
CREATE TABLE listings.embedding_pipelines (
    pipeline_id bytea PRIMARY KEY CHECK (octet_length(pipeline_id) = 32),
    encoding jsonb NOT NULL CHECK (jsonb_typeof(encoding) = 'object'),
    state text NOT NULL DEFAULT 'planned'
        CHECK (state IN ('planned','building','serving','retired')),
    created_at timestamptz(6) NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX embedding_one_serving
    ON listings.embedding_pipelines ((true)) WHERE state = 'serving';

CREATE TABLE listings.embedding_generations (
    listing_id uuid NOT NULL REFERENCES listings.sale_listings ON DELETE RESTRICT,
    pipeline_id bytea NOT NULL REFERENCES listings.embedding_pipelines ON DELETE RESTRICT,
    generation_id uuid NOT NULL UNIQUE CHECK (substring(generation_id::text,15,1) = '4' AND substring(generation_id::text,20,1) IN ('8','9','a','b')),
    source_fingerprint bytea NOT NULL CHECK (octet_length(source_fingerprint) = 32),
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','leased','ready','failed')),
    lease_token uuid,
    lease_until timestamptz(6),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts BETWEEN 0 AND 5),
    retry_after timestamptz(6) NOT NULL DEFAULT clock_timestamp(),
    failure_code text CHECK (failure_code IN ('timeout','helper_unavailable','invalid_vectors','lease_exhausted')),
    title_count integer NOT NULL DEFAULT 0,
    description_count integer NOT NULL DEFAULT 0,
    created_at timestamptz(6) NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz(6) NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (listing_id,pipeline_id),
    CHECK ((state = 'leased' AND lease_token IS NOT NULL AND lease_until IS NOT NULL)
        OR (state <> 'leased' AND lease_token IS NULL AND lease_until IS NULL)),
    CHECK (lease_token IS NULL OR (substring(lease_token::text,15,1) = '4' AND substring(lease_token::text,20,1) IN ('8','9','a','b'))),
    CHECK ((state = 'ready' AND title_count = 1 AND description_count BETWEEN 1 AND 96)
        OR (state <> 'ready' AND title_count = 0 AND description_count = 0)),
    CHECK (state <> 'failed' OR failure_code IS NOT NULL),
    CHECK (state NOT IN ('leased','ready') OR attempts BETWEEN 1 AND 5)
);
CREATE INDEX embedding_generation_due
    ON listings.embedding_generations (retry_after,listing_id,pipeline_id)
    WHERE state IN ('pending','leased');

-- Length-prefix the exact stored UTF-8 bytes; no extension or JSON/text-format
-- dependency. Workers carry this DB fingerprint instead of inventing a new hash.
CREATE FUNCTION listings.embedding_source_fingerprint(title text, description text)
RETURNS bytea LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
    SELECT sha256(convert_to('clip-listing-embedding-source-v1','UTF8')
        || int8send(octet_length(convert_to(title,'UTF8'))::bigint)
        || convert_to(title,'UTF8')
        || int8send(octet_length(convert_to(description,'UTF8'))::bigint)
        || convert_to(description,'UTF8'))
$$;

CREATE FUNCTION listings.embedding_vector_valid(vector real[])
RETURNS boolean LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
DECLARE squared double precision;
BEGIN
    IF vector IS NULL OR array_ndims(vector) IS DISTINCT FROM 1
        OR array_lower(vector,1) IS DISTINCT FROM 1 OR cardinality(vector) <> 384 THEN
        RETURN false;
    END IF;
    IF EXISTS (SELECT 1 FROM unnest(vector) AS value
        WHERE value IS NULL OR value::text IN ('NaN','Infinity','-Infinity')) THEN
        RETURN false;
    END IF;
    SELECT sum(value::double precision * value::double precision ORDER BY ordinal)
        INTO squared FROM unnest(vector) WITH ORDINALITY AS item(value,ordinal);
    RETURN squared IS NOT NULL AND abs(sqrt(squared) - 1.0) <= 0.001;
END;
$$;

CREATE FUNCTION listings.embedding_cosine(left_vector real[], right_vector real[])
RETURNS double precision LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE AS $$
DECLARE product double precision; left_norm double precision; right_norm double precision;
BEGIN
    IF NOT listings.embedding_vector_valid(left_vector)
        OR NOT listings.embedding_vector_valid(right_vector) THEN
        RAISE EXCEPTION 'Invalid embedding vector' USING ERRCODE = '23514';
    END IF;
    SELECT sum(left_vector[i]::double precision * right_vector[i]::double precision ORDER BY i),
        sqrt(sum(left_vector[i]::double precision ^ 2 ORDER BY i)),
        sqrt(sum(right_vector[i]::double precision ^ 2 ORDER BY i))
        INTO product,left_norm,right_norm FROM generate_series(1,384) AS i;
    RETURN greatest(-1.0,least(1.0,product / (left_norm * right_norm)));
END;
$$;

CREATE TABLE listings.embedding_chunks (
    generation_id uuid NOT NULL REFERENCES listings.embedding_generations(generation_id) ON DELETE CASCADE,
    part_kind text NOT NULL CHECK (part_kind IN ('title','description')),
    ordinal integer NOT NULL CHECK ((part_kind = 'title' AND ordinal = 0)
        OR (part_kind = 'description' AND ordinal BETWEEN 0 AND 95)),
    vector real[] NOT NULL CHECK (listings.embedding_vector_valid(vector)),
    PRIMARY KEY (generation_id,part_kind,ordinal)
);

CREATE FUNCTION listings.guard_embedding_pipeline() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    -- Serialize the two-build limit; a partial unique index also fences serving.
    PERFORM pg_advisory_xact_lock(1129072976,21);
    IF TG_OP = 'UPDATE' AND (NEW.pipeline_id IS DISTINCT FROM OLD.pipeline_id
        OR NEW.encoding IS DISTINCT FROM OLD.encoding OR NEW.created_at IS DISTINCT FROM OLD.created_at) THEN
        RAISE EXCEPTION 'Embedding encoding is immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.state IN ('building','serving') AND
        (SELECT count(*) FROM listings.embedding_pipelines
         WHERE state IN ('building','serving') AND pipeline_id <> NEW.pipeline_id) >= 2 THEN
        RAISE EXCEPTION 'Embedding pipeline limit' USING ERRCODE = '23514';
    END IF;
    IF NEW.state = 'serving' AND EXISTS (
        SELECT 1 FROM listings.sale_listings AS listing
        LEFT JOIN listings.embedding_generations AS generation
          ON generation.listing_id = listing.id AND generation.pipeline_id = NEW.pipeline_id
        WHERE listing.retired_at IS NULL AND listing.retirement_pending_operation_id IS NULL
          AND (generation.state IS DISTINCT FROM 'ready'
            OR generation.source_fingerprint IS DISTINCT FROM
               listings.embedding_source_fingerprint(listing.title,listing.description))
    ) THEN
        RAISE EXCEPTION 'Embedding coverage incomplete' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER embedding_pipeline_guard BEFORE INSERT OR UPDATE ON listings.embedding_pipelines
    FOR EACH ROW EXECUTE FUNCTION listings.guard_embedding_pipeline();

CREATE FUNCTION listings.invalidate_listing_embeddings() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.title IS NOT DISTINCT FROM OLD.title
        AND NEW.description IS NOT DISTINCT FROM OLD.description
        AND NEW.retired_at IS NOT DISTINCT FROM OLD.retired_at THEN
        RETURN NEW;
    END IF;
    -- Parent row is already locked by the original listing write. Delete ALL
    -- old spaces, including retired pipelines, before optionally queuing new.
    DELETE FROM listings.embedding_generations WHERE listing_id = NEW.id;
    IF NEW.retired_at IS NULL THEN
        INSERT INTO listings.embedding_generations
            (listing_id,pipeline_id,generation_id,source_fingerprint)
        SELECT NEW.id,pipeline_id,gen_random_uuid(),
            listings.embedding_source_fingerprint(NEW.title,NEW.description)
        FROM listings.embedding_pipelines WHERE state IN ('building','serving')
        ORDER BY pipeline_id;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER listing_embedding_invalidation
    AFTER INSERT OR UPDATE OF title,description,retired_at ON listings.sale_listings
    FOR EACH ROW EXECUTE FUNCTION listings.invalidate_listing_embeddings();

CREATE FUNCTION listings.check_embedding_generation() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE target uuid; generation listings.embedding_generations%ROWTYPE;
    titles integer; descriptions integer; first_part integer; last_part integer;
BEGIN
    FOREACH target IN ARRAY (CASE WHEN TG_OP = 'UPDATE' THEN ARRAY[OLD.generation_id,NEW.generation_id]
        WHEN TG_OP = 'DELETE' THEN ARRAY[OLD.generation_id] ELSE ARRAY[NEW.generation_id] END) LOOP
    SELECT * INTO generation FROM listings.embedding_generations WHERE generation_id = target;
    IF NOT FOUND THEN CONTINUE; END IF; -- intentional parent deletion/cascade
    IF EXISTS (SELECT 1 FROM listings.sale_listings WHERE id = generation.listing_id
        AND (retired_at IS NOT NULL OR generation.source_fingerprint IS DISTINCT FROM
             listings.embedding_source_fingerprint(title,description))) THEN
        RAISE EXCEPTION 'Embedding source is stale' USING ERRCODE = '23514';
    END IF;
    SELECT count(*) FILTER (WHERE part_kind = 'title'),
        count(*) FILTER (WHERE part_kind = 'description'),
        min(ordinal) FILTER (WHERE part_kind = 'description'),
        max(ordinal) FILTER (WHERE part_kind = 'description')
        INTO titles,descriptions,first_part,last_part
        FROM listings.embedding_chunks WHERE generation_id = target;
    IF (generation.state = 'ready' AND
        (titles <> generation.title_count OR descriptions <> generation.description_count
          OR first_part IS DISTINCT FROM 0 OR last_part IS DISTINCT FROM generation.description_count - 1))
        OR (generation.state <> 'ready' AND titles + descriptions <> 0) THEN
        RAISE EXCEPTION 'Embedding generation incomplete' USING ERRCODE = '23514';
    END IF;
    END LOOP;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER embedding_generation_complete
    AFTER INSERT OR UPDATE OR DELETE ON listings.embedding_generations
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION listings.check_embedding_generation();
CREATE CONSTRAINT TRIGGER embedding_chunks_complete
    AFTER INSERT OR UPDATE OR DELETE ON listings.embedding_chunks
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION listings.check_embedding_generation();

COMMENT ON TABLE listings.embedding_chunks IS
    'Private derived listing content. Removed atomically on source edits/final retirement; never public metadata.';

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Serialize against writers before testing emptiness; no destructive down of data.
LOCK TABLE listings.sale_listings IN SHARE ROW EXCLUSIVE MODE;
LOCK TABLE listings.embedding_pipelines,listings.embedding_generations,listings.embedding_chunks IN ACCESS EXCLUSIVE MODE;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM listings.embedding_generations)
        OR EXISTS (SELECT 1 FROM listings.embedding_chunks) THEN
        RAISE EXCEPTION 'Populated embedding store blocks rollback' USING ERRCODE = '23514';
    END IF;
END; $$;
DROP TRIGGER listing_embedding_invalidation ON listings.sale_listings;
DROP TRIGGER embedding_generation_complete ON listings.embedding_generations;
DROP TRIGGER embedding_chunks_complete ON listings.embedding_chunks;
DROP TRIGGER embedding_pipeline_guard ON listings.embedding_pipelines;
DROP TABLE listings.embedding_chunks;
DROP TABLE listings.embedding_generations;
DROP TABLE listings.embedding_pipelines;
DROP FUNCTION listings.check_embedding_generation();
DROP FUNCTION listings.invalidate_listing_embeddings();
DROP FUNCTION listings.guard_embedding_pipeline();
DROP FUNCTION listings.embedding_cosine(real[],real[]);
DROP FUNCTION listings.embedding_vector_valid(real[]);
DROP FUNCTION listings.embedding_source_fingerprint(text,text);
