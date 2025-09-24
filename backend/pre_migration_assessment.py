#!/usr/bin/env python3
"""
Pre-Migration Assessment for Phase 1B
Check existing data before migration
"""

import asyncio
import os
import asyncpg
import json
from pathlib import Path

async def assess_existing_data():
    """Assess existing data before migration"""
    
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
    print("🔍 PRE-MIGRATION ASSESSMENT")
    print("=" * 50)
    
    # Check existing adaptive_packs
    adaptive_packs = await connection.fetchrow("""
        SELECT 
            COUNT(*) as total_packs,
            COUNT(CASE WHEN pack_data IS NOT NULL THEN 1 END) as packs_with_data,
            COUNT(CASE WHEN status = 'prepared' THEN 1 END) as prepared_packs,
            COUNT(CASE WHEN status = 'served' THEN 1 END) as served_packs
        FROM adaptive_packs
    """)
    
    print(f"📦 Existing adaptive_packs:")
    print(f"   Total packs: {adaptive_packs['total_packs']}")
    print(f"   Packs with data: {adaptive_packs['packs_with_data']}")
    print(f"   Prepared packs: {adaptive_packs['prepared_packs']}")
    print(f"   Served packs: {adaptive_packs['served_packs']}")
    
    # Check existing sessions
    sessions = await connection.fetchrow("""
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN status = 'created' THEN 1 END) as created_sessions,
            COUNT(CASE WHEN status = 'started' THEN 1 END) as started_sessions,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
            COUNT(DISTINCT user_id) as unique_users
        FROM sessions
    """)
    
    print(f"📝 Existing sessions:")
    print(f"   Total sessions: {sessions['total_sessions']}")
    print(f"   Created: {sessions['created_sessions']}")
    print(f"   Started: {sessions['started_sessions']}")
    print(f"   Completed: {sessions['completed_sessions']}")
    print(f"   Unique users: {sessions['unique_users']}")
    
    # Check question_actions (for answer migration)
    question_actions = await connection.fetchrow("""
        SELECT 
            COUNT(*) as total_actions,
            COUNT(CASE WHEN action = 'submit' THEN 1 END) as submit_actions,
            COUNT(DISTINCT session_id) as sessions_with_actions
        FROM question_actions
    """)
    
    print(f"🎯 Existing question_actions:")
    print(f"   Total actions: {question_actions['total_actions']}")
    print(f"   Submit actions: {question_actions['submit_actions']}")
    print(f"   Sessions with actions: {question_actions['sessions_with_actions']}")
    
    # Sample pack data structure
    sample_pack = await connection.fetchrow("""
        SELECT pack_data 
        FROM adaptive_packs 
        WHERE pack_data IS NOT NULL 
        LIMIT 1
    """)
    
    if sample_pack and sample_pack['pack_data']:
        pack_data = sample_pack['pack_data']
        if isinstance(pack_data, list) and len(pack_data) > 0:
            sample_question = pack_data[0]
            print(f"📋 Sample question structure:")
            print(f"   Keys available: {list(sample_question.keys()) if isinstance(sample_question, dict) else 'Invalid format'}")
            
            # Check for blueprint-required fields
            required_fields = ['id', 'stem', 'option_a', 'option_b', 'option_c', 'option_d', 'answer']
            if isinstance(sample_question, dict):
                missing_fields = [field for field in required_fields if field not in sample_question]
                if missing_fields:
                    print(f"   ⚠️ Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ All required fields present")
    
    # Check blueprint tables (should be empty before migration)
    blueprint_status = await connection.fetchrow("""
        SELECT 
            (SELECT COUNT(*) FROM session_packs) as existing_session_packs,
            (SELECT COUNT(*) FROM session_pack_questions) as existing_questions,
            (SELECT COUNT(*) FROM session_answers) as existing_answers
    """)
    
    print(f"📊 Blueprint tables (should be empty):")
    print(f"   session_packs: {blueprint_status['existing_session_packs']}")
    print(f"   session_pack_questions: {blueprint_status['existing_questions']}")
    print(f"   session_answers: {blueprint_status['existing_answers']}")
    
    await connection.close()
    
    # Determine migration readiness
    migration_ready = (
        adaptive_packs['packs_with_data'] > 0 and 
        blueprint_status['existing_session_packs'] == 0
    )
    
    print(f"\n🚦 Migration Readiness: {'✅ READY' if migration_ready else '⚠️ NOT READY'}")
    
    return {
        'migration_ready': migration_ready,
        'adaptive_packs_count': adaptive_packs['packs_with_data'],
        'sessions_count': sessions['total_sessions'],
        'question_actions_count': question_actions['total_actions']
    }

if __name__ == "__main__":
    result = asyncio.run(assess_existing_data())
    print(f"\nAssessment Result: {json.dumps(result, indent=2)}")