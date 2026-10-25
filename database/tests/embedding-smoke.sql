-- Read-only native math/catalogue checks. Never model relevance or NFR evidence.
BEGIN;
DO $$
DECLARE vector real[] := array_fill(0::real,ARRAY[384]);
    other real[] := array_fill(0::real,ARRAY[384]); result double precision;
BEGIN
    vector[1] := 1;
    other[2] := 1;
    IF NOT listings.embedding_vector_valid(vector)
        OR listings.embedding_vector_valid(NULL::real[])
        OR listings.embedding_vector_valid(array_fill(0::real,ARRAY[384]))
        OR listings.embedding_vector_valid(array_fill(0::real,ARRAY[384],ARRAY[0]))
        OR listings.embedding_vector_valid(ARRAY[[1::real]]) THEN
        RAISE EXCEPTION 'Embedding vector shape validation failed';
    END IF;
    result := listings.embedding_cosine(vector,vector);
    IF abs(result-1) > 1e-12 OR abs(listings.embedding_cosine(vector,other)) > 1e-12 THEN
        RAISE EXCEPTION 'Embedding exact cosine failed';
    END IF;
    vector[1] := 'NaN'::real;
    IF listings.embedding_vector_valid(vector) THEN
        RAISE EXCEPTION 'Embedding NaN accepted';
    END IF;
    vector[1] := 'Infinity'::real;
    IF listings.embedding_vector_valid(vector) THEN
        RAISE EXCEPTION 'Embedding infinity accepted';
    END IF;
    IF octet_length(listings.embedding_source_fingerprint('title','description')) <> 32
        OR listings.embedding_source_fingerprint('ab','c') = listings.embedding_source_fingerprint('a','bc') THEN
        RAISE EXCEPTION 'Embedding source boundary invalid';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname='listings' AND indexname='sale_full_text') THEN
        RAISE EXCEPTION 'Original full-text index missing';
    END IF;
END;
$$;
ROLLBACK;
