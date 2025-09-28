-- Migration 022: Adaptive Insights Cache Tables
-- Creates cache tables and indexes for "Proof of the Pudding" adaptive insights feature

-- Cache table for dashboard insights (two sections)
CREATE TABLE IF NOT EXISTS user_dashboard_insights (
    user_id varchar(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    all_time_insights jsonb NOT NULL,
    recent_insights jsonb NOT NULL, 
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

-- Cache table for pre-session insight cards
CREATE TABLE IF NOT EXISTS user_pre_session_insights (
    user_id varchar(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    insight_card jsonb NOT NULL,
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

-- Debug table (optional) for storing raw slices
CREATE TABLE IF NOT EXISTS user_insight_debug (
    user_id varchar(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    all_time_slice jsonb,
    recent_slice jsonb,
    pre_session_slice jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Performance indexes for faster query execution
CREATE INDEX IF NOT EXISTS idx_attempt_events_user_session ON attempt_events(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status_completed ON sessions(user_id, status, completed_at);
CREATE INDEX IF NOT EXISTS idx_session_pack_questions_session ON session_pack_questions(session_id);
CREATE INDEX IF NOT EXISTS idx_learner_notebook_user_concept_updated ON learner_notebook(user_id, concept_norm, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_coverage_debt_user_subcategory ON coverage_debt(user_id, subcategory, type_of_question);

-- Generated column for PYQ score (performance optimization)
ALTER TABLE session_pack_questions 
ADD COLUMN IF NOT EXISTS pyq_score_num float 
GENERATED ALWAYS AS ((question_data->>'pyq_frequency_score')::float) STORED;

-- Index the generated column for fast aggregation
CREATE INDEX IF NOT EXISTS idx_session_pack_questions_pyq_score ON session_pack_questions(pyq_score_num);

-- Comments for documentation
COMMENT ON TABLE user_dashboard_insights IS 'Cache for all-time journey and recent momentum insights';
COMMENT ON TABLE user_pre_session_insights IS 'Cache for pre-session insight cards';
COMMENT ON TABLE user_insight_debug IS 'Debug storage for raw insight data slices (optional)';