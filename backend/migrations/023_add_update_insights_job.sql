-- Migration: Add UPDATE_INSIGHTS job type to support adaptive insights
-- Extends the background job system with a third job type

-- Add UPDATE_INSIGHTS to the job_type enum
ALTER TYPE job_type ADD VALUE 'UPDATE_INSIGHTS';

-- Add comment to document the complete flow
COMMENT ON TYPE job_type IS 'Background job types: SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS';