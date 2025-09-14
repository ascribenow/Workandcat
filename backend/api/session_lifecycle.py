"""
Session Lifecycle API Endpoints
Handles session start and completion events for timestamp management
"""

from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from services.session_completion import mark_session_started, mark_session_completed

router = APIRouter(tags=["sessions"])

@router.post("/mark-started")
async def api_mark_started(payload: dict, user_id: str = Depends(get_current_user)):
    """
    Mark session as started - sets served_at timestamp
    
    Body may include session_id for FE convenience, but trusts user_id from auth
    """
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail={"code": "SESSION_ID_REQUIRED"})
    
    mark_session_started(user_id, session_id)
    return {"ok": True}

@router.post("/mark-completed") 
async def api_mark_completed(payload: dict, user_id: str = Depends(get_current_user)):
    """
    Mark session as completed - sets completed_at timestamp and triggers summarizer
    
    Body may include session_id for FE convenience, but trusts user_id from auth
    """
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail={"code": "SESSION_ID_REQUIRED"})
    
    # Run completion handler with summarizer (non-blocking)
    mark_session_completed(user_id, session_id)
    return {"ok": True}