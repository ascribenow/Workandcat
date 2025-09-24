-- =====================================================
-- Twelvr Blueprint Migration 015: Core Schema Creation
-- =====================================================
-- This migration creates the new blueprint architecture tables
-- Addresses Deviations #2, #4, #7, #8

-- Create backup of existing tables before migration
CREATE TABLE IF NOT EXISTS adaptive_packs_backup AS 
SELECT * FROM adaptive_packs WHERE 1=0; -- Structure only initially

CREATE TABLE IF NOT EXISTS sessions_backup AS 
SELECT * FROM sessions WHERE 1=0; -- Structure only initially

-- =====================================================
-- 1. PACK-LEVEL METADATA TABLE (Deviation #7 - Single constraint report per pack)
-- =====================================================
CREATE TABLE session_packs (
    session_id UUID PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    constraint_report JSONB NOT NULL DEFAULT '{}', -- Single pack-level report
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    INDEX idx_session_packs_user (user_id),
    INDEX idx_session_packs_created (created_at)
);

-- =====================================================
-- 2. QUESTION POSITIONS TABLE (Deviation #2 - 1-based positions)
-- =====================================================
CREATE TABLE session_pack_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_packs(session_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 12), -- 1-based positions
    question_id UUID NOT NULL,
    question_data JSONB NOT NULL, -- Complete question with options, answers, explanations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Critical constraint: Each session must have unique positions 1-12
    UNIQUE(session_id, position),
    
    -- Indexes for performance
    INDEX idx_session_pack_questions_session (session_id),
    INDEX idx_session_pack_questions_position (session_id, position),
    INDEX idx_session_pack_questions_question (question_id)
);

-- =====================================================
-- 3. ANSWER TRACKING WITH IDEMPOTENCY (Deviation #4)
-- =====================================================
CREATE TABLE session_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 12), -- 1-based positions
    question_id UUID NOT NULL,
    user_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    explanation TEXT, -- Store explanation for quick access
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- CRITICAL: Prevents duplicate answers per position (Deviation #4)
    UNIQUE(session_id, position),
    
    -- Indexes for performance and analytics
    INDEX idx_session_answers_session (session_id),
    INDEX idx_session_answers_question (question_id),
    INDEX idx_session_answers_timestamp (timestamp),
    INDEX idx_session_answers_correctness (session_id, is_correct)
);

-- =====================================================
-- 4. ENHANCE SESSIONS TABLE (Deviation #2, #8)
-- =====================================================
-- Add new columns for position tracking and session lifecycle
ALTER TABLE sessions 
ADD COLUMN IF NOT EXISTS current_position INTEGER DEFAULT 0, -- 0-based internal tracking
ADD COLUMN IF NOT EXISTS served_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS abandoned_at TIMESTAMP WITH TIME ZONE;

-- Standardize status values (Deviation #8)
ALTER TABLE sessions 
DROP CONSTRAINT IF EXISTS sessions_status_check;

ALTER TABLE sessions 
ADD CONSTRAINT sessions_status_check 
CHECK (status IN ('planned', 'active', 'completed', 'abandoned'));

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_sessions_current_position ON sessions(current_position);
CREATE INDEX IF NOT EXISTS idx_sessions_served_at ON sessions(served_at);
CREATE INDEX IF NOT EXISTS idx_sessions_status_user ON sessions(user_id, status);

-- =====================================================
-- 5. ADVISORY LOCK SUPPORT TABLE
-- =====================================================
CREATE TABLE advisory_locks (
    lock_key TEXT PRIMARY KEY,
    user_id UUID NOT NULL,
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '10 minutes',
    
    -- Cleanup index for expired locks
    INDEX idx_advisory_locks_expires (expires_at)
);

-- =====================================================
-- 6. VALIDATION CONSTRAINTS & RULES
-- =====================================================

-- Ensure session packs have exactly 12 questions
CREATE OR REPLACE FUNCTION validate_session_pack_complete()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if session has exactly 12 questions after insert/update
    IF (SELECT COUNT(*) FROM session_pack_questions WHERE session_id = NEW.session_id) > 12 THEN
        RAISE EXCEPTION 'Session pack cannot have more than 12 questions';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_session_pack_complete
    AFTER INSERT OR UPDATE ON session_pack_questions
    FOR EACH ROW EXECUTE FUNCTION validate_session_pack_complete();

-- Ensure position sequence integrity (1-12 with no gaps when complete)
CREATE OR REPLACE FUNCTION validate_position_sequence()
RETURNS TRIGGER AS $$
BEGIN
    -- Only validate when we have 12 questions (complete pack)
    IF (SELECT COUNT(*) FROM session_pack_questions WHERE session_id = NEW.session_id) = 12 THEN
        -- Check that positions are exactly 1,2,3,...,12
        IF NOT EXISTS (
            SELECT 1 FROM generate_series(1, 12) AS pos(position)
            WHERE EXISTS (
                SELECT 1 FROM session_pack_questions 
                WHERE session_id = NEW.session_id AND position = pos.position
            )
            HAVING COUNT(*) = 12
        ) THEN
            RAISE EXCEPTION 'Session pack must have positions 1-12 with no gaps';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_position_sequence
    AFTER INSERT OR UPDATE ON session_pack_questions
    FOR EACH ROW EXECUTE FUNCTION validate_position_sequence();

-- =====================================================
-- 7. HELPER FUNCTIONS FOR BLUEPRINT OPERATIONS
-- =====================================================

-- Function to get next available session position
CREATE OR REPLACE FUNCTION get_next_position(p_session_id UUID)
RETURNS INTEGER AS $$
DECLARE
    next_pos INTEGER;
BEGIN
    SELECT COALESCE(MAX(position), 0) + 1 
    INTO next_pos
    FROM session_pack_questions 
    WHERE session_id = p_session_id;
    
    RETURN next_pos;
END;
$$ LANGUAGE plpgsql;

-- Function to check if session is ready (has 12 questions)
CREATE OR REPLACE FUNCTION is_session_ready(p_session_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (
        SELECT COUNT(*) = 12 
        FROM session_pack_questions 
        WHERE session_id = p_session_id
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get session completion percentage
CREATE OR REPLACE FUNCTION get_session_progress(p_session_id UUID)
RETURNS DECIMAL AS $$
DECLARE
    answered_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO answered_count
    FROM session_answers
    WHERE session_id = p_session_id;
    
    SELECT COUNT(*) INTO total_count
    FROM session_pack_questions
    WHERE session_id = p_session_id;
    
    IF total_count = 0 THEN
        RETURN 0;
    END IF;
    
    RETURN (answered_count::DECIMAL / total_count::DECIMAL) * 100;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 8. MIGRATION TRACKING
-- =====================================================
CREATE TABLE IF NOT EXISTS migration_log (
    id SERIAL PRIMARY KEY,
    migration_name TEXT NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- Record this migration
INSERT INTO migration_log (migration_name, notes) 
VALUES ('015_blueprint_schema', 'Created blueprint architecture tables with all deviation fixes');

-- =====================================================
-- 9. GRANT PERMISSIONS (Adjust as needed for your setup)
-- =====================================================
-- These grants assume your application user is 'twelvr_app'
-- Adjust according to your database user configuration

-- GRANT ALL PRIVILEGES ON session_packs TO twelvr_app;
-- GRANT ALL PRIVILEGES ON session_pack_questions TO twelvr_app;
-- GRANT ALL PRIVILEGES ON session_answers TO twelvr_app;
-- GRANT ALL PRIVILEGES ON advisory_locks TO twelvr_app;
-- GRANT ALL PRIVILEGES ON migration_log TO twelvr_app;

-- Grant sequence permissions if using SERIAL
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO twelvr_app;

COMMIT;