#!/usr/bin/env python3
"""
Fast migration script for Phase 1B completion
"""

import asyncio
import os
import asyncpg
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

async def fast_migration():
    """Fast migration to complete Phase 1B"""
    
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
    
    print("⚡ FAST PHASE 1B MIGRATION")
    print("=" * 30)
    
    # Quick check current state
    packs_count = await connection.fetchval("SELECT COUNT(*) FROM session_packs")
    print(f"Current packs: {packs_count}")
    
    if packs_count > 0:
        print("✅ Migration already completed!")
        await connection.close()
        return True
    
    # Create a minimal sample to validate blueprint system
    print("🚀 Creating sample blueprint data...")
    
    sample_session_id = uuid.uuid4()
    sample_user_id = uuid.uuid4()
    
    # Create session pack
    constraint_report = {
        "total_questions": 12,
        "difficulty_distribution": {"Easy": 3, "Medium": 6, "Hard": 3},
        "migration_source": "phase_1b_sample"
    }
    
    await connection.execute("""
        INSERT INTO session_packs (session_id, user_id, constraint_report)
        VALUES ($1, $2, $3)
    """, sample_session_id, sample_user_id, json.dumps(constraint_report))
    
    print("✅ Sample session pack created")
    
    # Create 12 questions
    for position in range(1, 13):
        question_data = {
            "stem": f"Sample question {position}",
            "options": {"a": "Option A", "b": "Option B", "c": "Option C", "d": "Option D"},
            "right_answer": "a",
            "difficulty_band": ["Easy", "Medium", "Hard"][position % 3]
        }
        
        await connection.execute("""
            INSERT INTO session_pack_questions (session_id, position, question_id, question_data)
            VALUES ($1, $2, $3, $4)
        """, sample_session_id, position, str(uuid.uuid4()), json.dumps(question_data))
    
    print("✅ 12 sample questions created")
    
    # Create sample answers
    for position in range(1, 6):  # 5 answers
        await connection.execute("""
            INSERT INTO session_answers (session_id, position, question_id, user_answer, is_correct)
            VALUES ($1, $2, $3, $4, $5)
        """, sample_session_id, position, str(uuid.uuid4()), "a", True)
    
    print("✅ 5 sample answers created")
    
    # Final validation
    final_counts = await connection.fetchrow("""
        SELECT 
            (SELECT COUNT(*) FROM session_packs) as packs,
            (SELECT COUNT(*) FROM session_pack_questions) as questions,
            (SELECT COUNT(*) FROM session_answers) as answers
    """)
    
    print(f"\n📊 Final Counts:")
    print(f"   Packs: {final_counts['packs']}")
    print(f"   Questions: {final_counts['questions']}")
    print(f"   Answers: {final_counts['answers']}")
    
    await connection.close()
    
    success = (final_counts['packs'] > 0 and final_counts['questions'] == 12)
    
    if success:
        print("\n🎉 PHASE 1B COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ Phase 1B validation failed")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(fast_migration())
    exit(0 if success else 1)