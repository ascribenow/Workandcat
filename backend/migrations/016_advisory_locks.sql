-- =====================================================
-- Twelvr Blueprint Migration 016: Advisory Lock System
-- =====================================================
-- This migration creates PostgreSQL advisory lock support functions
-- Addresses Deviation #3: Advisory lock integration in core planning flow

-- =====================================================
-- 1. ADVISORY LOCK FUNCTIONS
-- =====================================================

-- Function to acquire a named advisory lock with timeout
CREATE OR REPLACE FUNCTION acquire_advisory_lock(
    lock_name TEXT, 
    timeout_seconds INTEGER DEFAULT 30
) 
RETURNS BOOLEAN AS $$
DECLARE
    lock_id BIGINT;
    acquired BOOLEAN := FALSE;
    start_time TIMESTAMP;
BEGIN
    -- Convert lock name to numeric ID for pg_advisory_lock
    lock_id := ABS(HASHTEXT(lock_name));
    start_time := NOW();
    
    -- Try to acquire lock with timeout
    WHILE NOT acquired AND (NOW() - start_time) < (timeout_seconds || ' seconds')::INTERVAL LOOP
        SELECT pg_try_advisory_lock(lock_id) INTO acquired;
        
        IF NOT acquired THEN
            -- Wait 100ms before retrying
            PERFORM pg_sleep(0.1);
        END IF;
    END LOOP;
    
    -- Log lock acquisition in advisory_locks table for monitoring
    IF acquired THEN
        INSERT INTO advisory_locks (lock_key, user_id, acquired_at, expires_at)
        VALUES (
            lock_name, 
            NULL, -- Will be updated by application
            NOW(), 
            NOW() + (timeout_seconds || ' seconds')::INTERVAL
        )
        ON CONFLICT (lock_key) DO UPDATE SET
            acquired_at = NOW(),
            expires_at = NOW() + (timeout_seconds || ' seconds')::INTERVAL;
    END IF;
    
    RETURN acquired;
END;
$$ LANGUAGE plpgsql;

-- Function to release a named advisory lock
CREATE OR REPLACE FUNCTION release_advisory_lock(lock_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    lock_id BIGINT;
    released BOOLEAN;
BEGIN
    -- Convert lock name to numeric ID
    lock_id := ABS(HASHTEXT(lock_name));
    
    -- Release the lock
    SELECT pg_advisory_unlock(lock_id) INTO released;
    
    -- Remove from tracking table
    DELETE FROM advisory_locks WHERE lock_key = lock_name;
    
    RETURN released;
END;
$$ LANGUAGE plpgsql;

-- Function to check if a lock is currently held
CREATE OR REPLACE FUNCTION is_advisory_lock_held(lock_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    lock_id BIGINT;
BEGIN
    lock_id := ABS(HASHTEXT(lock_name));
    
    -- Check if lock is held (this is session-specific in PostgreSQL)
    RETURN EXISTS (
        SELECT 1 FROM pg_locks 
        WHERE locktype = 'advisory' 
        AND objid = lock_id 
        AND granted = true
    );
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 2. SESSION PLANNING SPECIFIC LOCK FUNCTIONS
-- =====================================================

-- Function to acquire session planning lock for a user
CREATE OR REPLACE FUNCTION acquire_session_planning_lock(
    p_user_id UUID,
    timeout_seconds INTEGER DEFAULT 30
)
RETURNS BOOLEAN AS $$
DECLARE
    lock_name TEXT;
    acquired BOOLEAN;
BEGIN
    lock_name := 'session_planning_' || p_user_id::TEXT;
    
    SELECT acquire_advisory_lock(lock_name, timeout_seconds) INTO acquired;
    
    -- Update user_id in tracking table
    IF acquired THEN
        UPDATE advisory_locks 
        SET user_id = p_user_id 
        WHERE lock_key = lock_name;
    END IF;
    
    RETURN acquired;
END;
$$ LANGUAGE plpgsql;

-- Function to release session planning lock for a user
CREATE OR REPLACE FUNCTION release_session_planning_lock(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    lock_name TEXT;
BEGIN
    lock_name := 'session_planning_' || p_user_id::TEXT;
    
    RETURN release_advisory_lock(lock_name);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 3. LOCK CLEANUP AND MONITORING
-- =====================================================

-- Function to clean up expired locks
CREATE OR REPLACE FUNCTION cleanup_expired_advisory_locks()
RETURNS INTEGER AS $$
DECLARE
    cleanup_count INTEGER;
BEGIN
    -- Get count of expired locks
    SELECT COUNT(*) INTO cleanup_count
    FROM advisory_locks 
    WHERE expires_at < NOW();
    
    -- Delete expired lock records
    DELETE FROM advisory_locks WHERE expires_at < NOW();
    
    RETURN cleanup_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get current lock status for monitoring
CREATE OR REPLACE FUNCTION get_advisory_lock_status()
RETURNS TABLE (
    lock_key TEXT,
    user_id UUID,
    acquired_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN,
    duration_minutes INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        al.lock_key,
        al.user_id,
        al.acquired_at,
        al.expires_at,
        al.expires_at > NOW() AS is_active,
        EXTRACT(EPOCH FROM (NOW() - al.acquired_at))::INTEGER / 60 AS duration_minutes
    FROM advisory_locks al
    ORDER BY al.acquired_at DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 4. AUTOMATIC CLEANUP JOB SETUP
-- =====================================================

-- Create a cleanup function that can be called periodically
CREATE OR REPLACE FUNCTION periodic_advisory_lock_cleanup()
RETURNS VOID AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    SELECT cleanup_expired_advisory_locks() INTO cleaned_count;
    
    -- Log cleanup activity
    INSERT INTO migration_log (migration_name, notes) 
    VALUES (
        'advisory_lock_cleanup', 
        'Cleaned up ' || cleaned_count || ' expired advisory locks'
    );
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 5. BLUEPRINT-SPECIFIC HELPER FUNCTIONS
-- =====================================================

-- Check if user already has a planned session (with lock safety)
CREATE OR REPLACE FUNCTION has_planned_session(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM sessions s
        WHERE s.user_id = p_user_id 
        AND s.status = 'planned'
        AND EXISTS (
            SELECT 1 FROM session_packs sp 
            WHERE sp.session_id = s.id
        )
    );
END;
$$ LANGUAGE plpgsql;

-- Get or create session with advisory lock protection
CREATE OR REPLACE FUNCTION get_or_create_session_safe(p_user_id UUID)
RETURNS UUID AS $$
DECLARE
    session_uuid UUID;
    lock_acquired BOOLEAN;
BEGIN
    -- Try to acquire planning lock
    SELECT acquire_session_planning_lock(p_user_id, 10) INTO lock_acquired;
    
    IF NOT lock_acquired THEN
        RAISE EXCEPTION 'Could not acquire session planning lock for user %', p_user_id;
    END IF;
    
    BEGIN
        -- Check for existing planned session
        SELECT s.id INTO session_uuid
        FROM sessions s
        WHERE s.user_id = p_user_id 
        AND s.status = 'planned'
        LIMIT 1;
        
        IF session_uuid IS NULL THEN
            -- Create new session
            INSERT INTO sessions (id, user_id, status, created_at)
            VALUES (gen_random_uuid(), p_user_id, 'planned', NOW())
            RETURNING id INTO session_uuid;
        END IF;
        
        -- Always release lock in finally block
        PERFORM release_session_planning_lock(p_user_id);
        
        RETURN session_uuid;
        
    EXCEPTION
        WHEN OTHERS THEN
            -- Ensure lock is released even on exception
            PERFORM release_session_planning_lock(p_user_id);
            RAISE;
    END;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 6. MONITORING AND DIAGNOSTICS
-- =====================================================

-- View for monitoring current advisory locks
CREATE OR REPLACE VIEW advisory_lock_monitor AS
SELECT 
    al.lock_key,
    al.user_id,
    al.acquired_at,
    al.expires_at,
    CASE 
        WHEN al.expires_at > NOW() THEN 'ACTIVE'
        ELSE 'EXPIRED'
    END AS status,
    EXTRACT(EPOCH FROM (NOW() - al.acquired_at))::INTEGER AS duration_seconds,
    EXTRACT(EPOCH FROM (al.expires_at - NOW()))::INTEGER AS remaining_seconds
FROM advisory_locks al
ORDER BY al.acquired_at DESC;

-- =====================================================
-- 7. MIGRATION COMPLETION
-- =====================================================

-- Record this migration
INSERT INTO migration_log (migration_name, notes) 
VALUES ('016_advisory_locks', 'Created PostgreSQL advisory lock system for session planning');

-- Create initial cleanup to remove any existing expired locks
SELECT cleanup_expired_advisory_locks();

COMMIT;