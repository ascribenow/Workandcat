-- Migration: Add foreign keys with zero-downtime strategy
-- Strategy: NOT VALID → VALIDATE → Enforced
-- This allows adding constraints without locking tables for existing data validation

BEGIN;

-- ==============================================================================
-- PHASE 1: Add constraints as NOT VALID (instant, no validation of existing data)
-- ==============================================================================

-- Foreign key: session_summary_final.session_id -> sessions.session_id
-- Note: This FK may already exist from previous migrations, so use IF NOT EXISTS logic
DO $$ 
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_session_summary_session' 
        AND conrelid = 'session_summary_final'::regclass
    ) THEN
        ALTER TABLE session_summary_final
        ADD CONSTRAINT fk_session_summary_session NOT VALID
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        ON DELETE CASCADE;
        
        RAISE NOTICE 'Added FK constraint: fk_session_summary_session';
    ELSE
        RAISE NOTICE 'FK constraint fk_session_summary_session already exists';
    END IF;
END $$;

-- Foreign key: concept_alias_map_latest.user_id -> users.id
-- Note: May already exist, so use IF NOT EXISTS logic
DO $$ 
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_concept_map_user' 
        AND conrelid = 'concept_alias_map_latest'::regclass
    ) THEN
        ALTER TABLE concept_alias_map_latest
        ADD CONSTRAINT fk_concept_map_user NOT VALID
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE;
        
        RAISE NOTICE 'Added FK constraint: fk_concept_map_user';
    ELSE
        RAISE NOTICE 'FK constraint fk_concept_map_user already exists';
    END IF;
END $$;

COMMIT;

-- ==============================================================================
-- PHASE 2: Validate constraints (can be run after Phase 1 commits)
-- ==============================================================================

-- Validate session_summary_final FK
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_session_summary_session' 
        AND conrelid = 'session_summary_final'::regclass
        AND convalidated = FALSE
    ) THEN
        ALTER TABLE session_summary_final VALIDATE CONSTRAINT fk_session_summary_session;
        RAISE NOTICE 'Validated FK constraint: fk_session_summary_session';
    ELSE
        RAISE NOTICE 'FK constraint fk_session_summary_session already validated';
    END IF;
END $$;

-- Validate concept_alias_map_latest FK
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'fk_concept_map_user' 
        AND conrelid = 'concept_alias_map_latest'::regclass
        AND convalidated = FALSE
    ) THEN
        ALTER TABLE concept_alias_map_latest VALIDATE CONSTRAINT fk_concept_map_user;
        RAISE NOTICE 'Validated FK constraint: fk_concept_map_user';
    ELSE
        RAISE NOTICE 'FK constraint fk_concept_map_user already validated';
    END IF;
END $$;

-- ==============================================================================
-- PHASE 3: Add performance indexes for FK lookups
-- ==============================================================================

-- Index for session_summary_final.session_id (if not exists)
CREATE INDEX IF NOT EXISTS idx_session_summary_final_session_id 
ON session_summary_final(session_id);

-- Index for concept_alias_map_latest.user_id (if not exists)
CREATE INDEX IF NOT EXISTS idx_concept_alias_map_user_id 
ON concept_alias_map_latest(user_id);

-- Comments for documentation
COMMENT ON CONSTRAINT fk_session_summary_session ON session_summary_final
IS 'Ensures session_id references valid session, added with zero-downtime strategy';

COMMENT ON CONSTRAINT fk_concept_map_user ON concept_alias_map_latest
IS 'Ensures user_id references valid user, added with zero-downtime strategy';
