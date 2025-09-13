-- Migration: Create sessions table for session lifecycle management
-- Minimal session tracking with monotonic sess_seq per user

CREATE TABLE sessions (
    session_id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL,
    sess_seq INTEGER NOT NULL,                        -- Monotonic sequence per user (1, 2, 3...)
    
    -- Session lifecycle
    status VARCHAR(20) DEFAULT 'planned',             -- 'planned', 'served', 'completed', 'abandoned'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    served_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Session metadata
    total_questions INTEGER DEFAULT 12,
    questions_answered INTEGER DEFAULT 0,
    questions_correct INTEGER DEFAULT 0,
    questions_skipped INTEGER DEFAULT 0,
    
    -- Unique constraint: one sess_seq per user
    UNIQUE(user_id, sess_seq),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_user_sess_seq ON sessions(user_id, sess_seq);
CREATE INDEX idx_sessions_created_at ON sessions(created_at);