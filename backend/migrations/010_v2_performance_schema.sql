-- V2 Performance & Schema Migrations (Safe, Additive)
-- Can be applied without downtime

-- 1) Fast deterministic selection (eliminates ORDER BY RANDOM())
ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS shuffle_hash int
  GENERATED ALWAYS AS (hashtext(id::text)) STORED;

-- Performance indexes for fast candidate selection
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_q_pyq_band_hash
  ON questions (pyq_frequency_score, difficulty_band, shuffle_hash);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_questions_pyq_band
  ON questions (pyq_frequency_score, difficulty_band);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_questions_subcat_type
  ON questions (subcategory, type_of_question);

-- 2) Session pack plan enhancements
-- Add sess_seq for internal canonical identification
ALTER TABLE session_pack_plan
  ADD COLUMN IF NOT EXISTS sess_seq int;

-- Add pack_json as canonical pack storage  
ALTER TABLE session_pack_plan
  ADD COLUMN IF NOT EXISTS pack_json jsonb;

-- Add V2 telemetry fields
ALTER TABLE session_pack_plan
  ADD COLUMN IF NOT EXISTS planner_fallback boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS retry_used smallint DEFAULT 0,
  ADD COLUMN IF NOT EXISTS llm_model_used text,
  ADD COLUMN IF NOT EXISTS processing_time_ms integer;

-- Backfill sess_seq from sessions table
UPDATE session_pack_plan spp
SET sess_seq = s.sess_seq
FROM sessions s
WHERE spp.session_id = s.session_id
  AND spp.sess_seq IS NULL;

-- Backfill pack_json from pack column  
UPDATE session_pack_plan
SET pack_json = pack
WHERE pack_json IS NULL AND pack IS NOT NULL;

-- Create idempotency constraint on (user_id, sess_seq)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_pack_user_sess
  ON session_pack_plan (user_id, sess_seq);

-- Optional: Index for fast session_id to sess_seq resolution
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sessions_session_id_sess_seq
  ON sessions (session_id, sess_seq);

-- Comment for tracking
COMMENT ON COLUMN questions.shuffle_hash IS 'V2: Generated hash for deterministic selection';
COMMENT ON COLUMN session_pack_plan.sess_seq IS 'V2: Internal canonical session sequence';
COMMENT ON COLUMN session_pack_plan.pack_json IS 'V2: Canonical pack storage (replaces pack)';
COMMENT ON COLUMN session_pack_plan.planner_fallback IS 'V2: True if deterministic fallback was used';