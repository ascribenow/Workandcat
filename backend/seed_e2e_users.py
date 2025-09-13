#!/usr/bin/env python3
"""
E2E Test Database Seed Script
Creates dedicated test users with proper session history for Phase 4 testing
"""

import logging
from database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

def seed_e2e_users():
    """Seed dedicated E2E test users and session data"""
    db = SessionLocal()
    try:
        print("🌱 Seeding E2E test users and session data...")
        
        # Clean up any existing E2E data first
        cleanup_sql = """
        -- Clean planned packs & summaries for E2E users
        DELETE FROM session_pack_plan WHERE user_id IN ('U_COLD_01','U_ADAPT_01');
        DELETE FROM session_summary_llm WHERE user_id IN ('U_COLD_01','U_ADAPT_01');  
        DELETE FROM session_summary_final WHERE user_id IN ('U_COLD_01','U_ADAPT_01');
        """
        
        # Execute cleanup
        for stmt in cleanup_sql.strip().split(';'):
            if stmt.strip():
                db.execute(text(stmt.strip()))
        
        # Seed users
        users_sql = """
        INSERT INTO users (id, email, full_name, password_hash, created_at) VALUES
          ('U_COLD_01',  'e2e+cold@twelvr.app', 'E2E Cold Start User', '$2b$12$dummy.hash.for.testing', NOW()),
          ('U_ADAPT_01', 'e2e+adapt@twelvr.app', 'E2E Adaptive User', '$2b$12$dummy.hash.for.testing', NOW())
        ON CONFLICT (id) DO UPDATE SET
          email = EXCLUDED.email,
          full_name = EXCLUDED.full_name;
        """
        
        db.execute(text(users_sql))
        
        # Seed sessions for adaptive user (2 completed sessions)
        sessions_sql = """
        INSERT INTO sessions (user_id, session_id, sess_seq, status, questions_answered, questions_correct, completed_at) VALUES
          ('U_ADAPT_01', '3c1f8f0c-8c2e-4f0c-9b0e-3e5f2b9a1111', 1, 'completed', 12, 8, NOW() - INTERVAL '2 days'),
          ('U_ADAPT_01', '6a2b2b1a-1f2e-4d3c-8a7b-0c1d2e3f2222', 2, 'completed', 12, 9, NOW() - INTERVAL '1 day')
        ON CONFLICT (user_id, sess_seq) DO UPDATE SET
          status = EXCLUDED.status,
          questions_answered = EXCLUDED.questions_answered,
          questions_correct = EXCLUDED.questions_correct,
          completed_at = EXCLUDED.completed_at;
        """
        
        db.execute(text(sessions_sql))
        
        # Get some real question IDs from the database for attempt events
        real_questions = db.execute(text("""
            SELECT id, difficulty_band, subcategory, type_of_question, core_concepts, pyq_frequency_score
            FROM questions_rows 
            WHERE is_active = true 
            LIMIT 3
        """)).fetchall()
        
        if real_questions:
            # Create attempt events for the last session (sess_seq_at_serve=2)
            for i, q in enumerate(real_questions):
                attempt_sql = """
                INSERT INTO attempt_events (
                    user_id, question_id, session_id, was_correct, skipped, 
                    sess_seq_at_serve, difficulty_band, subcategory, type_of_question, 
                    core_concepts, pyq_frequency_score, created_at
                ) VALUES (
                    'U_ADAPT_01', :question_id, '6a2b2b1a-1f2e-4d3c-8a7b-0c1d2e3f2222', 
                    :was_correct, false, 2, :difficulty_band, :subcategory, :type_of_question,
                    :core_concepts, :pyq_frequency_score, NOW() - INTERVAL '1 day'
                ) ON CONFLICT DO NOTHING;
                """
                
                db.execute(text(attempt_sql), {
                    'question_id': q.id,
                    'was_correct': i % 2 == 0,  # Alternate correct/incorrect
                    'difficulty_band': q.difficulty_band,
                    'subcategory': q.subcategory, 
                    'type_of_question': q.type_of_question,
                    'core_concepts': str(q.core_concepts) if q.core_concepts else '[]',
                    'pyq_frequency_score': float(q.pyq_frequency_score) if q.pyq_frequency_score else 0.5
                })
        
        db.commit()
        print("✅ E2E test users and session data seeded successfully")
        
        # Verify the setup
        cold_sessions = db.execute(text("SELECT COUNT(*) FROM sessions WHERE user_id = 'U_COLD_01' AND status IN ('completed', 'served')")).scalar()
        adapt_sessions = db.execute(text("SELECT COUNT(*) FROM sessions WHERE user_id = 'U_ADAPT_01' AND status IN ('completed', 'served')")).scalar()
        adapt_attempts = db.execute(text("SELECT COUNT(*) FROM attempt_events WHERE user_id = 'U_ADAPT_01'")).scalar()
        
        print(f"📊 Verification:")
        print(f"   Cold-start user (U_COLD_01): {cold_sessions} served sessions (should be 0)")
        print(f"   Adaptive user (U_ADAPT_01): {adapt_sessions} served sessions (should be ≥1)")  
        print(f"   Adaptive user attempt events: {adapt_attempts} (should be ≥1)")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding E2E users: {e}")
        return False
    finally:
        db.close()

def cleanup_e2e_data():
    """Clean up E2E test artifacts"""
    db = SessionLocal()
    try:
        print("🧹 Cleaning up E2E test artifacts...")
        
        cleanup_sql = """
        -- Clean planned packs & summaries for E2E users
        DELETE FROM session_pack_plan WHERE user_id IN ('U_COLD_01','U_ADAPT_01');
        DELETE FROM session_summary_llm WHERE user_id IN ('U_COLD_01','U_ADAPT_01');
        DELETE FROM session_summary_final WHERE user_id IN ('U_COLD_01','U_ADAPT_01');
        """
        
        # Execute cleanup
        for stmt in cleanup_sql.strip().split(';'):
            if stmt.strip():
                result = db.execute(text(stmt.strip()))
                print(f"   Cleaned {result.rowcount} rows from {stmt.split()[2]}")
        
        db.commit()
        print("✅ E2E cleanup completed")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning E2E data: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_e2e_data()
    else:
        seed_e2e_users()