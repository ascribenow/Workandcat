-- Migration 027: Clean up stale failed jobs and add documentation
-- Purpose: 
--   1. Mark old failed UPDATE_INSIGHTS jobs as 'ignored' to fix success rate metrics
--   2. Add comments documenting session_answers as source of truth for accuracy

-- Mark stale failed UPDATE_INSIGHTS jobs from before worker restart
-- These failures were due to old code (missing method) and should not affect current metrics
UPDATE bg_jobs 
SET status = 'ignored', 
    error_message = CONCAT('HISTORICAL FAILURE (pre-worker restart): ', error_message)
WHERE job_type = 'UPDATE_INSIGHTS' 
AND status = 'failed' 
AND created_at < '2025-10-02 15:00:00+00:00';  -- Before successful job timestamp

-- Add table comments for clarity
COMMENT ON TABLE session_answers IS 'Source of truth for session accuracy calculation. Each row represents final answer for a position. Use this table (not attempt_events) for computing session accuracy.';

COMMENT ON TABLE attempt_events IS 'All question attempts including duplicates and retries. For accuracy calculation, use session_answers instead.';

-- Verify the cleanup
SELECT 
    job_type,
    COUNT(*) FILTER (WHERE status = 'succeeded') as succeeded,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'ignored') as ignored,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'succeeded') / 
          NULLIF(COUNT(*) FILTER (WHERE status != 'ignored'), 0), 2) as success_rate_pct
FROM bg_jobs
WHERE job_type IN ('SUMMARIZE_SESSION', 'PLAN_NEXT_SESSION', 'UPDATE_INSIGHTS')
GROUP BY job_type
ORDER BY job_type;
