#!/usr/bin/env python3
"""
Fix Session Data Consistency
Reconciles existing sessions with their attempt_events and session_answers data
"""

import sys
from database import SessionLocal
from sqlalchemy import text

def fix_session_consistency():
    """Fix sessions that have attempt_events but show 0 progress"""
    
    db = SessionLocal()
    try:
        print("🔧 FIXING SESSION DATA CONSISTENCY")
        print("=" * 50)
        
        # Find all sessions with attempt_events but no recorded progress
        broken_sessions = db.execute(text("""
            SELECT DISTINCT s.session_id, s.user_id, s.status, s.questions_answered, COUNT(ae.id) as attempts
            FROM sessions s
            LEFT JOIN attempt_events ae ON ae.session_id = s.session_id
            WHERE s.questions_answered = 0  -- Sessions showing no progress
            AND ae.id IS NOT NULL  -- But have attempt events
            GROUP BY s.session_id, s.user_id, s.status, s.questions_answered
            ORDER BY s.user_id, attempts DESC
        """)).fetchall()
        
        print(f"📊 Found {len(broken_sessions)} sessions needing reconciliation")
        
        fixed_count = 0
        
        for session in broken_sessions:
            session_id, user_id, status, current_answered, actual_attempts = session
            
            print(f"\n🔧 Fixing session {session_id[:8]}...")
            print(f"   User: {user_id}")
            print(f"   Status: {status}")
            print(f"   DB shows answered: {current_answered}")
            print(f"   Actual attempts: {actual_attempts}")
            
            # Get correct statistics from session_answers (if exists)
            session_answer_stats = db.execute(text("""
                SELECT 
                    COUNT(*) as total_answered,
                    COUNT(*) FILTER (WHERE is_correct = true) as total_correct,
                    MAX(position) as current_position
                FROM session_answers 
                WHERE session_id = :session_id
            """), {"session_id": session_id}).fetchone()
            
            # Get statistics from attempt_events as fallback
            attempt_stats = db.execute(text("""
                SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(*) FILTER (WHERE was_correct = true) as correct_attempts,
                    MAX(sess_seq_at_serve) as max_position
                FROM attempt_events 
                WHERE session_id = :session_id
            """), {"session_id": session_id}).fetchone()
            
            # Determine correct statistics
            if session_answer_stats and session_answer_stats[0] > 0:
                # Use session_answers data (more reliable for Blueprint sessions)
                total_answered, total_correct, current_position = session_answer_stats
                print(f"   ✅ Using session_answers data: {total_correct}/{total_answered} correct, position {current_position}")
            elif attempt_stats and attempt_stats[0] > 0:
                # Fallback to attempt_events data
                total_answered, total_correct, current_position = attempt_stats
                print(f"   ⚠️  Using attempt_events data: {total_correct}/{total_answered} correct, position {current_position}")
            else:
                print(f"   ❌ No valid data found, skipping")
                continue
            
            # Update sessions table with correct data
            db.execute(text("""
                UPDATE sessions 
                SET questions_answered = :questions_answered,
                    questions_correct = :questions_correct,
                    current_position = :current_position
                WHERE session_id = :session_id
            """), {
                "questions_answered": total_answered,
                "questions_correct": total_correct, 
                "current_position": current_position,
                "session_id": session_id
            })
            
            print(f"   ✅ Updated session {session_id[:8]} with correct progress")
            fixed_count += 1
        
        # Commit all changes
        db.commit()
        
        print(f"\n🎉 RECONCILIATION COMPLETE")
        print(f"   Fixed {fixed_count} sessions")
        print(f"   All session progress data is now consistent")
        
        # Verify the fix
        print(f"\n🔍 VERIFICATION:")
        remaining_broken = db.execute(text("""
            SELECT COUNT(DISTINCT s.session_id)
            FROM sessions s
            LEFT JOIN attempt_events ae ON ae.session_id = s.session_id  
            WHERE s.questions_answered = 0
            AND ae.id IS NOT NULL
        """)).scalar()
        
        print(f"   Remaining broken sessions: {remaining_broken}")
        
        if remaining_broken == 0:
            print("   ✅ All sessions successfully reconciled!")
        else:
            print(f"   ⚠️  {remaining_broken} sessions still need attention")
            
    except Exception as e:
        print(f"❌ Error during reconciliation: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    success = fix_session_consistency()
    sys.exit(0 if success else 1)