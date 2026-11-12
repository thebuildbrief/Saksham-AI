-- Apply once to existing SQLite or PostgreSQL databases before deploying
-- application code that records authenticated submission ownership.
ALTER TABLE coding_submissions
    ADD COLUMN user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_coding_submissions_user_id
    ON coding_submissions (user_id);
