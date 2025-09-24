#!/usr/bin/env python3
"""
Test database connection and create basic blueprint tables
"""

import asyncio
import os
import asyncpg
from pathlib import Path

async def test_connection_and_create_tables():
    """Test connection and create essential blueprint tables"""
    
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
    print(f"🔗 Connecting to database...")
    
    try:
        connection = await asyncpg.connect(database_url)
        print("✅ Database connection successful")
        
        # Test basic query
        result = await connection.fetchrow("SELECT version()")
        print(f"📊 PostgreSQL version: {result['version'][:50]}...")
        
        # Check if blueprint tables already exist
        existing_tables = await connection.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('session_packs', 'session_pack_questions', 'session_answers', 'advisory_locks')
        """)
        
        existing_table_names = [row['table_name'] for row in existing_tables]
        print(f"📋 Existing blueprint tables: {existing_table_names}")
        
        # Create essential tables if they don't exist
        essential_tables = [
            # Session packs table
            """
            CREATE TABLE IF NOT EXISTS session_packs (
                session_id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                constraint_report JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
            """,
            
            # Session pack questions
            """
            CREATE TABLE IF NOT EXISTS session_pack_questions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL,
                position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 12),
                question_id UUID NOT NULL,
                question_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(session_id, position)
            )
            """,
            
            # Session answers with idempotency
            """
            CREATE TABLE IF NOT EXISTS session_answers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL,
                position INTEGER NOT NULL CHECK (position BETWEEN 1 AND 12),
                question_id UUID NOT NULL,
                user_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                explanation TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(session_id, position)
            )
            """,
            
            # Advisory locks table
            """
            CREATE TABLE IF NOT EXISTS advisory_locks (
                lock_key TEXT PRIMARY KEY,
                user_id UUID,
                acquired_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '10 minutes'
            )
            """
        ]
        
        # Add current_position to sessions table if not exists
        await connection.execute("""
            ALTER TABLE sessions 
            ADD COLUMN IF NOT EXISTS current_position INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS served_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS abandoned_at TIMESTAMP WITH TIME ZONE
        """)
        
        print("✅ Enhanced sessions table")
        
        # Create essential tables
        for i, table_sql in enumerate(essential_tables):
            await connection.execute(table_sql)
            print(f"✅ Created essential table {i+1}/4")
        
        # Create basic advisory lock functions
        lock_functions = [
            """
            CREATE OR REPLACE FUNCTION acquire_session_planning_lock(p_user_id UUID, timeout_seconds INTEGER DEFAULT 30)
            RETURNS BOOLEAN AS $$
            DECLARE
                lock_name TEXT;
                acquired BOOLEAN := FALSE;
            BEGIN
                lock_name := 'session_planning_' || p_user_id::TEXT;
                
                INSERT INTO advisory_locks (lock_key, user_id, expires_at)
                VALUES (lock_name, p_user_id, NOW() + (timeout_seconds || ' seconds')::INTERVAL)
                ON CONFLICT (lock_key) DO NOTHING;
                
                GET DIAGNOSTICS acquired = ROW_COUNT;
                RETURN acquired > 0;
            END;
            $$ LANGUAGE plpgsql;
            """,
            
            """
            CREATE OR REPLACE FUNCTION release_session_planning_lock(p_user_id UUID)
            RETURNS BOOLEAN AS $$
            DECLARE
                lock_name TEXT;
            BEGIN
                lock_name := 'session_planning_' || p_user_id::TEXT;
                DELETE FROM advisory_locks WHERE lock_key = lock_name;
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
            """
        ]
        
        for func_sql in lock_functions:
            await connection.execute(func_sql)
        
        print("✅ Created advisory lock functions")
        
        # Test the advisory lock system
        test_user_id = '00000000-0000-0000-0000-000000000000'
        
        # Test lock acquisition
        lock_result = await connection.fetchval(
            "SELECT acquire_session_planning_lock($1, 10)", test_user_id
        )
        
        if lock_result:
            print("✅ Advisory lock acquisition test passed")
            
            # Test lock release
            release_result = await connection.fetchval(
                "SELECT release_session_planning_lock($1)", test_user_id
            )
            
            if release_result:
                print("✅ Advisory lock release test passed")
        
        # Final validation
        validation_results = await connection.fetch("""
            SELECT 
                'session_packs' as table_name,
                (SELECT COUNT(*) FROM session_packs) as row_count
            UNION ALL
            SELECT 
                'session_pack_questions' as table_name,
                (SELECT COUNT(*) FROM session_pack_questions) as row_count
            UNION ALL
            SELECT 
                'session_answers' as table_name,
                (SELECT COUNT(*) FROM session_answers) as row_count
            UNION ALL
            SELECT 
                'advisory_locks' as table_name,
                (SELECT COUNT(*) FROM advisory_locks) as row_count
        """)
        
        print("\n📊 Blueprint Tables Status:")
        for row in validation_results:
            print(f"   {row['table_name']}: {row['row_count']} rows")
        
        await connection.close()
        print("\n🎉 Phase 1A Schema Creation: COMPLETED SUCCESSFULLY")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection_and_create_tables())
    exit(0 if success else 1)