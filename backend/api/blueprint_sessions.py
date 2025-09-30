"""
Blueprint Session API - Phase 3 Implementation
New /session/* endpoints using BlueprintSessionPlanner for immediate availability
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import asyncpg
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text, select

from auth import get_current_user
from services.blueprint_planner import BlueprintSessionPlanner, create_blueprint_planner
from database import get_async_compatible_db, get_database, SessionLocal, User
from subscription_access_service import subscription_access_service
from free_tier_session_service import free_tier_service
from utils.uuid_validator import validate_canonical_uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["blueprint_sessions"])

# Request/Response Models
class SessionStartRequest(BaseModel):
    user_id: str

class AnswerSubmitRequest(BaseModel):
    session_id: str
    position: int  # 1-based position
    answer: str

class SessionCompleteRequest(BaseModel):
    session_id: str

# Global planner instance (will be initialized on startup)
_planner_instance: Optional[BlueprintSessionPlanner] = None

async def get_blueprint_planner() -> BlueprintSessionPlanner:
    """Get or create blueprint planner instance"""
    global _planner_instance
    
    if _planner_instance is None:
        _planner_instance = create_blueprint_planner()
        logger.info("Blueprint planner instance created successfully")
    
    return _planner_instance

@router.post("/start")
async def start_session(
    request: SessionStartRequest,
    auth_user_id: str = Depends(get_current_user)
):
    """
    Start a new blueprint session - with session limit enforcement
    
    Serves pre-packed sessions when user has access, blocks when limits exceeded
    """
    
    # Validate UUID format at API boundary
    user_id = validate_canonical_uuid(request.user_id, "user_id")
    auth_user_id = validate_canonical_uuid(auth_user_id, "authenticated_user_id")
    
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Cannot start session for other users")
    
    logger.info(f"Starting blueprint session for user {user_id[:8]} - checking access limits")
    
    # SESSION ACCESS CONTROL - Check limits before serving pre-packed session
    db = SessionLocal()
    try:
        # Get user details for access checking
        user_result = db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check user's subscription access level
        access_level = subscription_access_service.get_user_access_level(
            user_id, user.email, db
        )
        
        logger.info(f"User {request.user_id[:8]} access level: {access_level['plan_type']} - unlimited: {access_level['unlimited_sessions']}")
        
        # For users with unlimited sessions (Pro Regular, Pro Exclusive, Privileged)
        if access_level["unlimited_sessions"]:
            logger.info(f"User {request.user_id[:8]} has unlimited access - proceeding to serve session")
        else:
            # Free tier users - check session limits using FreeTierSessionService
            logger.info(f"User {request.user_id[:8]} is free tier - checking session availability")
            
            try:
                session_status = free_tier_service.get_user_session_status(
                    request.user_id, user.email, db
                )
                
                sessions_available = session_status.get("sessions_available", 0)
                is_initial_period = session_status.get("is_initial_period", True)
                cycle_end_date = session_status.get("cycle_end_date")
                
                logger.info(f"Free tier status - Available: {sessions_available}, Initial period: {is_initial_period}")
                
                if sessions_available <= 0:
                    # No sessions available - return detailed error
                    if is_initial_period:
                        error_msg = f"You've used all {free_tier_service.initial_sessions} initial sessions. Upgrade to Pro for unlimited sessions."
                    else:
                        error_msg = f"Weekly session limit reached. Next sessions available: {cycle_end_date}. Upgrade to Pro for unlimited access."
                    
                    logger.info(f"Session access denied for user {request.user_id[:8]}: {error_msg}")
                    raise HTTPException(
                        status_code=403, 
                        detail={
                            "error": "session_limit_exceeded",
                            "message": error_msg,
                            "user_type": "free_tier",
                            "sessions_available": 0,
                            "next_allocation_date": cycle_end_date,
                            "upgrade_required": True
                        }
                    )
                
                logger.info(f"Free tier user {request.user_id[:8]} has {sessions_available} sessions available - proceeding")
                
            except Exception as e:
                logger.error(f"Error checking free tier limits for user {request.user_id[:8]}: {e}")
                # If free tier service fails, allow session but log the error
                logger.warning("Free tier service error - allowing session to prevent service disruption")
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error checking session access for user {request.user_id[:8]}: {e}")
        # If access check fails completely, allow session to prevent service disruption
        logger.warning("Session access check failed - allowing session to prevent service disruption")
    finally:
        db.close()
    
    # ACCESS GRANTED - Proceed to serve pre-packed session
    try:
        # CACHE TTL PRAGMATISM: Force refresh insights if stale before session start
        # Rationale: Pre-session "aha moment" is critical - stale cards kill the effect
        from services.bg_job_queue import job_queue
        
        try:
            db_cache_check = SessionLocal()
            cache_check = db_cache_check.execute(text("""
                SELECT last_updated_at FROM user_dashboard_insights 
                WHERE user_id = :user_id
            """), {"user_id": request.user_id}).fetchone()
            
            should_force_refresh = False
            if cache_check and cache_check.last_updated_at:
                cache_age_hours = (datetime.now(timezone.utc) - cache_check.last_updated_at).total_seconds() / 3600
                # Force refresh if cache is older than 4 hours before session start
                should_force_refresh = cache_age_hours > 4
                
                if should_force_refresh:
                    logger.info(f"🔄 Force refreshing insights for session start - cache age: {cache_age_hours:.1f}h")
            else:
                # No cache exists - definitely refresh
                should_force_refresh = True
                logger.info(f"🔄 Force refreshing insights for session start - no cache exists")
            
            if should_force_refresh:
                await job_queue.enqueue_job("UPDATE_INSIGHTS", request.user_id)
                
        except Exception as cache_check_error:
            logger.warning(f"Cache staleness check failed: {cache_check_error}")
        finally:
            db_cache_check.close()

        planner = await get_blueprint_planner()
        
        # Plan/serve session (will use pre-packed if available, create new if not)
        session_data = await planner.plan_session(request.user_id)
        
        # Get calculated session number based on completed sessions (FIX: Use meaningful progression)
        db = planner.get_db_session()
        try:
            # Calculate session number based on completed sessions count
            completed_count_result = db.execute(text("""
                SELECT COUNT(*) FROM sessions 
                WHERE user_id = :user_id AND status = 'completed'
            """), {"user_id": request.user_id})
            completed_count = completed_count_result.scalar() or 0
            calculated_session_number = completed_count + 1
        finally:
            db.close()
        
        logger.info(f"Blueprint session {session_data['session_id'][:8]} created successfully with {len(session_data.get('questions', []))} questions")
        
        return JSONResponse({
            "success": True,
            "session_id": session_data["session_id"],
            "status": session_data["status"],
            "questions": session_data["questions"],
            "constraint_report": session_data["constraint_report"],
            "total_questions": len(session_data.get("questions", [])),
            "current_position": 1,  # Blueprint sessions start at position 1
            "session_type": "blueprint",
            "session_number": calculated_session_number,  # FIX: Use calculated number instead of stored sess_seq
            "created_at": datetime.now(timezone.utc).isoformat()
        }, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to start blueprint session for user {request.user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")

@router.get("/status/{session_id}")
async def get_session_status(
    session_id: str,
    auth_user_id: str = Depends(get_current_user)
):
    """
    Get current status of a blueprint session
    """
    
    try:
        planner = await get_blueprint_planner()
        
        # Get session data from database
        session_data = await planner._get_existing_planned_session(uuid.UUID(auth_user_id))
        
        if not session_data or session_data["session_id"] != session_id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get current progress
        answered_count = 0
        # In a full implementation, we'd check session_answers table
        # For now, return basic status
        
        return JSONResponse({
            "session_id": session_id,
            "status": session_data["status"],
            "total_questions": len(session_data.get("questions", [])),
            "answered_count": answered_count,
            "current_position": answered_count + 1,
            "constraint_report": session_data["constraint_report"],
            "session_type": "blueprint"
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status for {session_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")

@router.get("/questions/{session_id}")
async def get_session_questions(
    session_id: str,
    auth_user_id: str = Depends(get_current_user)
):
    """
    Get all questions for a Blueprint session at once (performance optimization)
    """
    
    try:
        planner = await get_blueprint_planner()
        
        # Validate session_id format
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        # Get session questions
        questions = await planner._get_session_questions(session_uuid)
        
        if not questions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Format questions for frontend consumption
        formatted_questions = []
        for q in questions:
            # POSITION INTEGRITY CHECK: Ensure question position consistency
            question_position = q.get('position', 0)
            question_id = q.get('id', 'NO_ID')
            
            # Validate question data completeness
            critical_fields = ['id', 'stem', 'option_a', 'option_b', 'option_c', 'option_d', 'answer']
            missing_fields = [field for field in critical_fields if not q.get(field)]
            if missing_fields:
                logger.warning(f"Question {question_id[:8]} at position {question_position} missing fields: {missing_fields}")
            
            formatted_question = {
                "id": question_id,
                "stem": q.get("stem", ""),
                "option_a": q.get("option_a", ""),
                "option_b": q.get("option_b", ""),
                "option_c": q.get("option_c", ""),
                "option_d": q.get("option_d", ""),
                "difficulty_band": q.get("difficulty_band", ""),
                "subcategory": q.get("subcategory", ""),
                "type_of_question": q.get("type_of_question", ""),
                "position": question_position,
                "answer": q.get("answer", ""),
                # Add validation metadata for frontend debugging
                "_display_meta": {
                    "has_all_options": all(q.get(f'option_{opt}') for opt in ['a', 'b', 'c', 'd']),
                    "has_solution_feedback": any(q.get(field) for field in ['snap_read', 'solution_approach', 'detailed_solution', 'principle_to_remember']),
                    "served_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            formatted_questions.append(formatted_question)
        
        # Sort by position to ensure correct order
        formatted_questions.sort(key=lambda x: x["position"])
        
        logger.info(f"Retrieved {len(formatted_questions)} questions for session {session_id[:8]}")
        
        return JSONResponse({
            "session_id": session_id,
            "total_questions": len(formatted_questions),
            "questions": formatted_questions
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get questions for session {session_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session questions: {str(e)}")

@router.get("/question/{session_id}/{position}")
async def get_question(
    session_id: str,
    position: int,
    auth_user_id: str = Depends(get_current_user)
):
    """
    Get specific question by position from blueprint session
    """
    
    if not (1 <= position <= 12):
        raise HTTPException(status_code=400, detail="Position must be between 1 and 12")
    
    try:
        planner = await get_blueprint_planner()
        
        # Validate session_id format
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        # Get session questions
        questions = await planner._get_session_questions(session_uuid)
        
        if not questions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify user owns this session (security check)
        # In a full implementation, we'd check session ownership
        
        # Find question at specified position
        question_at_position = None
        for q in questions:
            if q.get('position') == position:
                question_at_position = q
                break
        
        if not question_at_position:
            # Better error message for missing position
            available_positions = sorted([q.get('position', 0) for q in questions])
            raise HTTPException(
                status_code=404, 
                detail=f"Question at position {position} not found. Available positions: {available_positions}"
            )
        
        return JSONResponse({
            "session_id": session_id,
            "position": position,
            "question": {
                "id": question_at_position.get("id", ""),
                "stem": question_at_position.get("stem", ""),
                "option_a": question_at_position.get("option_a", ""),
                "option_b": question_at_position.get("option_b", ""),
                "option_c": question_at_position.get("option_c", ""),
                "option_d": question_at_position.get("option_d", ""),
                "difficulty_band": question_at_position.get("difficulty_band", ""),
                "subcategory": question_at_position.get("subcategory", ""),
                "type_of_question": question_at_position.get("type_of_question", "")
                # Note: Answer and explanation are not included in question retrieval for security
            },
            "is_last": position == len(questions),
            "next_position": position + 1 if position < len(questions) else None,
            "total_questions": len(questions)
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get question {position} for session {session_id[:8] if len(session_id) > 8 else session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get question: {str(e)}")

@router.post("/submit")
async def submit_answer(
    request: AnswerSubmitRequest,
    auth_user_id: str = Depends(get_current_user)
):
    """
    Submit answer for a question in blueprint session
    """
    
    if not (1 <= request.position <= 12):
        raise HTTPException(status_code=400, detail="Position must be between 1 and 12")
    
    try:
        planner = await get_blueprint_planner()
        
        # Validate session_id format
        try:
            session_uuid = uuid.UUID(request.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID format")
        
        # Get session questions to validate answer
        questions = await planner._get_session_questions(session_uuid)
        
        if not questions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if position is valid for this session
        available_positions = [q.get('position', 0) for q in questions]
        if request.position not in available_positions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid position {request.position}. Available positions: {sorted(available_positions)}"
            )
        
        # POSITION INTEGRITY CHECK: Cross-validate question at position with display data  
        question_at_position = None
        for q in questions:
            if q.get('position') == request.position:
                question_at_position = q
                break
        
        if not question_at_position:
            raise HTTPException(status_code=404, detail=f"Question at position {request.position} not found")
        
        # CROSS-VALIDATION: Check if this matches what was displayed to user
        display_meta = question_at_position.get('_validation', {})
        if display_meta:
            logger.info(f"Question validation metadata: stored_position={display_meta.get('stored_position')}, has_all_options={display_meta.get('has_all_options')}")
        
        # DEBUG: Enhanced question data logging for troubleshooting
        question_id = question_at_position.get('id', 'NO_ID')
        logger.info(f"Answer submission for position {request.position}: ID={question_id[:8]}")
        logger.info(f"Question stem preview: {question_at_position.get('stem', 'NO_STEM')[:100]}...")
        logger.info(f"Question options: A='{question_at_position.get('option_a', '')[:20]}', B='{question_at_position.get('option_b', '')[:20]}'")
        logger.info(f"Solution feedback availability: snap_read={bool(question_at_position.get('snap_read'))}, approach={bool(question_at_position.get('solution_approach'))}")
        
        # VALIDATION: Cross-check question data integrity
        expected_fields = ['id', 'stem', 'option_a', 'option_b', 'option_c', 'option_d', 'answer']
        missing_fields = [field for field in expected_fields if not question_at_position.get(field)]
        if missing_fields:
            logger.error(f"CRITICAL: Question at position {request.position} missing fields: {missing_fields}")
            # Continue with submission but log the critical issue
        
        # Check if answer is correct
        correct_answer = question_at_position.get('answer', '')
        user_answer = request.answer.strip().lower()
        correct_answer_clean = correct_answer.strip().lower()
        
        is_correct = user_answer == correct_answer_clean
        
        # Store answer in session_answers table
        db = planner.get_db_session()
        try:
            db.execute(text("""
                INSERT INTO session_answers (session_id, position, question_id, user_answer, is_correct, explanation, timestamp)
                VALUES (:session_id, :position, :question_id, :user_answer, :is_correct, :explanation, :timestamp)
                ON CONFLICT (session_id, position) DO UPDATE SET
                    user_answer = EXCLUDED.user_answer,
                    is_correct = EXCLUDED.is_correct,
                    timestamp = EXCLUDED.timestamp
            """), {
                "session_id": request.session_id,  # Use string directly
                "position": request.position,
                "question_id": question_at_position['id'],  # Use string directly
                "user_answer": request.answer,
                "is_correct": is_correct,
                "explanation": question_at_position.get('explanation', ''),
                "timestamp": datetime.now(timezone.utc)
            })
            
            # DASHBOARD FIX: Create attempt_events record for dashboard category breakdown  
            # Use UPSERT to prevent duplicates based on session + position
            db.execute(text("""
                INSERT INTO attempt_events (
                    id, user_id, session_id, question_id, was_correct, skipped,
                    response_time_ms, created_at, difficulty_band, subcategory,
                    type_of_question, core_concepts, pyq_frequency_score, sess_seq_at_serve
                ) VALUES (
                    :id, :user_id, :session_id, :question_id, :was_correct, :skipped,
                    :response_time_ms, :created_at, :difficulty_band, :subcategory,
                    :type_of_question, :core_concepts, :pyq_frequency_score, :sess_seq_at_serve
                )
                ON CONFLICT (user_id, session_id, sess_seq_at_serve) DO UPDATE SET
                    was_correct = EXCLUDED.was_correct,
                    response_time_ms = EXCLUDED.response_time_ms,
                    created_at = EXCLUDED.created_at
            """), {
                "id": str(uuid.uuid4()),
                "user_id": auth_user_id,
                "session_id": request.session_id,
                "question_id": question_at_position['id'],
                "was_correct": is_correct,
                "skipped": False,  # Blueprint answers are never skipped
                "response_time_ms": 30000,  # Default response time for Blueprint answers
                "created_at": datetime.now(timezone.utc),
                "difficulty_band": question_at_position.get('difficulty_band', 'Medium'),
                "subcategory": question_at_position.get('subcategory', 'General'),
                "type_of_question": question_at_position.get('type_of_question', 'MCQ'),
                "core_concepts": json.dumps(question_at_position.get('core_concepts', [])),  # Convert to JSON string
                "pyq_frequency_score": question_at_position.get('pyq_frequency_score', 0),
                "sess_seq_at_serve": request.position  # Use position as sequence
            })
            
            # REAL-TIME SESSION PROGRESS UPDATE: Update sessions table with current progress
            # Get current session stats from session_answers
            session_stats = db.execute(text("""
                SELECT 
                    COUNT(*) as total_answered,
                    COUNT(*) FILTER (WHERE is_correct = true) as total_correct,
                    MAX(position) as current_position
                FROM session_answers 
                WHERE session_id = :session_id
            """), {"session_id": request.session_id}).fetchone()
            
            if session_stats:
                total_answered, total_correct, current_pos = session_stats
                
                # Update sessions table with real-time progress
                db.execute(text("""
                    UPDATE sessions 
                    SET questions_answered = :questions_answered,
                        questions_correct = :questions_correct,
                        current_position = :current_position
                    WHERE session_id = :session_id
                """), {
                    "questions_answered": total_answered,
                    "questions_correct": total_correct,
                    "current_position": current_pos,
                    "session_id": request.session_id
                })
                
                logger.info(f"Real-time session update: {total_correct}/{total_answered} correct, position {current_pos}")
            
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Answer submitted for session {request.session_id[:8]}, position {request.position}: {'correct' if is_correct else 'incorrect'}")
        
        # Build solution feedback object from question data with improved formatting
        from utils.solution_formatter import format_solution_content, format_solution_approach, format_snap_read
        
        solution_feedback = {
            "snap_read": format_snap_read(question_at_position.get('snap_read', '')),
            "solution_approach": format_solution_approach(question_at_position.get('solution_approach', '')),
            "detailed_solution": format_solution_content(question_at_position.get('detailed_solution', '')),
            "principle_to_remember": format_solution_content(question_at_position.get('principle_to_remember', ''))
        }
        
        # VALIDATION: If solution feedback is missing or questionable, fetch from questions table directly
        feedback_quality_check = any(len(str(v)) > 50 for v in solution_feedback.values() if v)  # Check if feedback seems substantial
        
        if not feedback_quality_check:
            logger.warning(f"Solution feedback appears insufficient for position {request.position}, fetching from questions table")
            
            try:
                question_id = question_at_position.get('id')
                if question_id:
                    db_question_result = db.execute(text("""
                        SELECT snap_read, solution_approach, detailed_solution, principle_to_remember, answer, stem
                        FROM questions
                        WHERE id = :question_id
                    """), {"question_id": question_id})
                    
                    db_question_row = db_question_result.fetchone()
                    if db_question_row:
                        # Cross-validate question consistency by checking stem
                        db_stem = db_question_row.stem or ''
                        session_stem = question_at_position.get('stem', '')
                        
                        if db_stem[:100] != session_stem[:100]:  # Compare first 100 chars
                            logger.error(f"CRITICAL MISMATCH: Question stems don't match!")
                            logger.error(f"DB stem: {db_stem[:100]}")
                            logger.error(f"Session stem: {session_stem[:100]}")
                        else:
                            logger.info(f"✅ Question stem consistency validated")
                        
                        # Use database solution feedback if it's better (with formatting)
                        db_solution_feedback = {
                            "snap_read": format_snap_read(db_question_row.snap_read or ''),
                            "solution_approach": format_solution_approach(db_question_row.solution_approach or ''),
                            "detailed_solution": format_solution_content(db_question_row.detailed_solution or ''),
                            "principle_to_remember": format_solution_content(db_question_row.principle_to_remember or '')
                        }
                        
                        db_feedback_quality = any(len(str(v)) > 50 for v in db_solution_feedback.values() if v)
                        if db_feedback_quality:
                            solution_feedback = db_solution_feedback
                            logger.info(f"✅ Enhanced solution feedback retrieved from questions table")
                        
                        # Also update correct answer if different
                        db_correct_answer = db_question_row.answer or ''
                        if db_correct_answer != correct_answer:
                            logger.warning(f"Answer mismatch found - session data: '{correct_answer}', questions table: '{db_correct_answer}'. Using questions table.")
                            correct_answer = db_correct_answer
                            correct_answer_clean = correct_answer.strip().lower()
                            is_correct = user_answer == correct_answer_clean  # Recalculate correctness
                    
            except Exception as fallback_error:
                logger.error(f"Failed to fetch solution feedback from questions table: {fallback_error}")
        
        logger.info(f"Final solution feedback status: {[k for k, v in solution_feedback.items() if v and len(str(v)) > 10]}")
        
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "position": request.position,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": question_at_position.get('explanation', ''),
            "solution_feedback": solution_feedback,
            "next_position": request.position + 1 if request.position < 12 else None,
            "is_complete": request.position == 12
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit answer for session {request.session_id[:8]}, position {request.position}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit answer: {str(e)}")

@router.post("/complete")
async def complete_session(
    request: SessionCompleteRequest,
    auth_user_id: str = Depends(get_current_user)
):
    """
    Mark blueprint session as complete and enqueue background adaptive intelligence jobs
    """
    
    try:
        # Validate UUID format at API boundary
        session_id = validate_canonical_uuid(request.session_id, "session_id")
        auth_user_id = validate_canonical_uuid(auth_user_id, "authenticated_user_id")
        
        planner = await get_blueprint_planner()
        
        # Get session answers to calculate final score
        db = planner.get_db_session()
        try:
            answers_result = db.execute(text("""
                SELECT position, is_correct, question_id, user_answer
                FROM session_answers
                WHERE session_id = :session_id
                ORDER BY position ASC
            """), {"session_id": request.session_id})  # Use string directly
            
            answers_data = answers_result.fetchall()
            
            if not answers_data:
                raise HTTPException(status_code=404, detail="No answers found for this session")
            
            # Calculate session statistics
            total_questions = len(answers_data)
            correct_answers = sum(1 for answer in answers_data if answer[1])  # is_correct is at index 1
            accuracy = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            
            # FINAL RECONCILIATION: Update session with complete stats and completion status
            completed_at = datetime.now(timezone.utc)
            db.execute(text("""
                UPDATE sessions 
                SET status = 'completed',
                    completed_at = :completed_at,
                    questions_answered = :questions_answered,
                    questions_correct = :questions_correct,
                    questions_skipped = :questions_skipped,
                    current_position = :current_position
                WHERE session_id = :session_id
            """), {
                "completed_at": completed_at,
                "questions_answered": total_questions,
                "questions_correct": correct_answers,
                "questions_skipped": 0,  # Blueprint sessions don't allow skipping
                "current_position": total_questions,  # Completed = at final position
                "session_id": request.session_id
            })
            
            logger.info(f"Final reconciliation: Session {request.session_id[:8]} completed with {correct_answers}/{total_questions} correct")
            
            db.commit()
            
        finally:
            db.close()
        
        logger.info(f"Blueprint session {request.session_id[:8]} completed with {correct_answers}/{total_questions} correct ({accuracy:.1f}%)")
        
        # BACKGROUND ADAPTIVE INTELLIGENCE: Two-job pipeline (SUMMARIZE → PLAN)
        bg_jobs_enqueued = False
        try:
            from services.bg_job_queue import job_queue
            
            # Single job: SUMMARIZE_SESSION (which will enqueue PLAN_NEXT_SESSION)
            summarization_job_id = await job_queue.enqueue_job(
                job_type="SUMMARIZE_SESSION",
                user_id=auth_user_id,
                session_id=request.session_id
            )
            
            bg_jobs_enqueued = True
            logger.info(f"🚀 Enqueued SUMMARIZE_SESSION job {summarization_job_id[:8]} for session {request.session_id[:8]}")
            
        except Exception as bg_error:
            # NO SYNCHRONOUS FALLBACK - trust the async pipeline
            logger.error(f"❌ Failed to enqueue background jobs for session {request.session_id[:8]}: {bg_error}")
            # Still return 200 - next session planning will use last-known signals
        
        # Generate session summary (enhanced with adaptive processing indicator)
        session_summary = {
            "session_id": request.session_id,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy": round(accuracy, 1),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "session_type": "blueprint",
            "adaptive_processing": "queued" if bg_jobs_enqueued else "enqueue_failed"
        }
        
        return JSONResponse({
            "success": True,
            "session_completed": True,
            "summary": session_summary
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete session {request.session_id[:8] if hasattr(request, 'session_id') else 'UNKNOWN'}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete session: {str(e)}")

@router.get("/list")
async def list_user_sessions(
    auth_user_id: str = Depends(get_current_user),
    limit: int = 10,
    status_filter: Optional[str] = None
):
    """
    List user's blueprint sessions with optional status filtering
    """
    
    try:
        planner = await get_blueprint_planner()
        
        db = planner.get_db_session()
        try:
            # Build query with optional status filter
            if status_filter:
                query = text("""
                    WITH completed_sessions AS (
                        SELECT session_id, created_at,
                               ROW_NUMBER() OVER (ORDER BY created_at) as display_session_number
                        FROM sessions 
                        WHERE user_id = :user_id AND status = 'completed'
                    )
                    SELECT s.session_id, s.status, s.created_at, s.served_at, s.abandoned_at, s.sess_seq,
                           sp.constraint_report,
                           (SELECT COUNT(*) FROM session_answers sa WHERE sa.session_id::text = s.session_id) as answered_count,
                           COALESCE(cs.display_session_number, 
                                   (SELECT COUNT(*) FROM sessions WHERE user_id = :user_id AND status = 'completed') + 1) as calculated_session_number
                    FROM sessions s
                    LEFT JOIN session_packs sp ON s.session_id = sp.session_id::text
                    LEFT JOIN completed_sessions cs ON s.session_id = cs.session_id
                    WHERE s.user_id = :user_id AND s.status = :status_filter
                    ORDER BY s.created_at DESC
                    LIMIT :limit
                """)
                sessions_result = db.execute(query, {
                    "user_id": auth_user_id,
                    "status_filter": status_filter,
                    "limit": limit
                })
            else:
                query = text("""
                    WITH completed_sessions AS (
                        SELECT session_id, created_at,
                               ROW_NUMBER() OVER (ORDER BY created_at) as display_session_number
                        FROM sessions 
                        WHERE user_id = :user_id AND status = 'completed'
                    )
                    SELECT s.session_id, s.status, s.created_at, s.served_at, s.abandoned_at, s.sess_seq,
                           sp.constraint_report,
                           (SELECT COUNT(*) FROM session_answers sa WHERE sa.session_id::text = s.session_id) as answered_count,
                           COALESCE(cs.display_session_number, 
                                   (SELECT COUNT(*) FROM sessions WHERE user_id = :user_id AND status = 'completed') + 1) as calculated_session_number
                    FROM sessions s
                    LEFT JOIN session_packs sp ON s.session_id = sp.session_id::text
                    LEFT JOIN completed_sessions cs ON s.session_id = cs.session_id
                    WHERE s.user_id = :user_id
                    ORDER BY s.created_at DESC
                    LIMIT :limit
                """)
                sessions_result = db.execute(query, {
                    "user_id": auth_user_id,
                    "limit": limit
                })
            
            sessions_data = sessions_result.fetchall()
            
            sessions_list = []
            for session in sessions_data:
                answered_count = session[7] or 0
                current_position = answered_count + 1 if answered_count < 12 else 12  # Calculate next question position
                
                sessions_list.append({
                    "session_id": str(session[0]),  # id is at index 0
                    "status": session[1],           # status is at index 1
                    "session_number": session[8] or 1,  # calculated_session_number is at index 8 (FIX: Use calculated number)
                    "answered_count": answered_count,  # answered_count is at index 7
                    "current_position": current_position,  # FIX: Add current position for resumption
                    "total_questions": 12,  # Blueprint sessions always have 12 questions
                    "created_at": session[2].isoformat() if session[2] else None,  # created_at is at index 2
                    "served_at": session[3].isoformat() if session[3] else None,   # served_at is at index 3
                    "completed_at": session[4].isoformat() if session[4] else None, # abandoned_at is at index 4
                    "progress_percentage": ((answered_count) / 12) * 100,  # Use answered_count directly
                    "session_type": "blueprint"
                })
        finally:
            db.close()
        
        return JSONResponse({
            "success": True,
            "sessions": sessions_list,
            "total_returned": len(sessions_list),
            "filter_applied": status_filter
        }, status_code=200)
        
    except Exception as e:
        logger.error(f"Failed to list sessions for user {auth_user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

# Health check for blueprint system
@router.get("/health")
async def blueprint_health():
    """
    Health check for blueprint session system
    """
    try:
        planner = await get_blueprint_planner()
        
        # Test database connection
        db = planner.get_db_session()
        try:
            result = db.execute(text("SELECT 1")).scalar()
            
            if result == 1:
                return JSONResponse({
                    "status": "healthy",
                    "blueprint_system": "operational",
                    "database_connection": "active",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, status_code=200)
            else:
                raise Exception("Database test query failed")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Blueprint health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "blueprint_system": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=503)