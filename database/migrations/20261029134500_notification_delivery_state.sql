-- Durable retry reservation and replay-safe worker result tracking.
-- migrate:up
ALTER TABLE conversations.notification_intents
    ADD COLUMN next_attempt_at timestamptz(6),
    ADD COLUMN dispatch_started_at timestamptz(6),
    ADD COLUMN last_result_token uuid,
    ADD COLUMN last_result_outcome text CHECK (last_result_outcome IN ('delivered','transient_failure','terminal_failure','ambiguous'));
CREATE INDEX notification_retry_due ON conversations.notification_intents (state, next_attempt_at, due_at);

-- migrate:down
DROP INDEX conversations.notification_retry_due;
ALTER TABLE conversations.notification_intents
    DROP COLUMN last_result_outcome, DROP COLUMN last_result_token,
    DROP COLUMN dispatch_started_at, DROP COLUMN next_attempt_at;
