-- PostgreSQL migration: backfill/add authenticated submission ownership safely.
-- Existing submission rows remain and receive NULL user_id until ownership can be assigned.
ALTER TABLE coding_submissions ADD COLUMN IF NOT EXISTS user_id VARCHAR(36);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_coding_submissions_user_id_users'
          AND conrelid = 'coding_submissions'::regclass
    ) THEN
        ALTER TABLE coding_submissions
            ADD CONSTRAINT fk_coding_submissions_user_id_users
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS ix_coding_submissions_user_id ON coding_submissions(user_id);
