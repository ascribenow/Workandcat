#!/usr/bin/env python3
"""
Adaptive Logic Pipeline Service
Orchestrates session planning with cold start detection and dual-path logic
Now includes full LLM integration (Summarizer + Planner)
"""

import logging
from typing import Dict, Any, Optional, List
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

def _group_candidates_by_band(candidates) -> Dict[str, List]:
    """Group question candidates by difficulty band"""
    grouped = {"Easy": [], "Medium": [], "Hard": []}
    
    for candidate in candidates:
        band = getattr(candidate, 'difficulty_band', 'Medium')
        if band in grouped:
            grouped[band].append({
                "question_id": getattr(candidate, 'question_id', ''),
                "difficulty_band": band,
                "pair": getattr(candidate, 'pair', ''),
                "core_concepts": getattr(candidate, 'core_concepts', []),
                "pyq_frequency_score": getattr(candidate, 'pyq_frequency_score', 0.5)
            })
    
    return grouped

def _convert_dominance_to_weights(dominance_by_item: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Convert LLM dominance labels to deterministic weights"""
    weights_by_item = {}
    
    for item_id, dominance_info in dominance_by_item.items():
        dominant_concepts = dominance_info.get("dominant", [])
        secondary_concepts = dominance_info.get("secondary", [])
        confidence = dominance_info.get("dominance_confidence", "med")
        
        # Apply dominance rules from spec
        total_concepts = len(dominant_concepts) + len(secondary_concepts)
        if total_concepts == 0:
            continue
            
        weights = {}
        
        if confidence == "high" and len(dominant_concepts) == 1:
            # High confidence + 1 dominant → 0.7/0.3 split
            weights[dominant_concepts[0]] = 0.7
            remaining_weight = 0.3
            for concept in secondary_concepts:
                weights[concept] = remaining_weight / len(secondary_concepts) if secondary_concepts else 0
        elif confidence == "high" and len(dominant_concepts) == 2:
            # High confidence + 2 dominants → 0.5/0.5 split
            for concept in dominant_concepts:
                weights[concept] = 0.5
            for concept in secondary_concepts:
                weights[concept] = 0.0  # No weight for secondary if 2 dominants
        else:
            # Equal split 1/k
            weight_per_concept = 1.0 / total_concepts
            for concept in dominant_concepts + secondary_concepts:
                weights[concept] = weight_per_concept
        
        weights_by_item[item_id] = weights
    
    return weights_by_item

def _load_user_attempts(user_id: str, session_limit: int = 5) -> List[AttemptEvent]:
    """Load user's recent attempt events for deterministic processing"""
    db = SessionLocal()
    try:
        attempts = db.execute(text("""
            SELECT question_id, was_correct, skipped, response_time_ms,
                   sess_seq_at_serve, difficulty_band, subcategory, 
                   type_of_question, core_concepts, pyq_frequency_score
            FROM attempt_events ae
            JOIN sessions s ON ae.session_id = s.session_id
            WHERE ae.user_id = :user_id
            AND s.sess_seq > (
                SELECT COALESCE(MAX(sess_seq), 0) - :session_limit
                FROM sessions
                WHERE user_id = :user_id
            )
            ORDER BY ae.sess_seq_at_serve, ae.created_at
        """), {
            "user_id": user_id,
            "session_limit": session_limit
        }).fetchall()
        
        attempt_events = []
        for attempt in attempts:
            try:
                # Parse core concepts
                if isinstance(attempt.core_concepts, list):
                    concepts = attempt.core_concepts
                elif isinstance(attempt.core_concepts, str):
                    import json
                    concepts = json.loads(attempt.core_concepts)
                else:
                    concepts = []
                
                event = AttemptEvent(
                    question_id=attempt.question_id,
                    was_correct=attempt.was_correct,
                    skipped=attempt.skipped,
                    response_time_ms=attempt.response_time_ms,
                    sess_seq_at_serve=attempt.sess_seq_at_serve,
                    difficulty_band=attempt.difficulty_band,
                    subcategory=attempt.subcategory,
                    type_of_question=attempt.type_of_question,
                    core_concepts=concepts,
                    pyq_frequency_score=float(attempt.pyq_frequency_score) if attempt.pyq_frequency_score else 0.5
                )
                attempt_events.append(event)
                
            except Exception as e:
                logger.warning(f"Error parsing attempt: {e}")
                continue
        
        return attempt_events
        
    finally:
        db.close()

def plan_next_session(user_id: str, force_cold_start: bool = False) -> Dict[str, Any]:
    """
    Main pipeline function - plans the next session for a user
    
    Implements dual-path logic with full LLM integration:
    - Cold start path: Skip summarizer, use diversity-first selection via Planner
    - Normal path: Full LLM analysis (Summarizer + Planner) + adaptive selection
    
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
        # COLD START PATH - Skip Summarizer, use diversity-first Planner
        logger.info("🔥 Using COLD START pipeline...")
        
        # Build cold start candidate pool
        candidates, metadata = candidate_provider.build_coldstart_pool(user_id)
        
        if not candidates:
            return {
                'success': False,
                'error': 'No candidates available for cold start',
                'user_id': user_id,
                'session_sequence': next_sess_seq
            }
        
        # Group candidates by difficulty band for Planner
        candidate_pool_by_band = _group_candidates_by_band(candidates)
        
        # Run Planner in cold start mode (no Summarizer needed)
        plan_result = planner_service.run_planner(
            user_id=user_id,
            candidate_pool_by_band=candidate_pool_by_band,
            final_readiness=[],  # Empty for cold start
            concept_weights_by_item={},  # Empty for cold start
            pair_coverage_final=[],  # Empty for cold start
            cold_start_mode=True
        )
        
        return {
            'success': True,
            'user_id': user_id,
            'session_sequence': next_sess_seq,
            'cold_start_mode': True,
            'pipeline_path': 'cold_start',
            'plan': plan_result,
            'metadata': {
                'served_sessions': 0,
                'planning_strategy': 'cold_start_diversity',
                'candidate_pool_size': len(candidates),
                'pool_metadata': metadata
            }
        }
        
    else:
        # NORMAL ADAPTIVE PATH - Full LLM pipeline
        logger.info("🧠 Using NORMAL ADAPTIVE pipeline...")
        
        # Step 1: Run Summarizer for qualitative analysis
        summary_result = summarizer_service.run_summarizer(user_id)
        
        # Step 2: Convert LLM dominance to deterministic weights
        concept_weights_by_item = _convert_dominance_to_weights(
            summary_result.get("dominance_by_item", {})
        )
        
        # Step 3: Load user attempt history for deterministic processing
        attempt_events = _load_user_attempts(user_id)
        
        # Step 4: Run deterministic kernels with LLM weights
        weighted_counts = compute_weighted_counts(
            attempt_events, concept_weights_by_item, {}  # TODO: semantic_id_map from summarizer
        )
        readiness_map = finalize_readiness(weighted_counts)
        coverage_debt = coverage_debt_by_sessions(attempt_events)
        
        # Step 5: Build adaptive candidate pool with expansion logic
        readiness_levels_str = {k: v.value for k, v in readiness_map.items()}  # Convert enum to string
        
        # Try with base pool size first
        candidates, metadata = candidate_provider.build_candidate_pool(
            user_id, readiness_levels_str, coverage_debt
        )
        
        # Check feasibility and expand if needed
        pool_expanded = False
        expansion_attempts = 0
        max_expansions = len(AdaptiveConfig.K_POOL_EXPANSION)
        
        while expansion_attempts < max_expansions:
            feasible, feasibility_details = candidate_provider.preflight_feasible(candidates)
            
            if feasible:
                break  # Pool is feasible, proceed
            
            # Expand pool size and retry
            expansion_attempts += 1
            if expansion_attempts < max_expansions:
                expanded_k = AdaptiveConfig.K_POOL_EXPANSION[expansion_attempts]
                logger.info(f"🔄 Expanding pool to K={expanded_k} (attempt {expansion_attempts})")
                
                candidates, metadata = candidate_provider.build_candidate_pool(
                    user_id, readiness_levels_str, coverage_debt, k_pool_per_band=expanded_k
                )
                pool_expanded = True
            else:
                logger.warning(f"⚠️ Pool expansion exhausted, proceeding with infeasible pool")
                break
        
        if not candidates:
            return {
                'success': False,
                'error': 'No candidates available for adaptive session',
                'user_id': user_id,
                'session_sequence': next_sess_seq
            }
        
        # Step 6: Group candidates and prepare data for Planner
        candidate_pool_by_band = _group_candidates_by_band(candidates)
        
        final_readiness = [
            {
                "semantic_id": semantic_id,
                "readiness_level": level.value,
                "pair": "unknown:unknown"  # TODO: Extract from summarizer
            }
            for semantic_id, level in readiness_map.items()
        ]
        
        pair_coverage_final = [
            {
                "pair": pair,
                "coverage_debt": "high" if debt > 0.7 else "med" if debt > 0.3 else "low"
            }
            for pair, debt in coverage_debt.items()
        ]
        
        # Step 7: Run Planner with full adaptive data
        plan_result = planner_service.run_planner(
            user_id=user_id,
            candidate_pool_by_band=candidate_pool_by_band,
            final_readiness=final_readiness,
            concept_weights_by_item=concept_weights_by_item,
            pair_coverage_final=pair_coverage_final,
            cold_start_mode=False
        )
        
        # Add metadata about pool expansion and retry usage
        if "constraint_report" in plan_result:
            plan_result["constraint_report"].setdefault("meta", {}).update({
                "pool_expanded": pool_expanded,
                "expansion_attempts": expansion_attempts
            })
        
        # Step 8: Save summarizer results for future sessions
        # TODO: Get actual session_id
        temp_session_id = f"session_{next_sess_seq}_{user_id[:8]}"
        summarizer_service.save_session_summary(user_id, temp_session_id, summary_result)
        
        return {
            'success': True,
            'user_id': user_id,
            'session_sequence': next_sess_seq,
            'cold_start_mode': False,
            'pipeline_path': 'adaptive',
            'plan': plan_result,
            'summary': summary_result,
            'metadata': {
                'served_sessions': len(attempt_events),
                'planning_strategy': 'adaptive_readiness',
                'candidate_pool_size': len(candidates),
                'pool_metadata': metadata,
                'concepts_analyzed': len(readiness_map),
                'coverage_pairs': len(coverage_debt)
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
    COVERAGE_K = 6             # Coverage calculation window
    COVERAGE_S_HIGH = 4        # Sessions since last for high debt
    COVERAGE_S_MED = 2         # Sessions since last for med debt
    
    # PYQ score requirements
    PYQ_MIN_1_0 = 2           # Min questions with PYQ score 1.0
    PYQ_MIN_1_5 = 2           # Min questions with PYQ score 1.5
    
    # Session structure
    QUESTIONS_PER_SESSION = 12
    DIFFICULTY_DISTRIBUTION = {'Easy': 3, 'Medium': 6, 'Hard': 3}
    
    # Concept exposure
    MIN_CONCEPT_EXPOSURE = 2   # Min questions per concept in cold start