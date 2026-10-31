-- migrate:up
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Cross-row storage invariants. These trigger functions are not public domain
-- services and confer no permission to bypass live account/API authorization.

-- Preserve original account identity/lifetime and restrict password credentials
-- to temporary users. Hash algorithms/OTP verification remain ID-01 outputs.
CREATE FUNCTION identity.guard_user_history() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id OR NEW.account_class IS DISTINCT FROM OLD.account_class
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR (OLD.activated_at IS NOT NULL AND (NEW.activated_at IS DISTINCT FROM OLD.activated_at
            OR NEW.expires_at IS DISTINCT FROM OLD.expires_at))
        OR (OLD.profile_removed_at IS NOT NULL
            AND NEW.profile_removed_at IS DISTINCT FROM OLD.profile_removed_at) THEN
        RAISE EXCEPTION 'Original account identity and lifetime cannot be rewritten' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER users_history BEFORE UPDATE ON identity.users
    FOR EACH ROW EXECUTE FUNCTION identity.guard_user_history();

CREATE FUNCTION identity.guard_local_credential() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM identity.users WHERE id = NEW.user_id
        AND account_class = 'temporary' AND profile_removed_at IS NULL) THEN
        RAISE EXCEPTION 'Local credentials require an intact temporary account' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.user_id IS DISTINCT FROM OLD.user_id
        OR NEW.login_email_key IS DISTINCT FROM OLD.login_email_key
        OR NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.revision < OLD.revision) THEN
        RAISE EXCEPTION 'Credential identity is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER credentials_owner BEFORE INSERT OR UPDATE ON identity.temporary_credentials
    FOR EACH ROW EXECUTE FUNCTION identity.guard_local_credential();

-- The enrollment guard survives credential cleanup. Per-key uniqueness is not
-- a substitute for the pending reviewed cross-key normalization/lookup contract.
CREATE FUNCTION identity.guard_enrollment() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Preserve the minimal verified enrollment guard' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id
        OR NEW.login_digest IS DISTINCT FROM OLD.login_digest
        OR NEW.digest_key_version IS DISTINCT FROM OLD.digest_key_version
        OR NEW.first_activated_at IS DISTINCT FROM OLD.first_activated_at
        OR NEW.original_expires_at IS DISTINCT FROM OLD.original_expires_at
        OR (OLD.user_id IS NOT NULL AND NEW.user_id IS NOT NULL
            AND NEW.user_id IS DISTINCT FROM OLD.user_id)) THEN
        RAISE EXCEPTION 'Verified enrollment identity and lifetime are immutable' USING ERRCODE = '23514';
    END IF;
    IF NEW.user_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM identity.users
        WHERE id = NEW.user_id AND account_class = 'temporary'
            AND activated_at = NEW.first_activated_at AND expires_at = NEW.original_expires_at) THEN
        RAISE EXCEPTION 'Enrollment must match the original verified account lifetime' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enrollment_history BEFORE INSERT OR UPDATE OR DELETE ON identity.temporary_enrollments
    FOR EACH ROW EXECUTE FUNCTION identity.guard_enrollment();

-- Image writes make a real parent-row version even when no scalar value changes.
-- That serializes counts and forces conflicting repeatable-read writers to fail
-- rather than both deleting the final images from an old snapshot.
CREATE FUNCTION listings.guard_image() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    item listings.sale_listings%ROWTYPE;
    upload listings.image_uploads%ROWTYPE;
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE listings.sale_listings SET revision = revision WHERE id = OLD.listing_id;
        RETURN OLD;
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id
        OR NEW.listing_id IS DISTINCT FROM OLD.listing_id
        OR NEW.upload_id IS DISTINCT FROM OLD.upload_id
        OR NEW.object_key IS DISTINCT FROM OLD.object_key
        OR (OLD.retired_at IS NOT NULL AND NEW.retired_at IS DISTINCT FROM OLD.retired_at)) THEN
        RAISE EXCEPTION 'An image cannot be rebound or unretired' USING ERRCODE = '23514';
    END IF;
    UPDATE listings.sale_listings SET revision = revision WHERE id = NEW.listing_id RETURNING * INTO item;
    SELECT * INTO upload FROM listings.image_uploads WHERE id = NEW.upload_id FOR UPDATE;
    IF item.id IS NULL OR upload.id IS NULL OR upload.owner_id <> item.owner_id
        OR upload.state <> 'confirmed' OR upload.object_key <> NEW.object_key THEN
        RAISE EXCEPTION 'Image requires a matching confirmed owner upload' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' AND (item.retired_at IS NOT NULL OR upload.expires_at <= statement_timestamp()) THEN
        RAISE EXCEPTION 'Cannot attach an expired upload or retired listing image' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER image_binding BEFORE INSERT OR UPDATE OR DELETE ON listings.images
    FOR EACH ROW EXECUTE FUNCTION listings.guard_image();

CREATE FUNCTION listings.guard_upload() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.id IS DISTINCT FROM OLD.id OR NEW.owner_id IS DISTINCT FROM OLD.owner_id
        OR NEW.object_key IS DISTINCT FROM OLD.object_key
        OR NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.expires_at IS DISTINCT FROM OLD.expires_at THEN
        RAISE EXCEPTION 'Upload identity and original deadline are immutable' USING ERRCODE = '23514';
    END IF;
    IF EXISTS (SELECT 1 FROM listings.images WHERE upload_id = OLD.id)
        AND (NEW.state <> 'confirmed' OR NEW.confirmed_at IS DISTINCT FROM OLD.confirmed_at) THEN
        RAISE EXCEPTION 'An attached image upload must remain confirmed' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER upload_history BEFORE UPDATE ON listings.image_uploads
    FOR EACH ROW EXECUTE FUNCTION listings.guard_upload();

-- Deferred publication checks allow listing + image insertion and retirement in
-- one transaction without exposing an image-less live listing at commit.
CREATE FUNCTION listings.check_publication() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    target uuid;
    item listings.sale_listings%ROWTYPE;
    image_count bigint;
BEGIN
    IF TG_TABLE_NAME = 'sale_listings' THEN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSE
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.listing_id ELSE NEW.listing_id END;
    END IF;
    SELECT * INTO item FROM listings.sale_listings WHERE id = target;
    IF NOT FOUND THEN RETURN NULL; END IF;
    SELECT count(*) INTO image_count FROM listings.images WHERE listing_id = target AND retired_at IS NULL;
    IF (item.retired_at IS NULL AND image_count NOT BETWEEN 1 AND 8)
        OR (item.retired_at IS NOT NULL AND image_count <> 0) THEN
        RAISE EXCEPTION 'Live listings need one to eight usable images; retired listings need none' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER listing_publication AFTER INSERT OR UPDATE ON listings.sale_listings
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION listings.check_publication();
CREATE CONSTRAINT TRIGGER image_publication AFTER INSERT OR UPDATE OR DELETE ON listings.images
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION listings.check_publication();

-- Origin locks precede thread locks. Continuous eligibility is preserved across
-- edits that remain unavailable, reset on restored eligibility, and backfilled
-- to an elapsed end instant rather than the later cleanup execution time.
CREATE FUNCTION listings.guard_origin() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    anchor timestamptz;
    moment timestamptz := statement_timestamp();
    target uuid;
BEGIN
    IF TG_OP = 'INSERT' AND NEW.retired_at IS NOT NULL THEN
        RAISE EXCEPTION 'New origins must contain live required fields' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.id IS DISTINCT FROM OLD.id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        -- Generated search_vector is not populated yet in a BEFORE trigger;
        -- exclude it when permitting a value-preserving retirement lock write.
        OR (OLD.retired_at IS NOT NULL AND (to_jsonb(NEW) - 'search_vector')
            IS DISTINCT FROM (to_jsonb(OLD) - 'search_vector'))) THEN
        RAISE EXCEPTION 'Origin identity or retired content cannot be rewritten' USING ERRCODE = '23514';
    END IF;
    target := NEW.id;
    IF TG_TABLE_NAME = 'sale_listings' THEN
        IF TG_OP = 'INSERT' AND NOT EXISTS (SELECT 1 FROM identity.users
            WHERE id = NEW.owner_id AND account_class = 'regular' AND status = 'active') THEN
            RAISE EXCEPTION 'New listings require an active regular owner' USING ERRCODE = '23514';
        END IF;
        IF TG_OP = 'UPDATE' AND NEW.owner_id IS DISTINCT FROM OLD.owner_id THEN
            RAISE EXCEPTION 'Listing owner is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.selected_buyer_id IS NOT NULL AND (TG_OP = 'INSERT'
            OR NEW.selected_buyer_id IS DISTINCT FROM OLD.selected_buyer_id) THEN
            IF NEW.retired_at IS NOT NULL OR NEW.availability <> 'available'
                OR NEW.available_from > moment OR NEW.available_until <= moment
                OR NOT EXISTS (SELECT 1 FROM conversations.threads WHERE listing_id = NEW.id
                    AND initiator_id = NEW.selected_buyer_id AND counterparty_id = NEW.owner_id) THEN
                RAISE EXCEPTION 'Selection requires an available listing and its conversation buyer' USING ERRCODE = '23514';
            END IF;
        END IF;
        IF TG_OP = 'UPDATE' THEN
            anchor := OLD.retirement_eligible_since;
            IF anchor IS NULL AND OLD.available_until <= moment THEN
                anchor := greatest(OLD.available_until, OLD.created_at);
            END IF;
        END IF;
        IF NEW.availability = 'unavailable' OR NEW.available_until <= moment THEN
            NEW.retirement_eligible_since := coalesce(anchor,
                CASE WHEN NEW.available_until <= moment
                    THEN greatest(NEW.available_until, NEW.created_at) ELSE moment END);
        ELSE
            NEW.retirement_eligible_since := NULL;
        END IF;
        anchor := NEW.retirement_eligible_since;
    ELSE
        IF TG_OP = 'UPDATE' AND NEW.author_id IS DISTINCT FROM OLD.author_id THEN
            RAISE EXCEPTION 'Wanted Request author is immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.status = 'open' THEN
            NEW.closed_at := NULL;
        ELSIF TG_OP = 'INSERT' THEN
            NEW.closed_at := coalesce(NEW.closed_at, NEW.created_at);
        ELSIF OLD.status = 'open' THEN
            NEW.closed_at := moment;
        ELSE
            NEW.closed_at := OLD.closed_at;
        END IF;
        anchor := NEW.closed_at;
    END IF;
    IF TG_OP = 'UPDATE' AND OLD.retired_at IS NULL AND NEW.retired_at IS NOT NULL THEN
        IF NEW.retired_at > moment OR anchor IS NULL OR anchor > moment - INTERVAL '4320 hours' THEN
            RAISE EXCEPTION 'Origin retirement requires 180 continuously inactive days' USING ERRCODE = '23514';
        END IF;
        -- Participant writes acquire the same origin lock before their thread.
        PERFORM 1 FROM conversations.threads
            WHERE (TG_TABLE_NAME = 'sale_listings' AND listing_id = target)
                OR (TG_TABLE_NAME = 'wanted_requests' AND wanted_request_id = target)
            ORDER BY id FOR UPDATE;
        IF EXISTS (SELECT 1 FROM conversations.threads
            WHERE ((TG_TABLE_NAME = 'sale_listings' AND listing_id = target)
                OR (TG_TABLE_NAME = 'wanted_requests' AND wanted_request_id = target))
            AND last_activity_at > moment - INTERVAL '2160 hours') THEN
            RAISE EXCEPTION 'Origin retirement requires 90 days without participant writes' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER listing_lifecycle BEFORE INSERT OR UPDATE ON listings.sale_listings
    FOR EACH ROW EXECUTE FUNCTION listings.guard_origin();
CREATE TRIGGER wanted_lifecycle BEFORE INSERT OR UPDATE ON search.wanted_requests
    FOR EACH ROW EXECUTE FUNCTION listings.guard_origin();

-- Bind fixed participants to the authoritative origin at insertion. Table-level
-- integrity may read FKs; runtime consumers still use public domain contracts.
CREATE FUNCTION conversations.guard_thread() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    owner uuid;
    unavailable boolean;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.id IS DISTINCT FROM OLD.id OR NEW.listing_id IS DISTINCT FROM OLD.listing_id
            OR NEW.wanted_request_id IS DISTINCT FROM OLD.wanted_request_id
            OR NEW.initiator_id IS DISTINCT FROM OLD.initiator_id
            OR NEW.counterparty_id IS DISTINCT FROM OLD.counterparty_id
            OR NEW.created_at IS DISTINCT FROM OLD.created_at
            OR NEW.next_sequence < OLD.next_sequence OR NEW.last_activity_at < OLD.last_activity_at THEN
            RAISE EXCEPTION 'Thread identity and ordering cannot be rewritten' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.listing_id IS NOT NULL THEN
        UPDATE listings.sale_listings SET revision = revision WHERE id = NEW.listing_id
            RETURNING owner_id, retired_at IS NOT NULL INTO owner, unavailable;
    ELSE
        UPDATE search.wanted_requests SET revision = revision WHERE id = NEW.wanted_request_id
            RETURNING author_id, retired_at IS NOT NULL OR status <> 'open' INTO owner, unavailable;
        IF NOT EXISTS (SELECT 1 FROM identity.users WHERE id = NEW.initiator_id AND account_class = 'regular') THEN
            RAISE EXCEPTION 'Wanted Request responders must be regular accounts' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF owner IS NULL OR unavailable OR owner <> NEW.counterparty_id THEN
        RAISE EXCEPTION 'Thread participants must match an eligible origin' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER thread_binding BEFORE INSERT OR UPDATE ON conversations.threads
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_thread();

-- Members and entry insertion serialize on an actual thread row version.
-- Sequence allocation is server-side; immutable entries become content-free
-- markers on retention, rather than losing replay/ordering uniqueness.
CREATE FUNCTION conversations.guard_member() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
    first_unread bigint;
    episode_time timestamptz;
BEGIN
    IF TG_OP = 'DELETE' THEN
        UPDATE conversations.threads SET next_sequence = next_sequence WHERE id = OLD.conversation_id;
        RETURN OLD;
    END IF;
    IF TG_OP = 'UPDATE' AND (NEW.conversation_id IS DISTINCT FROM OLD.conversation_id
        OR NEW.user_id IS DISTINCT FROM OLD.user_id OR NEW.joined_at IS DISTINCT FROM OLD.joined_at
        OR NEW.last_read_sequence < OLD.last_read_sequence) THEN
        RAISE EXCEPTION 'Membership identity and read watermarks are monotonic' USING ERRCODE = '23514';
    END IF;
    UPDATE conversations.threads SET next_sequence = next_sequence
        WHERE id = NEW.conversation_id RETURNING * INTO thread;
    IF thread.id IS NULL OR NEW.user_id NOT IN (thread.initiator_id, thread.counterparty_id) THEN
        RAISE EXCEPTION 'Only the two origin participants can be members' USING ERRCODE = '23514';
    END IF;
    SELECT min(sequence) INTO first_unread FROM conversations.entries
        WHERE conversation_id = NEW.conversation_id AND sender_id <> NEW.user_id
            AND kind = 'message' AND sequence > NEW.last_read_sequence;
    IF first_unread IS NULL THEN
        NEW.reminder_episode_start_sequence := NULL;
        NEW.reminder_sent_at := NULL;
    ELSIF TG_OP = 'UPDATE' AND OLD.reminder_episode_start_sequence IS NOT NULL THEN
        IF NEW.reminder_episode_start_sequence IS DISTINCT FROM OLD.reminder_episode_start_sequence
            OR (OLD.reminder_sent_at IS NOT NULL AND NEW.reminder_sent_at IS DISTINCT FROM OLD.reminder_sent_at) THEN
            RAISE EXCEPTION 'An unread episode cannot restart before read catch-up' USING ERRCODE = '23514';
        END IF;
    ELSE
        NEW.reminder_episode_start_sequence := first_unread;
        NEW.reminder_sent_at := NULL;
    END IF;
    IF NEW.reminder_sent_at IS NOT NULL THEN
        SELECT created_at INTO episode_time FROM conversations.entries
            WHERE conversation_id = NEW.conversation_id AND sequence = NEW.reminder_episode_start_sequence;
        IF NEW.reminder_sent_at < episode_time + INTERVAL '15 minutes' THEN
            RAISE EXCEPTION 'A reminder cannot be marked sent before its due time' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER member_binding BEFORE INSERT OR UPDATE OR DELETE ON conversations.members
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_member();

CREATE FUNCTION conversations.guard_entry() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
    assigned bigint;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Preserve entry markers; purge retained content instead' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.conversation_id, NEW.sequence, NEW.sender_id, NEW.client_operation_id, NEW.kind, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.conversation_id, OLD.sequence, OLD.sender_id,
                OLD.client_operation_id, OLD.kind, OLD.created_at)
            OR (OLD.content_deleted_at IS NOT NULL AND NEW.content_deleted_at IS DISTINCT FROM OLD.content_deleted_at) THEN
            RAISE EXCEPTION 'Entry routing, operation identity and deletion are immutable' USING ERRCODE = '23514';
        END IF;
        RETURN NEW;
    END IF;
    SELECT * INTO thread FROM conversations.threads WHERE id = NEW.conversation_id;
    IF thread.listing_id IS NOT NULL THEN
        UPDATE listings.sale_listings SET revision = revision WHERE id = thread.listing_id;
    ELSE
        UPDATE search.wanted_requests SET revision = revision WHERE id = thread.wanted_request_id;
    END IF;
    UPDATE conversations.threads SET next_sequence = next_sequence + 1,
        last_activity_at = greatest(last_activity_at, NEW.created_at)
        WHERE id = NEW.conversation_id RETURNING next_sequence - 1 INTO assigned;
    IF assigned IS NULL OR (NEW.sequence IS NOT NULL AND NEW.sequence <> assigned)
        OR NEW.content_deleted_at IS NOT NULL THEN
        RAISE EXCEPTION 'New entries require the next server sequence and live content' USING ERRCODE = '23514';
    END IF;
    NEW.sequence := assigned;
    RETURN NEW;
END;
$$;
CREATE TRIGGER entry_order BEFORE INSERT OR UPDATE OR DELETE ON conversations.entries
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_entry();

-- Initialize/coalesce unread episode state only after the actual message row
-- exists. Read acknowledgements clear it in guard_member on real catch-up.
CREATE FUNCTION conversations.register_unread() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.kind = 'message' THEN
        UPDATE conversations.members SET reminder_episode_start_sequence =
            coalesce(reminder_episode_start_sequence, NEW.sequence)
            WHERE conversation_id = NEW.conversation_id AND user_id <> NEW.sender_id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE TRIGGER message_unread AFTER INSERT ON conversations.entries
    FOR EACH ROW EXECUTE FUNCTION conversations.register_unread();

-- Deferred membership/sequence checks permit atomic creation of both members
-- and a first message, but reject third participants, nonexistent read targets
-- or hand-edited sequence counters at commit.
CREATE FUNCTION conversations.check_thread() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    target uuid;
    thread conversations.threads%ROWTYPE;
    maximum bigint;
BEGIN
    IF TG_TABLE_NAME = 'threads' THEN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSE
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.conversation_id ELSE NEW.conversation_id END;
    END IF;
    SELECT * INTO thread FROM conversations.threads WHERE id = target;
    IF NOT FOUND THEN RETURN NULL; END IF;
    SELECT coalesce(max(sequence), 0) INTO maximum FROM conversations.entries WHERE conversation_id = target;
    IF (SELECT count(*) FROM conversations.members WHERE conversation_id = target) <> 2
        OR thread.next_sequence <> maximum + 1 THEN
        RAISE EXCEPTION 'A thread requires two fixed members and a consistent sequence head' USING ERRCODE = '23514';
    END IF;
    IF EXISTS (SELECT 1 FROM conversations.members member WHERE member.conversation_id = target AND (
        member.user_id NOT IN (thread.initiator_id, thread.counterparty_id)
        OR member.last_read_sequence > maximum
        OR (member.reminder_episode_start_sequence IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM conversations.entries entry WHERE entry.conversation_id = target
                AND entry.sequence = member.reminder_episode_start_sequence
                AND entry.kind = 'message' AND entry.sender_id <> member.user_id)))) THEN
        RAISE EXCEPTION 'Read and reminder targets must belong to the member thread' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER thread_complete AFTER INSERT OR UPDATE ON conversations.threads
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_thread();
CREATE CONSTRAINT TRIGGER members_complete AFTER INSERT OR UPDATE OR DELETE ON conversations.members
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_thread();
CREATE CONSTRAINT TRIGGER entry_head AFTER INSERT OR UPDATE ON conversations.entries
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_thread();

-- Public bundles cannot be rebound after referenced. Retirement retains old
-- public material, never a private key or a server decryption/recovery route.
CREATE FUNCTION conversations.guard_key() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF ROW(NEW.id, NEW.user_id, NEW.version, NEW.public_key_material, NEW.protocol_id, NEW.created_at)
        IS DISTINCT FROM ROW(OLD.id, OLD.user_id, OLD.version, OLD.public_key_material, OLD.protocol_id, OLD.created_at)
        OR (OLD.retired_at IS NOT NULL AND NEW.retired_at IS DISTINCT FROM OLD.retired_at) THEN
        RAISE EXCEPTION 'Referenced public-key versions are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER key_history BEFORE UPDATE ON conversations.public_key_versions
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_key();

CREATE FUNCTION conversations.guard_payload() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    sender_key conversations.public_key_versions%ROWTYPE;
    recipient_key conversations.public_key_versions%ROWTYPE;
    other_user uuid;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Encrypted envelopes are immutable; append a new entry' USING ERRCODE = '23514';
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads WHERE id = entry.conversation_id;
    SELECT * INTO sender_key FROM conversations.public_key_versions WHERE id = NEW.sender_key_version_id;
    SELECT * INTO recipient_key FROM conversations.public_key_versions WHERE id = NEW.recipient_key_version_id;
    other_user := CASE WHEN entry.sender_id = thread.initiator_id THEN thread.counterparty_id ELSE thread.initiator_id END;
    IF entry.id IS NULL OR entry.content_deleted_at IS NOT NULL OR sender_key.id IS NULL OR recipient_key.id IS NULL
        OR sender_key.user_id <> entry.sender_id OR recipient_key.user_id <> other_user
        OR sender_key.protocol_id <> NEW.protocol_id OR recipient_key.protocol_id <> NEW.protocol_id THEN
        RAISE EXCEPTION 'Envelope key owners and protocol must match the entry participants' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER payload_binding BEFORE INSERT OR UPDATE ON conversations.encrypted_payloads
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_payload();

-- Offers keep a minimal lifetime pair/counter when privacy cleanup removes
-- history. Updates must advance by the next revision or explicitly clear
-- history; the deferred check validates the final matching revision set.
CREATE FUNCTION conversations.guard_offer() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
BEGIN
    SELECT * INTO thread FROM conversations.threads WHERE id = NEW.conversation_id;
    IF thread.listing_id IS NULL OR thread.initiator_id <> NEW.buyer_id THEN
        RAISE EXCEPTION 'Structured offers require the listing conversation buyer' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.conversation_id, NEW.buyer_id, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.conversation_id, OLD.buyer_id, OLD.created_at)
            OR NEW.next_revision < OLD.next_revision THEN
            RAISE EXCEPTION 'Logical offer identity and revision counter are immutable' USING ERRCODE = '23514';
        END IF;
        IF NEW.current_revision IS DISTINCT FROM OLD.current_revision AND NEW.current_revision IS NOT NULL
            AND (NEW.current_revision <> OLD.next_revision OR NEW.next_revision <> OLD.next_revision + 1) THEN
            RAISE EXCEPTION 'Offer changes must append the next revision' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER offer_identity BEFORE INSERT OR UPDATE ON conversations.offers
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_offer();

CREATE FUNCTION conversations.guard_offer_revision() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    offer conversations.offers%ROWTYPE;
    entry conversations.entries%ROWTYPE;
    thread conversations.threads%ROWTYPE;
    item listings.sale_listings%ROWTYPE;
    previous conversations.offer_revisions%ROWTYPE;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Offer revisions are append-only' USING ERRCODE = '23514';
    END IF;
    UPDATE conversations.offers SET next_revision = next_revision WHERE id = NEW.offer_id RETURNING * INTO offer;
    SELECT * INTO entry FROM conversations.entries WHERE id = NEW.entry_id;
    SELECT * INTO thread FROM conversations.threads WHERE id = offer.conversation_id;
    SELECT * INTO item FROM listings.sale_listings WHERE id = thread.listing_id FOR UPDATE;
    IF offer.id IS NULL OR entry.id IS NULL OR entry.kind <> 'offer'
        OR entry.content_deleted_at IS NOT NULL OR entry.conversation_id <> offer.conversation_id
        OR entry.sender_id <> offer.buyer_id OR NEW.revision IS DISTINCT FROM offer.current_revision
        OR NEW.revision <> offer.next_revision - 1 OR item.retired_at IS NOT NULL THEN
        RAISE EXCEPTION 'Offer revision must match its current buyer entry and live origin' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = 'submitted' AND (item.availability <> 'available'
        OR item.available_from > statement_timestamp()
        OR item.available_until <= statement_timestamp()) THEN
        RAISE EXCEPTION 'New or revised offers require current listing availability' USING ERRCODE = '23514';
    END IF;
    IF NEW.status = 'withdrawn' THEN
        SELECT * INTO previous FROM conversations.offer_revisions WHERE offer_id = NEW.offer_id
            ORDER BY revision DESC LIMIT 1;
        IF previous.status IS DISTINCT FROM 'submitted' OR previous.amount_paise <> NEW.amount_paise THEN
            RAISE EXCEPTION 'Withdrawal must follow a submitted revision and retain its amount' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER offer_revision_binding BEFORE INSERT OR UPDATE ON conversations.offer_revisions
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_offer_revision();

CREATE FUNCTION conversations.check_offer() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    target uuid;
    offer conversations.offers%ROWTYPE;
    maximum bigint;
BEGIN
    IF TG_TABLE_NAME = 'offers' THEN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSE
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.offer_id ELSE NEW.offer_id END;
    END IF;
    SELECT * INTO offer FROM conversations.offers WHERE id = target;
    IF NOT FOUND THEN RETURN NULL; END IF;
    SELECT max(revision) INTO maximum FROM conversations.offer_revisions WHERE offer_id = target;
    IF (offer.history_deleted_at IS NOT NULL AND maximum IS NOT NULL)
        OR (offer.history_deleted_at IS NULL AND (maximum IS NULL OR maximum <> offer.current_revision
            OR offer.next_revision <> maximum + 1)) THEN
        RAISE EXCEPTION 'Offer history and its current pointer must agree' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER offer_complete AFTER INSERT OR UPDATE ON conversations.offers
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_offer();
CREATE CONSTRAINT TRIGGER revisions_complete AFTER INSERT OR DELETE ON conversations.offer_revisions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_offer();

-- Validate the final entry subtype graph, including the deliberate retention
-- exception. An orphan payload/link or a hidden payload after deletion fails.
CREATE FUNCTION conversations.check_entry_content() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    target uuid;
    entry conversations.entries%ROWTYPE;
    payload boolean;
    share boolean;
    offer_revision boolean;
BEGIN
    IF TG_TABLE_NAME = 'entries' THEN
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSE
        target := CASE WHEN TG_OP = 'DELETE' THEN OLD.entry_id ELSE NEW.entry_id END;
    END IF;
    SELECT * INTO entry FROM conversations.entries WHERE id = target;
    IF NOT FOUND THEN RETURN NULL; END IF;
    payload := EXISTS (SELECT 1 FROM conversations.encrypted_payloads WHERE entry_id = target);
    share := EXISTS (SELECT 1 FROM conversations.contact_shares WHERE entry_id = target);
    offer_revision := EXISTS (SELECT 1 FROM conversations.offer_revisions WHERE entry_id = target);
    IF (entry.content_deleted_at IS NOT NULL AND (payload OR share OR offer_revision))
        OR (entry.content_deleted_at IS NULL AND (
            (entry.kind = 'message' AND (NOT payload OR share OR offer_revision))
            OR (entry.kind = 'contact_share' AND (NOT payload OR NOT share OR offer_revision))
            OR (entry.kind = 'offer' AND (NOT offer_revision OR share)))) THEN
        RAISE EXCEPTION 'Entry kind, retained payload and subtype references must agree' USING ERRCODE = '23514';
    END IF;
    RETURN NULL;
END;
$$;
CREATE CONSTRAINT TRIGGER entry_content AFTER INSERT OR UPDATE ON conversations.entries
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_entry_content();
CREATE CONSTRAINT TRIGGER payload_content AFTER INSERT OR UPDATE OR DELETE ON conversations.encrypted_payloads
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_entry_content();
CREATE CONSTRAINT TRIGGER share_content AFTER INSERT OR UPDATE OR DELETE ON conversations.contact_shares
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_entry_content();
CREATE CONSTRAINT TRIGGER revision_content AFTER INSERT OR UPDATE OR DELETE ON conversations.offer_revisions
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION conversations.check_entry_content();

-- Lifetime origin/thread/offer guards are retired in place, not physically
-- deleted and recreated. A contact-share link has no editable scalar fields;
-- rebinding its PK would otherwise evade validation of the old entry subtype.
CREATE FUNCTION conversations.reject_reference_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Preserve immutable references; use the documented retirement path' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER share_identity BEFORE UPDATE ON conversations.contact_shares
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();
CREATE TRIGGER thread_reference BEFORE DELETE ON conversations.threads
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();
CREATE TRIGGER offer_reference BEFORE DELETE ON conversations.offers
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();
CREATE TRIGGER listing_reference BEFORE DELETE ON listings.sale_listings
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();
CREATE TRIGGER request_reference BEFORE DELETE ON search.wanted_requests
    FOR EACH ROW EXECUTE FUNCTION conversations.reject_reference_change();

-- Immutable source-derived due times and keys prevent replay from resetting
-- a job's 24-hour window after terminal-record retention has elapsed. Dispatch,
-- recipient eligibility, lease fencing and provider effects remain CN-03 work.
CREATE FUNCTION conversations.guard_notification() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    thread conversations.threads%ROWTYPE;
    member conversations.members%ROWTYPE;
    first_message conversations.entries%ROWTYPE;
    target_message conversations.entries%ROWTYPE;
    trigger_entry conversations.entries%ROWTYPE;
    original_due timestamptz;
    expected_key text;
BEGIN
    SELECT * INTO thread FROM conversations.threads WHERE id = NEW.conversation_id;
    SELECT * INTO member FROM conversations.members WHERE conversation_id = NEW.conversation_id AND user_id = NEW.recipient_id;
    IF thread.id IS NULL OR member.user_id IS NULL THEN
        RAISE EXCEPTION 'Notification recipient must be a thread member' USING ERRCODE = '23514';
    END IF;
    IF NEW.trigger_entry_id IS NOT NULL THEN
        SELECT * INTO trigger_entry FROM conversations.entries WHERE id = NEW.trigger_entry_id;
        IF trigger_entry.id IS NULL OR trigger_entry.conversation_id <> thread.id THEN
            RAISE EXCEPTION 'Notification trigger must belong to its thread' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF NEW.event_kind = 'new_conversation' THEN
        IF NEW.recipient_id <> thread.counterparty_id THEN
            RAISE EXCEPTION 'New conversation email targets the other participant' USING ERRCODE = '23514';
        END IF;
        original_due := thread.created_at;
        expected_key := 'new_conversation:' || thread.id::text || ':' || NEW.recipient_id::text;
    ELSE
        SELECT * INTO first_message FROM conversations.entries WHERE conversation_id = thread.id
            AND sequence = NEW.unread_episode_start_sequence AND kind = 'message' AND sender_id <> NEW.recipient_id;
        SELECT * INTO target_message FROM conversations.entries WHERE conversation_id = thread.id
            AND sequence = NEW.unread_through_sequence AND kind = 'message' AND sender_id <> NEW.recipient_id;
        IF first_message.id IS NULL OR target_message.id IS NULL THEN
            RAISE EXCEPTION 'Reminder targets must be incoming messages in the same thread' USING ERRCODE = '23514';
        END IF;
        IF TG_OP = 'INSERT' AND (member.reminder_episode_start_sequence IS DISTINCT FROM NEW.unread_episode_start_sequence
            OR member.reminder_sent_at IS NOT NULL OR member.last_read_sequence >= NEW.unread_through_sequence) THEN
            RAISE EXCEPTION 'Reminder requires a current unreminded unread episode' USING ERRCODE = '23514';
        END IF;
        original_due := first_message.created_at + INTERVAL '15 minutes';
        expected_key := 'unread_reminder:' || thread.id::text || ':' || NEW.recipient_id::text
            || ':' || NEW.unread_episode_start_sequence::text;
    END IF;
    IF NEW.due_at IS DISTINCT FROM original_due OR NEW.expires_at IS DISTINCT FROM original_due + INTERVAL '24 hours'
        OR NEW.deduplication_key IS DISTINCT FROM expected_key THEN
        RAISE EXCEPTION 'Notification deadline and key must match their immutable source' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'INSERT' AND NEW.expires_at <= statement_timestamp() THEN
        RAISE EXCEPTION 'An expired notification cannot be recreated with a new delivery window' USING ERRCODE = '23514';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.conversation_id, NEW.recipient_id, NEW.event_kind, NEW.deduplication_key,
                NEW.due_at, NEW.expires_at, NEW.unread_episode_start_sequence, NEW.created_at)
            IS DISTINCT FROM ROW(OLD.id, OLD.conversation_id, OLD.recipient_id, OLD.event_kind,
                OLD.deduplication_key, OLD.due_at, OLD.expires_at, OLD.unread_episode_start_sequence, OLD.created_at)
            OR NEW.attempts < OLD.attempts
            OR NEW.unread_through_sequence < OLD.unread_through_sequence THEN
            RAISE EXCEPTION 'Notification source identity and counters cannot be reset' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF NEW.state = 'leased' AND (NEW.expires_at <= statement_timestamp() OR NEW.due_at > statement_timestamp()) THEN
        RAISE EXCEPTION 'Notification leasing requires its original eligible delivery window' USING ERRCODE = '23514';
    END IF;
    IF NEW.state = 'leased' AND NEW.event_kind = 'unread_reminder'
        AND (member.reminder_episode_start_sequence IS DISTINCT FROM NEW.unread_episode_start_sequence
            OR member.reminder_sent_at IS NOT NULL OR member.last_read_sequence >= NEW.unread_through_sequence) THEN
        RAISE EXCEPTION 'A read or already reminded episode cannot be leased' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER notification_source BEFORE INSERT OR UPDATE ON conversations.notification_intents
    FOR EACH ROW EXECUTE FUNCTION conversations.guard_notification();

-- migrate:down
SET LOCAL TIME ZONE 'UTC';
SET LOCAL lock_timeout = '10s';
SELECT pg_advisory_xact_lock(1129072976, 8);
-- Remove named triggers/functions only; never broadly cascade unrelated work.
DROP TRIGGER notification_source ON conversations.notification_intents;
DROP FUNCTION conversations.guard_notification();
DROP TRIGGER request_reference ON search.wanted_requests;
DROP TRIGGER listing_reference ON listings.sale_listings;
DROP TRIGGER offer_reference ON conversations.offers;
DROP TRIGGER thread_reference ON conversations.threads;
DROP TRIGGER share_identity ON conversations.contact_shares;
DROP FUNCTION conversations.reject_reference_change();
DROP TRIGGER revision_content ON conversations.offer_revisions;
DROP TRIGGER share_content ON conversations.contact_shares;
DROP TRIGGER payload_content ON conversations.encrypted_payloads;
DROP TRIGGER entry_content ON conversations.entries;
DROP FUNCTION conversations.check_entry_content();
DROP TRIGGER revisions_complete ON conversations.offer_revisions;
DROP TRIGGER offer_complete ON conversations.offers;
DROP FUNCTION conversations.check_offer();
DROP TRIGGER offer_revision_binding ON conversations.offer_revisions;
DROP FUNCTION conversations.guard_offer_revision();
DROP TRIGGER offer_identity ON conversations.offers;
DROP FUNCTION conversations.guard_offer();
DROP TRIGGER payload_binding ON conversations.encrypted_payloads;
DROP FUNCTION conversations.guard_payload();
DROP TRIGGER key_history ON conversations.public_key_versions;
DROP FUNCTION conversations.guard_key();
DROP TRIGGER entry_head ON conversations.entries;
DROP TRIGGER members_complete ON conversations.members;
DROP TRIGGER thread_complete ON conversations.threads;
DROP FUNCTION conversations.check_thread();
DROP TRIGGER entry_order ON conversations.entries;
DROP FUNCTION conversations.guard_entry();
DROP TRIGGER message_unread ON conversations.entries;
DROP FUNCTION conversations.register_unread();
DROP TRIGGER member_binding ON conversations.members;
DROP FUNCTION conversations.guard_member();
DROP TRIGGER thread_binding ON conversations.threads;
DROP FUNCTION conversations.guard_thread();
DROP TRIGGER wanted_lifecycle ON search.wanted_requests;
DROP TRIGGER listing_lifecycle ON listings.sale_listings;
DROP FUNCTION listings.guard_origin();
DROP TRIGGER image_publication ON listings.images;
DROP TRIGGER listing_publication ON listings.sale_listings;
DROP FUNCTION listings.check_publication();
DROP TRIGGER upload_history ON listings.image_uploads;
DROP FUNCTION listings.guard_upload();
DROP TRIGGER image_binding ON listings.images;
DROP FUNCTION listings.guard_image();
DROP TRIGGER enrollment_history ON identity.temporary_enrollments;
DROP FUNCTION identity.guard_enrollment();
DROP TRIGGER credentials_owner ON identity.temporary_credentials;
DROP FUNCTION identity.guard_local_credential();
DROP TRIGGER users_history ON identity.users;
DROP FUNCTION identity.guard_user_history();
