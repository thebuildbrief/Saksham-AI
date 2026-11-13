-- PostgreSQL migration for persisted profile, interview, resume and subscription data.
-- Every statement is additive and safe to rerun; no existing rows are deleted or rewritten.
CREATE TABLE IF NOT EXISTS user_profiles (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    data JSON NOT NULL DEFAULT '{}'::json,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles(user_id);

CREATE TABLE IF NOT EXISTS interview_contexts (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL UNIQUE REFERENCES interview_sessions(id) ON DELETE CASCADE,
    title VARCHAR(160) NOT NULL,
    role VARCHAR(120) NOT NULL,
    interview_type VARCHAR(40) NOT NULL DEFAULT 'behavioral',
    difficulty VARCHAR(20) NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interview_contexts_session_id ON interview_contexts(session_id);

CREATE TABLE IF NOT EXISTS interview_turns (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interview_turns_session_id ON interview_turns(session_id);
CREATE INDEX IF NOT EXISTS ix_interview_turns_created_at ON interview_turns(created_at);

CREATE TABLE IF NOT EXISTS interview_evaluations (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    total_score INTEGER NOT NULL,
    rubric JSON NOT NULL DEFAULT '{}'::json,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interview_evaluations_session_id ON interview_evaluations(session_id);
CREATE INDEX IF NOT EXISTS ix_interview_evaluations_user_id ON interview_evaluations(user_id);

CREATE TABLE IF NOT EXISTS resume_documents (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes INTEGER NOT NULL,
    object_key VARCHAR(512) NOT NULL UNIQUE,
    extracted_text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_resume_documents_user_id ON resume_documents(user_id);

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(40) NOT NULL DEFAULT 'free',
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    provider VARCHAR(40),
    provider_reference VARCHAR(255),
    current_period_end TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_user_subscriptions_user_id ON user_subscriptions(user_id);
