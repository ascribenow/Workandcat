-- Migration: Add Foreign Key Constraint to Prevent Orphaned Questions
-- Date: 2025-10-11
-- Purpose: Ensure session_pack_questions cannot exist without parent session_packs entry

-- Step 1: Clean up any existing orphaned questions (should be none after our fix)
DO $$
DECLARE
    orphan_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO orphan_count
    FROM session_pack_questions spq
    LEFT JOIN session_packs sp ON spq.session_id = sp.session_id
    WHERE sp.session_id IS NULL;
    
    IF orphan_count > 0 THEN
        RAISE NOTICE 'Found % orphaned questions - deleting...', orphan_count;
        
        DELETE FROM session_pack_questions spq
        WHERE NOT EXISTS (
            SELECT 1 FROM session_packs sp WHERE sp.session_id = spq.session_id
        );
        
        RAISE NOTICE 'Deleted % orphaned questions', orphan_count;
    ELSE
        RAISE NOTICE 'No orphaned questions found - database is clean';
    END IF;
END $$;

-- Step 2: Add Foreign Key Constraint
-- This will PREVENT questions from being inserted without a pack
ALTER TABLE session_pack_questions
ADD CONSTRAINT fk_session_pack_questions_pack
FOREIGN KEY (session_id) 
REFERENCES session_packs(session_id)
ON DELETE CASCADE;  -- If pack is deleted, delete all its questions

-- Step 3: Add index for FK performance
CREATE INDEX IF NOT EXISTS idx_session_pack_questions_session_id
ON session_pack_questions(session_id);

-- Step 4: Verification
DO $$
DECLARE
    fk_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_session_pack_questions_pack'
        AND table_name = 'session_pack_questions'
    ) INTO fk_exists;
    
    IF fk_exists THEN
        RAISE NOTICE '✅ Foreign key constraint successfully added';
    ELSE
        RAISE EXCEPTION '❌ Foreign key constraint was not created!';
    END IF;
END $$;

-- Success message
SELECT 
    'Foreign key constraint added successfully' as status,
    'session_pack_questions.session_id -> session_packs.session_id' as constraint,
    'Orphaned questions are now prevented' as effect;
