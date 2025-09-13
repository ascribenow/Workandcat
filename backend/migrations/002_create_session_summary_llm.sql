-- Migration: Create session_summary_llm table
-- Stores LLM-generated session summaries with concept mapping, dominance, readiness, and coverage

CREATE TABLE session_summary_llm (
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    
    -- LLM outputs
    concept_alias_map JSONB NOT NULL DEFAULT '{}',     -- Map of raw concepts to canonical labels
    dominance JSONB NOT NULL DEFAULT '{}',             -- Concept dominance labels from LLM
    readiness_reasons JSONB NOT NULL DEFAULT '{}',     -- Readiness explanations per concept
    coverage_labels JSONB NOT NULL DEFAULT '{}',       -- Coverage debt labels per pair
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_model_used VARCHAR(50),
    processing_time_ms INTEGER,
    
    -- Primary key
    PRIMARY KEY (user_id, session_id),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_session_summary_llm_user_id ON session_summary_llm(user_id);
CREATE INDEX idx_session_summary_llm_created_at ON session_summary_llm(created_at);