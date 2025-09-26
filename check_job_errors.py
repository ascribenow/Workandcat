#!/usr/bin/env python3
"""
Check job errors in bg_jobs table
"""

import sys
sys.path.append('/app/backend')

from database import SessionLocal
from sqlalchemy import text

def check_job_errors():
    print("🔍 CHECKING JOB ERRORS")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Get failed jobs with error messages
        result = db.execute(text("""
            SELECT id, job_type, user_id, session_id, status, attempts, 
                   error_message, created_at, started_at, completed_at
            FROM bg_jobs 
            WHERE status = 'failed' OR error_message IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        failed_jobs = result.fetchall()
        
        if not failed_jobs:
            print("   ✅ No failed jobs found")
            return
        
        print(f"   📊 Found {len(failed_jobs)} failed jobs:")
        print()
        
        for i, job in enumerate(failed_jobs):
            print(f"   📋 Failed Job {i+1}:")
            print(f"      ID: {str(job.id)[:8]}...")
            print(f"      Type: {job.job_type}")
            print(f"      Status: {job.status}")
            print(f"      Attempts: {job.attempts}")
            print(f"      User: {str(job.user_id)[:8]}...")
            if job.session_id:
                print(f"      Session: {str(job.session_id)[:8]}...")
            print(f"      Created: {job.created_at}")
            print(f"      Started: {job.started_at}")
            print(f"      Completed: {job.completed_at}")
            if job.error_message:
                print(f"      ❌ Error: {job.error_message}")
            else:
                print(f"      ❌ Error: No error message recorded")
            print()
        
        # Check if there are any running jobs stuck
        result = db.execute(text("""
            SELECT COUNT(*) FROM bg_jobs 
            WHERE status = 'running' 
            AND started_at < NOW() - INTERVAL '5 minutes'
        """))
        
        stuck_jobs = result.scalar()
        if stuck_jobs > 0:
            print(f"   ⚠️ Found {stuck_jobs} jobs stuck in 'running' state for >5 minutes")
        
    except Exception as e:
        print(f"   ❌ Error checking job errors: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_job_errors()