"""
Fix Session 511067a1 - Generate Missing Pack
This script manually triggers pack generation for the stuck session
"""
import os
import sys
import asyncio
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bg_job_queue import job_queue
from database import SessionLocal

SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"
USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"

async def fix_session():
    print("=" * 80)
    print("FIXING SESSION 511067a1 - Generating Missing Pack")
    print("=" * 80)
    
    db = SessionLocal()
    
    try:
        # 1. Verify session exists
        print("\n1. Verifying session...")
        result = db.execute(text("""
            SELECT session_id, user_id, sess_seq, status
            FROM sessions
            WHERE session_id = :session_id
        """), {"session_id": SESSION_ID})
        
        session = result.fetchone()
        if not session:
            print(f"✗ Session {SESSION_ID} not found!")
            return False
        
        print(f"✓ Session found: {session[0]}")
        print(f"  User ID: {session[1]}")
        print(f"  Session #: {session[2]}")
        print(f"  Status: {session[3]}")
        
        # 2. Check current pack status
        print("\n2. Checking pack status...")
        result = db.execute(text("""
            SELECT COUNT(*) FROM session_pack_questions
            WHERE session_id = :session_id
        """), {"session_id": SESSION_ID})
        
        q_count = result.scalar()
        print(f"  Current questions in pack: {q_count}")
        
        if q_count >= 12:
            print("✓ Pack already has sufficient questions!")
            return True
        
        # 3. Enqueue PLAN_NEXT_SESSION job with session_id
        print("\n3. Enqueueing pack generation job...")
        
        # Create a specific job for this session
        job_id = await job_queue.enqueue_job(
            job_type="PLAN_NEXT_SESSION",
            user_id=USER_ID,
            session_id=SESSION_ID,  # Include session_id so it generates for this specific session
            correlation_id=None,
            max_attempts=6,
            metadata={
                "sess_seq": session[2],
                "fix_script": True,
                "reason": "Manual fix for stuck session 511067a1"
            }
        )
        
        print(f"✓ Job enqueued: {job_id}")
        print(f"  Job type: PLAN_NEXT_SESSION")
        print(f"  User ID: {USER_ID}")
        print(f"  Session ID: {SESSION_ID}")
        
        # 4. Wait a moment and check status
        print("\n4. Waiting for job to process...")
        await asyncio.sleep(5)
        
        result = db.execute(text("""
            SELECT status, attempts, error_message
            FROM bg_jobs
            WHERE id = :job_id
        """), {"job_id": job_id})
        
        job_status = result.fetchone()
        if job_status:
            print(f"  Job status: {job_status[0]}")
            print(f"  Attempts: {job_status[1]}")
            if job_status[2]:
                print(f"  Error: {job_status[2][:200]}")
        
        # 5. Check if pack was created
        print("\n5. Verifying pack creation...")
        result = db.execute(text("""
            SELECT COUNT(*) FROM session_pack_questions
            WHERE session_id = :session_id
        """), {"session_id": SESSION_ID})
        
        new_q_count = result.scalar()
        print(f"  Questions in pack after job: {new_q_count}")
        
        if new_q_count >= 12:
            print("\n✅ SUCCESS: Pack generated successfully!")
            print(f"   Session 511067a1 now has {new_q_count} questions")
            print(f"   User can now resume their session")
            return True
        else:
            print("\n⚠️  Pack generation may still be in progress")
            print("   Check background job status and logs")
            return False
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    result = asyncio.run(fix_session())
    sys.exit(0 if result else 1)
