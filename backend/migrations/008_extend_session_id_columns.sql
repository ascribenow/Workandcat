-- Migration: Extend session_id columns from VARCHAR(36) to VARCHAR(100)
-- Fixes issue where UUID-based session IDs can be longer than 36 characters

-- Extend session_id in sessions table
ALTER TABLE sessions ALTER COLUMN session_id TYPE VARCHAR(100);

-- Extend session_id in session_pack_plan table  
ALTER TABLE session_pack_plan ALTER COLUMN session_id TYPE VARCHAR(100);

-- Extend session_id in session_summary_llm table
ALTER TABLE session_summary_llm ALTER COLUMN session_id TYPE VARCHAR(100);

-- Note: No need to recreate indexes as they will automatically handle the new column size