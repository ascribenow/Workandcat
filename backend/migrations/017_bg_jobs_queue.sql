-- Migration: Create background jobs queue table
-- Supports job queuing, processing, retry logic, and observability

CREATE TABLE bg_jobs (
    id SERIAL PRIMARY KEY,
    job_type VARCHAR(100) NOT NULL,
    job_data JSONB NOT NULL DEFAULT '{}',
    
    -- Job ownership and context
    user_id VARCHAR(36),
    session_id VARCHAR(50),
    
    -- Job lifecycle
    status VARCHAR(20) NOT NULL DEFAULT 'queued',  -- queued|processing|completed|failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Retry logic
    attempt_count INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 6,
    next_attempt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Results and error handling
    result JSONB,
    error_message TEXT,
    
    -- Processing metadata
    worker_id VARCHAR(50),
    processing_duration_ms INTEGER,
    
    -- Constraints for job status
    CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    CHECK (attempt_count <= max_attempts),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for efficient job processing
CREATE INDEX idx_bg_jobs_status_next_attempt ON bg_jobs(status, next_attempt_at) WHERE status IN ('queued', 'failed');
CREATE INDEX idx_bg_jobs_user_session ON bg_jobs(user_id, session_id);
CREATE INDEX idx_bg_jobs_created_at ON bg_jobs(created_at);
CREATE INDEX idx_bg_jobs_job_type ON bg_jobs(job_type);

-- Index for worker job picking with advisory locks
CREATE INDEX idx_bg_jobs_worker_pick ON bg_jobs(id) WHERE status = 'queued' AND next_attempt_at <= CURRENT_TIMESTAMP;