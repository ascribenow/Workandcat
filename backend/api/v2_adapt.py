"""
Coverage-Based Adaptive API - COVERAGE V1 IMPLEMENTATION

Coverage-only endpoints with no legacy paths. Uses Coverage Pipeline.
Frontend unchanged. Backend completely Coverage V1 internally.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any

from services.coverage_pipeline import coverage_pipeline
from auth import get_current_user
from database import SessionLocal
from sqlalchemy import text
from utils.json_safe import as_json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adapt", tags=["coverage_adaptive_sessions"])

@router.post("/plan-next")
async def v2_plan_next_controller(body: dict, request: Request, user_id: str = Depends(get_current_user)):
    """
    Coverage Plan-Next Endpoint - COVERAGE V1 IMPLEMENTATION
    
    External contract unchanged (session_id strings for frontend compatibility).
    Internal: Pure Coverage pipeline with deterministic selection.
    
    Target: p95 ≤ 6s (was 98.7s)
    """
    # Diagnostic timing setup
    rid = request.headers.get("X-Request-Id") or request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    t0 = time.perf_counter()
    start_ts = datetime.utcnow().isoformat() + 'Z'
    
    logger.info(f"🚀 COVERAGE PLAN-NEXT: request_id={rid}")
    
    try:
        # Extract and validate parameters
        req_user_id = body.get("user_id")
        last_session_id = body.get("last_session_id") 
        next_session_id = body.get("next_session_id")
        
        if not all([req_user_id, next_session_id]):
            raise HTTPException(status_code=400, detail="user_id and next_session_id are required")
        
        if req_user_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot plan sessions for other users")
        
        # Idempotency validation
        idem_key = request.headers.get("Idempotency-Key")
        if not idem_key:
            raise HTTPException(status_code=400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED"})
        
        # Coverage Pipeline execution
        pipeline_result = await coverage_pipeline.plan_next_session(
            user_id=req_user_id,
            session_id=next_session_id
        )
        
        # Coverage pipeline returns pack directly, check for errors in audit
        if not pipeline_result.get("pack") or pipeline_result.get("audit", {}).get("error"):
            error_msg = pipeline_result.get("audit", {}).get("error", "Unknown pipeline error")
            logger.error(f"COVERAGE PLAN-NEXT: Pipeline failed - {error_msg}")
            raise HTTPException(status_code=502, detail={"code": "COVERAGE_PIPELINE_FAILED", "msg": error_msg})
        
        pack = pipeline_result.get("pack", []) or []
        audit = pipeline_result.get("audit", {}) or {}

        # Safe defaults so the report mapper never sees missing keys
        audit_defaults = {
            "shape": {"easy": 0, "medium": 0, "hard": 0},
            "pyq": {"1_5": 0, "1_0": 0},
            "borrow": {"easy": 0, "medium": 0, "hard": 0},
        }
        merged_audit = {**audit_defaults, **audit}
        merged_audit["shape"]  = {**audit_defaults["shape"],  **merged_audit.get("shape", {})}
        merged_audit["pyq"]    = {**audit_defaults["pyq"],    **merged_audit.get("pyq", {})}
        merged_audit["borrow"] = {**audit_defaults["borrow"], **merged_audit.get("borrow", {})}

        # If you already had a minimal constraint_report, merge it here
        base_constraint_report = {}  # replace with your existing dict if present

        constraint_report = {
            **base_constraint_report,
            **merged_audit,  # full audit goes where frontend expects it
            "pyq_distribution": {  # compatibility alias
                "ge_1_5": merged_audit["pyq"].get("1_5", 0),
                "ge_1_0": merged_audit["pyq"].get("1_0", 0),
            },
            "pack_size": len(pack),
            "selection_method": "coverage_v1",
        }

        # Prepare response (frontend compatible)
        response = {
            "user_id": req_user_id,
            "session_id": next_session_id,
            "status": "planned",
            "constraint_report": constraint_report
        }
        
        # Log success with timing
        duration_ms = int((time.perf_counter() - t0) * 1000)
        end_ts = datetime.utcnow().isoformat() + 'Z'
        
        logger.info(f"✅ COVERAGE PLAN-NEXT: SUCCESS in {duration_ms}ms, request_id={rid}")
        
        # Detailed trace logging for diagnostics
        trace_data = {
            "request_id": rid,
            "route": "POST /api/adapt/plan-next (Coverage)",
            "start_ts": start_ts,
            "end_ts": end_ts,
            "dur_ms": duration_ms,
            "http_status": 200,
            "resp_bytes": len(json.dumps(response)),
            "coverage_telemetry": pipeline_result.get("pipeline_telemetry", {}),
            "performance_target_met": duration_ms < 10000  # <10s target
        }
        
        logger.info(f"🔍 COVERAGE TRACE: {json.dumps(trace_data)}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.error(f"❌ COVERAGE PLAN-NEXT: ERROR after {duration_ms}ms, request_id={rid}, error={str(e)}")
        raise HTTPException(status_code=502, detail={"code": "COVERAGE_EXECUTION_FAILED", "msg": str(e)})

@router.get("/pack")
async def v2_get_pack_controller(user_id: str, session_id: str, auth_user_id: str = Depends(get_current_user)):
    """
    Coverage Pack Fetch - Returns assembled pack from pack_json
    
    Frontend unchanged. Backend reads from Coverage pack_json column.
    """
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Cannot access other users' packs")
    
    logger.info(f"COVERAGE PACK: Fetching pack for user {user_id[:8]}, session {session_id[:8]}")
    
    # Fetch from Coverage pack_json column
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT pack_json, status, selection_method, processing_time_ms
            FROM session_pack_plan
            WHERE user_id = :user_id AND session_id = :session_id
            LIMIT 1
        """), {"user_id": user_id, "session_id": session_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Pack not found")
        
        pack_json = result[0]
        pack_status = result[1]
        selection_method = result[2]
        processing_time = result[3]
        
        if pack_status != "planned":
            raise HTTPException(status_code=409, detail=f"Pack not in planned state: {pack_status}")
        
        # Parse pack_json and return in frontend format
        if isinstance(pack_json, str):
            pack_data = json.loads(pack_json)
        else:
            pack_data = pack_json
        
        logger.info(f"COVERAGE PACK: Retrieved pack for session {session_id[:8]}, "
                   f"method={selection_method}, processing={processing_time}ms")
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "status": pack_status,
            "pack": pack_data if isinstance(pack_data, list) else pack_data.get("items", []),
            "meta": {
                "selection_method": selection_method,
                "processing_time_ms": processing_time,
                "version": "coverage_v1"
            }
        }
        
    finally:
        db.close()

@router.post("/mark-served") 
async def v2_mark_served_controller(body: dict, auth_user_id: str = Depends(get_current_user)):
    """
    FIXED: Optimized mark-served using session_id-only WHERE with atomic coverage_ledger updates
    """
    user_id = body.get("user_id")
    session_id = body.get("session_id")
    
    if not all([user_id, session_id]):
        raise HTTPException(status_code=400, detail="user_id and session_id required")
    
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Cannot mark other users' sessions")
    
    logger.info(f"COVERAGE MARK-SERVED: Transitioning session {session_id[:8]} to served")
    
    db = SessionLocal()
    try:
        # FIXED: Atomic transaction wrapper for race safety
        db.begin()
        
        # FIXED: Idempotent race guard - update status first, check affected rows
        update_result = db.execute(text("""
            UPDATE session_pack_plan
            SET status='served', served_at=NOW()
            WHERE session_id=:session_id AND status!='served'
        """), {"session_id": session_id})
        
        # Check if update affected any rows (prevents double-counting)
        if update_result.rowcount == 0:
            # Already served - no-op
            db.rollback()
            logger.info(f"COVERAGE MARK-SERVED: Session {session_id[:8]} already served")
            return {"ok": True, "already_served": True}
        
        # First serve confirmed - get pack using session_id only for performance
        pack_data = db.execute(text("""
            SELECT pack_json, user_id FROM session_pack_plan
            WHERE session_id = :session_id
        """), {"session_id": session_id}).fetchone()
        
        if not pack_data:
            db.rollback()
            raise HTTPException(status_code=404, detail="Pack data not found")
        
        pack_json = pack_data[0]
        actual_user_id = pack_data[1]
        
        # Parse pack with safe JSON handling (prevents 502 from double parsing)
        pack = as_json(pack_json)
        
        if not isinstance(pack, list):
            pack = pack.get("items", []) if isinstance(pack, dict) else []
        
        # ATOMIC: Update coverage_ledger for each question in pack
        for question in pack:
            subcategory = question.get('subcategory', 'Unknown')
            type_of_question = question.get('type_of_question', 'Unknown')
            subcategory_type = f"{subcategory}|{type_of_question}"
            
            db.execute(text("""
                INSERT INTO coverage_ledger (user_id, subcategory_type, served_count, last_served_at)
                VALUES (:user_id, :subcategory_type, 1, NOW())
                ON CONFLICT (user_id, subcategory_type) DO UPDATE SET
                    served_count = coverage_ledger.served_count + 1,
                    last_served_at = NOW()
            """), {
                "user_id": actual_user_id,
                "subcategory_type": subcategory_type
            })
        
        db.commit()
        
        logger.info(f"COVERAGE MARK-SERVED: Successfully marked session {session_id[:8]} as served, updated {len(pack)} coverage entries")
        return {"ok": True, "served_questions": len(pack), "first_serve": True}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ COVERAGE MARK-SERVED: Failed for session {session_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark session as served: {str(e)}")
    finally:
        db.close()

@router.post("/start-first")
async def v2_start_first_controller(request: dict, auth_user_id: str = Depends(get_current_user)):
    """
    Coverage Start-First - Cold start convenience endpoint
    
    Combines plan-next and pack fetching for immediate session start.
    Perfect for adaptive-only system where users always get adaptive sessions.
    """
    user_id = request.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Cannot create session for other users")
    
    logger.info(f"COVERAGE START-FIRST: Cold start for user {user_id[:8]}")
    
    try:
        # Generate session ID for cold start
        session_id = str(uuid.uuid4())
        last_session_id = "S0"  # Cold start
        
        # Step 1: Plan the session
        plan_result = await coverage_pipeline.plan_next_session(
            user_id=user_id,
            session_id=session_id
        )
        
        if not plan_result.get("pack"):
            raise HTTPException(status_code=502, detail="Session planning failed")
        
        # Step 2: Fetch the pack (already saved by coverage pipeline)
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT pack_json, status, created_at 
                FROM session_pack_plan 
                WHERE user_id = :user_id AND session_id = :session_id
                LIMIT 1
            """), {"user_id": user_id, "session_id": session_id})
            
            pack_row = result.fetchone()
            if not pack_row or not pack_row.pack_json:
                raise HTTPException(status_code=404, detail="Pack not found after planning")
            
            pack_data = pack_row.pack_json
            
            # Mark as served immediately
            db.execute(text("""
                UPDATE session_pack_plan 
                SET status = 'served', served_at = NOW()
                WHERE user_id = :user_id AND session_id = :session_id
            """), {"user_id": user_id, "session_id": session_id})
            
            db.commit()
            
            logger.info(f"COVERAGE START-FIRST: Successfully created and served session {session_id[:8]}")
            
            return {
                "success": True,
                "session_id": session_id,
                "pack": pack_data,
                "status": "served",
                "version": "coverage_v1",
                "message": "Adaptive session ready to start"
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ COVERAGE START-FIRST: Error for user {user_id[:8]}: {str(e)}")
        raise HTTPException(status_code=502, detail=f"Start-first failed: {str(e)}")

# Import for registration
from database import SessionLocal
from sqlalchemy import text