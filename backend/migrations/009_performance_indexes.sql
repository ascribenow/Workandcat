-- P1 FIX: Add composite index for fast candidate selection
-- Replaces slow ORDER BY RANDOM() with efficient indexed queries

-- Composite index for PYQ score and difficulty band combinations
CREATE INDEX IF NOT EXISTS ix_questions_pyq_band
  ON questions (pyq_frequency_score, difficulty_band)
  WHERE is_active = true;

-- Additional covering index for seeded hash queries  
CREATE INDEX IF NOT EXISTS ix_questions_active_id_hash
  ON questions (is_active, id)
  WHERE is_active = true;

-- Index for session pack plan lookups (if missing)
CREATE INDEX IF NOT EXISTS ix_session_pack_plan_user_sess_seq
  ON session_pack_plan (user_id, session_id);

-- Ensure proper index exists for attempt events
CREATE INDEX IF NOT EXISTS ix_attempt_events_user_sess_seq
  ON attempt_events (user_id, sess_seq_at_serve);