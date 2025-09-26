#!/usr/bin/env python3
"""
Test the fixed job processing
"""

import asyncio
import sys
import time

sys.path.append('/app/backend')

from services.bg_job_queue import job_queue, JobType
from database import SessionLocal
from sqlalchemy import text

async def test_fixed_jobs():
    print("🔧 TESTING FIXED JOB PROCESSING")
    print("=" * 60)
    
    test_user_id = "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1"
    test_session_id = "test-session-" + str(int(time.time()))
    
    try:
        # 1. Enqueue a PLAN_NEXT_SESSION job directly to test the fix
        print("📋 Enqueueing PLAN_NEXT_SESSION job...")
        
        job_id = await job_queue.enqueue_job(
            job_type=JobType.PLAN_NEXT_SESSION.value,
            user_id=test_user_id,
            session_id=None  # Planning jobs don't need session_id
        )
        
        print(f"   ✅ Enqueued job: {job_id[:8]}")
        
        # 2. Process the job
        print("⚙️ Processing job...")
        
        processed = await job_queue.process_single_job()
        
        if processed:
            print(f"   ✅ Job processed successfully")
        else:
            print(f"   📊 No job was processed")
        
        # 3. Check job status
        print("🔍 Checking job status...")
        
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT id, job_type, status, attempts, error_message, completed_at
                FROM bg_jobs 
                WHERE id = :job_id
            """), {"job_id": job_id})
            
            job_row = result.fetchone()
            
            if job_row:
                print(f"   📊 Job status: {job_row.status}")
                print(f"   📊 Attempts: {job_row.attempts}")
                if job_row.error_message:
                    print(f"   ❌ Error: {job_row.error_message}")
                else:
                    print(f"   ✅ No errors")
                if job_row.completed_at:
                    print(f"   ✅ Completed at: {job_row.completed_at}")
                
                return job_row.status == 'succeeded'
            else:
                print(f"   ❌ Job not found")
                return False
                
        finally:
            db.close()
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

async def main():
    success = await test_fixed_jobs()
    
    if success:
        print("\n🎉 Fixed job processing test successful!")
        return 0
    else:
        print("\n❌ Fixed job processing test failed!")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)