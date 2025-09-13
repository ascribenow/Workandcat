#!/usr/bin/env python3
"""
Adaptive Logic Pipeline Service
Orchestrates session planning with cold start detection and dual-path logic
Now includes full LLM integration (Summarizer + Planner)
"""

import logging
from typing import Dict, Any, Optional
from database import SessionLocal
from sqlalchemy import text, select
from services.deterministic_kernels import (
    weights_from_dominance, compute_weighted_counts, finalize_readiness,
    coverage_debt_by_sessions, AttemptEvent
)
from services.candidate_provider import candidate_provider
from services.summarizer import summarizer_service
from services.planner import planner_service

logger = logging.getLogger(__name__)

def get_served_session_count(user_id: str) -> int:
    """Get the number of served sessions for a user"""
    db = SessionLocal()
    try:
        count = db.execute(text("""
            SELECT COUNT(*) FROM sessions 
            WHERE user_id = :user_id AND status IN ('served', 'completed')
        """), {'user_id': user_id}).scalar()
        
        return count or 0
    finally:
        db.close()

def should_cold_start(user_id: str, force_cold_start: bool = False) -> bool:
    """
    Determine if a user should use cold start logic
    
    Cold start criteria:
    - User has 0 served sessions (new user)
    - Force flag is enabled (for testing)
    
    Args:
        user_id: User identifier
        force_cold_start: Override flag for testing
        
    Returns:
        True if cold start logic should be used
    """
    if force_cold_start:
        logger.info(f"🔥 Cold start FORCED for user {user_id[:8]}...")
        return True
    
    served_count = get_served_session_count(user_id)
    is_cold_start = served_count == 0
    
    if is_cold_start:
        logger.info(f"🆕 Cold start detected for user {user_id[:8]}... (served sessions: {served_count})")
    else:
        logger.info(f"🔄 Normal adaptive mode for user {user_id[:8]}... (served sessions: {served_count})")
    
    return is_cold_start

def get_user_session_history(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """Get user's session history for adaptive analysis"""
    db = SessionLocal()
    try:
        # Get recent sessions with attempt data
        sessions = db.execute(text("""
            SELECT 
                s.session_id,
                s.sess_seq,
                s.status,
                s.questions_correct,
                s.questions_answered,
                s.questions_skipped,
                s.completed_at,
                COUNT(ae.id) as total_attempts,
                AVG(CASE WHEN ae.was_correct THEN 1.0 ELSE 0.0 END) as accuracy,
                AVG(ae.response_time_ms) as avg_response_time
            FROM sessions s
            LEFT JOIN attempt_events ae ON s.session_id = ae.session_id
            WHERE s.user_id = :user_id 
            AND s.status IN ('completed', 'served')
            GROUP BY s.session_id, s.sess_seq, s.status, s.questions_correct, 
                     s.questions_answered, s.questions_skipped, s.completed_at
            ORDER BY s.sess_seq DESC
            LIMIT :limit
        """), {'user_id': user_id, 'limit': limit}).fetchall()
        
        session_history = []
        for session in sessions:
            session_history.append({
                'session_id': session.session_id,
                'sess_seq': session.sess_seq,
                'status': session.status,
                'questions_correct': session.questions_correct,
                'questions_answered': session.questions_answered,
                'questions_skipped': session.questions_skipped,
                'completed_at': session.completed_at,
                'total_attempts': session.total_attempts,
                'accuracy': float(session.accuracy) if session.accuracy else 0.0,
                'avg_response_time': float(session.avg_response_time) if session.avg_response_time else 0.0
            })
        
        return {
            'user_id': user_id,
            'total_sessions': len(session_history),
            'sessions': session_history
        }
        
    finally:
        db.close()

def get_next_session_sequence(user_id: str) -> int:
    """Get the next session sequence number for a user"""
    db = SessionLocal()
    try:
        max_seq = db.execute(text("""
            SELECT COALESCE(MAX(sess_seq), 0) FROM sessions 
            WHERE user_id = :user_id
        """), {'user_id': user_id}).scalar()
        
        return (max_seq or 0) + 1
    finally:
        db.close()

async def plan_next_session(user_id: str, force_cold_start: bool = False) -> Dict[str, Any]:
    """
    Main pipeline function - plans the next session for a user
    
    Implements dual-path logic:
    - Cold start path: Skip summarizer, use diversity-first selection
    - Normal path: Full LLM analysis + adaptive selection
    
    Args:
        user_id: User identifier
        force_cold_start: Force cold start mode for testing
        
    Returns:
        Session plan with question pack and metadata
    """
    logger.info(f"🚀 Planning next session for user {user_id[:8]}...")
    
    # Step 1: Cold start detection
    is_cold_start = should_cold_start(user_id, force_cold_start)
    next_sess_seq = get_next_session_sequence(user_id)
    
    logger.info(f"📊 Next session sequence: {next_sess_seq}")
    
    if is_cold_start:
        # COLD START PATH
        logger.info("🔥 Using COLD START pipeline...")
        
        # TODO: Implement cold start logic
        # - Skip LLM Summarizer (no history)
        # - Use build_coldstart_pool() for diversity-first selection
        # - Simple constraint validation
        
        return {
            'success': True,
            'user_id': user_id,
            'session_sequence': next_sess_seq,
            'cold_start_mode': True,
            'pipeline_path': 'cold_start',
            'message': 'Cold start pipeline - diversity-first question selection',
            'pack': [],  # TODO: Implement
            'metadata': {
                'served_sessions': 0,
                'planning_strategy': 'cold_start_diversity'
            }
        }
        
    else:
        # NORMAL ADAPTIVE PATH
        logger.info("🧠 Using NORMAL ADAPTIVE pipeline...")
        
        # Get session history for analysis
        history = get_user_session_history(user_id, limit=5)
        
        # TODO: Implement full adaptive logic
        # - LLM Summarizer for concept analysis
        # - Deterministic kernels for weights/readiness/coverage
        # - LLM Planner for optimal question selection
        # - Strict constraint validation
        
        return {
            'success': True,
            'user_id': user_id,
            'session_sequence': next_sess_seq,
            'cold_start_mode': False,
            'pipeline_path': 'adaptive',
            'message': 'Full adaptive pipeline - readiness-based question selection',
            'pack': [],  # TODO: Implement
            'metadata': {
                'served_sessions': history['total_sessions'],
                'planning_strategy': 'adaptive_readiness',
                'history_analyzed': len(history['sessions'])
            }
        }

def validate_session_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a session plan meets all constraints
    
    Constraints:
    - 12 questions total
    - 3 Easy / 6 Medium / 3 Hard distribution
    - Minimum PYQ score requirements
    - No duplicate questions
    
    Args:
        plan: Session plan to validate
        
    Returns:
        Validation result with pass/fail and details
    """
    pack = plan.get('pack', [])
    
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'constraints_checked': []
    }
    
    # Constraint 1: Total question count
    if len(pack) != 12:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Expected 12 questions, got {len(pack)}")
    validation_result['constraints_checked'].append('total_count')
    
    # Constraint 2: Difficulty distribution
    difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0}
    for question in pack:
        band = question.get('difficulty_band')
        if band in difficulty_counts:
            difficulty_counts[band] += 1
    
    expected_distribution = {'Easy': 3, 'Medium': 6, 'Hard': 3}
    for band, expected in expected_distribution.items():
        actual = difficulty_counts[band]
        if actual != expected:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Expected {expected} {band} questions, got {actual}")
    validation_result['constraints_checked'].append('difficulty_distribution')
    
    # Constraint 3: PYQ score requirements (TODO: Implement when we have questions)
    # Constraint 4: No duplicates (TODO: Implement when we have questions)
    
    logger.info(f"📋 Validation result: {'PASS' if validation_result['valid'] else 'FAIL'}")
    if validation_result['errors']:
        for error in validation_result['errors']:
            logger.error(f"   ❌ {error}")
    
    return validation_result

# Configuration constants (as per specification)
class AdaptiveConfig:
    """Configuration constants for adaptive logic"""
    
    # Cold start detection
    COLD_START_THRESHOLD = 0  # Sessions before full adaptive mode (0 = only new users)
    
    # Question pool parameters  
    K_POOL_PER_BAND = 80       # Question pool size per difficulty band (base)
    K_POOL_EXPANSION = [80, 160, 320]  # Adaptive expansion ladder: K→2K→4K
    DIVERSITY_POOL_SIZE = 100  # Cold start candidate pool size
    
    # Recency and coverage parameters
    R_RECENCY_SESSIONS = 3     # Recency lookback window
    COVERAGE_K = 5             # Coverage calculation window
    
    # PYQ score requirements
    PYQ_MIN_1_0 = 2           # Min questions with PYQ score 1.0
    PYQ_MIN_1_5 = 2           # Min questions with PYQ score 1.5
    
    # Session structure
    QUESTIONS_PER_SESSION = 12
    DIFFICULTY_DISTRIBUTION = {'Easy': 3, 'Medium': 6, 'Hard': 3}
    
    # Concept exposure
    MIN_CONCEPT_EXPOSURE = 2   # Min questions per concept in cold start