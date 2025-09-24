#!/usr/bin/env python3
"""
Simple data state check without joins
"""

import asyncio
import os
import asyncpg
from pathlib import Path

async def simple_data_check():
    """Simple check of current data state"""
    
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
    
    print("📊 SIMPLE DATA STATE CHECK")
    print("=" * 40)
    
    # Check sessions table structure and data
    sessions_info = await connection.fetchrow("""
        SELECT COUNT(*) as count FROM sessions
    """)
    print(f"📝 Sessions table: {sessions_info['count']} records")
    
    if sessions_info['count'] > 0:
        # Get sample session to check structure
        sample_session = await connection.fetchrow("""
            SELECT session_id, user_id, status, current_position, created_at
            FROM sessions 
            LIMIT 1
        """)
        print(f"   Sample session_id type: {type(sample_session['session_id'])}")
        print(f"   Sample status: {sample_session['status']}")
        print(f"   Sample current_position: {sample_session['current_position']}")
    
    # Check blueprint tables
    tables = ['session_packs', 'session_pack_questions', 'session_answers', 'advisory_locks']
    
    for table in tables:
        count = await connection.fetchval(f"SELECT COUNT(*) FROM {table}")
        print(f"🎯 {table}: {count} records")
    
    # Check session_packs structure if it has data
    packs_count = await connection.fetchval("SELECT COUNT(*) FROM session_packs")
    if packs_count > 0:
        sample_pack = await connection.fetchrow("SELECT session_id, user_id FROM session_packs LIMIT 1")
        print(f"   Sample pack session_id type: {type(sample_pack['session_id'])}")
    
    # Check session_pack_questions structure
    questions_count = await connection.fetchval("SELECT COUNT(*) FROM session_pack_questions")
    if questions_count > 0:
        question_positions = await connection.fetch("""
            SELECT position, COUNT(*) as count 
            FROM session_pack_questions 
            GROUP BY position 
            ORDER BY position
            LIMIT 12
        """)
        print(f"📋 Question positions distribution:")
        for pos_info in question_positions:
            print(f"   Position {pos_info['position']}: {pos_info['count']} questions")
    
    await connection.close()
    
    print(f"\n🎯 PHASE 1B STATUS:")
    if packs_count > 0 and questions_count > 0:
        print("   ✅ Blueprint data already exists!")
        print("   🔄 Phase 1B appears to be already completed")
        print("   📋 Ready to validate and proceed to Phase 2")
    else:
        print("   📝 Blueprint tables exist but are empty")
        print("   🔄 Need to migrate data to blueprint format")
    
    return packs_count > 0

if __name__ == "__main__":
    has_data = asyncio.run(simple_data_check())
    if has_data:
        print("✅ Phase 1B: Data appears to be already migrated")
    else:
        print("🔄 Phase 1B: Migration needed")