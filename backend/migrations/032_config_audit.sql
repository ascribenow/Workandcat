-- Migration: Configuration change audit trail

BEGIN;

-- ==============================================================================
-- Configuration Change Log Table
-- ==============================================================================

CREATE TABLE IF NOT EXISTS config_change_log (
    id SERIAL PRIMARY KEY,
    changed_by VARCHAR(255) NOT NULL DEFAULT 'system',
    change_reason TEXT NOT NULL,
    old_config JSONB NOT NULL,
    new_config JSONB NOT NULL,
    approval_ticket VARCHAR(255),
    deployment_id VARCHAR(255),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    deployed_at TIMESTAMPTZ,
    rollback_available BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_config_changes_time 
ON config_change_log(changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_config_changes_by 
ON config_change_log(changed_by);

CREATE INDEX IF NOT EXISTS idx_config_changes_deployed 
ON config_change_log(deployed_at DESC) WHERE deployed_at IS NOT NULL;

COMMENT ON TABLE config_change_log
IS 'Audit trail for adaptive learning configuration changes';

COMMENT ON COLUMN config_change_log.changed_by
IS 'User or system that made the change (email or "system")';

COMMENT ON COLUMN config_change_log.change_reason
IS 'Why the change was made (required for accountability)';

COMMENT ON COLUMN config_change_log.old_config
IS 'Previous configuration as JSON (for rollback)';

COMMENT ON COLUMN config_change_log.new_config
IS 'New configuration as JSON (for deployment)';

COMMENT ON COLUMN config_change_log.approval_ticket
IS 'Reference to approval ticket/issue (e.g., JIRA-123)';

COMMENT ON COLUMN config_change_log.deployment_id
IS 'Deployment identifier from CI/CD system';

COMMENT ON COLUMN config_change_log.rollback_available
IS 'Whether this change can be safely rolled back';

-- ==============================================================================
-- Configuration Diff Function
-- ==============================================================================

CREATE OR REPLACE FUNCTION config_diff_summary(
    old_config JSONB,
    new_config JSONB
) RETURNS TEXT AS $$
DECLARE
    changes TEXT[];
    key TEXT;
    old_val TEXT;
    new_val TEXT;
BEGIN
    -- Find changed keys
    FOR key IN 
        SELECT DISTINCT jsonb_object_keys(old_config)
        UNION
        SELECT DISTINCT jsonb_object_keys(new_config)
    LOOP
        old_val := old_config->>key;
        new_val := new_config->>key;
        
        IF old_val IS DISTINCT FROM new_val THEN
            changes := array_append(changes, 
                format('%s: %s → %s', key, 
                    COALESCE(old_val, 'null'), 
                    COALESCE(new_val, 'null')
                )
            );
        END IF;
    END LOOP;
    
    IF array_length(changes, 1) IS NULL THEN
        RETURN 'No changes detected';
    END IF;
    
    RETURN array_to_string(changes, E'\n');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION config_diff_summary(JSONB, JSONB)
IS 'Generate human-readable summary of configuration changes';

-- ==============================================================================
-- Log Configuration Change Function
-- ==============================================================================

CREATE OR REPLACE FUNCTION log_config_change(
    p_changed_by VARCHAR,
    p_change_reason TEXT,
    p_old_config JSONB,
    p_new_config JSONB,
    p_approval_ticket VARCHAR DEFAULT NULL,
    p_deployment_id VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_change_id INTEGER;
BEGIN
    -- Validate inputs
    IF p_change_reason IS NULL OR trim(p_change_reason) = '' THEN
        RAISE EXCEPTION 'change_reason is required and cannot be empty';
    END IF;
    
    -- Insert change log
    INSERT INTO config_change_log (
        changed_by,
        change_reason,
        old_config,
        new_config,
        approval_ticket,
        deployment_id
    ) VALUES (
        p_changed_by,
        p_change_reason,
        p_old_config,
        p_new_config,
        p_approval_ticket,
        p_deployment_id
    )
    RETURNING id INTO v_change_id;
    
    -- Log summary
    RAISE NOTICE 'Config change % logged by %: %',
        v_change_id,
        p_changed_by,
        config_diff_summary(p_old_config, p_new_config);
    
    RETURN v_change_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_config_change(VARCHAR, TEXT, JSONB, JSONB, VARCHAR, VARCHAR)
IS 'Log configuration change with validation and audit trail';

-- ==============================================================================
-- Get Current Active Configuration
-- ==============================================================================

CREATE OR REPLACE FUNCTION get_active_config()
RETURNS JSONB AS $$
DECLARE
    v_config JSONB;
BEGIN
    -- Get most recent deployed configuration
    SELECT new_config INTO v_config
    FROM config_change_log
    WHERE deployed_at IS NOT NULL
    ORDER BY deployed_at DESC
    LIMIT 1;
    
    -- If no deployed config, return default (should match Python config)
    IF v_config IS NULL THEN
        v_config := '{
            "version": "1.0.0",
            "last_updated": "2025-09-30",
            "session": {"questions_count": 12, "min_questions": 8, "timeout_minutes": 60},
            "mastery": {
                "min_score": 0.0, "max_score": 10.0, "initial_score": 5.0,
                "increase_correct": 1.0, "decrease_incorrect": 0.5,
                "weak_threshold": 3.0, "moderate_threshold": 7.0
            },
            "readiness": {"levels": ["Weak", "Moderate", "Strong"], "weak_max": 3.0, "moderate_max": 7.0},
            "coverage_debt": {
                "initial": 1.0, "decrease_served": 0.3, "decay_rate": 0.05,
                "min": 0.0, "max": 10.0
            }
        }'::jsonb;
    END IF;
    
    RETURN v_config;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_active_config()
IS 'Get currently active configuration (most recent deployed)';

COMMIT;

-- Log initial configuration
SELECT log_config_change(
    'system',
    'Initial configuration baseline - Phase 4 implementation',
    '{}'::jsonb,
    get_active_config(),
    NULL,
    'phase4-initial'
);
