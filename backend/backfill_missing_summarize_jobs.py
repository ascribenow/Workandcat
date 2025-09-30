#!/usr/bin/env python3
"""
Backfill Missing SUMMARIZE_SESSION Jobs
Creates SUMMARIZE_SESSION jobs for completed sessions that don't have them
"""

import asyncio
import sys
from database import SessionLocal
from sqlalchemy import text
from services.bg_job_queue import job_queue

async def backfill_missing_summarize_jobs():
    """Create SUMMARIZE_SESSION jobs for completed sessions that are missing them"""
    
    db = SessionLocal()
    try:
        print("🔧 BACKFILLING MISSING SUMMARIZE_SESSION JOBS")
        print("=" * 60)
        
        # Find completed sessions without SUMMARIZE_SESSION jobs
        missing_jobs = db.execute(text("""
            SELECT s.user_id, s.session_id, s.completed_at, s.status
            FROM sessions s
            LEFT JOIN bg_jobs bj ON bj.session_id = s.session_id AND bj.job_type = 'SUMMARIZE_SESSION'
            WHERE s.status = 'completed' 
            AND s.completed_at IS NOT NULL
            AND bj.id IS NULL
            ORDER BY s.user_id, s.completed_at DESC
        """)).fetchall()
        
        print(f"📊 Found {len(missing_jobs)} completed sessions without SUMMARIZE_SESSION jobs")
        
        if len(missing_jobs) == 0:
            print("✅ No missing jobs to backfill")
            return True
        
        print()
        print("📋 Sessions needing SUMMARIZE_SESSION jobs:")
        for session in missing_jobs:
            user_id, session_id, completed_at, status = session
            print(f"   User: {user_id[:8]}... | Session: {session_id[:8]}... | Completed: {completed_at}")
        
        print()
        
        # Create jobs for missing sessions
        jobs_created = 0
        for session in missing_jobs:
            user_id, session_id, completed_at, status = session
            
            try:
                print(f"🚀 Creating SUMMARIZE_SESSION job for {session_id[:8]}...")
                
                job_id = await job_queue.enqueue_job(
                    job_type="SUMMARIZE_SESSION",
                    user_id=user_id,
                    session_id=session_id
                )
                
                print(f"   ✅ Job {job_id[:8]}... created successfully")
                jobs_created += 1
                
            except Exception as e:
                print(f"   ❌ Failed to create job: {e}")
        
        print()
        print(f"🎉 BACKFILL COMPLETE")
        print(f"   Created {jobs_created}/{len(missing_jobs)} SUMMARIZE_SESSION jobs")
        
        if jobs_created == len(missing_jobs):
            print("   ✅ All missing jobs successfully created!")
        else:
            print(f"   ⚠️  {len(missing_jobs) - jobs_created} jobs failed to create")
        
        print()
        print("📋 Next Steps:")
        print("   1. Background job worker will process these jobs")
        print("   2. Jobs will populate session_summary_final table")
        print("   3. Jobs will update concept_alias_map_latest table")
        print("   4. Adaptive insights will be refreshed")
        
        return jobs_created == len(missing_jobs)
        
    except Exception as e:
        print(f"❌ Error during backfill: {e}")
        return False
    finally:
        db.close()

async def verify_backfill():
    """Verify that the backfill worked correctly"""
    
    db = SessionLocal()
    try:
        print()
        print("🔍 VERIFICATION:")
        
        # Check remaining missing jobs
        remaining_missing = db.execute(text("""
            SELECT COUNT(*)
            FROM sessions s
            LEFT JOIN bg_jobs bj ON bj.session_id = s.session_id AND bj.job_type = 'SUMMARIZE_SESSION'
            WHERE s.status = 'completed' 
            AND s.completed_at IS NOT NULL
            AND bj.id IS NULL
        """)).scalar()
        
        print(f"   Remaining sessions without SUMMARIZE_SESSION jobs: {remaining_missing}")
        
        # Check total SUMMARIZE_SESSION jobs by status
        job_stats = db.execute(text("""
            SELECT status, COUNT(*) as count
            FROM bg_jobs 
            WHERE job_type = 'SUMMARIZE_SESSION'
            GROUP BY status
            ORDER BY status
        """)).fetchall()
        
        print("   SUMMARIZE_SESSION jobs by status:")
        for stat in job_stats:
            status, count = stat
            print(f"     {status}: {count}")
        
        if remaining_missing == 0:
            print("   ✅ Backfill verification successful!")
        else:
            print(f"   ⚠️  {remaining_missing} sessions still missing jobs")
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    async def main():
        success = await backfill_missing_summarize_jobs()
        await verify_backfill()
        return success
    
    result = asyncio.run(main())
    sys.exit(0 if result else 1)