-- Migration: Create session progress tracking table
-- This table tracks user's progress within a session for resumption capability

CREATE TABLE IF NOT EXISTS session_progress_tracking (
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    current_question_index INTEGER NOT NULL DEFAULT 0,
    total_questions INTEGER NOT NULL DEFAULT 12,
    last_question_id VARCHAR(36),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (user_id, session_id),
    
    -- Foreign key constraints
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Indexes for performance
    INDEX idx_session_progress_user_session (user_id, session_id),
    INDEX idx_session_progress_updated (updated_at)
);

-- Add comment for documentation
COMMENT ON TABLE session_progress_tracking IS 'Tracks user progress within sessions for resumption capability. Cleaned up after session completion.';