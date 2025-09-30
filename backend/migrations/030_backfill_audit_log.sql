-- Migration: Backfill audit log for provenance tracking

CREATE TABLE IF NOT EXISTS backfill_audit_log (
    id SERIAL PRIMARY KEY,
    batch_id UUID NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    batch_size INTEGER,
    per_user_limit INTEGER,
    status VARCHAR(20) CHECK (status IN ('queued', 'running', 'completed', 'paused', 'failed')),
    sessions_found INTEGER,
    jobs_enqueued INTEGER,
    jobs_failed INTEGER,
    sessions_skipped INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_backfill_audit_started ON backfill_audit_log(started_at DESC);
CREATE INDEX idx_backfill_audit_status ON backfill_audit_log(status);

COMMENT ON TABLE backfill_audit_log 
IS 'Audit trail for backfill operations executed via API';

COMMENT ON COLUMN backfill_audit_log.batch_id
IS 'Unique identifier for each backfill batch - stored in job metadata for traceability';

COMMENT ON COLUMN backfill_audit_log.per_user_limit
IS 'Max sessions enqueued per user in this batch (fairness constraint)';
