-- Migration: Enhanced health metrics and observability

BEGIN;

-- ==============================================================================
-- 1. Core metrics table for storing health metrics
-- ==============================================================================
CREATE TABLE IF NOT EXISTS pipeline_health_metrics (
    metric_name VARCHAR(100) PRIMARY KEY,
    metric_value NUMERIC,
    metric_type VARCHAR(20) CHECK (metric_type IN ('counter', 'gauge', 'percentage', 'duration')),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_health_metrics_updated 
ON pipeline_health_metrics(last_updated DESC);

COMMENT ON TABLE pipeline_health_metrics
IS 'Stores real-time health metrics for the adaptive learning pipeline';

-- ==============================================================================
-- 2. Alert state tracking (persistence filtering)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS pipeline_alerts (
    id SERIAL PRIMARY KEY,
    alert_name VARCHAR(100) NOT NULL,
    alert_level VARCHAR(20) CHECK (alert_level IN ('info', 'warning', 'critical')),
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    occurrences INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    context JSONB DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pipeline_alerts_name 
ON pipeline_alerts(alert_name) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_pipeline_alerts_level 
ON pipeline_alerts(alert_level, is_active);

COMMENT ON TABLE pipeline_alerts
IS 'Tracks alert state with persistence filtering to prevent alert fatigue';

-- ==============================================================================
-- 3. Root cause context - Materialized view for failing job analysis
-- ==============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_failing_job_types_30m AS
SELECT 
    job_type,
    COUNT(*) as failure_count,
    COUNT(DISTINCT user_id) as affected_users,
    array_agg(DISTINCT substring(error_message, 1, 200)) FILTER (WHERE error_message IS NOT NULL) as error_samples,
    MIN(created_at) as first_failure,
    MAX(created_at) as last_failure
FROM bg_jobs
WHERE status = 'failed'
AND created_at > NOW() - INTERVAL '30 minutes'
GROUP BY job_type
ORDER BY failure_count DESC
LIMIT 10;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_failing_jobs_type 
ON mv_failing_job_types_30m(job_type);

COMMENT ON MATERIALIZED VIEW mv_failing_job_types_30m
IS 'Provides root cause context for job failures in the last 30 minutes';

-- ==============================================================================
-- 4. Correlation IDs for end-to-end tracing
-- ==============================================================================

-- Add correlation_id to bg_jobs if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'bg_jobs' AND column_name = 'correlation_id'
    ) THEN
        ALTER TABLE bg_jobs ADD COLUMN correlation_id UUID;
        CREATE INDEX idx_bg_jobs_correlation ON bg_jobs(correlation_id);
        RAISE NOTICE 'Added correlation_id to bg_jobs';
    END IF;
END $$;

-- Add correlation_id to sessions if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'correlation_id'
    ) THEN
        ALTER TABLE sessions ADD COLUMN correlation_id UUID;
        CREATE INDEX idx_sessions_correlation ON sessions(correlation_id);
        RAISE NOTICE 'Added correlation_id to sessions';
    END IF;
END $$;

-- ==============================================================================
-- 5. Alert persistence function
-- ==============================================================================
CREATE OR REPLACE FUNCTION should_fire_alert(
    p_alert_name VARCHAR,
    p_alert_level VARCHAR,
    p_min_occurrences INTEGER DEFAULT 3,
    p_min_duration_minutes INTEGER DEFAULT 15,
    p_context JSONB DEFAULT '{}'::jsonb
) RETURNS BOOLEAN AS $$
DECLARE
    v_first_seen TIMESTAMPTZ;
    v_occurrences INTEGER;
    v_duration_minutes NUMERIC;
BEGIN
    -- Check if alert already exists
    SELECT first_seen, occurrences 
    INTO v_first_seen, v_occurrences
    FROM pipeline_alerts
    WHERE alert_name = p_alert_name AND is_active = TRUE;
    
    IF v_first_seen IS NULL THEN
        -- New alert - create it but don't fire yet
        INSERT INTO pipeline_alerts (alert_name, alert_level, context)
        VALUES (p_alert_name, p_alert_level, p_context);
        RETURN FALSE;
    ELSE
        -- Existing alert - update occurrence count
        v_duration_minutes := EXTRACT(EPOCH FROM (NOW() - v_first_seen))/60;
        
        UPDATE pipeline_alerts
        SET last_seen = NOW(), occurrences = occurrences + 1, context = p_context
        WHERE alert_name = p_alert_name AND is_active = TRUE;
        
        -- Fire alert if it meets thresholds
        IF v_occurrences >= p_min_occurrences OR v_duration_minutes >= p_min_duration_minutes THEN
            RETURN TRUE;
        END IF;
        
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION should_fire_alert(VARCHAR, VARCHAR, INTEGER, INTEGER, JSONB)
IS 'Implements alert persistence filtering to prevent alert fatigue. Only fires after sustained conditions.';

-- ==============================================================================
-- 6. Metrics update function
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_pipeline_health_metrics()
RETURNS void AS $$
DECLARE
    v_total_completed INTEGER;
    v_with_summaries INTEGER;
    v_orphaned INTEGER;
    v_completion_rate NUMERIC;
    v_job_success_rate NUMERIC;
    v_total_jobs INTEGER;
    v_succeeded_jobs INTEGER;
BEGIN
    -- Calculate summary completion rate
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN EXISTS (
            SELECT 1 FROM session_summary_final ssf 
            WHERE CAST(ssf.session_id AS VARCHAR) = CAST(s.session_id AS VARCHAR)
        ) THEN 1 END) as with_summary
    INTO v_total_completed, v_with_summaries
    FROM sessions s
    WHERE s.status = 'completed';
    
    v_orphaned := v_total_completed - v_with_summaries;
    v_completion_rate := CASE 
        WHEN v_total_completed > 0 
        THEN (v_with_summaries::numeric / v_total_completed * 100)
        ELSE 100 
    END;
    
    -- Insert/update summary completion rate metric
    INSERT INTO pipeline_health_metrics (metric_name, metric_value, metric_type, description)
    VALUES ('summary_completion_rate', v_completion_rate, 'percentage', '% of completed sessions with summaries')
    ON CONFLICT (metric_name) DO UPDATE SET 
        metric_value = EXCLUDED.metric_value, 
        last_updated = NOW();
    
    -- Insert/update orphaned sessions metric
    INSERT INTO pipeline_health_metrics (metric_name, metric_value, metric_type, description)
    VALUES ('orphaned_sessions_count', v_orphaned, 'gauge', 'Sessions without summaries')
    ON CONFLICT (metric_name) DO UPDATE SET 
        metric_value = EXCLUDED.metric_value, 
        last_updated = NOW();
    
    -- Calculate job success rate (last 24 hours)
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN status = 'succeeded' THEN 1 END) as succeeded
    INTO v_total_jobs, v_succeeded_jobs
    FROM bg_jobs
    WHERE created_at > NOW() - INTERVAL '24 hours';
    
    v_job_success_rate := CASE 
        WHEN v_total_jobs > 0 
        THEN (v_succeeded_jobs::numeric / v_total_jobs * 100)
        ELSE 100 
    END;
    
    -- Insert/update job success rate metric
    INSERT INTO pipeline_health_metrics (metric_name, metric_value, metric_type, description)
    VALUES ('job_success_rate_24h', v_job_success_rate, 'percentage', 'Job success rate last 24h')
    ON CONFLICT (metric_name) DO UPDATE SET 
        metric_value = EXCLUDED.metric_value, 
        last_updated = NOW();
    
    -- Refresh materialized view for failing jobs
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_failing_job_types_30m;
    
EXCEPTION WHEN OTHERS THEN
    -- Log error but don't fail
    RAISE WARNING 'Error updating pipeline health metrics: %', SQLERRM;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_pipeline_health_metrics()
IS 'Updates all pipeline health metrics and refreshes failing jobs analysis';

COMMIT;

-- Initial metrics calculation
SELECT update_pipeline_health_metrics();
