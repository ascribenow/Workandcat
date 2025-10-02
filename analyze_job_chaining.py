#!/usr/bin/env python3
"""
Comprehensive Job Chaining Analysis
Analyzes the current state of job chaining and identifies issues
"""

import sys
sys.path.append('/app/backend')

from database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta

def analyze_job_chaining():
    """Analyze the current state of job chaining"""
    print("🔍 COMPREHENSIVE JOB CHAINING ANALYSIS")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        # 1. Check recent SUMMARIZE_SESSION jobs
        print("\n📊 RECENT SUMMARIZE_SESSION JOBS (Last 7 days):")
        result = db.execute(text("""
            SELECT id, user_id, session_id, correlation_id, status, created_at, completed_at
            FROM bg_jobs 
            WHERE job_type = 'SUMMARIZE_SESSION' 
            AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 10
        """))
        
        summarize_jobs = result.fetchall()
        print(f"Found {len(summarize_jobs)} SUMMARIZE_SESSION jobs")
        
        successful_summarize_jobs = []
        for job in summarize_jobs:
            status_icon = "✅" if job.status == "succeeded" else "❌" if job.status == "failed" else "⏳"
            print(f"  {status_icon} {job.id} | {job.status} | Correlation: {job.correlation_id}")
            print(f"     Created: {job.created_at} | Completed: {job.completed_at}")
            
            if job.status == "succeeded":
                successful_summarize_jobs.append(job)
        
        print(f"\n✅ Successful SUMMARIZE_SESSION jobs: {len(successful_summarize_jobs)}")
        
        # 2. For each successful SUMMARIZE_SESSION job, check if PLAN_NEXT_SESSION was created
        print("\n🔗 JOB CHAINING ANALYSIS:")
        chaining_working = 0
        chaining_broken = 0
        
        for summarize_job in successful_summarize_jobs:
            correlation_id = summarize_job.correlation_id
            if not correlation_id:
                print(f"  ❌ Job {summarize_job.id} has no correlation_id - cannot track chain")
                chaining_broken += 1
                continue
            
            # Check for PLAN_NEXT_SESSION with same correlation_id
            plan_result = db.execute(text("""
                SELECT id, status, created_at, completed_at
                FROM bg_jobs 
                WHERE job_type = 'PLAN_NEXT_SESSION' 
                AND correlation_id = :correlation_id
            """), {"correlation_id": correlation_id})
            
            plan_jobs = plan_result.fetchall()
            
            if plan_jobs:
                print(f"  ✅ Chain working: {summarize_job.id} → {len(plan_jobs)} PLAN_NEXT_SESSION job(s)")
                chaining_working += 1
                
                # Check for UPDATE_INSIGHTS
                for plan_job in plan_jobs:
                    insights_result = db.execute(text("""
                        SELECT id, status, created_at, completed_at
                        FROM bg_jobs 
                        WHERE job_type = 'UPDATE_INSIGHTS' 
                        AND correlation_id = :correlation_id
                    """), {"correlation_id": correlation_id})
                    
                    insights_jobs = insights_result.fetchall()
                    if insights_jobs:
                        print(f"    ✅ Complete chain: SUMMARIZE → PLAN → {len(insights_jobs)} UPDATE_INSIGHTS")
                    else:
                        print(f"    ❌ Incomplete chain: Missing UPDATE_INSIGHTS")
            else:
                print(f"  ❌ Chain broken: {summarize_job.id} → No PLAN_NEXT_SESSION job found")
                chaining_broken += 1
        
        # 3. Summary
        print(f"\n📊 JOB CHAINING SUMMARY:")
        print(f"  Working chains: {chaining_working}")
        print(f"  Broken chains: {chaining_broken}")
        print(f"  Success rate: {(chaining_working / (chaining_working + chaining_broken) * 100):.1f}%" if (chaining_working + chaining_broken) > 0 else "N/A")
        
        # 4. Check correlation_id propagation fix
        print(f"\n🔧 CORRELATION_ID PROPAGATION ANALYSIS:")
        jobs_with_correlation = db.execute(text("""
            SELECT COUNT(*) FROM bg_jobs 
            WHERE correlation_id IS NOT NULL 
            AND created_at > NOW() - INTERVAL '7 days'
        """)).scalar()
        
        total_jobs = db.execute(text("""
            SELECT COUNT(*) FROM bg_jobs 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)).scalar()
        
        print(f"  Jobs with correlation_id: {jobs_with_correlation}/{total_jobs}")
        print(f"  Correlation_id coverage: {(jobs_with_correlation / total_jobs * 100):.1f}%" if total_jobs > 0 else "N/A")
        
        # 5. Check for event loop issues in recent jobs
        print(f"\n🔄 ERROR ANALYSIS:")
        error_result = db.execute(text("""
            SELECT job_type, error_message, created_at
            FROM bg_jobs 
            WHERE status = 'failed' 
            AND created_at > NOW() - INTERVAL '24 hours'
            AND error_message IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 5
        """))
        
        error_jobs = error_result.fetchall()
        print(f"Recent failed jobs: {len(error_jobs)}")
        
        event_loop_issues = 0
        for error_job in error_jobs:
            error_msg = error_job.error_message.lower()
            if any(keyword in error_msg for keyword in ['event loop', 'asyncio', 'coroutine', 'await']):
                event_loop_issues += 1
                print(f"  ❌ {error_job.job_type}: Event loop issue detected")
                print(f"     Error: {error_job.error_message[:100]}...")
            else:
                print(f"  ⚠️ {error_job.job_type}: Other error")
                print(f"     Error: {error_job.error_message[:100]}...")
        
        print(f"\n🎯 FINAL ASSESSMENT:")
        
        # Determine if job chaining is working
        if chaining_working > 0 and chaining_broken == 0:
            print("✅ JOB CHAINING: WORKING")
            job_chaining_status = "working"
        elif chaining_working > chaining_broken:
            print("⚠️ JOB CHAINING: PARTIALLY WORKING")
            job_chaining_status = "partial"
        else:
            print("❌ JOB CHAINING: BROKEN")
            job_chaining_status = "broken"
        
        # Determine if correlation_id propagation is working
        if jobs_with_correlation > 0 and (jobs_with_correlation / total_jobs) > 0.5:
            print("✅ CORRELATION_ID PROPAGATION: WORKING")
            correlation_status = "working"
        else:
            print("❌ CORRELATION_ID PROPAGATION: ISSUES DETECTED")
            correlation_status = "broken"
        
        # Determine if event loop issues are resolved
        if event_loop_issues == 0:
            print("✅ EVENT LOOP ISSUES: RESOLVED")
            event_loop_status = "resolved"
        else:
            print("❌ EVENT LOOP ISSUES: DETECTED")
            event_loop_status = "issues"
        
        return {
            "job_chaining_status": job_chaining_status,
            "correlation_status": correlation_status,
            "event_loop_status": event_loop_status,
            "working_chains": chaining_working,
            "broken_chains": chaining_broken,
            "jobs_with_correlation": jobs_with_correlation,
            "total_jobs": total_jobs,
            "event_loop_issues": event_loop_issues
        }
        
    finally:
        db.close()

def main():
    """Main analysis"""
    try:
        results = analyze_job_chaining()
        
        print(f"\n" + "=" * 80)
        print("🎯 TESTING AGENT ASSESSMENT")
        print("=" * 80)
        
        if (results["job_chaining_status"] == "working" and 
            results["correlation_status"] == "working" and 
            results["event_loop_status"] == "resolved"):
            print("✅ ALL FIXES VALIDATED: Job chaining system working correctly")
            return True
        else:
            print("❌ ISSUES DETECTED: Job chaining system needs attention")
            
            if results["job_chaining_status"] != "working":
                print(f"   - Job chaining: {results['working_chains']} working, {results['broken_chains']} broken")
            
            if results["correlation_status"] != "working":
                print(f"   - Correlation ID: {results['jobs_with_correlation']}/{results['total_jobs']} jobs have correlation_id")
            
            if results["event_loop_status"] != "resolved":
                print(f"   - Event loop issues: {results['event_loop_issues']} detected")
            
            return False
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)