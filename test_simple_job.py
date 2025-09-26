#!/usr/bin/env python3
"""
Test simple job processing without external dependencies
"""

import asyncio
import sys
import time
import uuid

sys.path.append('/app/backend')

from database import SessionLocal
from sqlalchemy import text

async def test_simple_job_insert():
    """Test inserting into session_packs with correct schema"""
    print("🔧 TESTING SESSION_PACKS INSERT")
    print("=" * 60)
    
    test_user_id = "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1"
    pack_id = str(uuid.uuid4())
    
    db = SessionLocal()
    try:
        # Test the corrected insert statement
        db.execute(text("""
            INSERT INTO session_packs (
                session_id, user_id, constraint_report, created_at
            ) VALUES (
                :session_id, :user_id, :constraint_report, :created_at
            )
        """), {
            "session_id": pack_id,
            "user_id": test_user_id,
            "constraint_report": '{"pack_type": "test", "difficulty_distribution": {"easy": 3, "medium": 6, "hard": 3}}',
            "created_at": "2025-09-26 19:50:00+00:00"
        })
        
        db.commit()
        print(f"   ✅ Successfully inserted session pack: {pack_id[:8]}")
        
        # Verify the insert
        result = db.execute(text("""
            SELECT session_id, user_id, constraint_report
            FROM session_packs 
            WHERE session_id = :session_id
        """), {"session_id": pack_id})
        
        row = result.fetchone()
        if row:
            print(f"   ✅ Verified insert: session_id={str(row.session_id)[:8]}")
            print(f"   📊 Constraint report: {row.constraint_report}")
            return True
        else:
            print(f"   ❌ Insert verification failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Insert failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

async def main():
    success = await test_simple_job_insert()
    
    if success:
        print("\n🎉 Session packs insert test successful!")
        return 0
    else:
        print("\n❌ Session packs insert test failed!")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)