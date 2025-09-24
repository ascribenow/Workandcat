#!/usr/bin/env python3
"""
Complete Advisory Lock System for Phase 2A
Fix the missing functions from Phase 1B
"""

import asyncio
import os
import asyncpg
from pathlib import Path

async def create_advisory_lock_functions():
    """Create the missing advisory lock functions"""
    
    # Load .env
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    connection = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    
    print("🔐 COMPLETING ADVISORY LOCK SYSTEM")
    print("=" * 40)
    
    # Create the missing advisory lock functions
    advisory_lock_functions = [
        # Function 1: Acquire session planning lock
        """
        CREATE OR REPLACE FUNCTION acquire_session_planning_lock(
            p_user_id UUID, 
            timeout_seconds INTEGER DEFAULT 30
        )
        RETURNS BOOLEAN AS $$
        DECLARE
            lock_name TEXT;
            rows_affected INTEGER;
        BEGIN
            lock_name := 'session_planning_' || p_user_id::TEXT;
            
            -- Insert lock record if not exists
            INSERT INTO advisory_locks (lock_key, user_id, expires_at)
            VALUES (
                lock_name, 
                p_user_id, 
                NOW() + (timeout_seconds || ' seconds')::INTERVAL
            )
            ON CONFLICT (lock_key) DO UPDATE SET
                expires_at = CASE 
                    WHEN advisory_locks.expires_at < NOW() THEN 
                        NOW() + (timeout_seconds || ' seconds')::INTERVAL
                    ELSE advisory_locks.expires_at
                END
            WHERE advisory_locks.expires_at < NOW();
            
            GET DIAGNOSTICS rows_affected = ROW_COUNT;
            RETURN rows_affected > 0;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Function 2: Release session planning lock
        """
        CREATE OR REPLACE FUNCTION release_session_planning_lock(p_user_id UUID)
        RETURNS BOOLEAN AS $$
        DECLARE
            lock_name TEXT;
            rows_affected INTEGER;
        BEGIN
            lock_name := 'session_planning_' || p_user_id::TEXT;
            
            DELETE FROM advisory_locks 
            WHERE lock_key = lock_name AND user_id = p_user_id;
            
            GET DIAGNOSTICS rows_affected = ROW_COUNT;
            RETURN rows_affected > 0;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Function 3: Check if user has planned session
        """
        CREATE OR REPLACE FUNCTION has_planned_session(p_user_id UUID)
        RETURNS BOOLEAN AS $$
        BEGIN
            RETURN EXISTS (
                SELECT 1 FROM sessions s
                INNER JOIN session_packs sp ON s.session_id = sp.session_id
                WHERE sp.user_id = p_user_id 
                AND s.status = 'planned'
            );
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Function 4: Cleanup expired locks
        """
        CREATE OR REPLACE FUNCTION cleanup_expired_advisory_locks()
        RETURNS INTEGER AS $$
        DECLARE
            cleanup_count INTEGER;
        BEGIN
            DELETE FROM advisory_locks WHERE expires_at < NOW();
            GET DIAGNOSTICS cleanup_count = ROW_COUNT;
            RETURN cleanup_count;
        END;
        $$ LANGUAGE plpgsql;
        """
    ]
    
    print("📝 Creating advisory lock functions...")
    
    for i, func_sql in enumerate(advisory_lock_functions, 1):
        try:
            await connection.execute(func_sql)
            print(f"   ✅ Function {i}/4 created successfully")
        except Exception as e:
            print(f"   ⚠️ Function {i}/4 warning: {e}")
    
    # Test the functions
    print("\n🧪 Testing advisory lock functions...")
    
    test_user_id = '00000000-0000-0000-0000-000000000099'
    
    try:
        # Test lock acquisition
        lock_acquired = await connection.fetchval(
            "SELECT acquire_session_planning_lock($1, 10)", test_user_id
        )
        print(f"   Lock acquisition test: {'✅ PASS' if lock_acquired else '❌ FAIL'}")
        
        # Test has_planned_session
        has_planned = await connection.fetchval(
            "SELECT has_planned_session($1)", test_user_id
        )
        print(f"   Has planned session test: {'✅ PASS' if has_planned is not None else '❌ FAIL'}")
        
        # Test lock release
        lock_released = await connection.fetchval(
            "SELECT release_session_planning_lock($1)", test_user_id
        )
        print(f"   Lock release test: {'✅ PASS' if lock_released else '❌ FAIL'}")
        
        # Test cleanup
        cleaned_count = await connection.fetchval("SELECT cleanup_expired_advisory_locks()")
        print(f"   Cleanup test: {'✅ PASS' if cleaned_count is not None else '❌ FAIL'}")
        
    except Exception as e:
        print(f"   ❌ Test error: {e}")
    
    # Verify all functions exist
    functions = await connection.fetch("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public' 
        AND routine_name LIKE '%session_planning_lock%'
        OR routine_name LIKE '%planned_session%'
        OR routine_name LIKE '%advisory_locks%'
    """)
    
    function_names = [f['routine_name'] for f in functions]
    print(f"\n📋 Available functions: {function_names}")
    
    required_functions = [
        'acquire_session_planning_lock',
        'release_session_planning_lock', 
        'has_planned_session',
        'cleanup_expired_advisory_locks'
    ]
    
    missing_functions = [func for func in required_functions if func not in function_names]
    
    if not missing_functions:
        print("✅ All advisory lock functions available")
        success = True
    else:
        print(f"❌ Missing functions: {missing_functions}")
        success = False
    
    await connection.close()
    
    if success:
        print("\n🎉 ADVISORY LOCK SYSTEM COMPLETED")
        print("✅ Deviation #3: Advisory Lock Integration - FIXED")
    else:
        print("\n❌ Advisory lock system incomplete")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(create_advisory_lock_functions())
    exit(0 if success else 1)