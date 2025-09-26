-- Migration: Simplified Background Job System
-- Two job types only: SUMMARIZE_SESSION → PLAN_NEXT_SESSION

-- Create ENUMs for type safety
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='job_type') THEN
    CREATE TYPE job_type AS ENUM ('SUMMARIZE_SESSION','PLAN_NEXT_SESSION');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='job_status') THEN
    CREATE TYPE job_status AS ENUM ('queued','running','succeeded','failed');
  END IF;
END $$;

-- Drop existing complex bg_jobs table and recreate lean version
DROP TABLE IF EXISTS bg_jobs CASCADE;

CREATE TABLE bg_jobs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type        job_type NOT NULL,
  user_id         uuid NOT NULL,
  session_id      uuid,
  dedupe_key      text UNIQUE,           -- e.g. u:{uid}|s:{sid}|SUMMARIZE
  status          job_status NOT NULL DEFAULT 'queued',
  attempts        int NOT NULL DEFAULT 0,
  max_attempts    int NOT NULL DEFAULT 6,
  next_attempt_at timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  started_at      timestamptz,
  completed_at    timestamptz,
  error_message   text,
  
  -- Foreign key to users table
  CONSTRAINT fk_bg_jobs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Efficient indexes for worker job picking
CREATE INDEX idx_bg_jobs_ready 
  ON bg_jobs (status, next_attempt_at) 
  WHERE status IN ('queued','failed');

CREATE INDEX idx_bg_jobs_user_session ON bg_jobs(user_id, session_id);
CREATE INDEX idx_bg_jobs_created_at ON bg_jobs(created_at);

-- Recreate simplified learner_notebook (minimal schema)
DROP TABLE IF EXISTS learner_notebook CASCADE;

CREATE TABLE learner_notebook (
  user_id       uuid NOT NULL,
  concept_norm  text NOT NULL,
  mastery_score float NOT NULL,              -- 0..1 EMA 
  readiness     text NOT NULL,               -- 'Weak'|'Moderate'|'Strong'
  last_seen_at  timestamptz NOT NULL DEFAULT now(),
  
  PRIMARY KEY (user_id, concept_norm),
  CONSTRAINT fk_learner_notebook_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT chk_mastery_score CHECK (mastery_score >= 0.0 AND mastery_score <= 1.0),
  CONSTRAINT chk_readiness CHECK (readiness IN ('Weak', 'Moderate', 'Strong'))
);

CREATE INDEX idx_learner_notebook_user_mastery ON learner_notebook(user_id, mastery_score);
CREATE INDEX idx_learner_notebook_readiness ON learner_notebook(readiness);

-- Recreate simplified coverage_debt (minimal schema)
DROP TABLE IF EXISTS coverage_debt CASCADE;

CREATE TABLE coverage_debt (
  user_id          uuid NOT NULL,
  subcategory      text NOT NULL,
  type_of_question text NOT NULL,
  debt_score       float NOT NULL DEFAULT 0.0,    -- 0..1
  updated_at       timestamptz NOT NULL DEFAULT now(),
  
  PRIMARY KEY (user_id, subcategory, type_of_question),
  CONSTRAINT fk_coverage_debt_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT chk_debt_score CHECK (debt_score >= 0.0 AND debt_score <= 1.0)
);

CREATE INDEX idx_coverage_debt_user_score ON coverage_debt(user_id, debt_score DESC);
CREATE INDEX idx_coverage_debt_updated ON coverage_debt(updated_at);