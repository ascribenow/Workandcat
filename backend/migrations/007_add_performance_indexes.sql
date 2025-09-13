-- Migration: Add performance indexes for adaptive system
-- Required indexes for optimal pack generation performance

-- Questions table performance indexes
CREATE INDEX IF NOT EXISTS idx_questions_band_pyq
  ON questions(difficulty_band, pyq_frequency_score);

CREATE INDEX IF NOT EXISTS idx_questions_pair
  ON questions(subcategory, type_of_question);

-- Unique constraint: only one 'planned' pack per (user, session)
CREATE UNIQUE INDEX IF NOT EXISTS uq_pack_plan_planned
  ON session_pack_plan(user_id, session_id, status)
  WHERE status = 'planned';

-- Additional performance indexes
CREATE INDEX IF NOT EXISTS idx_questions_active_difficulty
  ON questions(is_active, difficulty_band)
  WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_questions_quality_verified
  ON questions(quality_verified, difficulty_band)
  WHERE quality_verified = true;