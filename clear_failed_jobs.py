#!/usr/bin/env python3
"""
Clear failed jobs from bg_jobs table
"""

import sys
sys.path.append('/app/backend')

from database import SessionLocal
from sqlalchemy import text

def clear_failed_jobs():
    print("🧹 CLEARING FAILED JOBS")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Delete failed jobs
        result = db.execute(text("""
            DELETE FROM bg_jobs 
            WHERE status = 'failed' OR attempts >= max_attempts
        """))
        
        deleted_count = result.rowcount
        db.commit()
        
        print(f"   ✅ Deleted {deleted_count} failed jobs")
        
        # Show remaining jobs
        result = db.execute(text("""
            SELECT id, job_type, status, attempts, created_at
            FROM bg_jobs 
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        jobs = result.fetchall()
        print(f"   📊 Remaining jobs: {len(jobs)}")
        
        for job in jobs:
            print(f"      {job.job_type} | {job.status} | attempts={job.attempts}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_failed_jobs()