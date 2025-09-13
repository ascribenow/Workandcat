#!/usr/bin/env python3
"""
Generate pseudo data for adaptive logic testing
- 18 users (6 new, 6 early, 6 experienced)
- Realistic session/attempt patterns
- Performance distributions per difficulty band
"""

import sys
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.append('.')
from database import SessionLocal, Question
from sqlalchemy import text, select

def generate_pseudo_users():
    """Generate 18 test users"""
    users = []
    
    # 6 New users (0 sessions)
    for i in range(6):
        users.append({
            'id': str(uuid.uuid4()),
            'email': f'new_user_{i+1}@test.com',
            'full_name': f'New User {i+1}',
            'password_hash': 'hashed_password',
            'is_admin': False,
            'created_at': datetime.now() - timedelta(days=random.randint(1, 30)),
            'referral_code': f'NEW{i+1:03d}',
            'cohort': 'new',
            'target_sessions': 0
        })
    
    # 6 Early users (1-3 sessions)
    for i in range(6):
        users.append({
            'id': str(uuid.uuid4()),
            'email': f'early_user_{i+1}@test.com',
            'full_name': f'Early User {i+1}',
            'password_hash': 'hashed_password',
            'is_admin': False,
            'created_at': datetime.now() - timedelta(days=random.randint(10, 60)),
            'referral_code': f'ERL{i+1:03d}',
            'cohort': 'early',
            'target_sessions': random.randint(1, 3)
        })
    
    # 6 Experienced users (4-10 sessions)
    for i in range(6):
        users.append({
            'id': str(uuid.uuid4()),
            'email': f'experienced_user_{i+1}@test.com',
            'full_name': f'Experienced User {i+1}',
            'password_hash': 'hashed_password',
            'is_admin': False,
            'created_at': datetime.now() - timedelta(days=random.randint(30, 180)),
            'referral_code': f'EXP{i+1:03d}',
            'cohort': 'experienced',
            'target_sessions': random.randint(4, 10)
        })
    
    return users

def get_performance_pattern(difficulty_band: str) -> Dict[str, float]:
    """Get performance distribution for difficulty band"""
    patterns = {
        'Easy': {'correct': 0.75, 'wrong': 0.20, 'skipped': 0.05},
        'Medium': {'correct': 0.55, 'wrong': 0.35, 'skipped': 0.10},
        'Hard': {'correct': 0.35, 'wrong': 0.55, 'skipped': 0.10}
    }
    
    # Add ±5% jitter
    pattern = patterns[difficulty_band].copy()
    jitter = random.uniform(-0.05, 0.05)
    
    # Adjust correct rate and rebalance
    pattern['correct'] = max(0.1, min(0.9, pattern['correct'] + jitter))
    remaining = 1.0 - pattern['correct']
    pattern['wrong'] = remaining * 0.8  # Most of remaining goes to wrong
    pattern['skipped'] = remaining * 0.2
    
    return pattern

def select_session_questions(active_questions: List[Dict], used_question_ids: set) -> List[Dict]:
    """Select 12 questions for a session (3 Easy / 6 Medium / 3 Hard)"""
    
    # Group questions by difficulty band
    by_band = {'Easy': [], 'Medium': [], 'Hard': []}
    
    for q in active_questions:
        if q['id'] not in used_question_ids:
            band = q['difficulty_band']
            if band in by_band:
                by_band[band].append(q)
    
    # Select questions: 3 Easy, 6 Medium, 3 Hard
    session_questions = []
    
    target_counts = {'Easy': 3, 'Medium': 6, 'Hard': 3}
    
    for band, count in target_counts.items():
        available = by_band[band]
        if len(available) >= count:
            selected = random.sample(available, count)
            session_questions.extend(selected)
            # Mark as used
            for q in selected:
                used_question_ids.add(q['id'])
        else:
            # If not enough questions, take what we can
            session_questions.extend(available)
            for q in available:
                used_question_ids.add(q['id'])
    
    # Shuffle to randomize order
    random.shuffle(session_questions)
    
    return session_questions

def generate_attempt_event(user_id: str, session_id: str, question: Dict, 
                         sess_seq: int, question_order: int) -> Dict:
    """Generate a single attempt event"""
    
    difficulty_band = question['difficulty_band']
    performance = get_performance_pattern(difficulty_band)
    
    # Determine outcome based on performance pattern
    rand = random.random()
    if rand < performance['correct']:
        was_correct = True
        skipped = False
    elif rand < performance['correct'] + performance['skipped']:
        was_correct = False
        skipped = True
    else:
        was_correct = False
        skipped = False
    
    # Generate realistic response time (30s - 180s for correct, 15s - 60s for incorrect/skipped)
    if was_correct:
        response_time = random.randint(30000, 180000)  # 30s - 3min
    else:
        response_time = random.randint(15000, 60000)   # 15s - 1min
    
    return {
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'session_id': session_id,
        'question_id': question['id'],
        'was_correct': was_correct,
        'skipped': skipped,
        'response_time_ms': response_time,
        'sess_seq_at_serve': sess_seq,
        'difficulty_band': difficulty_band,
        'subcategory': question['subcategory'],
        'type_of_question': question['type_of_question'],
        'core_concepts': question['core_concepts'],
        'pyq_frequency_score': question['pyq_frequency_score'],
        'created_at': datetime.now() - timedelta(minutes=random.randint(1, 1440))  # Last 24 hours
    }

def main():
    """Generate all pseudo data"""
    
    db = SessionLocal()
    try:
        print("🚀 GENERATING PSEUDO DATA FOR ADAPTIVE LOGIC...")
        
        # Get active questions from database
        print("📊 Loading active questions...")
        active_questions = db.execute(
            select(Question)
            .where(Question.is_active == True)
        ).scalars().all()
        
        questions_data = []
        for q in active_questions:
            questions_data.append({
                'id': q.id,
                'difficulty_band': q.difficulty_band or 'Medium',
                'subcategory': q.subcategory,
                'type_of_question': q.type_of_question,
                'core_concepts': q.core_concepts,
                'pyq_frequency_score': float(q.pyq_frequency_score) if q.pyq_frequency_score else 0.5
            })
        
        print(f"   Found {len(questions_data)} active questions")
        
        # Generate users
        print("👥 Generating users...")
        users = generate_pseudo_users()
        
        # Insert users
        for user in users:
            user_data = {k: v for k, v in user.items() if k not in ['cohort', 'target_sessions']}
            db.execute(text("""
                INSERT INTO users (id, email, full_name, password_hash, is_admin, created_at, referral_code)
                VALUES (:id, :email, :full_name, :password_hash, :is_admin, :created_at, :referral_code)
                ON CONFLICT (id) DO NOTHING
            """), user_data)
        
        db.commit()
        print(f"   ✅ Inserted {len(users)} users")
        
        # Generate sessions and attempts for non-new users
        print("🎯 Generating sessions and attempts...")
        
        total_sessions = 0
        total_attempts = 0
        
        for user in users:
            if user['target_sessions'] == 0:
                continue  # Skip new users
            
            user_id = user['id']
            used_questions = set()
            
            for sess_num in range(1, user['target_sessions'] + 1):
                session_id = str(uuid.uuid4())
                
                # Create session
                session_data = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'sess_seq': sess_num,
                    'status': 'completed',
                    'created_at': datetime.now() - timedelta(days=random.randint(1, 30)),
                    'served_at': datetime.now() - timedelta(days=random.randint(1, 30)),
                    'completed_at': datetime.now() - timedelta(days=random.randint(1, 30)),
                    'total_questions': 12,
                    'questions_answered': 12,
                    'questions_correct': 0,  # Will update after attempts
                    'questions_skipped': 0   # Will update after attempts
                }
                
                db.execute(text("""
                    INSERT INTO sessions (session_id, user_id, sess_seq, status, created_at, 
                                        served_at, completed_at, total_questions, questions_answered)
                    VALUES (:session_id, :user_id, :sess_seq, :status, :created_at, 
                           :served_at, :completed_at, :total_questions, :questions_answered)
                """), session_data)
                
                # Select questions for this session
                session_questions = select_session_questions(questions_data, used_questions)
                
                if len(session_questions) < 12:
                    print(f"   ⚠️ Only {len(session_questions)} questions available for {user['email']} session {sess_num}")
                
                # Generate attempts
                correct_count = 0
                skipped_count = 0
                
                for q_order, question in enumerate(session_questions, 1):
                    attempt = generate_attempt_event(user_id, session_id, question, sess_num, q_order)
                    
                    db.execute(text("""
                        INSERT INTO attempt_events (id, user_id, session_id, question_id, was_correct, 
                                                  skipped, response_time_ms, sess_seq_at_serve, 
                                                  difficulty_band, subcategory, type_of_question, 
                                                  core_concepts, pyq_frequency_score, created_at)
                        VALUES (:id, :user_id, :session_id, :question_id, :was_correct, :skipped, 
                               :response_time_ms, :sess_seq_at_serve, :difficulty_band, :subcategory, 
                               :type_of_question, :core_concepts, :pyq_frequency_score, :created_at)
                    """), attempt)
                    
                    if attempt['was_correct']:
                        correct_count += 1
                    if attempt['skipped']:
                        skipped_count += 1
                    
                    total_attempts += 1
                
                # Update session with correct counts
                db.execute(text("""
                    UPDATE sessions 
                    SET questions_correct = :correct_count, questions_skipped = :skipped_count
                    WHERE session_id = :session_id
                """), {
                    'correct_count': correct_count,
                    'skipped_count': skipped_count,
                    'session_id': session_id
                })
                
                total_sessions += 1
        
        db.commit()
        
        print(f"   ✅ Generated {total_sessions} sessions")
        print(f"   ✅ Generated {total_attempts} attempt events")
        
        # Summary by cohort
        print("\n📊 SUMMARY BY COHORT:")
        
        cohort_summary = db.execute(text("""
            SELECT 
                CASE 
                    WHEN u.email LIKE 'new_%' THEN 'New Users (0 sessions)'
                    WHEN u.email LIKE 'early_%' THEN 'Early Users (1-3 sessions)'
                    WHEN u.email LIKE 'experienced_%' THEN 'Experienced Users (4-10 sessions)'
                END as cohort,
                COUNT(DISTINCT u.id) as user_count,
                COALESCE(COUNT(DISTINCT s.session_id), 0) as total_sessions,
                COALESCE(COUNT(DISTINCT ae.id), 0) as total_attempts
            FROM users u
            LEFT JOIN sessions s ON u.id = s.user_id 
            LEFT JOIN attempt_events ae ON u.id = ae.user_id
            WHERE u.email LIKE '%_user_%@test.com'
            GROUP BY cohort
            ORDER BY cohort
        """)).fetchall()
        
        for row in cohort_summary:
            print(f"   {row.cohort}: {row.user_count} users, {row.total_sessions} sessions, {row.total_attempts} attempts")
        
        print("\n✅ PSEUDO DATA GENERATION COMPLETED!")
        
    except Exception as e:
        print(f"❌ Error generating pseudo data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()