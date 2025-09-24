#!/usr/bin/env python3
"""
Check current data state in blueprint tables
"""

import asyncio
import os
import asyncpg
import json
from pathlib import Path

async def check_current_data_state():
    """Check current state of data in blueprint and sessions tables"""
    
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
    
    print("📊 CURRENT DATA STATE ANALYSIS")
    print("=" * 50)
    
    # Check sessions table
    sessions_stats = await connection.fetchrow("""
        SELECT 
            COUNT(*) as total_sessions,
            COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_sessions,
            COUNT(CASE WHEN status = 'created' THEN 1 END) as created_sessions,
            COUNT(CASE WHEN current_position IS NOT NULL THEN 1 END) as sessions_with_position,
            COUNT(DISTINCT user_id) as unique_users,
            MIN(created_at) as earliest_session,
            MAX(created_at) as latest_session
        FROM sessions
    """)
    
    print(f"📝 Sessions Table:")
    print(f"   Total sessions: {sessions_stats['total_sessions']}")
    print(f"   Completed: {sessions_stats['completed_sessions']}")
    print(f"   Created: {sessions_stats['created_sessions']}")
    print(f"   With position: {sessions_stats['sessions_with_position']}")
    print(f"   Unique users: {sessions_stats['unique_users']}")
    print(f"   Date range: {sessions_stats['earliest_session']} to {sessions_stats['latest_session']}")
    
    # Check blueprint tables
    blueprint_stats = await connection.fetchrow("""
        SELECT 
            (SELECT COUNT(*) FROM session_packs) as session_packs_count,
            (SELECT COUNT(*) FROM session_pack_questions) as questions_count,
            (SELECT COUNT(*) FROM session_answers) as answers_count,
            (SELECT COUNT(*) FROM advisory_locks) as locks_count
    """)
    
    print(f"\n🎯 Blueprint Tables:")
    print(f"   session_packs: {blueprint_stats['session_packs_count']}")
    print(f"   session_pack_questions: {blueprint_stats['questions_count']}")
    print(f"   session_answers: {blueprint_stats['answers_count']}")
    print(f"   advisory_locks: {blueprint_stats['locks_count']}")
    
    # Check if blueprint data matches sessions
    if blueprint_stats['session_packs_count'] > 0:
        print(f"\n📋 Blueprint Data Analysis:")
        
        # Check pack completeness
        pack_completeness = await connection.fetch("""
            SELECT 
                sp.session_id,
                COUNT(spq.position) as question_count,
                CASE WHEN COUNT(spq.position) = 12 THEN 'COMPLETE' ELSE 'INCOMPLETE' END as status
            FROM session_packs sp
            LEFT JOIN session_pack_questions spq ON sp.session_id = spq.session_id
            GROUP BY sp.session_id
            ORDER BY sp.session_id
            LIMIT 5
        """)
        
        complete_packs = sum(1 for pack in pack_completeness if pack['status'] == 'COMPLETE')
        incomplete_packs = sum(1 for pack in pack_completeness if pack['status'] == 'INCOMPLETE')
        
        print(f"   Complete packs (12 questions): {complete_packs}")
        print(f"   Incomplete packs: {incomplete_packs}")
        
        if pack_completeness:
            print(f"   Sample packs:")
            for pack in pack_completeness[:3]:
                print(f"      {pack['session_id'][:8]}...: {pack['question_count']} questions ({pack['status']})")
    
    # Check session-blueprint alignment
    sessions_with_packs = await connection.fetchval("""
        SELECT COUNT(DISTINCT s.session_id)
        FROM sessions s
        INNER JOIN session_packs sp ON s.session_id = sp.session_id
    """)
    
    sessions_without_packs = sessions_stats['total_sessions'] - sessions_with_packs
    
    print(f"\n🔗 Session-Blueprint Alignment:")
    print(f"   Sessions with blueprint packs: {sessions_with_packs}")
    print(f"   Sessions without blueprint packs: {sessions_without_packs}")
    
    # Sample session data
    if sessions_stats['total_sessions'] > 0:
        sample_session = await connection.fetchrow("""
            SELECT session_id, user_id, status, current_position, created_at
            FROM sessions 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        print(f"\n📄 Sample Recent Session:")
        print(f"   ID: {sample_session['session_id']}")
        print(f"   Status: {sample_session['status']}")
        print(f"   Position: {sample_session['current_position']}")
        print(f"   Created: {sample_session['created_at']}")
    
    # Check question structure if questions exist
    if blueprint_stats['questions_count'] > 0:
        sample_question = await connection.fetchrow("""
            SELECT session_id, position, question_data
            FROM session_pack_questions
            ORDER BY session_id, position
            LIMIT 1
        """)
        
        if sample_question and sample_question['question_data']:
            question_data = sample_question['question_data']
            print(f"\n📋 Sample Question Structure:")
            print(f"   Position: {sample_question['position']}")
            
            if isinstance(question_data, dict):
                print(f"   Available fields: {list(question_data.keys())}")
                
                # Check for required blueprint fields
                required_fields = ['stem', 'options', 'right_answer']
                missing_fields = [field for field in required_fields if field not in question_data]
                
                if not missing_fields:
                    print(f"   ✅ All required blueprint fields present")
                else:
                    print(f"   ⚠️ Missing fields: {missing_fields}")
    
    await connection.close()
    
    # Determine migration strategy
    migration_needed = sessions_without_packs > 0
    data_looks_good = (
        blueprint_stats['session_packs_count'] > 0 and 
        sessions_with_packs > 0
    )
    
    print(f"\n🚦 Migration Assessment:")
    if data_looks_good and not migration_needed:
        print("   ✅ Blueprint data already exists and looks complete")
        print("   Strategy: Validate existing data and proceed to Phase 2")
    elif migration_needed:
        print(f"   ⚠️ {sessions_without_packs} sessions need blueprint migration")
        print("   Strategy: Migrate remaining sessions to blueprint format")
    else:
        print("   🔄 Need to populate blueprint data")
        print("   Strategy: Create blueprint packs for existing sessions")
    
    return {
        'total_sessions': sessions_stats['total_sessions'],
        'blueprint_packs': blueprint_stats['session_packs_count'],
        'sessions_with_packs': sessions_with_packs,
        'migration_needed': migration_needed,
        'data_looks_good': data_looks_good
    }

if __name__ == "__main__":
    result = asyncio.run(check_current_data_state())
    print(f"\nData State: {json.dumps(result, indent=2)}")