-- Idempotent PostgreSQL base schema for clean deployments.
-- Existing tables and rows are left untouched by CREATE TABLE IF NOT EXISTS.
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    full_name VARCHAR(200) NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

CREATE TABLE IF NOT EXISTS interview_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_interview_sessions_user_id ON interview_sessions(user_id);

CREATE TABLE IF NOT EXISTS coding_problems (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'Medium',
    category VARCHAR(100) DEFAULT 'Arrays & Hashing',
    description TEXT NOT NULL,
    constraints TEXT DEFAULT '[]',
    examples TEXT DEFAULT '[]',
    starter_code TEXT DEFAULT '{}',
    hints TEXT DEFAULT '[]',
    time_limit_sec INTEGER DEFAULT 2,
    memory_limit_mb INTEGER DEFAULT 256,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coding_test_cases (
    id VARCHAR(36) PRIMARY KEY,
    problem_id VARCHAR(50) NOT NULL REFERENCES coding_problems(id) ON DELETE CASCADE,
    input_data TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS coding_submissions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NULL REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(36) NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
    problem_id VARCHAR(50) NOT NULL REFERENCES coding_problems(id),
    language VARCHAR(30) DEFAULT 'python',
    code TEXT NOT NULL,
    status VARCHAR(30) DEFAULT 'Accepted',
    passed_tests INTEGER DEFAULT 0,
    total_tests INTEGER DEFAULT 0,
    execution_time_ms INTEGER DEFAULT 0,
    memory_kb INTEGER DEFAULT 0,
    output TEXT DEFAULT '',
    ai_complexity_feedback TEXT DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
