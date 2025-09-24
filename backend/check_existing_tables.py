#!/usr/bin/env python3
"""
Check existing tables before migration
"""

import asyncio
import os
import asyncpg
from pathlib import Path

async def check_existing_tables():
    """Check what tables currently exist"""
    
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
    
    print("🔍 EXISTING DATABASE TABLES")
    print("=" * 50)
    
    # Get all tables
    tables = await connection.fetch("""
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    print("📋 Current tables:")
    for table in tables:
        print(f"   {table['table_name']} ({table['table_type']})")
    
    # Check if we have session-related tables
    session_tables = [table for table in tables if 'session' in table['table_name'].lower()]
    if session_tables:
        print(f"\n📝 Session-related tables: {[t['table_name'] for t in session_tables]}")
        
        # Check sessions table structure
        if any(t['table_name'] == 'sessions' for t in session_tables):
            sessions_columns = await connection.fetch("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'sessions' AND table_schema = 'public'
                ORDER BY ordinal_position
            """)
            
            print(f"\n📊 Sessions table structure:")
            for col in sessions_columns:
                print(f"   {col['column_name']}: {col['data_type']} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
            
            # Check sample session data
            session_count = await connection.fetchval("SELECT COUNT(*) FROM sessions")
            print(f"   Total sessions: {session_count}")
            
            if session_count > 0:
                sample_session = await connection.fetchrow("SELECT * FROM sessions LIMIT 1")
                print(f"   Sample session status: {sample_session.get('status', 'N/A')}")
    
    # Check question-related tables
    question_tables = [table for table in tables if 'question' in table['table_name'].lower()]
    if question_tables:
        print(f"\n❓ Question-related tables: {[t['table_name'] for t in question_tables]}")
    
    # Check if blueprint tables exist
    blueprint_tables = ['session_packs', 'session_pack_questions', 'session_answers', 'advisory_locks']
    existing_blueprint = [table['table_name'] for table in tables if table['table_name'] in blueprint_tables]
    
    print(f"\n🎯 Blueprint tables: {existing_blueprint}")
    
    await connection.close()
    
    # Determine what kind of migration we need
    has_sessions = any(t['table_name'] == 'sessions' for t in tables)
    has_blueprint = len(existing_blueprint) == 4
    
    print(f"\n🚦 Migration Status:")
    print(f"   Has sessions table: {'✅' if has_sessions else '❌'}")
    print(f"   Has blueprint tables: {'✅' if has_blueprint else '❌'}")
    
    if has_sessions and has_blueprint:
        print("   Strategy: Create sample data for blueprint system testing")
    elif has_sessions:
        print("   Strategy: Migrate sessions to blueprint format")
    else:
        print("   Strategy: Create fresh blueprint schema")

if __name__ == "__main__":
    asyncio.run(check_existing_tables())