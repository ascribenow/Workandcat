#!/usr/bin/env python3
"""
Generate sessions and attempts for existing test users
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
    pattern['wrong'] = remaining * 0.8
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
            for q in selected:
                used_question_ids.add(q['id'])
        else:
            # Take what we can get
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
    
    # Determine outcome
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
    
    # Generate response time
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
        'created_at': datetime.now() - timedelta(minutes=random.randint(1, 1440))
    }

def main():
    """Generate sessions and attempts for existing test users"""
    
    db = SessionLocal()
    try:
        print("🚀 GENERATING SESSIONS AND ATTEMPTS...")
        
        # Get active questions
        print("📊 Loading active questions...")
        active_questions = db.execute(
            select(Question).where(Question.is_active == True)
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
        
        # Get existing test users
        test_users = db.execute(text('''
            SELECT id, email FROM users WHERE email LIKE '%test.com' ORDER BY email
        ''')).fetchall()
        
        print(f"   Found {len(test_users)} test users")
        
        # Determine target sessions for each user
        user_targets = {}
        for user in test_users:
            email = user.email
            if 'new_user' in email:
                user_targets[user.id] = 0  # New users get 0 sessions
            elif 'early_user' in email:
                user_targets[user.id] = random.randint(1, 3)  # Early users get 1-3
            elif 'experienced_user' in email:
                user_targets[user.id] = random.randint(4, 10)  # Experienced get 4-10
        
        total_sessions = 0
        total_attempts = 0
        
        # Generate sessions and attempts
        for user in test_users:
            user_id = user.id
            target_sessions = user_targets[user_id]
            
            if target_sessions == 0:
                print(f"   📝 {user.email}: New user (0 sessions)")
                continue
            
            print(f"   📝 {user.email}: Generating {target_sessions} sessions...")
            
            used_questions = set()
            
            for sess_num in range(1, target_sessions + 1):
                session_id = str(uuid.uuid4())
                
                # Create session
                session_created = datetime.now() - timedelta(days=random.randint(1, 60))
                session_data = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'sess_seq': sess_num,
                    'status': 'completed',
                    'created_at': session_created,
                    'served_at': session_created + timedelta(minutes=1),
                    'completed_at': session_created + timedelta(minutes=random.randint(15, 45)),
                    'total_questions': 12
                }
                
                db.execute(text('''
                    INSERT INTO sessions (session_id, user_id, sess_seq, status, created_at, 
                                        served_at, completed_at, total_questions)
                    VALUES (:session_id, :user_id, :sess_seq, :status, :created_at, 
                           :served_at, :completed_at, :total_questions)
                '''), session_data)
                
                # Select questions for this session
                session_questions = select_session_questions(questions_data, used_questions)
                
                # Generate attempts
                correct_count = 0
                skipped_count = 0
                
                for q_order, question in enumerate(session_questions, 1):
                    attempt = generate_attempt_event(user_id, session_id, question, sess_num, q_order)
                    
                    db.execute(text('''
                        INSERT INTO attempt_events (id, user_id, session_id, question_id, was_correct, 
                                                  skipped, response_time_ms, sess_seq_at_serve, 
                                                  difficulty_band, subcategory, type_of_question, 
                                                  core_concepts, pyq_frequency_score, created_at)
                        VALUES (:id, :user_id, :session_id, :question_id, :was_correct, :skipped, 
                               :response_time_ms, :sess_seq_at_serve, :difficulty_band, :subcategory, 
                               :type_of_question, :core_concepts, :pyq_frequency_score, :created_at)
                    '''), attempt)
                    
                    if attempt['was_correct']:
                        correct_count += 1
                    if attempt['skipped']:
                        skipped_count += 1
                    
                    total_attempts += 1
                
                # Update session with stats
                db.execute(text('''
                    UPDATE sessions 
                    SET questions_answered = :total, questions_correct = :correct, questions_skipped = :skipped
                    WHERE session_id = :session_id
                '''), {
                    'total': len(session_questions),
                    'correct': correct_count,
                    'skipped': skipped_count,
                    'session_id': session_id
                })
                
                total_sessions += 1
        
        db.commit()
        
        print(f"\\n✅ Generated {total_sessions} sessions")
        print(f"✅ Generated {total_attempts} attempt events")
        
        # Final summary
        summary = db.execute(text('''
            SELECT 
                CASE 
                    WHEN u.email LIKE 'new_%' THEN 'New Users (0 sessions)'
                    WHEN u.email LIKE 'early_%' THEN 'Early Users (1-3 sessions)'  
                    WHEN u.email LIKE 'experienced_%' THEN 'Experienced Users (4-10 sessions)'
                END as cohort,
                COUNT(DISTINCT u.id) as user_count,
                COALESCE(COUNT(DISTINCT s.session_id), 0) as total_sessions,
                COALESCE(COUNT(DISTINCT ae.id), 0) as total_attempts,
                COALESCE(AVG(s.questions_correct), 0) as avg_correct
            FROM users u
            LEFT JOIN sessions s ON u.id = s.user_id 
            LEFT JOIN attempt_events ae ON u.id = ae.user_id
            WHERE u.email LIKE '%test.com'
            GROUP BY cohort
            ORDER BY cohort
        ''')).fetchall()
        
        print("\\n📊 FINAL SUMMARY:")
        for row in summary:
            print(f"   {row.cohort}:")
            print(f"     Users: {row.user_count}")
            print(f"     Sessions: {row.total_sessions}")
            print(f"     Attempts: {row.total_attempts}")
            print(f"     Avg Correct: {row.avg_correct:.1f}")
        
        print("\\n✅ PSEUDO DATA GENERATION COMPLETED!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()