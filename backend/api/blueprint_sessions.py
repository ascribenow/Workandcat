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
        
        # Get session questions
        questions = await planner._get_session_questions(uuid.UUID(session_id))
        
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
            raise HTTPException(status_code=404, detail=f"Question at position {position} not found")
        
        return JSONResponse({
            "session_id": session_id,
            "position": position,
            "question": {
                "id": question_at_position["id"],
                "stem": question_at_position["stem"],
                "option_a": question_at_position["option_a"],
                "option_b": question_at_position["option_b"],
                "option_c": question_at_position["option_c"],
                "option_d": question_at_position["option_d"],
                "difficulty_band": question_at_position["difficulty_band"],
                "subcategory": question_at_position["subcategory"],
                "type_of_question": question_at_position["type_of_question"]
                # Note: Answer and explanation are not included in question retrieval for security
            },
            "is_last": position == 12,
            "next_position": position + 1 if position < 12 else None
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get question {position} for session {session_id[:8]}: {e}")
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
        
        # Get session questions to validate answer
        questions = await planner._get_session_questions(uuid.UUID(request.session_id))
        
        if not questions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Find question at specified position
        question_at_position = None
        for q in questions:
            if q.get('position') == request.position:
                question_at_position = q
                break
        
        if not question_at_position:
            raise HTTPException(status_code=404, detail=f"Question at position {request.position} not found")
        
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
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Answer submitted for session {request.session_id[:8]}, position {request.position}: {'correct' if is_correct else 'incorrect'}")
        
        return JSONResponse({
            "success": True,
            "session_id": request.session_id,
            "position": request.position,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": question_at_position.get('explanation', ''),
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
            """), {"session_id": uuid.UUID(request.session_id)})
            
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
                    SELECT s.session_id, s.status, s.created_at, s.served_at, s.abandoned_at,
                           sp.constraint_report,
                           (SELECT COUNT(*) FROM session_answers sa WHERE sa.session_id = s.session_id) as answered_count
                    FROM sessions s
                    LEFT JOIN session_packs sp ON s.session_id = sp.session_id
                    WHERE s.user_id = :user_id AND s.status = :status_filter
                    ORDER BY s.created_at DESC
                    LIMIT :limit
                """)
                sessions_result = db.execute(query, {
                    "user_id": auth_user_id,  # Use string directly
                    "status_filter": status_filter,
                    "limit": limit
                })
            else:
                query = text("""
                    SELECT s.session_id, s.status, s.created_at, s.served_at, s.abandoned_at,
                           sp.constraint_report,
                           (SELECT COUNT(*) FROM session_answers sa WHERE sa.session_id = s.session_id) as answered_count
                    FROM sessions s
                    LEFT JOIN session_packs sp ON s.session_id = sp.session_id
                    WHERE s.user_id = :user_id
                    ORDER BY s.created_at DESC
                    LIMIT :limit
                """)
                sessions_result = db.execute(query, {
                    "user_id": auth_user_id,  # Use string directly
                    "limit": limit
                })
            
            sessions_data = sessions_result.fetchall()
            
            sessions_list = []
            for session in sessions_data:
                sessions_list.append({
                    "session_id": str(session[0]),  # id is at index 0
                    "status": session[1],           # status is at index 1
                    "answered_count": session[6] or 0,  # answered_count is at index 6
                    "total_questions": 12,  # Blueprint sessions always have 12 questions
                    "created_at": session[2].isoformat() if session[2] else None,  # created_at is at index 2
                    "served_at": session[3].isoformat() if session[3] else None,   # served_at is at index 3
                    "completed_at": session[4].isoformat() if session[4] else None, # abandoned_at is at index 4
                    "progress_percentage": ((session[6] or 0) / 12) * 100,
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