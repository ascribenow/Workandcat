-- Migration: Add UUID format validation constraints

-- Create UUID validation function
CREATE OR REPLACE FUNCTION is_valid_uuid(value TEXT) 
RETURNS BOOLEAN AS $$
BEGIN
    -- Validate UUID is in canonical format: lowercase, dashed, 36 characters
    -- Example: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
    RETURN value ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION is_valid_uuid(TEXT)
IS 'Validates UUID is in canonical format (lowercase, dashed, 36 characters)';

-- Add UUID format constraints to key tables

-- bg_jobs table
ALTER TABLE bg_jobs 
ADD CONSTRAINT check_bg_jobs_user_id_uuid_format
CHECK (is_valid_uuid(user_id));

ALTER TABLE bg_jobs 
ADD CONSTRAINT check_bg_jobs_session_id_uuid_format
CHECK (session_id IS NULL OR is_valid_uuid(session_id));

-- session_summary_final table
ALTER TABLE session_summary_final
ADD CONSTRAINT check_summary_user_id_uuid_format
CHECK (is_valid_uuid(user_id));

ALTER TABLE session_summary_final
ADD CONSTRAINT check_summary_session_id_uuid_format
CHECK (is_valid_uuid(session_id));

-- concept_alias_map_latest table
ALTER TABLE concept_alias_map_latest
ADD CONSTRAINT check_concept_user_id_uuid_format
CHECK (is_valid_uuid(user_id));

-- Comments for documentation
COMMENT ON CONSTRAINT check_bg_jobs_user_id_uuid_format ON bg_jobs
IS 'Ensures user_id is in canonical UUID format (lowercase, dashed)';

COMMENT ON CONSTRAINT check_bg_jobs_session_id_uuid_format ON bg_jobs
IS 'Ensures session_id is in canonical UUID format or NULL';

COMMENT ON CONSTRAINT check_summary_user_id_uuid_format ON session_summary_final
IS 'Ensures user_id is in canonical UUID format (lowercase, dashed)';

COMMENT ON CONSTRAINT check_summary_session_id_uuid_format ON session_summary_final
IS 'Ensures session_id is in canonical UUID format (lowercase, dashed)';

COMMENT ON CONSTRAINT check_concept_user_id_uuid_format ON concept_alias_map_latest
IS 'Ensures user_id is in canonical UUID format (lowercase, dashed)';
