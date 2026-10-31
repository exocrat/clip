-- One Identity-owned account preference controls conversation emails only.
-- migrate:up
ALTER TABLE identity.users
    ADD COLUMN conversation_email_enabled boolean NOT NULL DEFAULT true;
ALTER TABLE conversations.notification_intents
    DROP CONSTRAINT notification_intents_last_result_outcome_check,
    ADD CONSTRAINT notification_intents_last_result_outcome_check CHECK (
        last_result_outcome IN ('delivered','transient_failure','terminal_failure','ambiguous','preference_suppressed')
    );

-- migrate:down
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM conversations.notification_intents WHERE last_result_outcome='preference_suppressed') THEN
        RAISE EXCEPTION 'Preference suppression records require reviewed rollback';
    END IF;
END $$;
ALTER TABLE conversations.notification_intents
    DROP CONSTRAINT notification_intents_last_result_outcome_check,
    ADD CONSTRAINT notification_intents_last_result_outcome_check CHECK (
        last_result_outcome IN ('delivered','transient_failure','terminal_failure','ambiguous')
    );
ALTER TABLE identity.users DROP COLUMN conversation_email_enabled;
