"""
Test script to verify stuck job cleanup and idempotency

Test Flow:
1. Create a stuck job (manually insert with old timestamp)
2. Verify job exists in queue
3. Try to enqueue a new job (should cleanup stuck job and create fresh one)
4. Verify fresh job was created
5. Run the job handler to verify it processes correctly
6. Try to run again to verify idempotency (should skip)
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from sqlalchemy import text
from services.bg_job_queue import job_queue
from services.simplified_job_handlers import run_simplified_summarizer, handle_plan_next_session, handle_update_insights
import uuid

# Test user: twelvrhelp@gmail.com
TEST_USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"
TEST_SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"  # Completed session

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
            for job in deleted:
                print(f"   - {job[1]} ({job[2]})")
        else:
            print("✅ No existing jobs to clean up")
        
        return len(deleted)
    finally:
        db.close()

async def create_stuck_job(job_type, minutes_old=5):
    """Manually create a stuck job with old timestamp"""
    print_section(f"TEST 1: Creating stuck {job_type} job ({minutes_old} min old)")
    
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        old_timestamp = datetime.utcnow() - timedelta(minutes=minutes_old)
        
        # Build dedupe_key
        if job_type == "SUMMARIZE_SESSION":
            dedupe_key = f"u:{TEST_USER_ID}|s:{TEST_SESSION_ID}|{job_type}"
            session_id = TEST_SESSION_ID
        else:
            dedupe_key = f"u:{TEST_USER_ID}|{job_type}"
            session_id = None
        
        db.execute(text("""
            INSERT INTO bg_jobs (
                id, job_type, user_id, session_id, dedupe_key, 
                status, attempts, max_attempts, next_attempt_at, created_at
            ) VALUES (
                :id, :job_type, :user_id, :session_id, :dedupe_key,
                'queued', 0, 6, :next_attempt_at, :created_at
            )
        """), {
            "id": job_id,
            "job_type": job_type,
            "user_id": TEST_USER_ID,
            "session_id": session_id,
            "dedupe_key": dedupe_key,
            "next_attempt_at": old_timestamp,
            "created_at": old_timestamp
        })
        
        db.commit()
        
        print(f"✅ Created stuck job:")
        print(f"   Job ID: {job_id}")
        print(f"   Type: {job_type}")
        print(f"   Created: {old_timestamp} ({minutes_old} min ago)")
        print(f"   Dedupe Key: {dedupe_key}")
        
        return job_id
    finally:
        db.close()

async def verify_job_exists(job_id):
    """Verify job exists in database"""
    print_section("TEST 2: Verifying stuck job exists")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT id, job_type, status, created_at
            FROM bg_jobs
            WHERE id = :job_id
        """), {"job_id": job_id}).fetchone()
        
        if result:
            print(f"✅ Job found in database:")
            print(f"   ID: {result[0]}")
            print(f"   Type: {result[1]}")
            print(f"   Status: {result[2]}")
            print(f"   Created: {result[3]}")
            return True
        else:
            print(f"❌ Job not found: {job_id}")
            return False
    finally:
        db.close()

async def enqueue_fresh_job(job_type):
    """Enqueue a fresh job (should trigger cleanup of stuck job)"""
    print_section("TEST 3: Enqueueing fresh job (should cleanup stuck job)")
    
    print(f"📋 Attempting to enqueue fresh {job_type} job...")
    
    if job_type == "SUMMARIZE_SESSION":
        job_id = await job_queue.enqueue_job(
            job_type=job_type,
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID
        )
    else:
        job_id = await job_queue.enqueue_job(
            job_type=job_type,
            user_id=TEST_USER_ID
        )
    
    print(f"✅ Fresh job enqueued: {job_id}")
    return job_id

async def verify_fresh_job_created(old_job_id, new_job_id):
    """Verify old job was deleted and new job was created"""
    print_section("TEST 4: Verifying cleanup happened")
    
    db = SessionLocal()
    try:
        # Check if old job still exists
        old_job = db.execute(text("""
            SELECT id FROM bg_jobs WHERE id = :job_id
        """), {"job_id": old_job_id}).fetchone()
        
        # Check if new job exists
        new_job = db.execute(text("""
            SELECT id, status, created_at FROM bg_jobs WHERE id = :job_id
        """), {"job_id": new_job_id}).fetchone()
        
        if old_job:
            print(f"❌ Old stuck job still exists: {old_job_id}")
            print("   Cleanup did NOT work!")
            return False
        else:
            print(f"✅ Old stuck job was deleted: {old_job_id}")
        
        if new_job:
            print(f"✅ Fresh job created: {new_job_id}")
            print(f"   Status: {new_job[1]}")
            print(f"   Created: {new_job[2]}")
            return True
        else:
            print(f"❌ Fresh job not found: {new_job_id}")
            return False
    finally:
        db.close()

async def run_job_handler(job_id, job_type):
    """Run the job handler to process the job"""
    print_section(f"TEST 5: Running {job_type} handler")
    
    db = SessionLocal()
    try:
        # Get job details
        job = db.execute(text("""
            SELECT id, job_type, user_id, session_id, attempts, max_attempts
            FROM bg_jobs
            WHERE id = :job_id
        """), {"job_id": job_id}).fetchone()
        
        if not job:
            print(f"❌ Job not found: {job_id}")
            return None
        
        job_dict = {
            "id": str(job[0]),
            "job_type": job[1],
            "user_id": job[2],
            "session_id": job[3],
            "attempts": job[4],
            "max_attempts": job[5]
        }
        
        print(f"📋 Processing job: {job_dict['job_type']}")
        
        # Run appropriate handler
        if job_type == "SUMMARIZE_SESSION":
            result = await run_simplified_summarizer(job_dict["user_id"], job_dict["session_id"])
        elif job_type == "PLAN_NEXT_SESSION":
            result = await handle_plan_next_session(job_dict)
        elif job_type == "UPDATE_INSIGHTS":
            result = await handle_update_insights(job_dict)
        else:
            print(f"❌ Unknown job type: {job_type}")
            return None
        
        print(f"✅ Handler completed:")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        return result
    finally:
        db.close()

async def run_job_handler_again(job_id, job_type):
    """Run handler again to test idempotency"""
    print_section(f"TEST 6: Running {job_type} handler AGAIN (idempotency test)")
    
    result = await run_job_handler(job_id, job_type)
    
    if result:
        if result.get('message') and 'already exists' in result.get('message', '').lower():
            print("✅ IDEMPOTENCY PASSED: Handler skipped processing (already exists)")
            return True
        elif result.get('message') and 'too recent' in result.get('message', '').lower():
            print("✅ STALENESS CHECK PASSED: Handler skipped processing (too recent)")
            return True
        else:
            print("⚠️  Handler processed again (may not be idempotent)")
            return False
    
    return False

async def test_summarize_session():
    """Test SUMMARIZE_SESSION with stuck job cleanup"""
    print("\n" + "█"*80)
    print("  TEST SUITE: SUMMARIZE_SESSION")
    print("█"*80)
    
    # Cleanup
    await cleanup_test_jobs()
    
    # Create stuck job
    stuck_job_id = await create_stuck_job("SUMMARIZE_SESSION", minutes_old=5)
    
    # Verify it exists
    exists = await verify_job_exists(stuck_job_id)
    if not exists:
        print("❌ TEST FAILED: Could not create stuck job")
        return False
    
    # Enqueue fresh job (should cleanup stuck one)
    fresh_job_id = await enqueue_fresh_job("SUMMARIZE_SESSION")
    
    # Verify cleanup happened
    cleanup_success = await verify_fresh_job_created(stuck_job_id, fresh_job_id)
    if not cleanup_success:
        print("❌ TEST FAILED: Cleanup did not work")
        return False
    
    # Run the handler
    result = await run_job_handler(fresh_job_id, "SUMMARIZE_SESSION")
    if not result or result.get("status") != "success":
        print("❌ TEST FAILED: Handler did not succeed")
        return False
    
    # Run again to test idempotency
    idempotent = await run_job_handler_again(fresh_job_id, "SUMMARIZE_SESSION")
    
    print("\n" + "█"*80)
    print("  SUMMARIZE_SESSION TEST RESULT")
    print("█"*80)
    if cleanup_success and result.get("status") == "success" and idempotent:
        print("✅ ALL TESTS PASSED!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

async def test_update_insights():
    """Test UPDATE_INSIGHTS with staleness check"""
    print("\n" + "█"*80)
    print("  TEST SUITE: UPDATE_INSIGHTS")
    print("█"*80)
    
    # Cleanup
    await cleanup_test_jobs()
    
    # Create stuck job
    stuck_job_id = await create_stuck_job("UPDATE_INSIGHTS", minutes_old=5)
    
    # Verify it exists
    exists = await verify_job_exists(stuck_job_id)
    if not exists:
        print("❌ TEST FAILED: Could not create stuck job")
        return False
    
    # Enqueue fresh job (should cleanup stuck one)
    fresh_job_id = await enqueue_fresh_job("UPDATE_INSIGHTS")
    
    # Verify cleanup happened
    cleanup_success = await verify_fresh_job_created(stuck_job_id, fresh_job_id)
    if not cleanup_success:
        print("❌ TEST FAILED: Cleanup did not work")
        return False
    
    # Run the handler
    result = await run_job_handler(fresh_job_id, "UPDATE_INSIGHTS")
    if not result or result.get("status") != "success":
        print("❌ TEST FAILED: Handler did not succeed")
        return False
    
    # Run again to test staleness check
    staleness_works = await run_job_handler_again(fresh_job_id, "UPDATE_INSIGHTS")
    
    print("\n" + "█"*80)
    print("  UPDATE_INSIGHTS TEST RESULT")
    print("█"*80)
    if cleanup_success and result.get("status") == "success" and staleness_works:
        print("✅ ALL TESTS PASSED!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

async def main():
    """Run all tests"""
    print("\n" + "█"*80)
    print("  STUCK JOB CLEANUP & IDEMPOTENCY TEST SUITE")
    print("  User: twelvrhelp@gmail.com")
    print("█"*80)
    
    # Test SUMMARIZE_SESSION
    test1_passed = await test_summarize_session()
    
    await asyncio.sleep(2)
    
    # Test UPDATE_INSIGHTS
    test2_passed = await test_update_insights()
    
    # Final cleanup
    await cleanup_test_jobs()
    
    # Summary
    print("\n" + "█"*80)
    print("  FINAL TEST RESULTS")
    print("█"*80)
    print(f"  SUMMARIZE_SESSION: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  UPDATE_INSIGHTS:   {'✅ PASSED' if test2_passed else '❌ FAILED'}")
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
