-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);

-- Original results support safe retries after ambiguous HTTP/commit outcomes.
-- Create scope is the author; edit/state scope is the wanted request. No other
-- actor may reuse or read the key. Content is private, not an audit log.
CREATE TABLE search.wanted_command_results (
    author_id uuid NOT NULL REFERENCES identity.users ON DELETE RESTRICT,
    scope_id uuid NOT NULL,
    command_kind text NOT NULL CHECK (command_kind IN ('create','edit','state')),
    operation_id uuid NOT NULL,
    request_id uuid NOT NULL REFERENCES search.wanted_requests ON DELETE RESTRICT,
    request_payload jsonb,
    result_payload jsonb,
    PRIMARY KEY (author_id, scope_id, command_kind, operation_id),
    CHECK ((command_kind='create' AND scope_id=author_id)
        OR (command_kind IN ('edit','state') AND scope_id=request_id)),
    CHECK ((request_payload IS NULL) = (result_payload IS NULL)),
    CHECK (request_payload IS NULL OR jsonb_typeof(request_payload)='object'),
    CHECK (result_payload IS NULL OR jsonb_typeof(result_payload)='object')
);
CREATE INDEX wanted_command_request ON search.wanted_command_results(request_id);

CREATE FUNCTION search.guard_wanted_command_result() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    origin search.wanted_requests%ROWTYPE;
BEGIN
    SELECT * INTO origin FROM search.wanted_requests WHERE id=NEW.request_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Wanted command origin missing' USING ERRCODE='23503';
    END IF;
    IF NEW.author_id IS DISTINCT FROM origin.author_id THEN
        RAISE EXCEPTION 'Wanted command author mismatch' USING ERRCODE='23514';
    END IF;
    IF TG_OP='UPDATE' AND (NEW.author_id IS DISTINCT FROM OLD.author_id
        OR NEW.scope_id IS DISTINCT FROM OLD.scope_id OR NEW.command_kind IS DISTINCT FROM OLD.command_kind
        OR NEW.operation_id IS DISTINCT FROM OLD.operation_id OR NEW.request_id IS DISTINCT FROM OLD.request_id) THEN
        RAISE EXCEPTION 'Wanted command identity is immutable' USING ERRCODE='23514';
    END IF;
    -- A successful retry outcome cannot be rewritten. Only clearing both
    -- payloads is allowed for the separately approved future cleanup path.
    IF TG_OP='UPDATE' AND NEW.request_payload IS NOT NULL AND
        (NEW.request_payload IS DISTINCT FROM OLD.request_payload
            OR NEW.result_payload IS DISTINCT FROM OLD.result_payload) THEN
        RAISE EXCEPTION 'Wanted command outcome is immutable' USING ERRCODE='23514';
    END IF;
    IF origin.retired_at IS NOT NULL AND NEW.request_payload IS NOT NULL THEN
        RAISE EXCEPTION 'Retired wanted command cannot retain content' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER wanted_command_guard BEFORE INSERT OR UPDATE ON search.wanted_command_results
    FOR EACH ROW EXECUTE FUNCTION search.guard_wanted_command_result();

-- This guard deletes nothing. Until the separately approved retirement path
-- clears receipt payloads transactionally, retirement must fail closed rather
-- than leaving copies of request content. Content-free key references may stay.
CREATE FUNCTION search.guard_wanted_retirement_receipts() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS(SELECT 1 FROM search.wanted_command_results
        WHERE request_id=NEW.id AND request_payload IS NOT NULL) THEN
        RAISE EXCEPTION 'Wanted retirement requires content-free command receipts' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER wanted_retirement_receipt_guard AFTER UPDATE OF retired_at ON search.wanted_requests
    FOR EACH ROW WHEN (OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL)
    EXECUTE FUNCTION search.guard_wanted_retirement_receipts();

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
DO $$
BEGIN
    IF EXISTS(SELECT 1 FROM search.wanted_command_results) THEN
        RAISE EXCEPTION 'Refuse rollback of retained wanted command keys' USING ERRCODE='23514';
    END IF;
END;
$$;
DROP TRIGGER wanted_retirement_receipt_guard ON search.wanted_requests;
DROP FUNCTION search.guard_wanted_retirement_receipts();
DROP TRIGGER wanted_command_guard ON search.wanted_command_results;
DROP FUNCTION search.guard_wanted_command_result();
DROP TABLE search.wanted_command_results;
