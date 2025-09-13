#!/usr/bin/env python3
"""
Adaptive Session API Endpoints
Phase 4 implementation of session orchestration endpoints
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Dict, Any
import logging

from services.session_orchestrator import plan_next, load_pack, transition_pack_to_served, ConflictError
from server import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adapt", tags=["adaptive_sessions"])

@router.post("/plan-next")
async def plan_next_controller(body: dict, request: Request, user_id: str = Depends(get_current_user)):
    """
    Plan the next session after current session completion
    
    Request body:
        user_id: User identifier
        last_session_id: Previous session ID  
        next_session_id: Next session ID to plan
        
    Response:
        user_id: User identifier
        session_id: Next session ID
        status: 'planned'
        constraint_report: Validation and relaxation details
    """
    try:
        # Extract request parameters
        req_user_id = body.get("user_id")
        last_session_id = body.get("last_session_id") 
        next_session_id = body.get("next_session_id")
        
        # Validate required parameters
        if not all([req_user_id, next_session_id]):
            raise HTTPException(status_code=400, detail="user_id and next_session_id are required")
        
        # Security check: ensure user can only plan their own sessions
        if req_user_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot plan sessions for other users")
        
        # Get idempotency key from headers
        idem_key = request.headers.get("Idempotency-Key")
        
        # Plan the session
        plan = plan_next(req_user_id, last_session_id, next_session_id, idem_key=idem_key)
        
        return {
            "user_id": req_user_id, 
            "session_id": next_session_id,
            "status": plan.get("status", "planned"),
            "constraint_report": plan.get("constraint_report_json", {})
        }
        
    except ConflictError as e:
        raise HTTPException(status_code=409, detail={"code": "PLANNING_IN_PROGRESS", "msg": str(e)})
    except Exception as e:
        logger.error(f"❌ Plan next session error: {e}")
        raise HTTPException(status_code=502, detail={"code": "PLANNER_FAILED", "msg": str(e)})

@router.get("/pack")
async def get_pack_controller(user_id: str, session_id: str, auth_user_id: str = Depends(get_current_user)):
    """
    Get the ordered 12-question pack for a planned session
    
    Query parameters:
        user_id: User identifier
        session_id: Session identifier
        
    Response:
        user_id: User identifier
        session_id: Session identifier
        status: Pack status
        pack: Array of 12 question objects with metadata
    """
    try:
        # Security check: ensure user can only access their own packs
        if user_id != auth_user_id:
            raise HTTPException(status_code=403, detail="Cannot access other users' packs")
        
        # Load the pack
        pack = load_pack(user_id, session_id)
        if not pack:
            raise HTTPException(status_code=404, detail="Session pack not found")
        
        return {
            "user_id": user_id, 
            "session_id": session_id, 
            "status": pack["status"], 
            "pack": pack["pack_json"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get pack error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session pack")

@router.post("/mark-served")
async def mark_served_controller(body: dict, user_id: str = Depends(get_current_user)):
    """
    Mark a planned pack as served (transition planned -> served)
    
    Request body:
        user_id: User identifier
        session_id: Session identifier
        
    Response:
        ok: True if successful
    """
    try:
        # Extract request parameters
        req_user_id = body.get("user_id")
        session_id = body.get("session_id")
        
        # Validate required parameters
        if not all([req_user_id, session_id]):
            raise HTTPException(status_code=400, detail="user_id and session_id are required")
        
        # Security check: ensure user can only mark their own sessions
        if req_user_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot mark other users' sessions")
        
        # Transition pack to served
        updated = transition_pack_to_served(req_user_id, session_id)
        if not updated:
            raise HTTPException(status_code=409, detail="Invalid state transition")
        
        return {"ok": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Mark served error: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark pack as served")

@router.post("/start-first")
async def start_first_controller(body: dict, user_id: str = Depends(get_current_user)):
    """
    Optional convenience endpoint for cold-start users
    Equivalent to POST /adapt/plan-next with cold_start_mode
    
    Request body:
        user_id: User identifier  
        next_session_id: Next session ID to plan
        
    Response:
        Same as GET /adapt/pack
    """
    try:
        # Extract request parameters
        req_user_id = body.get("user_id")
        next_session_id = body.get("next_session_id")
        
        # Security check
        if req_user_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot start sessions for other users")
        
        # Plan the cold-start session
        plan_body = {
            "user_id": req_user_id,
            "last_session_id": "S0",  # Cold start indicator
            "next_session_id": next_session_id
        }
        
        # Create fake request for plan_next_controller
        class FakeRequest:
            def __init__(self):
                self.headers = {}
        
        fake_request = FakeRequest()
        
        # Call plan_next_controller internally
        plan_result = await plan_next_controller(plan_body, fake_request, user_id)
        
        # Return pack immediately for convenience
        return await get_pack_controller(req_user_id, next_session_id, user_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Start first session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start first session")