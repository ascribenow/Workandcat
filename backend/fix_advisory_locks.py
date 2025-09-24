#!/usr/bin/env python3
"""
Fix advisory lock function
"""

import asyncio
import os
import asyncpg
from pathlib import Path

async def fix_advisory_locks():
    """Fix the advisory lock function"""
    
    # Load .env
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    database_url = os.getenv('DATABASE_URL')
    connection = await asyncpg.connect(database_url)
    
    # Fixed advisory lock function
    fixed_function = """
    CREATE OR REPLACE FUNCTION acquire_session_planning_lock(p_user_id UUID, timeout_seconds INTEGER DEFAULT 30)
    RETURNS BOOLEAN AS $$
    DECLARE
        lock_name TEXT;
        rows_affected INTEGER;
    BEGIN
        lock_name := 'session_planning_' || p_user_id::TEXT;
        
        INSERT INTO advisory_locks (lock_key, user_id, expires_at)
        VALUES (lock_name, p_user_id, NOW() + (timeout_seconds || ' seconds')::INTERVAL)
        ON CONFLICT (lock_key) DO NOTHING;
        
        GET DIAGNOSTICS rows_affected = ROW_COUNT;
        RETURN rows_affected > 0;
    END;
    $$ LANGUAGE plpgsql;
    """
    
    await connection.execute(fixed_function)
    print("✅ Fixed advisory lock function")
    
    # Test the fixed function
    test_user_id = '00000000-0000-0000-0000-000000000000'
    
    # Clean up any existing test locks
    await connection.execute("DELETE FROM advisory_locks WHERE user_id = $1", test_user_id)
    
    # Test lock acquisition
    lock_result = await connection.fetchval(
        "SELECT acquire_session_planning_lock($1, 10)", test_user_id
    )
    
    print(f"✅ Lock acquisition test: {lock_result}")
    
    # Test lock release
    release_result = await connection.fetchval(
        "SELECT release_session_planning_lock($1)", test_user_id
    )
    
    print(f"✅ Lock release test: {release_result}")
    
    await connection.close()
    print("🎉 Advisory lock system working correctly!")

if __name__ == "__main__":
    asyncio.run(fix_advisory_locks())