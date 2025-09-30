-- Migration: Fix stuck and failed background jobs
-- Addresses:
-- 1. Stuck jobs with NULL next_attempt_at
-- 2. Jobs stuck in 'running' status (likely crashed workers)
-- 3. Old failed jobs from outdated schema

-- Fix 1: Set next_attempt_at for all queued jobs that have NULL
UPDATE bg_jobs 
SET next_attempt_at = CURRENT_TIMESTAMP
WHERE status = 'queued' AND next_attempt_at IS NULL;

-- Fix 2: Reset jobs stuck in 'running' status back to 'queued'
-- These are likely from crashed workers that didn't complete
UPDATE bg_jobs
SET status = 'queued',
    next_attempt_at = CURRENT_TIMESTAMP,
    started_at = NULL
WHERE status = 'running' 
  AND started_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes';

-- Fix 3: Add constraint to ensure next_attempt_at is never NULL for queued jobs
-- This prevents future issues with jobs not being picked up
ALTER TABLE bg_jobs 
ADD CONSTRAINT chk_queued_has_next_attempt 
CHECK (
    status != 'queued' OR next_attempt_at IS NOT NULL
);

-- Note: Old failed PLAN_NEXT_SESSION job from outdated schema is left as 'failed'
-- It has exhausted all attempts and provides historical context
