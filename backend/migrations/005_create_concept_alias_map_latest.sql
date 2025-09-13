-- Migration: Create concept_alias_map_latest table
-- Stores the latest concept alias map for each user (semantic ID mappings)

CREATE TABLE concept_alias_map_latest (
    user_id VARCHAR(36) NOT NULL,
    semantic_id VARCHAR(64) NOT NULL,  -- SHA1 hash from canonical label
    
    -- Concept mapping data
    canonical_label VARCHAR(255) NOT NULL,            -- Canonical concept name
    members JSONB NOT NULL DEFAULT '[]',              -- Array of raw concept strings that map to this
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_seen_session_id VARCHAR(36),
    usage_count INTEGER DEFAULT 1,
    
    -- Primary key
    PRIMARY KEY (user_id, semantic_id),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_concept_alias_map_user_id ON concept_alias_map_latest(user_id);
CREATE INDEX idx_concept_alias_map_canonical ON concept_alias_map_latest(canonical_label);
CREATE INDEX idx_concept_alias_map_updated ON concept_alias_map_latest(last_updated);