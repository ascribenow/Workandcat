# Session Progress Tracking API
# Handles session resumption and question progress persistence

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from database import SessionLocal
from sqlalchemy import text
import json
import logging

# Authentication
import jwt
import os
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, os.getenv("JWT_SECRET"), algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session-progress")

class SessionProgressUpdate(BaseModel):
    session_id: str
    current_question_index: int
    total_questions: int
    last_question_id: str

@router.post("/update")
async def update_session_progress(
    progress: SessionProgressUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update session progress for resumption capability"""
    try:
        db = SessionLocal()
        try:
            # Upsert session progress
            db.execute(text("""
                INSERT INTO session_progress_tracking (
                    user_id, session_id, current_question_index, 
                    total_questions, last_question_id, updated_at
                ) VALUES (
                    :user_id, :session_id, :current_question_index,
                    :total_questions, :last_question_id, :updated_at
                )
                ON CONFLICT (user_id, session_id) 
                DO UPDATE SET
                    current_question_index = EXCLUDED.current_question_index,
                    last_question_id = EXCLUDED.last_question_id,
                    updated_at = EXCLUDED.updated_at
            """), {
                'user_id': user_id,
                'session_id': progress.session_id,
                'current_question_index': progress.current_question_index,
                'total_questions': progress.total_questions,
                'last_question_id': progress.last_question_id,
                'updated_at': datetime.utcnow()
            })
            
            db.commit()
            logger.info(f"✅ Session progress updated: {progress.session_id[:8]} Q{progress.current_question_index + 1}/{progress.total_questions}")
            
            return {
                "success": True,
                "message": "Session progress updated"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error updating session progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to update session progress")

@router.get("/{session_id}")
async def get_session_progress(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get session progress for resumption"""
    try:
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT current_question_index, total_questions, last_question_id, updated_at
                FROM session_progress_tracking
                WHERE user_id = :user_id AND session_id = :session_id
            """), {
                'user_id': user_id,
                'session_id': session_id
            })
            
            progress = result.fetchone()
            
            if progress:
                return {
                    "success": True,
                    "has_progress": True,
                    "current_question_index": progress.current_question_index,
                    "total_questions": progress.total_questions,
                    "last_question_id": progress.last_question_id,
                    "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
                }
            else:
                return {
                    "success": True,
                    "has_progress": False,
                    "message": "No progress found for this session"
                }
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting session progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session progress")

@router.get("/current/{user_id}")  
async def get_current_session_for_user(
    user_id_param: str,
    user_id: str = Depends(get_current_user)
):
    """Get current incomplete session for resumption"""
    try:
        # Security check
        if user_id_param != user_id:
            raise HTTPException(status_code=403, detail="Cannot access other users' sessions")
            
        db = SessionLocal()
        try:
            # Find the most recent incomplete session
            result = db.execute(text("""
                SELECT spt.session_id, spt.current_question_index, spt.total_questions, 
                       spt.last_question_id, spt.updated_at, s.status
                FROM session_progress_tracking spt
                JOIN sessions s ON s.session_id = spt.session_id AND s.user_id = spt.user_id
                WHERE spt.user_id = :user_id 
                  AND s.status IN ('planned', 'served')
                  AND spt.current_question_index < spt.total_questions
                ORDER BY spt.updated_at DESC
                LIMIT 1
            """), {'user_id': user_id})
            
            current_session = result.fetchone()
            
            if current_session:
                return {
                    "success": True,
                    "has_current_session": True,
                    "session_id": current_session.session_id,
                    "current_question_index": current_session.current_question_index,
                    "total_questions": current_session.total_questions,
                    "last_question_id": current_session.last_question_id,
                    "session_status": current_session.status,
                    "updated_at": current_session.updated_at.isoformat() if current_session.updated_at else None
                }
            else:
                return {
                    "success": True,
                    "has_current_session": False,
                    "message": "No incomplete session found"
                }
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error getting current session: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current session")

@router.delete("/{session_id}")
async def clear_session_progress(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """Clear session progress after completion"""
    try:
        db = SessionLocal()
        try:
            db.execute(text("""
                DELETE FROM session_progress_tracking
                WHERE user_id = :user_id AND session_id = :session_id
            """), {
                'user_id': user_id,
                'session_id': session_id
            })
            
            db.commit()
            logger.info(f"✅ Session progress cleared: {session_id[:8]}")
            
            return {
                "success": True,
                "message": "Session progress cleared"
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error clearing session progress: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear session progress")