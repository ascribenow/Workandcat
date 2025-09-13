-- Migration: Create session_pack_plan table  
-- Stores the planned next session's pack of questions and metadata

CREATE TABLE session_pack_plan (
    user_id VARCHAR(36) NOT NULL,
    session_id VARCHAR(36) NOT NULL,  -- This is the NEXT session to be served
    
    -- Planned session data
    pack JSONB NOT NULL DEFAULT '[]',                 -- Array of question objects with metadata
    constraint_report JSONB NOT NULL DEFAULT '{}',   -- Validation results and constraint checks
    status VARCHAR(20) DEFAULT 'planned',            -- 'planned', 'served', 'completed', 'expired'
    
    -- Planning context
    cold_start_mode BOOLEAN DEFAULT FALSE,
    planning_strategy VARCHAR(50),                    -- 'cold_start', 'adaptive', 'recovery'
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    served_at TIMESTAMP,
    completed_at TIMESTAMP,
    llm_model_used VARCHAR(50),
    processing_time_ms INTEGER,
    
    -- Primary key
    PRIMARY KEY (user_id, session_id),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Indexes for performance
CREATE INDEX idx_session_pack_plan_user_id ON session_pack_plan(user_id);
CREATE INDEX idx_session_pack_plan_status ON session_pack_plan(status);
CREATE INDEX idx_session_pack_plan_created_at ON session_pack_plan(created_at);