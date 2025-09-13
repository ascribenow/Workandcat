-- Phase 4: Database indexes and constraints setup
-- Execute this to add required indexes and constraints for adaptive session orchestration

-- Concurrency & lookups
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_sess
  ON attempt_events(user_id, sess_seq_at_serve);

CREATE INDEX IF NOT EXISTS idx_sessions_user_seq
  ON sessions(user_id, sess_seq);

CREATE INDEX IF NOT EXISTS idx_pack_plan_user_sess
  ON session_pack_plan(user_id, session_id);

-- Idempotency/state safety: only one 'planned' row per (user, session)
CREATE UNIQUE INDEX IF NOT EXISTS uq_pack_plan_planned
  ON session_pack_plan(user_id, session_id, status)
  WHERE status = 'planned';