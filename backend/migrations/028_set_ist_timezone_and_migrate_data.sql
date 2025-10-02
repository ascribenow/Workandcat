-- Migration 028: Set Database Timezone to IST and Migrate Existing UTC Data
-- Purpose:
--   1. Set database/connection timezone to Asia/Kolkata (IST)
--   2. Convert all existing UTC timestamps to IST
--   3. Ensure all future timestamps are in IST

-- ============================================================================
-- PART 1: SET DATABASE TIMEZONE TO IST
-- ============================================================================

-- Set session timezone to IST for this connection
SET timezone = 'Asia/Kolkata';

-- Note: For permanent database-level timezone, run as superuser:
-- ALTER DATABASE postgres SET timezone TO 'Asia/Kolkata';

-- ============================================================================
-- PART 2: MIGRATE EXISTING UTC DATA TO IST
-- ============================================================================

-- Convert timezone-naive timestamps (assume UTC, add 5:30)
-- These columns store timezone-naive timestamps

BEGIN;

-- Table: sessions
-- Column: created_at (timezone-naive, assumed UTC)
UPDATE sessions 
SET created_at = created_at + interval '5 hours 30 minutes'
WHERE created_at IS NOT NULL
AND created_at < '2025-10-02 20:00:00';  -- Only migrate old data

COMMENT ON COLUMN sessions.created_at IS 'Session creation time in IST (Asia/Kolkata timezone)';

-- Table: attempt_events  
-- Column: created_at (timezone-naive, assumed UTC)
UPDATE attempt_events
SET created_at = created_at + interval '5 hours 30 minutes'
WHERE created_at IS NOT NULL
AND created_at < '2025-10-02 20:00:00';  -- Only migrate old data

COMMENT ON COLUMN attempt_events.created_at IS 'Attempt time in IST (Asia/Kolkata timezone)';

-- Table: session_summary_final
-- Column: created_at (timezone-naive, assumed UTC)
UPDATE session_summary_final
SET created_at = created_at + interval '5 hours 30 minutes'
WHERE created_at IS NOT NULL
AND created_at < '2025-10-02 20:00:00';

COMMENT ON COLUMN session_summary_final.created_at IS 'Summary creation time in IST';

-- Table: session_summary_llm
-- Column: created_at (timezone-naive, assumed UTC)
UPDATE session_summary_llm
SET created_at = created_at + interval '5 hours 30 minutes'
WHERE created_at IS NOT NULL
AND created_at < '2025-10-02 20:00:00';

-- Table: learner_notebook
-- Column: last_seen_at (timezone-naive, assumed UTC)
UPDATE learner_notebook
SET last_seen_at = last_seen_at + interval '5 hours 30 minutes'
WHERE last_seen_at IS NOT NULL
AND last_seen_at < '2025-10-02 20:00:00';

COMMENT ON COLUMN learner_notebook.last_seen_at IS 'Last practice time in IST';

-- Table: coverage_debt
-- Column: updated_at (timezone-naive, assumed UTC)
UPDATE coverage_debt
SET updated_at = updated_at + interval '5 hours 30 minutes'
WHERE updated_at IS NOT NULL
AND updated_at < '2025-10-02 20:00:00';

COMMENT ON COLUMN coverage_debt.updated_at IS 'Last update time in IST';

-- Table: concept_alias_map_latest
-- Column: last_updated (timezone-naive, assumed UTC)
UPDATE concept_alias_map_latest
SET last_updated = last_updated + interval '5 hours 30 minutes'
WHERE last_updated IS NOT NULL
AND last_updated < '2025-10-02 20:00:00';

-- Table: session_packs
-- Column: created_at (timezone-naive, assumed UTC)
UPDATE session_packs
SET created_at = created_at + interval '5 hours 30 minutes'
WHERE created_at IS NOT NULL
AND created_at < '2025-10-02 20:00:00';

-- ============================================================================
-- PART 3: CONVERT TIMEZONE-AWARE TIMESTAMPS (UTC+00:00 -> IST)
-- ============================================================================

-- Table: bg_jobs (has timezone-aware timestamps in UTC)
-- Columns: created_at, started_at, completed_at, next_attempt_at

-- Convert created_at from UTC to IST
UPDATE bg_jobs
SET created_at = created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata'
WHERE created_at IS NOT NULL
AND created_at < '2025-10-02 20:00:00+00:00';

-- Convert started_at from UTC to IST
UPDATE bg_jobs
SET started_at = started_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata'
WHERE started_at IS NOT NULL
AND started_at < '2025-10-02 20:00:00+00:00';

-- Convert completed_at from UTC to IST
UPDATE bg_jobs
SET completed_at = completed_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata'
WHERE completed_at IS NOT NULL
AND completed_at < '2025-10-02 20:00:00+00:00';

-- Convert next_attempt_at from UTC to IST
UPDATE bg_jobs
SET next_attempt_at = next_attempt_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata'
WHERE next_attempt_at IS NOT NULL
AND next_attempt_at < '2025-10-02 20:00:00+00:00';

COMMENT ON COLUMN bg_jobs.created_at IS 'Job creation time in IST';
COMMENT ON COLUMN bg_jobs.started_at IS 'Job start time in IST';
COMMENT ON COLUMN bg_jobs.completed_at IS 'Job completion time in IST';

-- Table: session_answers
-- Column: timestamp (timezone-aware)
UPDATE session_answers
SET timestamp = timestamp AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata'
WHERE timestamp IS NOT NULL
AND timestamp < '2025-10-02 20:00:00+00:00';

COMMIT;

-- ============================================================================
-- PART 4: VERIFICATION QUERIES
-- ============================================================================

-- Verify sample timestamps after migration
SELECT 
    'sessions' as table_name,
    MIN(created_at) as earliest,
    MAX(created_at) as latest,
    COUNT(*) as total_rows
FROM sessions
UNION ALL
SELECT 
    'attempt_events',
    MIN(created_at),
    MAX(created_at),
    COUNT(*)
FROM attempt_events
UNION ALL
SELECT 
    'bg_jobs',
    MIN(created_at),
    MAX(created_at),
    COUNT(*)
FROM bg_jobs
UNION ALL
SELECT 
    'learner_notebook',
    MIN(last_seen_at),
    MAX(last_seen_at),
    COUNT(*)
FROM learner_notebook;

-- Show timezone setting
SHOW timezone;
