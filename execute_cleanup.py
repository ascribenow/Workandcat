#!/usr/bin/env python3
"""
Execute Database Cleanup - Remove Legacy Data
"""

import os
import sys
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database import SessionLocal

load_dotenv('/app/backend/.env')

def execute_database_cleanup():
    """Execute the actual database cleanup"""
    
    print("🧹 EXECUTING DATABASE CLEANUP")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # 1. Clean up orphaned attempt_events
        print("\n🗑️ CLEANUP 1: Removing orphaned attempt_events...")
        
        result = db.execute(text("""
            DELETE FROM attempt_events 
            WHERE session_id NOT IN (SELECT session_id FROM sessions)
        """))
        deleted_attempts = result.rowcount
        print(f"   ✅ Deleted {deleted_attempts} orphaned attempt_events")
        
        # 2. Update sessions with non-standard status to 'completed' if they have attempts
        print("\n🔄 CLEANUP 2: Standardizing session status...")
        
        result = db.execute(text("""
            UPDATE sessions 
            SET status = 'completed'
            WHERE status NOT IN ('planned', 'served', 'completed')
            AND session_id IN (
                SELECT DISTINCT session_id FROM attempt_events
            )
        """))
        updated_sessions = result.rowcount
        print(f"   ✅ Updated {updated_sessions} sessions to 'completed' status")
        
        # Remove sessions with no attempts and non-standard status
        result = db.execute(text("""
            DELETE FROM sessions 
            WHERE status NOT IN ('planned', 'served', 'completed')
            AND session_id NOT IN (
                SELECT DISTINCT session_id FROM attempt_events
            )
        """))
        deleted_empty_sessions = result.rowcount  
        print(f"   ✅ Deleted {deleted_empty_sessions} empty sessions with non-standard status")
        
        # 3. Archive inactive questions (optional - just mark for potential future archival)
        print("\n📦 CLEANUP 3: Marking inactive questions...")
        
        result = db.execute(text("""
            UPDATE questions 
            SET updated_at = NOW()
            WHERE is_active = false
        """))
        marked_questions = result.rowcount
        print(f"   ✅ Marked {marked_questions} inactive questions (keeping for reference)")
        
        # 4. Clean up old pack data that's no longer needed
        print("\n📦 CLEANUP 4: Cleaning old pack data...")
        
        # Remove planned packs older than 24 hours that were never served
        result = db.execute(text("""
            DELETE FROM session_pack_plan 
            WHERE status = 'planned' 
            AND created_at < NOW() - INTERVAL '24 hours'
        """))
        deleted_old_packs = result.rowcount
        print(f"   ✅ Deleted {deleted_old_packs} old unserved pack plans")
        
        # 5. Optimize session_progress_tracking
        print("\n📈 CLEANUP 5: Cleaning session progress tracking...")
        
        # Remove progress tracking for completed sessions older than 7 days
        result = db.execute(text("""
            DELETE FROM session_progress_tracking spt
            WHERE EXISTS (
                SELECT 1 FROM sessions s 
                WHERE s.session_id = spt.session_id 
                AND s.status = 'completed'
                AND s.updated_at < NOW() - INTERVAL '7 days'
            )
        """))
        deleted_progress = result.rowcount
        print(f"   ✅ Deleted {deleted_progress} old progress tracking records")
        
        # Commit all changes
        db.commit()
        
        print("\n" + "=" * 50)
        print("🎉 DATABASE CLEANUP COMPLETED!")
        print("📊 CLEANUP SUMMARY:")
        print(f"   • Orphaned attempt_events removed: {deleted_attempts}")
        print(f"   • Sessions status standardized: {updated_sessions}")
        print(f"   • Empty legacy sessions deleted: {deleted_empty_sessions}")
        print(f"   • Inactive questions marked: {marked_questions}")
        print(f"   • Old pack plans deleted: {deleted_old_packs}")
        print(f"   • Old progress records deleted: {deleted_progress}")
        
        # Final verification
        print("\n🔍 POST-CLEANUP VERIFICATION:")
        
        # Check orphaned attempts
        result = db.execute(text("""
            SELECT COUNT(*) as count FROM attempt_events ae
            LEFT JOIN sessions s ON ae.session_id = s.session_id
            WHERE s.session_id IS NULL
        """))
        remaining_orphans = result.fetchone().count
        print(f"   ✅ Remaining orphaned attempts: {remaining_orphans}")
        
        # Check session status
        result = db.execute(text("""
            SELECT status, COUNT(*) as count FROM sessions GROUP BY status ORDER BY count DESC
        """))
        status_counts = result.fetchall()
        print("   ✅ Session status distribution:")
        for row in status_counts:
            print(f"     - {row.status}: {row.count}")
        
        print("\n🚀 Database is now clean and optimized for adaptive-only system!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    execute_database_cleanup()