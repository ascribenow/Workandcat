-- Migration: Create session_summary_final table
-- Stores final processed session data with computed concept weights, readiness, and coverage

CREATE TABLE session_summary_final (
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,
    
    -- Processed outputs from deterministic kernels
    concept_weights JSONB NOT NULL DEFAULT '{}',       -- Semantic ID -> weight mapping
    final_readiness JSONB NOT NULL DEFAULT '{}',       -- Semantic ID -> readiness level
    final_coverage JSONB NOT NULL DEFAULT '{}',        -- Pair -> coverage debt level
    
    -- Aggregated counts for debugging/analysis  
    aggregate_counts JSONB NOT NULL DEFAULT '{}',      -- Per-concept weighted counts
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_ms INTEGER,
    
    -- Primary key
    PRIMARY KEY (user_id, session_id),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_session_summary_final_user_id ON session_summary_final(user_id);
CREATE INDEX idx_session_summary_final_created_at ON session_summary_final(created_at);