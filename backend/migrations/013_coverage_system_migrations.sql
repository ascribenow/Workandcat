-- Coverage System Database Migrations for Twelvr
-- Implementation Plan: Day 1 - Database Schema Changes

-- 1. Add anchors to questions table
ALTER TABLE questions ADD COLUMN IF NOT EXISTS anchors JSONB NOT NULL DEFAULT '[]';

-- 2. Add anchors snapshots to attempt_events table  
ALTER TABLE attempt_events ADD COLUMN IF NOT EXISTS anchors JSONB NOT NULL DEFAULT '[]';

-- 3. Add ALL required session_pack_plan columns for coverage system
ALTER TABLE session_pack_plan 
  ADD COLUMN IF NOT EXISTS pack_json JSONB NOT NULL DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS status_new TEXT NOT NULL DEFAULT 'planned',
  ADD COLUMN IF NOT EXISTS served_at_new TIMESTAMP NULL,
  ADD COLUMN IF NOT EXISTS coverage_audit JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS selection_method VARCHAR(32) NOT NULL DEFAULT 'coverage_v1';

-- Handle potential conflict with existing 'status' column by using status_new temporarily
-- Check if we need to migrate existing status column
DO $$
BEGIN
    -- If status column exists and is different type, handle migration
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'session_pack_plan' AND column_name = 'status' AND data_type != 'text') THEN
        -- Copy existing status data to new column if it exists
        UPDATE session_pack_plan SET status_new = COALESCE(status::text, 'planned');
        -- Drop old status column and rename new one
        ALTER TABLE session_pack_plan DROP COLUMN IF EXISTS status;
        ALTER TABLE session_pack_plan RENAME COLUMN status_new TO status;
    ELSE
        -- If status column doesn't exist or is already text type, just rename
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'session_pack_plan' AND column_name = 'status_new') THEN
            ALTER TABLE session_pack_plan DROP COLUMN IF EXISTS status;
            ALTER TABLE session_pack_plan RENAME COLUMN status_new TO status;
        END IF;
    END IF;
END $$;

-- Handle served_at column similarly
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'session_pack_plan' AND column_name = 'served_at_new') THEN
        -- Update served_at_new with existing served_at if it exists
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'session_pack_plan' AND column_name = 'served_at') THEN
            UPDATE session_pack_plan SET served_at_new = served_at WHERE served_at IS NOT NULL;
            ALTER TABLE session_pack_plan DROP COLUMN served_at;
        END IF;
        ALTER TABLE session_pack_plan RENAME COLUMN served_at_new TO served_at;
    END IF;
END $$;

-- 4. Add unique constraint for session_id for upsert ON CONFLICT
ALTER TABLE session_pack_plan
  ADD CONSTRAINT IF NOT EXISTS session_pack_plan_session_id_key UNIQUE (session_id);

-- 5. Add composite index for user_id + session_id performance
CREATE INDEX IF NOT EXISTS idx_session_pack_plan_user_session 
  ON session_pack_plan(user_id, session_id);

-- 6. Create learner_notebook table (latest only)
CREATE TABLE IF NOT EXISTS learner_notebook (
  user_id VARCHAR(36) PRIMARY KEY,
  notebook_json JSONB NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 7. Create coverage_ledger for variety tiebreaker
CREATE TABLE IF NOT EXISTS coverage_ledger (
  user_id VARCHAR(36) NOT NULL,
  subcategory_type VARCHAR(200) NOT NULL,  -- "subcategory|type_of_question"
  served_count INTEGER NOT NULL DEFAULT 0,
  last_served_at TIMESTAMP,
  PRIMARY KEY (user_id, subcategory_type)
);

-- 8. Add performance indexes
CREATE INDEX IF NOT EXISTS idx_coverage_ledger_user ON coverage_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_learner_notebook_updated ON learner_notebook(updated_at);

-- 9. Add eligibility scan performance index
CREATE INDEX IF NOT EXISTS ix_questions_eligible_band 
  ON questions (quality_verified, is_active, difficulty_band);

-- 10. Normalize existing data to consistent lowercase
UPDATE questions SET difficulty_band = LOWER(difficulty_band) WHERE difficulty_band IS NOT NULL;

-- 11. Lock casing forever with comprehensive CHECK constraint
-- First, make sure all difficulty_band values are valid
UPDATE questions SET difficulty_band = 'medium' WHERE difficulty_band IS NULL;

-- Make difficulty_band NOT NULL after backfilling for null safety
ALTER TABLE questions ALTER COLUMN difficulty_band SET NOT NULL;

-- Add CHECK constraint to lock casing
ALTER TABLE questions
  ADD CONSTRAINT IF NOT EXISTS questions_difficulty_band_chk
  CHECK (difficulty_band IN ('easy','medium','hard'));

-- 12. Add indexes for attempt_events performance (if not already exist)
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_session ON attempt_events(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_sess_seq ON attempt_events(user_id, sess_seq_at_serve);