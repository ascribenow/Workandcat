"""
Manual Stuck Job Recovery Test

This is a manual test where YOU control when to run cleanup.

Instructions:
1. Run this script - it will create a stuck job
2. Wait 2 minutes
3. Run the cleanup command provided
4. Verify the results

This simulates a real worker crash scenario.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from sqlalchemy import text
import uuid

TEST_USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"
TEST_SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"

async def cleanup_existing():
    """Clean up existing test jobs"""
    db = SessionLocal()
    try:
        db.execute(text("""
            DELETE FROM bg_jobs WHERE user_id = :user_id
        """), {"user_id": TEST_USER_ID})
        db.commit()
        print("✅ Cleaned up existing jobs\n")
    finally:
        db.close()

async def create_stuck_job():
    """Create a job stuck in running status"""
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        stuck_time = datetime.utcnow() - timedelta(minutes=3)
        
        db.execute(text("""
            INSERT INTO bg_jobs (
                id, job_type, user_id, session_id,
                dedupe_key, status, attempts, max_attempts,
                started_at, created_at
            ) VALUES (
                :id, 'SUMMARIZE_SESSION', :user_id, :session_id,
                :dedupe_key, 'running', 2, 6,
                :started_at, :created_at
            )
        """), {
            "id": job_id,
            "user_id": TEST_USER_ID,
            "session_id": TEST_SESSION_ID,
            "dedupe_key": f"u:{TEST_USER_ID}|s:{TEST_SESSION_ID}|SUMMARIZE_SESSION",
            "started_at": stuck_time,
            "created_at": stuck_time - timedelta(minutes=1)
        })
        db.commit()
        
        print("="*80)
        print("STUCK JOB CREATED")
        print("="*80)
        print(f"Job ID: {job_id}")
        print(f"User: twelvrhelp@gmail.com")
        print(f"Status: running (stuck for 3 minutes)")
        print(f"Attempts: 2/6")
        print("\n" + "="*80)
        print("CURRENT STATE IN DATABASE")
        print("="*80)
        
        # Show current state
        result = db.execute(text("""
            SELECT id, status, attempts, started_at,
                   EXTRACT(EPOCH FROM (NOW() - started_at))/60 as minutes_stuck
            FROM bg_jobs
            WHERE id = :job_id
        """), {"job_id": job_id}).fetchone()
        
        print(f"Job ID: {result[0][:16]}...")
        print(f"Status: {result[1]}")
        print(f"Attempts: {result[2]}/6")
        print(f"Stuck for: {result[4]:.1f} minutes")
        
        print("\n" + "="*80)
        print("TEST THE CLEANUP")
        print("="*80)
        print("\nTo test the cleanup, run this command:\n")
        print(f"cd /app/backend && python -c \"")
        print(f"import asyncio")
        print(f"from services.bg_job_queue import job_queue")
        print(f"result = asyncio.run(job_queue.cleanup_stuck_running_jobs(timeout_minutes=2))")
        print(f"print(f'\\\\nCleanup result: {{result}}')")
        print(f"\"\n")
        
        print("="*80)
        print("THEN VERIFY THE RESULT")
        print("="*80)
        print("\nAfter running cleanup, verify with:\n")
        print(f"cd /app/backend && python -c \"")
        print(f"from database import SessionLocal")
        print(f"from sqlalchemy import text")
        print(f"db = SessionLocal()")
        print(f"result = db.execute(text('SELECT id, status, attempts FROM bg_jobs WHERE id = \\\\'{job_id}\\\\'")).fetchone()")
        print(f"print(f'Status: {{result[1]}}, Attempts: {{result[2]}/6')")
        print(f"db.close()")
        print(f"\"\n")
        
        return job_id
        
    finally:
        db.close()

async def main():
    print("\n" + "█"*80)
    print("  MANUAL STUCK JOB RECOVERY TEST")
    print("  User: twelvrhelp@gmail.com")
    print("█"*80 + "\n")
    
    await cleanup_existing()
    await create_stuck_job()
    
    print("="*80)
    print("WAITING FOR YOU TO TEST...")
    print("="*80)
    print("\nThis script has created a stuck job.")
    print("Now YOU can manually test the cleanup by running the commands above.")
    print("\nExpected behavior:")
    print("  - Cleanup should detect the stuck job (> 2 min)")
    print("  - Job should be reset to 'queued' status")
    print("  - Attempts should remain at 2/6")
    print("  - next_attempt_at should be set (NOW + 4 min backoff)")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
