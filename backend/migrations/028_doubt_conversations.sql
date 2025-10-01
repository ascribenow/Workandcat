-- Migration: Create doubt_conversations table for Ask Twelvr chat history
-- Purpose: Persist conversation history in database instead of in-memory storage

CREATE TABLE IF NOT EXISTS doubt_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    question_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for efficient querying
    CONSTRAINT fk_doubt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_doubt_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_doubt_conversations_user_question 
    ON doubt_conversations(user_id, question_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_doubt_conversations_timestamp 
    ON doubt_conversations(timestamp DESC);

-- Table to track message counts per user per question
CREATE TABLE IF NOT EXISTS doubt_message_counts (
    user_id UUID NOT NULL,
    question_id UUID NOT NULL,
    message_count INTEGER DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, question_id),
    CONSTRAINT fk_count_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_count_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

COMMENT ON TABLE doubt_conversations IS 'Stores Ask Twelvr conversation history with persistent storage';
COMMENT ON TABLE doubt_message_counts IS 'Tracks message counts per user per question with 10 message limit';
