#!/usr/bin/env python3
"""
Adaptive Session API Endpoints
Phase 4 implementation of session orchestration endpoints
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Dict, Any
import logging
from datetime import datetime

from services.session_orchestrator import plan_next, load_pack, transition_pack_to_served, ConflictError
from auth import get_current_user
from util.constraint_validator import assert_no_forbidden_relaxations, validate_pack_constraints
from services.summarizer import run_summarizer
from services.telemetry import telemetry_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adapt", tags=["adaptive_sessions"])

@router.post("/plan-next")
async def plan_next_controller(body: dict, request: Request, user_id: str = Depends(get_current_user)):
    """
    Plan the next session after current session completion - WITH DIAGNOSTIC TRACING
    
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
    import asyncio
    import time
    import json
    import uuid
    from datetime import datetime
    
    # DIAGNOSTIC TRACING SETUP
    rid = request.headers.get("X-Request-Id") or request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    t0 = time.perf_counter()
    start_ts = datetime.utcnow().isoformat() + 'Z'
    tm = {"db_candidates": 0, "llm_planner": 0, "validator": 0, "db_write": 0, "other": 0}
    
    def td_ms():
        """Get milliseconds since start"""
        return int((time.perf_counter() - t0) * 1000)
    
    def t_section(key: str):
        """Time section wrapper"""
        return time.perf_counter()
    
    logger.info(f"🔍 TRACE START: request_id={rid}, route=POST /api/adapt/plan-next")
    
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
        
        # Get idempotency key from headers (REQUIRED)
        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
        
        # Optional strict format: user:last:next
        parts = idem_key.split(":")
        if len(parts) != 3:
            raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_BAD_FORMAT"})
        
        # TIMING SECTION 1: SESSION ORCHESTRATION (includes DB candidates + LLM + DB write)
        t_orchestration = t_section("orchestration")
        
        async def run_planning_with_timing():
            # This will internally call candidate selection, LLM planner, and DB write
            return plan_next(req_user_id, last_session_id, next_session_id, idem_key=idem_key, request_id=rid)
        
        try:
            # 60-second timeout for LLM operations  
            plan = await asyncio.wait_for(run_planning_with_timing(), timeout=60.0)
        except asyncio.TimeoutError:
            logger.warning(f"⏰ TRACE TIMEOUT: request_id={rid}, dur_ms={td_ms()}")
            raise HTTPException(status_code=502, detail={"code": "PLANNING_TIMEOUT", "msg": "Session planning timed out, please try again"})
        
        # TIMING SECTION 2: VALIDATION  
        t_validation = t_section("validation")
        constraint_report = plan.get("constraint_report_json", {})
        assert_no_forbidden_relaxations(constraint_report)
        tm["validator"] = int((time.perf_counter() - t_validation) * 1000)
        
        # TIMING SECTION 3: PACK LOADING (additional DB read)
        t_pack_load = t_section("pack_load") 
        pack_data = load_pack(req_user_id, next_session_id)
        if pack_data and pack_data.get("pack_json"):
            pack = pack_data["pack_json"]
            validate_pack_constraints(pack, constraint_report)
        pack_load_ms = int((time.perf_counter() - t_pack_load) * 1000)
        
        # PREPARE RESPONSE
        result = {
            "user_id": req_user_id, 
            "session_id": next_session_id,
            "status": plan.get("status", "planned"),
            "constraint_report": constraint_report
        }
        
        # FINAL TRACE LOGGING
        end_ts = datetime.utcnow().isoformat() + 'Z'
        dur_ms = td_ms()
        resp_bytes = len(json.dumps(result))
        
        # Extract detailed timings from plan if available
        plan_meta = plan.get("timing_meta", {})
        tm["db_candidates"] = plan_meta.get("db_candidates", 0)
        tm["llm_planner"] = plan_meta.get("llm_planner", 0) 
        tm["db_write"] = plan_meta.get("db_write", 0)
        tm["other"] = dur_ms - sum(tm.values()) - pack_load_ms
        
        trace_data = {
            "request_id": rid,
            "route": "POST /api/adapt/plan-next",
            "start_ts": start_ts,
            "end_ts": end_ts, 
            "dur_ms": dur_ms,
            "timings_ms": tm,
            "retries": plan_meta.get("retries", {"llm": 0, "db": 0}),
            "http_status": 200,
            "resp_bytes": resp_bytes,
            "pack_load_ms": pack_load_ms
        }
        
        logger.info(f"🔍 TRACE COMPLETE: {json.dumps(trace_data)}")
        
        return result
        
    except ConflictError as e:
        logger.error(f"🔍 TRACE ERROR: request_id={rid}, dur_ms={td_ms()}, error=CONFLICT: {str(e)}")
        raise HTTPException(status_code=409, detail={"code": "PLANNING_IN_PROGRESS", "msg": str(e)})
    except Exception as e:
        logger.error(f"🔍 TRACE ERROR: request_id={rid}, dur_ms={td_ms()}, error={str(e)}")
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
        
        # NEW: Always run summarizer post-session for LLM data capture
        try:
            logger.info(f"📊 Running post-session summarizer for user {req_user_id[:8]}, session {session_id}")
            summary_result = await run_summarizer(req_user_id, session_id)
            logger.info(f"✅ Post-session summarizer completed for session {session_id}")
        except Exception as e:
            # Map to telemetry only; do not fail the flow
            logger.warning(f"⚠️ Post-session summarizer failed for session {session_id}: {e}")
            if hasattr(telemetry_service, 'emit'):
                telemetry_service.emit("summarizer_error", {
                    "user_id": req_user_id, 
                    "session_id": session_id, 
                    "error": str(e)
                })
        
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

@router.get("/admin/dashboard")
async def admin_dashboard(user_id: str = Depends(get_current_user)):
    """
    Admin dashboard for monitoring adaptive session orchestration
    
    Response:
        Basic metrics and statistics for monitoring
    """
    try:
        # TODO: Add admin permission check
        
        from database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # Get basic statistics
            stats = {}
            
            # Session pack statistics
            pack_stats = db.execute(text("""
                SELECT status, COUNT(*) as count,
                       AVG(processing_time_ms) as avg_processing_time
                FROM session_pack_plan 
                GROUP BY status
            """)).fetchall()
            
            stats["pack_status"] = {row.status: {"count": row.count, "avg_processing_time": row.avg_processing_time} for row in pack_stats}
            
            # Planning strategy distribution
            strategy_stats = db.execute(text("""
                SELECT planning_strategy, COUNT(*) as count
                FROM session_pack_plan
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY planning_strategy
            """)).fetchall()
            
            stats["strategy_distribution"] = {row.planning_strategy: row.count for row in strategy_stats}
            
            # Cold start vs adaptive
            mode_stats = db.execute(text("""
                SELECT cold_start_mode, COUNT(*) as count
                FROM session_pack_plan
                WHERE created_at >= NOW() - INTERVAL '24 hours' 
                GROUP BY cold_start_mode
            """)).fetchall()
            
            stats["mode_distribution"] = {("cold_start" if row.cold_start_mode else "adaptive"): row.count for row in mode_stats}
            
            # Recent activity
            recent_activity = db.execute(text("""
                SELECT user_id, session_id, status, created_at, planning_strategy
                FROM session_pack_plan
                ORDER BY created_at DESC
                LIMIT 10
            """)).fetchall()
            
            stats["recent_activity"] = [
                {
                    "user_id": row.user_id[:8] + "...",
                    "session_id": row.session_id[:8] + "...",
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "strategy": row.planning_strategy
                }
                for row in recent_activity
            ]
            
            return {
                "dashboard_title": "Adaptive Session Orchestration Dashboard",
                "generated_at": datetime.utcnow().isoformat(),
                "statistics": stats
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Admin dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")