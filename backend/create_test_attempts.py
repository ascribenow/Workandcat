#!/usr/bin/env python3
"""
Create Test Attempt Events for Summarizer Testing
Creates realistic attempt events for a test user session to validate summarizer functionality
"""

import os
import sys
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_attempts():
    """Create test attempt events for summarizer validation"""
    
    # Database connection
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost/twelvr_db')
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get real test user ID (sp@theskinmantra.com)
        user_result = db.execute(text("""
            SELECT id FROM users WHERE email = 'sp@theskinmantra.com' LIMIT 1
        """)).fetchone()
        
        if not user_result:
            print("❌ Test user sp@theskinmantra.com not found in database")
            return None, None
            
        user_id = user_result.id
        
        # Get or create a test session
        session_result = db.execute(text("""
            SELECT session_id, sess_seq FROM sessions 
            WHERE user_id = :user_id 
            ORDER BY created_at DESC 
            LIMIT 1
        """), {"user_id": user_id}).fetchone()
        
        if session_result:
            session_id = session_result.session_id
            sess_seq = session_result.sess_seq
            print(f"Using existing session: {session_id} (sess_seq: {sess_seq})")
        else:
            # Create a test session
            session_id = str(uuid.uuid4())  # Just the UUID, no "session_" prefix
            sess_seq = 1
            
            db.execute(text("""
                INSERT INTO sessions (user_id, session_id, sess_seq, status, created_at)
                VALUES (:user_id, :session_id, :sess_seq, 'completed', :created_at)
            """), {
                "user_id": user_id,
                "session_id": session_id, 
                "sess_seq": sess_seq,
                "created_at": datetime.utcnow()
            })
            print(f"Created test session: {session_id} (sess_seq: {sess_seq})")
        
        # Check if attempts already exist
        existing_attempts = db.execute(text("""
            SELECT COUNT(*) as count FROM attempt_events 
            WHERE user_id = :user_id AND sess_seq_at_serve = :sess_seq
        """), {"user_id": user_id, "sess_seq": sess_seq}).fetchone()
        
        if existing_attempts.count > 0:
            print(f"Found {existing_attempts.count} existing attempts for this session")
            db.close()
            return session_id, sess_seq
        
        # Create 12 realistic attempt events  
        attempt_data = [
            {
                "question_id": f"q_{i+1:03d}",
                "difficulty_band": "Easy" if i < 3 else ("Hard" if i >= 9 else "Medium"),
                "subcategory": ["Arithmetic", "Algebra", "Geometry", "Statistics"][i % 4],
                "type_of_question": ["Problem Solving", "Data Analysis", "Computation"][i % 3],
                "core_concepts": json.dumps([f"concept_{i+1}", f"concept_{(i+1)%5 + 1}"]),
                "pyq_frequency_score": 1.0 if i % 3 == 0 else (1.5 if i % 4 == 0 else 0.5),
                "was_correct": i % 3 != 2,  # 2/3 correct rate
                "skipped": i % 7 == 6,  # Occasional skips
                "response_time_ms": 45000 + (i * 3000),  # 45-78 seconds
                "served_at": datetime.utcnow()
            }
            for i in range(12)
        ]
        
        # Insert attempt events
        for i, attempt in enumerate(attempt_data):
            attempt_id = str(uuid.uuid4())
            
            db.execute(text("""
                INSERT INTO attempt_events (
                    id, user_id, session_id, question_id, 
                    difficulty_band, subcategory, type_of_question, core_concepts,
                    pyq_frequency_score, was_correct, skipped, response_time_ms,
                    sess_seq_at_serve, created_at
                ) VALUES (
                    :attempt_id, :user_id, :session_id, :question_id,
                    :difficulty_band, :subcategory, :type_of_question, :core_concepts,
                    :pyq_frequency_score, :was_correct, :skipped, :response_time_ms,
                    :sess_seq_at_serve, :created_at
                )
            """), {
                "attempt_id": attempt_id,
                "user_id": user_id,
                "session_id": session_id,  # Use the actual session_id for the relationship
                "question_id": attempt["question_id"],
                "difficulty_band": attempt["difficulty_band"],
                "subcategory": attempt["subcategory"], 
                "type_of_question": attempt["type_of_question"],
                "core_concepts": attempt["core_concepts"],
                "pyq_frequency_score": attempt["pyq_frequency_score"],
                "was_correct": attempt["was_correct"],
                "skipped": attempt["skipped"],
                "response_time_ms": attempt["response_time_ms"],
                "sess_seq_at_serve": sess_seq,
                "created_at": datetime.utcnow()
            })
        
        db.commit()
        print(f"✅ Created {len(attempt_data)} test attempt events for session {session_id}")
        
        # Verification
        verification = db.execute(text("""
            SELECT COUNT(*) as attempt_count,
                   AVG(CASE WHEN was_correct THEN 1 ELSE 0 END)::DECIMAL(3,2) as accuracy,
                   COUNT(CASE WHEN difficulty_band = 'Easy' THEN 1 END) as easy_count,
                   COUNT(CASE WHEN difficulty_band = 'Medium' THEN 1 END) as medium_count,
                   COUNT(CASE WHEN difficulty_band = 'Hard' THEN 1 END) as hard_count
            FROM attempt_events 
            WHERE user_id = :user_id AND sess_seq_at_serve = :sess_seq
        """), {"user_id": user_id, "sess_seq": sess_seq}).fetchone()
        
        print(f"📊 Verification - Attempts: {verification.attempt_count}, Accuracy: {verification.accuracy}")
        print(f"📊 Distribution - Easy: {verification.easy_count}, Medium: {verification.medium_count}, Hard: {verification.hard_count}")
        
        return session_id, sess_seq
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating test attempts: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    session_id, sess_seq = create_test_attempts()
    print(f"✅ Test data creation complete for session {session_id[:8]} (sess_seq: {sess_seq})")