-- Migration: Create adaptive store tables for background intelligence
-- Stores learner notebook and coverage debt data

-- Learner Notebook: Per-user concept mastery and learning insights
CREATE TABLE learner_notebook (
    user_id VARCHAR(36) NOT NULL,
    concept_semantic_id VARCHAR(64) NOT NULL,
    
    -- Concept mastery tracking
    canonical_label VARCHAR(255) NOT NULL,
    mastery_level VARCHAR(20) DEFAULT 'novice',  -- novice|developing|proficient|expert
    confidence_score NUMERIC(3,2) DEFAULT 0.0,  -- 0.0 to 1.0
    
    -- Learning patterns
    total_attempts INTEGER DEFAULT 0,
    correct_attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    learning_velocity NUMERIC(5,4) DEFAULT 0.0,  -- Rate of improvement
    
    -- Readiness indicators
    readiness_labels JSONB DEFAULT '[]',  -- ["skipped", "wrong_1_to_3", etc.]
    coverage_gap_score NUMERIC(3,2) DEFAULT 0.0,
    
    -- Metadata
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    PRIMARY KEY (user_id, concept_semantic_id),
    CHECK (mastery_level IN ('novice', 'developing', 'proficient', 'expert')),
    CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CHECK (coverage_gap_score >= 0.0 AND coverage_gap_score <= 1.0),
    CHECK (correct_attempts <= total_attempts),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Coverage Debt: Areas needing more practice and attention
CREATE TABLE coverage_debt (
    user_id VARCHAR(36) NOT NULL,
    pair_identifier VARCHAR(255) NOT NULL,  -- "subcategory:type_of_question"
    
    -- Debt metrics
    debt_score NUMERIC(3,2) NOT NULL DEFAULT 0.0,  -- 0.0 to 1.0, higher = more debt
    debt_type VARCHAR(50) NOT NULL,  -- insufficient_exposure|performance_decline|avoidance_pattern
    
    -- Context and reasoning
    reason_codes JSONB DEFAULT '[]',  -- ["insufficient_exposure", "recent_failures"]
    last_practice_session_id VARCHAR(50),
    days_since_practice INTEGER DEFAULT 0,
    
    -- Recommendation priority
    priority_score NUMERIC(3,2) DEFAULT 0.5,
    recommended_difficulty VARCHAR(20) DEFAULT 'Medium',
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,  -- When debt was addressed
    
    -- Constraints
    PRIMARY KEY (user_id, pair_identifier),
    CHECK (debt_score >= 0.0 AND debt_score <= 1.0),
    CHECK (priority_score >= 0.0 AND priority_score <= 1.0),
    CHECK (debt_type IN ('insufficient_exposure', 'performance_decline', 'avoidance_pattern', 'concept_gap')),
    CHECK (recommended_difficulty IN ('Easy', 'Medium', 'Hard')),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for adaptive store performance
CREATE INDEX idx_learner_notebook_user_mastery ON learner_notebook(user_id, mastery_level);
CREATE INDEX idx_learner_notebook_confidence ON learner_notebook(confidence_score DESC);
CREATE INDEX idx_learner_notebook_last_updated ON learner_notebook(last_updated_at);

CREATE INDEX idx_coverage_debt_user_debt ON coverage_debt(user_id, debt_score DESC);
CREATE INDEX idx_coverage_debt_priority ON coverage_debt(priority_score DESC, created_at);
CREATE INDEX idx_coverage_debt_unresolved ON coverage_debt(user_id) WHERE resolved_at IS NULL;