"""
End-to-End Job Recovery Test with Real User
User: twelvrhelp@gmail.com

This test simulates a complete real-world scenario:
1. User completes a session
2. SUMMARIZE_SESSION job gets stuck in "running" status (worker crash)
3. User tries to complete another session (dedupe_key blocked)
4. Periodic cleanup detects stuck job and recovers
5. New job can be enqueued and processes successfully
6. Idempotency check prevents duplicate processing
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from sqlalchemy import text
from services.bg_job_queue import job_queue
from services.simplified_job_handlers import run_simplified_summarizer
import uuid

# Real test user
TEST_USER_EMAIL = "twelvrhelp@gmail.com"
TEST_USER_ID = "b223f5b0-5aed-40e1-929e-fbfd2a2bc5ca"
TEST_SESSION_ID = "511067a1-0cf5-4f81-98e0-7b2b6c315daf"  # Real completed session

def print_banner(title):
    print("\n" + "█"*80)
    print(f"  {title}")
    print("█"*80)

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

async def cleanup_test_jobs():
    """Clean up any existing test jobs"""
    print_section("STEP 0: Cleanup existing jobs")
    
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
            print(f"✅ Deleted {len(deleted)} existing jobs")
            for job in deleted:
                print(f"   - {job[1]} ({job[2]})")
        else:
            print("✅ No existing jobs found")
        
        return len(deleted)
    finally:
        db.close()

async def verify_session_exists():
    """Verify the test session exists and is completed"""
    print_section("STEP 1: Verify test session exists")
    
    db = SessionLocal()
    try:
        session = db.execute(text("""
            SELECT session_id, user_id, status, completed_at,
                   total_questions, questions_answered
            FROM sessions
            WHERE session_id = :session_id AND user_id = :user_id
        """), {
            "session_id": TEST_SESSION_ID,
            "user_id": TEST_USER_ID
        }).fetchone()
        
        if not session:
            print(f"❌ Session {TEST_SESSION_ID} not found!")
            return False
        
        print(f"✅ Found session:")
        print(f"   User: {TEST_USER_EMAIL}")
        print(f"   Session ID: {session[0]}")
        print(f"   Status: {session[2]}")
        print(f"   Completed: {session[3]}")
        print(f"   Questions: {session[5]}/{session[4]}")
        
        return True
    finally:
        db.close()

async def simulate_stuck_job():
    """Simulate a job that gets stuck in running status (worker crash)"""
    print_section("STEP 2: Simulate stuck job (worker crash scenario)")
    
    db = SessionLocal()
    try:
        job_id = str(uuid.uuid4())
        # Job started 3 minutes ago and got stuck
        stuck_timestamp = datetime.utcnow() - timedelta(minutes=3)
        
        dedupe_key = f"u:{TEST_USER_ID}|s:{TEST_SESSION_ID}|SUMMARIZE_SESSION"
        
        print(f"📋 Creating stuck job:")
        print(f"   Job ID: {job_id}")
        print(f"   Type: SUMMARIZE_SESSION")
        print(f"   User: {TEST_USER_EMAIL}")
        print(f"   Session: {TEST_SESSION_ID[:8]}...")
        print(f"   Stuck since: {stuck_timestamp} (3 min ago)")
        print(f"   Scenario: Worker crashed during processing")
        
        db.execute(text("""
            INSERT INTO bg_jobs (
                id, job_type, user_id, session_id, dedupe_key, 
                status, attempts, max_attempts, started_at, created_at
            ) VALUES (
                :id, :job_type, :user_id, :session_id, :dedupe_key,
                'running', 1, 6, :started_at, :created_at
            )
        """), {
            "id": job_id,
            "job_type": "SUMMARIZE_SESSION",
            "user_id": TEST_USER_ID,
            "session_id": TEST_SESSION_ID,
            "dedupe_key": dedupe_key,
            "started_at": stuck_timestamp,
            "created_at": stuck_timestamp - timedelta(minutes=1)
        })
        
        db.commit()
        
        print(f"✅ Stuck job created successfully")
        return job_id
    finally:
        db.close()

async def attempt_new_job_enqueue():
    """Try to enqueue a new job while old one is stuck (should fail with dedupe)"""
    print_section("STEP 3: Attempt to enqueue new job (dedupe key blocked)")
    
    print(f"📋 User tries to complete another session...")
    print(f"   This should fail because dedupe_key is blocked by stuck job")
    
    try:
        # This should fail due to dedupe key constraint
        job_id = await job_queue.enqueue_job(
            job_type="SUMMARIZE_SESSION",
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID
        )
        
        print(f"⚠️  New job created: {job_id}")
        print(f"   (This means cleanup already happened or dedupe didn't work)")
        return job_id, False
    except Exception as e:
        print(f"❌ Failed to enqueue (expected): {type(e).__name__}")
        print(f"   Error: {str(e)[:100]}...")
        print(f"✅ This is correct - dedupe_key is protecting against duplicates")
        return None, True

async def run_cleanup_manually():
    """Manually trigger cleanup to recover stuck job"""
    print_section("STEP 4: Run cleanup manually (simulating periodic cleanup)")
    
    print(f"🔧 Running cleanup_stuck_running_jobs(timeout_minutes=2)...")
    print(f"   In production, this runs automatically every 5 minutes")
    
    result = await job_queue.cleanup_stuck_running_jobs(timeout_minutes=2)
    
    print(f"\n✅ Cleanup completed:")
    print(f"   Jobs reset to queued: {result['reset']}")
    print(f"   Jobs marked as failed: {result['failed']}")
    
    if result['reset'] == 0 and result['failed'] == 0:
        print(f"   ℹ️  No stuck jobs found (they may have been cleaned already)")
    
    return result

async def verify_job_recovered(original_job_id):
    """Verify the stuck job was recovered"""
    print_section("STEP 5: Verify stuck job was recovered")
    
    db = SessionLocal()
    try:
        job = db.execute(text("""
            SELECT id, status, attempts, next_attempt_at, error_message
            FROM bg_jobs
            WHERE id = :job_id
        """), {"job_id": original_job_id}).fetchone()
        
        if not job:
            print(f"❌ Job not found: {original_job_id}")
            return False
        
        status = job[1]
        attempts = job[2]
        next_attempt = job[3]
        error_msg = job[4]
        
        print(f"📊 Job status after cleanup:")
        print(f"   ID: {job[0]}")
        print(f"   Status: {status}")
        print(f"   Attempts: {attempts}/6")
        print(f"   Next attempt: {next_attempt}")
        if error_msg:
            print(f"   Error: {error_msg[:80]}...")
        
        if status == "queued":
            print(f"✅ Job successfully reset to queued for retry!")
            return True
        else:
            print(f"⚠️  Job status is '{status}' (expected 'queued')")
            return False
    finally:
        db.close()

async def enqueue_new_job_after_cleanup():
    """Try enqueueing new job after cleanup (should succeed with stuck job cleanup)"""
    print_section("STEP 6: Enqueue new job after cleanup")
    
    print(f"📋 Enqueueing fresh SUMMARIZE_SESSION job...")
    print(f"   Cleanup should delete stuck job and allow new one")
    
    try:
        job_id = await job_queue.enqueue_job(
            job_type="SUMMARIZE_SESSION",
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID
        )
        
        print(f"✅ Fresh job enqueued successfully: {job_id}")
        return job_id
    except Exception as e:
        print(f"❌ Failed to enqueue: {type(e).__name__}")
        print(f"   Error: {str(e)[:200]}")
        return None

async def run_job_handler(job_id):
    """Process the job to verify it completes successfully"""
    print_section("STEP 7: Process job with handler")
    
    print(f"🔧 Running SUMMARIZE_SESSION handler...")
    print(f"   Job ID: {job_id}")
    
    try:
        result = await run_simplified_summarizer(TEST_USER_ID, TEST_SESSION_ID)
        
        print(f"\n✅ Handler execution result:")
        print(f"   Status: {result.get('status')}")
        print(f"   Summary created: {result.get('summary_created', 'N/A')}")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        if result.get('telemetry'):
            print(f"   Summarizer used: {result['telemetry'].get('summarizer_used', 'N/A')}")
        
        return result.get('status') == 'success'
    except Exception as e:
        print(f"❌ Handler execution failed: {type(e).__name__}")
        print(f"   Error: {str(e)[:200]}")
        return False

async def test_idempotency(job_id):
    """Run handler again to verify idempotency check works"""
    print_section("STEP 8: Test idempotency (run handler again)")
    
    print(f"🔧 Running handler again for same session...")
    print(f"   Should skip processing (summary already exists)")
    
    try:
        result = await run_simplified_summarizer(TEST_USER_ID, TEST_SESSION_ID)
        
        print(f"\n✅ Handler execution result:")
        print(f"   Status: {result.get('status')}")
        print(f"   Summary created: {result.get('summary_created', 'N/A')}")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        if 'already exists' in result.get('message', '').lower():
            print(f"✅ IDEMPOTENCY CHECK PASSED - Handler skipped processing")
            return True
        else:
            print(f"⚠️  Handler processed again (may not be idempotent)")
            return False
    except Exception as e:
        print(f"❌ Handler execution failed: {type(e).__name__}")
        return False

async def verify_final_state():
    """Verify final system state"""
    print_section("STEP 9: Verify final system state")
    
    db = SessionLocal()
    try:
        # Check for any remaining stuck jobs
        stuck_jobs = db.execute(text("""
            SELECT COUNT(*)
            FROM bg_jobs
            WHERE user_id = :user_id
            AND status = 'running'
            AND started_at < NOW() - INTERVAL '2 minutes'
        """), {"user_id": TEST_USER_ID}).fetchone()[0]
        
        # Check for queued jobs
        queued_jobs = db.execute(text("""
            SELECT COUNT(*)
            FROM bg_jobs
            WHERE user_id = :user_id
            AND status = 'queued'
        """), {"user_id": TEST_USER_ID}).fetchone()[0]
        
        # Check for successful summary
        summary_exists = db.execute(text("""
            SELECT COUNT(*)
            FROM session_summary_llm
            WHERE user_id = :user_id
            AND session_id = :session_id
        """), {
            "user_id": TEST_USER_ID,
            "session_id": TEST_SESSION_ID
        }).fetchone()[0]
        
        print(f"📊 System state:")
        print(f"   Stuck running jobs: {stuck_jobs}")
        print(f"   Queued jobs: {queued_jobs}")
        print(f"   Session summary exists: {'Yes' if summary_exists > 0 else 'No'}")
        
        all_good = (stuck_jobs == 0 and summary_exists > 0)
        
        if all_good:
            print(f"\n✅ System is in healthy state!")
        else:
            print(f"\n⚠️  System may need attention")
        
        return all_good
    finally:
        db.close()

async def main():
    """Run complete end-to-end test"""
    print_banner(f"END-TO-END JOB RECOVERY TEST")
    print(f"  User: {TEST_USER_EMAIL}")
    print(f"  Session: {TEST_SESSION_ID[:16]}...")
    print("█"*80)
    
    test_results = {}
    
    # Step 0: Cleanup
    await cleanup_test_jobs()
    
    # Step 1: Verify session exists
    test_results['session_exists'] = await verify_session_exists()
    if not test_results['session_exists']:
        print("\n❌ Cannot proceed without valid session")
        return 1
    
    await asyncio.sleep(1)
    
    # Step 2: Create stuck job
    stuck_job_id = await simulate_stuck_job()
    test_results['stuck_job_created'] = stuck_job_id is not None
    
    await asyncio.sleep(1)
    
    # Step 3: Try to enqueue (should fail)
    _, dedupe_blocked = await attempt_new_job_enqueue()
    test_results['dedupe_protection'] = dedupe_blocked
    
    await asyncio.sleep(1)
    
    # Step 4: Run cleanup
    cleanup_result = await run_cleanup_manually()
    test_results['cleanup_ran'] = cleanup_result['reset'] > 0 or cleanup_result['failed'] > 0
    
    await asyncio.sleep(1)
    
    # Step 5: Verify recovery
    test_results['job_recovered'] = await verify_job_recovered(stuck_job_id)
    
    await asyncio.sleep(1)
    
    # Step 6: Enqueue fresh job
    fresh_job_id = await enqueue_new_job_after_cleanup()
    test_results['fresh_job_enqueued'] = fresh_job_id is not None
    
    if fresh_job_id:
        await asyncio.sleep(1)
        
        # Step 7: Process job
        test_results['job_processed'] = await run_job_handler(fresh_job_id)
        
        await asyncio.sleep(1)
        
        # Step 8: Test idempotency
        test_results['idempotency_works'] = await test_idempotency(fresh_job_id)
    
    await asyncio.sleep(1)
    
    # Step 9: Final state
    test_results['final_state_healthy'] = await verify_final_state()
    
    # Cleanup
    await cleanup_test_jobs()
    
    # Summary
    print_banner("TEST RESULTS SUMMARY")
    print(f"\n{'Test Step':<30} {'Result'}")
    print("="*80)
    print(f"{'Session exists':<30} {'✅ PASS' if test_results.get('session_exists') else '❌ FAIL'}")
    print(f"{'Stuck job created':<30} {'✅ PASS' if test_results.get('stuck_job_created') else '❌ FAIL'}")
    print(f"{'Dedupe protection works':<30} {'✅ PASS' if test_results.get('dedupe_protection') else '❌ FAIL'}")
    print(f"{'Cleanup ran successfully':<30} {'✅ PASS' if test_results.get('cleanup_ran') else '❌ FAIL'}")
    print(f"{'Job recovered':<30} {'✅ PASS' if test_results.get('job_recovered') else '❌ FAIL'}")
    print(f"{'Fresh job enqueued':<30} {'✅ PASS' if test_results.get('fresh_job_enqueued') else '❌ FAIL'}")
    print(f"{'Job processed':<30} {'✅ PASS' if test_results.get('job_processed') else '❌ FAIL'}")
    print(f"{'Idempotency works':<30} {'✅ PASS' if test_results.get('idempotency_works') else '❌ FAIL'}")
    print(f"{'Final state healthy':<30} {'✅ PASS' if test_results.get('final_state_healthy') else '❌ FAIL'}")
    print("="*80)
    
    all_passed = all(test_results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nThe complete job recovery system is working correctly:")
        print("  ✅ Stuck jobs are detected")
        print("  ✅ Stuck jobs are recovered (reset or failed)")
        print("  ✅ Dedupe protection works")
        print("  ✅ Fresh jobs can be enqueued after cleanup")
        print("  ✅ Jobs process successfully")
        print("  ✅ Idempotency prevents duplicate processing")
        print("  ✅ System reaches healthy state")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        failed = [k for k, v in test_results.items() if not v]
        print(f"\nFailed tests: {', '.join(failed)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
