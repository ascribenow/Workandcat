-- Performance Indexes for Dashboard Timeout Fix
-- Target: Dashboard queries under 300ms

-- Index for fast session counts by user (dashboard)
CREATE INDEX IF NOT EXISTS idx_sessions_user_completed_at 
  ON sessions(user_id, completed_at DESC NULLS LAST);

-- Index for attempt events by user (dashboard stats)  
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_created_at
  ON attempt_events(user_id, created_at DESC);

-- Unique index for session pack plan lookups (pack endpoint)
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_pack_plan_session_id
  ON session_pack_plan(session_id);

-- Index for session pack status queries (dashboard + pack)
CREATE INDEX IF NOT EXISTS idx_session_pack_plan_user_status
  ON session_pack_plan(user_id, status);

-- Index for fast question lookups (pack assembly)
CREATE INDEX IF NOT EXISTS idx_questions_quality_verified
  ON questions(quality_verified, id) WHERE quality_verified = true;

-- Index for efficient session progress tracking
CREATE INDEX IF NOT EXISTS idx_session_progress_session_user
  ON session_progress(session_id, user_id);

-- Composite index for dashboard session summaries
CREATE INDEX IF NOT EXISTS idx_sessions_user_status_completed
  ON sessions(user_id, status, completed_at DESC NULLS LAST);

-- Add statement timeout for dashboard endpoints
-- This will be implemented in the API handlers