"""
Test script to verify stuck "running" jobs cleanup

Test Flow:
1. Create jobs stuck in "running" status (3 minutes old)
2. Run cleanup_stuck_running_jobs()
3. Verify jobs with remaining attempts are reset to "queued"
4. Verify jobs with exhausted attempts are marked as "failed"
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from sqlalchemy import text
from services.bg_job_queue import job_queue
import uuid

# Test user: twelvrhelp@gmail.com
TEST_USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"
TEST_SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

async def cleanup_test_jobs():
    """Clean up any existing test jobs"""
    print_section("CLEANUP: Removing existing test jobs")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            DELETE FROM bg_jobs
            WHERE user_id = :user_id
            RETURNING id, job_type, status
        """), {"user_id": TEST_USER_ID})
        
        deleted = result.fetchall()
        db.commit()
        
        if deleted:
            print(f"✅ Deleted {len(deleted)} existing jobs for test user")
        else:
            print("✅ No existing jobs to clean up")
        
        return len(deleted)
    finally:
        db.close()

async def create_stuck_running_job(attempts, max_attempts=6, minutes_old=3, test_case_id=None):
    """Create a job stuck in 'running' status"""
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        old_timestamp = datetime.utcnow() - timedelta(minutes=minutes_old)
        
        # Use unique dedupe_key for each test case
        session_suffix = f"-test{test_case_id}" if test_case_id else ""
        dedupe_key = f"u:{TEST_USER_ID}|s:{TEST_SESSION_ID}{session_suffix}|SUMMARIZE_SESSION"
        
        db.execute(text("""
            INSERT INTO bg_jobs (
                id, job_type, user_id, session_id, dedupe_key, 
                status, attempts, max_attempts, started_at, created_at
            ) VALUES (
                :id, :job_type, :user_id, :session_id, :dedupe_key,
                'running', :attempts, :max_attempts, :started_at, :created_at
            )
        """), {
            "id": job_id,
            "job_type": "SUMMARIZE_SESSION",
            "user_id": TEST_USER_ID,
            "session_id": TEST_SESSION_ID,
            "dedupe_key": dedupe_key,
            "attempts": attempts,
            "max_attempts": max_attempts,
            "started_at": old_timestamp,
            "created_at": old_timestamp - timedelta(minutes=5)
        })
        
        db.commit()
        
        print(f"✅ Created stuck running job:")
        print(f"   Job ID: {job_id}")
        print(f"   Attempts: {attempts}/{max_attempts}")
        print(f"   Started: {old_timestamp} ({minutes_old} min ago)")
        
        return job_id
    finally:
        db.close()

async def verify_job_status(job_id, expected_status):
    """Verify job's current status"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT id, status, attempts, error_message, next_attempt_at
            FROM bg_jobs
            WHERE id = :job_id
        """), {"job_id": job_id}).fetchone()
        
        if result:
            actual_status = result[1]
            print(f"   Job {job_id[:8]}: status = {actual_status}, attempts = {result[2]}")
            
            if actual_status == expected_status:
                print(f"   ✅ Status matches expected: {expected_status}")
                return True
            else:
                print(f"   ❌ Status mismatch: expected {expected_status}, got {actual_status}")
                return False
        else:
            print(f"   ❌ Job not found: {job_id}")
            return False
    finally:
        db.close()

async def test_stuck_running_jobs_cleanup():
    """Test cleanup of stuck running jobs"""
    print("\n" + "█"*80)
    print("  TEST: STUCK RUNNING JOBS CLEANUP")
    print("█"*80)
    
    # Cleanup existing jobs
    await cleanup_test_jobs()
    
    # Test Case 1: Job with attempts remaining (should reset to queued)
    print_section("TEST CASE 1: Job with remaining attempts (2/6)")
    job1_id = await create_stuck_running_job(attempts=2, max_attempts=6, minutes_old=3, test_case_id=1)
    
    # Test Case 2: Job with exhausted attempts (should mark as failed)
    print_section("TEST CASE 2: Job with exhausted attempts (6/6)")
    job2_id = await create_stuck_running_job(attempts=6, max_attempts=6, minutes_old=3, test_case_id=2)
    
    # Test Case 3: Job just at the limit (5/6) - should reset
    print_section("TEST CASE 3: Job just below limit (5/6)")
    job3_id = await create_stuck_running_job(attempts=5, max_attempts=6, minutes_old=3, test_case_id=3)
    
    # Run cleanup
    print_section("RUNNING CLEANUP")
    print("📋 Calling cleanup_stuck_running_jobs(timeout_minutes=2)...")
    result = await job_queue.cleanup_stuck_running_jobs(timeout_minutes=2)
    
    print(f"\n✅ Cleanup completed:")
    print(f"   Reset to queued: {result['reset']}")
    print(f"   Marked as failed: {result['failed']}")
    
    # Verify results
    print_section("VERIFYING RESULTS")
    
    print("\nJob 1 (2/6 attempts - should be reset to queued):")
    job1_success = await verify_job_status(job1_id, "queued")
    
    print("\nJob 2 (6/6 attempts - should be marked as failed):")
    job2_success = await verify_job_status(job2_id, "failed")
    
    print("\nJob 3 (5/6 attempts - should be reset to queued):")
    job3_success = await verify_job_status(job3_id, "queued")
    
    # Final cleanup
    await cleanup_test_jobs()
    
    # Summary
    print("\n" + "█"*80)
    print("  TEST RESULTS")
    print("█"*80)
    
    if job1_success and job2_success and job3_success:
        print("✅ ALL TESTS PASSED!")
        print(f"   - Jobs with remaining attempts: Reset to queued ✅")
        print(f"   - Jobs with exhausted attempts: Marked as failed ✅")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

async def test_periodic_cleanup_interval():
    """Test that cleanup doesn't process jobs < 2 minutes old"""
    print("\n" + "█"*80)
    print("  TEST: PERIODIC CLEANUP INTERVAL (2 minute threshold)")
    print("█"*80)
    
    await cleanup_test_jobs()
    
    # Create a job that's been running for only 1 minute
    print_section("Creating job stuck for 1 minute (should NOT be cleaned)")
    job_id = await create_stuck_running_job(attempts=2, max_attempts=6, minutes_old=1)
    
    # Run cleanup with 2 minute threshold
    print_section("RUNNING CLEANUP (2 min threshold)")
    result = await job_queue.cleanup_stuck_running_jobs(timeout_minutes=2)
    
    print(f"\n✅ Cleanup completed:")
    print(f"   Reset to queued: {result['reset']}")
    print(f"   Marked as failed: {result['failed']}")
    
    # Verify job is still in running status
    print_section("VERIFYING JOB STATUS")
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT status FROM bg_jobs WHERE id = :job_id
        """), {"job_id": job_id}).fetchone()
        
        if result and result[0] == "running":
            print(f"✅ Job still in 'running' status (correctly not cleaned up)")
            await cleanup_test_jobs()
            return True
        else:
            print(f"❌ Job was cleaned up (should not have been)")
            await cleanup_test_jobs()
            return False
    finally:
        db.close()

async def main():
    """Run all tests"""
    print("\n" + "█"*80)
    print("  STUCK RUNNING JOBS CLEANUP TEST SUITE")
    print("  User: twelvrhelp@gmail.com")
    print("█"*80)
    
    # Test 1: Cleanup logic
    test1_passed = await test_stuck_running_jobs_cleanup()
    
    await asyncio.sleep(2)
    
    # Test 2: Interval threshold
    test2_passed = await test_periodic_cleanup_interval()
    
    # Summary
    print("\n" + "█"*80)
    print("  FINAL TEST RESULTS")
    print("█"*80)
    print(f"  Cleanup Logic:      {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  Interval Threshold: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("█"*80)
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
