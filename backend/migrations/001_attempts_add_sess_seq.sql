-- Migration: Add sess_seq_at_serve column to attempt_events table
-- This tracks the sequence number of the session when the question was served

-- First check if attempt_events table exists, if not create it
CREATE TABLE IF NOT EXISTS attempt_events (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    question_id VARCHAR(36) NOT NULL,
    was_correct BOOLEAN,
    skipped BOOLEAN DEFAULT FALSE,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Snapshot fields at time of serve
    difficulty_band TEXT,
    subcategory TEXT,
    type_of_question TEXT,
    core_concepts JSONB,
    pyq_frequency_score NUMERIC(2,1),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- Add the new column
ALTER TABLE attempt_events 
ADD COLUMN IF NOT EXISTS sess_seq_at_serve INTEGER;

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_attempt_events_sess_seq 
ON attempt_events(sess_seq_at_serve);

-- Add composite index for user session queries
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_session 
ON attempt_events(user_id, session_id);