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
from sqlalchemy import text

from auth import get_current_user
from services.blueprint_planner import BlueprintSessionPlanner, create_blueprint_planner
from database import get_async_compatible_db, get_database
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
    Start a new blueprint session - immediate availability, no polling needed
    
    This replaces the old plan-next + pack polling pattern with immediate session creation
    """
    
    if request.user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Cannot start session for other users")
    
    logger.info(f"Starting blueprint session for user {request.user_id[:8]}")
    
    try:
        planner = await get_blueprint_planner()
        
        # Plan session with advisory lock protection
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
            formatted_questions.append({
                "id": q.get("id", ""),
                "stem": q.get("stem", ""),
                "option_a": q.get("option_a", ""),
                "option_b": q.get("option_b", ""),
                "option_c": q.get("option_c", ""),
                "option_d": q.get("option_d", ""),
                "difficulty_band": q.get("difficulty_band", ""),
                "subcategory": q.get("subcategory", ""),
                "type_of_question": q.get("type_of_question", ""),
                "position": q.get("position", 1),
                "answer": q.get("answer", "")
            })
        
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
        
        # Find question at specified position
        question_at_position = None
        for q in questions:
            if q.get('position') == request.position:
                question_at_position = q
                break
        
        if not question_at_position:
            raise HTTPException(status_code=404, detail=f"Question at position {request.position} not found")
        
        # DEBUG: Log question data for troubleshooting
        logger.info(f"Question at position {request.position}: ID={question_at_position.get('id', 'NO_ID')[:8]}")
        logger.info(f"Question stem preview: {question_at_position.get('stem', 'NO_STEM')[:100]}...")
        logger.info(f"Solution feedback availability: snap_read={bool(question_at_position.get('snap_read'))}, approach={bool(question_at_position.get('solution_approach'))}")
        
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
                ON CONFLICT (id) DO NOTHING
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
            
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Answer submitted for session {request.session_id[:8]}, position {request.position}: {'correct' if is_correct else 'incorrect'}")
        
        # Build solution feedback object from question data
        solution_feedback = {
            "snap_read": question_at_position.get('snap_read', ''),
            "solution_approach": question_at_position.get('solution_approach', ''),
            "detailed_solution": question_at_position.get('detailed_solution', ''),
            "principle_to_remember": question_at_position.get('principle_to_remember', '')
        }
        
        # VALIDATION: If solution feedback is missing, fetch from questions table directly
        if not any(solution_feedback.values()):
            logger.warning(f"Solution feedback missing for position {request.position}, fetching from questions table")
            
            try:
                question_id = question_at_position.get('id')
                if question_id:
                    db_question_result = db.execute(text("""
                        SELECT snap_read, solution_approach, detailed_solution, principle_to_remember, answer
                        FROM questions
                        WHERE id = :question_id
                    """), {"question_id": question_id})
                    
                    db_question_row = db_question_result.fetchone()
                    if db_question_row:
                        solution_feedback = {
                            "snap_read": db_question_row.snap_read or '',
                            "solution_approach": db_question_row.solution_approach or '',
                            "detailed_solution": db_question_row.detailed_solution or '',
                            "principle_to_remember": db_question_row.principle_to_remember or ''
                        }
                        
                        # Also update correct answer if different
                        db_correct_answer = db_question_row.answer or ''
                        if db_correct_answer != correct_answer:
                            logger.warning(f"Answer mismatch found - session data: '{correct_answer}', questions table: '{db_correct_answer}'. Using questions table.")
                            correct_answer = db_correct_answer
                            correct_answer_clean = correct_answer.strip().lower()
                            is_correct = user_answer == correct_answer_clean  # Recalculate correctness
                        
                        logger.info(f"Solution feedback retrieved from questions table for question {question_id[:8]}")
                    
            except Exception as fallback_error:
                logger.error(f"Failed to fetch solution feedback from questions table: {fallback_error}")
        
        logger.info(f"Final solution feedback status: {[k for k, v in solution_feedback.items() if v]}")
        
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
    Mark blueprint session as complete and generate summary
    """
    
    try:
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
            
            # Update session status to completed
            db.execute(text("""
                UPDATE sessions SET status = 'completed', abandoned_at = :completed_at 
                WHERE session_id = :session_id
            """), {
                "completed_at": datetime.now(timezone.utc),
                "session_id": request.session_id  # Use string directly
            })
            
            db.commit()
            
        finally:
            db.close()
        
        logger.info(f"Blueprint session {request.session_id[:8]} completed with {correct_answers}/{total_questions} correct ({accuracy:.1f}%)")
        
        # Generate session summary
        session_summary = {
            "session_id": request.session_id,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy": round(accuracy, 1),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "session_type": "blueprint"
        }
        
        return JSONResponse({
            "success": True,
            "session_completed": True,
            "summary": session_summary
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete session {request.session_id[:8]}: {e}")
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