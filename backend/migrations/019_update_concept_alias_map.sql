-- Migration: Update concept_alias_map_latest table structure
-- Align with new background job system requirements

-- Drop existing table and recreate with updated structure
DROP TABLE IF EXISTS concept_alias_map_latest CASCADE;

CREATE TABLE concept_alias_map_latest (
    user_id VARCHAR(36) NOT NULL,
    alias_map_json JSONB NOT NULL DEFAULT '[]',  -- Array of concept alias mappings
    
    -- Metadata
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_count INTEGER DEFAULT 0,  -- Number of sessions processed
    total_concepts INTEGER DEFAULT 0,  -- Total concepts in map
    
    -- Processing info
    last_processing_session_id VARCHAR(50),
    processing_model VARCHAR(50),  -- LLM model used for processing
    
    -- Constraints
    PRIMARY KEY (user_id),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for concept alias map
CREATE INDEX idx_concept_alias_map_updated_at ON concept_alias_map_latest(updated_at);
CREATE INDEX idx_concept_alias_map_session_count ON concept_alias_map_latest(session_count);