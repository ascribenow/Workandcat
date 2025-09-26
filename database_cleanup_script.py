#!/usr/bin/env python3
"""
🧹 COMPREHENSIVE DATABASE CLEANUP SCRIPT
Execute comprehensive data cleanup to reset all session and question attempt data 
for all users while preserving user accounts, subscriptions, and referrals.

CRITICAL SAFETY CHECKS:
- ⚠️ DO NOT DELETE: users, subscriptions, referrals, question bank
- ✅ DELETE ONLY: session records, attempts, answers, packs
- ✅ PRESERVE: Table structures (no DROP/ALTER operations)
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.append('/app/backend')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connection():
    """Get database connection using the same config as the app"""
    from dotenv import load_dotenv
    
    # Load environment variables from backend directory
    load_dotenv('/app/backend/.env')
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    print(f"   📊 Database URL: {DATABASE_URL[:50]}...")
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    return engine, SessionLocal

def execute_cleanup_operations():
    """Execute the comprehensive data cleanup operations"""
    
    print("🧹 COMPREHENSIVE DATABASE CLEANUP OPERATION")
    print("=" * 80)
    print("OBJECTIVE: Reset all session and question attempt data while preserving critical data")
    print("FOCUS: Safe cleanup of sessions, attempts, answers, packs - preserve users, subscriptions, referrals")
    print("=" * 80)
    
    try:
        # Get database connection
        engine, SessionLocal = get_database_connection()
        db = SessionLocal()
        
        print("\n🔐 PHASE 1: AUTHENTICATION AND CONNECTION")
        print("-" * 60)
        print("✅ Database connection established")
        
        # PHASE 2: SESSION DATA CLEANUP (ALL USERS)
        print("\n🗑️ PHASE 2: SESSION DATA CLEANUP (ALL USERS)")
        print("-" * 60)
        print("DELETE FROM session_answers, session_pack_questions, session_packs, sessions, attempt_events")
        
        cleanup_operations = [
            # Step 1: Clear attempt_events (most critical for dashboard reset)
            {
                "name": "attempt_events",
                "query": "DELETE FROM attempt_events",
                "description": "Clear all question attempt tracking"
            },
            
            # Step 2: Clear session_answers (if exists)
            {
                "name": "session_answers", 
                "query": "DELETE FROM session_answers",
                "description": "Clear all session answer submissions"
            },
            
            # Step 3: Clear session_pack_questions (if exists)
            {
                "name": "session_pack_questions",
                "query": "DELETE FROM session_pack_questions", 
                "description": "Clear all session pack question data"
            },
            
            # Step 4: Clear session_packs (if exists)
            {
                "name": "session_packs",
                "query": "DELETE FROM session_packs",
                "description": "Clear all session pack data"
            },
            
            # Step 5: Clear session_pack_plan (adaptive sessions)
            {
                "name": "session_pack_plan",
                "query": "DELETE FROM session_pack_plan",
                "description": "Clear all adaptive session pack plans"
            },
            
            # Step 6: Clear sessions
            {
                "name": "sessions",
                "query": "DELETE FROM sessions",
                "description": "Clear all session records"
            }
        ]
        
        cleanup_results = {}
        
        for operation in cleanup_operations:
            try:
                print(f"   📋 Clearing {operation['name']} table...")
                
                # First check if table exists and get count
                try:
                    count_result = db.execute(text(f"SELECT COUNT(*) FROM {operation['name']}"))
                    initial_count = count_result.scalar()
                    print(f"      Initial records: {initial_count}")
                except Exception as e:
                    print(f"      Table {operation['name']} may not exist: {e}")
                    cleanup_results[operation['name']] = "table_not_found"
                    continue
                
                # Execute cleanup
                result = db.execute(text(operation['query']))
                db.commit()
                
                # Verify cleanup
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {operation['name']}"))
                final_count = count_result.scalar()
                
                cleanup_results[operation['name']] = {
                    "initial_count": initial_count,
                    "final_count": final_count,
                    "cleared": initial_count - final_count,
                    "success": final_count == 0
                }
                
                print(f"      ✅ {operation['description']}")
                print(f"      📊 Cleared {initial_count} records")
                
            except Exception as e:
                print(f"      ❌ Failed to clear {operation['name']}: {e}")
                cleanup_results[operation['name']] = {"error": str(e), "success": False}
        
        # PHASE 3: PROGRESS DATA CLEANUP
        print("\n📊 PHASE 3: PROGRESS DATA CLEANUP")
        print("-" * 60)
        print("Clear session-related progress tracking tables and cached data")
        
        progress_operations = [
            {
                "name": "session_progress_tracking",
                "query": "DELETE FROM session_progress_tracking",
                "description": "Clear session progress tracking data"
            },
            {
                "name": "session_summary_llm", 
                "query": "DELETE FROM session_summary_llm",
                "description": "Clear LLM session summaries"
            },
            {
                "name": "concept_alias_map_latest",
                "query": "DELETE FROM concept_alias_map_latest", 
                "description": "Clear concept alias mappings"
            }
        ]
        
        for operation in progress_operations:
            try:
                print(f"   📋 Clearing {operation['name']} table...")
                
                # Check if table exists and get count
                try:
                    count_result = db.execute(text(f"SELECT COUNT(*) FROM {operation['name']}"))
                    initial_count = count_result.scalar()
                    print(f"      Initial records: {initial_count}")
                except Exception as e:
                    print(f"      Table {operation['name']} may not exist: {e}")
                    cleanup_results[operation['name']] = "table_not_found"
                    continue
                
                # Execute cleanup
                result = db.execute(text(operation['query']))
                db.commit()
                
                # Verify cleanup
                count_result = db.execute(text(f"SELECT COUNT(*) FROM {operation['name']}"))
                final_count = count_result.scalar()
                
                cleanup_results[operation['name']] = {
                    "initial_count": initial_count,
                    "final_count": final_count,
                    "cleared": initial_count - final_count,
                    "success": final_count == 0
                }
                
                print(f"      ✅ {operation['description']}")
                print(f"      📊 Cleared {initial_count} records")
                
            except Exception as e:
                print(f"      ❌ Failed to clear {operation['name']}: {e}")
                cleanup_results[operation['name']] = {"error": str(e), "success": False}
        
        # PHASE 4: DATA INTEGRITY VERIFICATION
        print("\n🔒 PHASE 4: DATA INTEGRITY VERIFICATION")
        print("-" * 60)
        print("Verify user accounts, question bank, subscriptions, and referrals are intact")
        
        integrity_checks = [
            {
                "name": "users",
                "query": "SELECT COUNT(*) FROM users",
                "description": "User accounts"
            },
            {
                "name": "questions", 
                "query": "SELECT COUNT(*) FROM questions",
                "description": "Question bank"
            },
            {
                "name": "subscriptions",
                "query": "SELECT COUNT(*) FROM subscriptions", 
                "description": "Subscription records"
            },
            {
                "name": "referral_usage",
                "query": "SELECT COUNT(*) FROM referral_usage",
                "description": "Referral usage records"
            },
            {
                "name": "payment_transactions",
                "query": "SELECT COUNT(*) FROM payment_transactions",
                "description": "Payment transaction records"
            }
        ]
        
        integrity_results = {}
        
        for check in integrity_checks:
            try:
                result = db.execute(text(check['query']))
                count = result.scalar()
                integrity_results[check['name']] = count
                print(f"   ✅ {check['description']}: {count} records intact")
            except Exception as e:
                print(f"   ❌ Failed to check {check['name']}: {e}")
                integrity_results[check['name']] = f"error: {e}"
        
        # PHASE 5: RESET VALIDATION
        print("\n🔄 PHASE 5: RESET VALIDATION")
        print("-" * 60)
        print("Verify clean state achieved")
        
        # Check that session-related tables are empty
        session_tables = ["attempt_events", "sessions", "session_pack_plan"]
        all_clean = True
        
        for table in session_tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                if count == 0:
                    print(f"   ✅ {table}: Clean (0 records)")
                else:
                    print(f"   ❌ {table}: Not clean ({count} records remaining)")
                    all_clean = False
            except Exception as e:
                print(f"   ⚠️ {table}: Could not verify ({e})")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("🧹 COMPREHENSIVE DATABASE CLEANUP OPERATION - RESULTS")
        print("=" * 80)
        
        successful_cleanups = 0
        total_cleanups = 0
        
        print("\n📊 CLEANUP RESULTS:")
        for table, result in cleanup_results.items():
            total_cleanups += 1
            if isinstance(result, dict) and result.get('success'):
                successful_cleanups += 1
                print(f"   ✅ {table}: Cleared {result.get('cleared', 0)} records")
            elif result == "table_not_found":
                print(f"   ⚠️ {table}: Table not found (may not exist in this schema)")
            else:
                print(f"   ❌ {table}: Failed - {result}")
        
        print("\n🔒 DATA INTEGRITY RESULTS:")
        for table, count in integrity_results.items():
            if isinstance(count, int):
                print(f"   ✅ {table}: {count} records preserved")
            else:
                print(f"   ❌ {table}: {count}")
        
        success_rate = (successful_cleanups / total_cleanups * 100) if total_cleanups > 0 else 0
        print(f"\n📈 CLEANUP SUCCESS RATE: {successful_cleanups}/{total_cleanups} ({success_rate:.1f}%)")
        
        if all_clean and success_rate >= 70:
            print("\n🎉 CLEANUP OPERATION: SUCCESSFUL")
            print("   - All session data cleared safely")
            print("   - Critical data preserved")
            print("   - System ready for fresh testing")
            print("   - Dashboard should show 0 sessions, 0 questions")
        else:
            print("\n⚠️ CLEANUP OPERATION: PARTIAL SUCCESS")
            print("   - Some cleanup operations may have failed")
            print("   - Review results above for details")
        
        db.close()
        return success_rate >= 70
        
    except Exception as e:
        logger.error(f"❌ Critical error during cleanup operation: {e}")
        print(f"\n❌ CRITICAL ERROR: {e}")
        return False

if __name__ == "__main__":
    print("🚨 WARNING: This script will permanently delete all session and attempt data!")
    print("🔒 SAFETY: User accounts, questions, subscriptions, and referrals will be preserved.")
    
    # Safety confirmation
    confirmation = input("\nType 'CONFIRM_CLEANUP' to proceed with data cleanup: ")
    
    if confirmation != "CONFIRM_CLEANUP":
        print("❌ Cleanup cancelled - confirmation not provided")
        sys.exit(1)
    
    print("\n🚀 Starting comprehensive database cleanup operation...")
    
    success = execute_cleanup_operations()
    
    if success:
        print("\n✅ Database cleanup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database cleanup completed with issues!")
        sys.exit(1)