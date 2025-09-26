-- Migration: Add job deduplication constraints and logic
-- Prevents duplicate jobs for the same user/session combination

-- Add unique constraint to prevent duplicate session-based jobs
CREATE UNIQUE INDEX IF NOT EXISTS idx_bg_jobs_unique_session_jobs 
ON bg_jobs(user_id, session_id, job_type) 
WHERE session_id IS NOT NULL 
  AND status IN ('queued', 'processing');

-- Add unique constraint for user-based jobs (without session)
CREATE UNIQUE INDEX IF NOT EXISTS idx_bg_jobs_unique_user_jobs 
ON bg_jobs(user_id, job_type) 
WHERE session_id IS NULL 
  AND status IN ('queued', 'processing')
  AND job_type IN ('concept_analysis', 'coverage_update');

-- Add column for job fingerprint (optional for advanced deduplication)
ALTER TABLE bg_jobs ADD COLUMN IF NOT EXISTS job_fingerprint VARCHAR(64);

-- Index for job fingerprint lookups
CREATE INDEX IF NOT EXISTS idx_bg_jobs_fingerprint ON bg_jobs(job_fingerprint) 
WHERE job_fingerprint IS NOT NULL;