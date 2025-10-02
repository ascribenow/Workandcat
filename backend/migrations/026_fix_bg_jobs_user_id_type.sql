-- Fix bg_jobs.user_id data type mismatch
-- Change from character varying to uuid to match users.id

BEGIN;

-- First, drop the foreign key constraint
ALTER TABLE bg_jobs DROP CONSTRAINT IF EXISTS fk_bg_jobs_user_id;

-- Convert user_id column from character varying to uuid
ALTER TABLE bg_jobs 
ALTER COLUMN user_id TYPE uuid USING user_id::uuid;

-- Recreate the foreign key constraint with proper types
ALTER TABLE bg_jobs 
ADD CONSTRAINT fk_bg_jobs_user_id 
FOREIGN KEY (user_id) REFERENCES users(id);

-- Also fix session_id to be proper uuid type for consistency
ALTER TABLE bg_jobs 
ALTER COLUMN session_id TYPE uuid USING CASE 
    WHEN session_id IS NULL THEN NULL 
    ELSE session_id::uuid 
END;

COMMIT;