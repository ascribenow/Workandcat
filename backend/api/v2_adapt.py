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
import asyncio
from datetime import datetime
from typing import Dict, Any

from services.coverage_pipeline import coverage_pipeline
from auth import get_current_user
from database import SessionLocal
from sqlalchemy import text
from utils.json_safe import as_json
from services.idempotency import idempotency_service
from fastapi import Header

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adapt", tags=["coverage_adaptive_sessions"])

@router.post("/plan-next")
async def async_plan_next_controller(
    body: dict, 
    request: Request, 
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    """
    Backend-canonical session_id with idempotency deduplication
    Returns 202 immediately, runs planning in background
    """
    # PERFORMANCE INSTRUMENTATION: Track every millisecond
    rid = request.headers.get("X-Request-Id") or idempotency_key or str(uuid.uuid4())
    t0 = time.perf_counter()
    
    logger.info(f"🚀 PLAN-NEXT START: request_id={rid}")
    
    try:
        # Validate required headers (FAST: <1ms)
        t_validation = time.perf_counter()
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="Idempotency-Key header required")
        
        dt_validation = int((time.perf_counter() - t_validation) * 1000)
        if dt_validation > 50:
            logger.warning(f"⚠️ SLOW VALIDATION: {dt_validation}ms for request_id={rid}")
        
        # Extract and validate parameters
        req_user_id = body.get("user_id")
        proposed_session_id = body.get("next_session_id")
        
        if not req_user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        if req_user_id != user_id:
            raise HTTPException(status_code=403, detail="Cannot plan sessions for other users")
        
        # IDEMPOTENCY CHECK (FAST: target <50ms)
        t_idem = time.perf_counter()
        canonical_session_id = idempotency_service.get_or_create_session_id(
            idempotency_key, proposed_session_id
        )
        dt_idem = int((time.perf_counter() - t_idem) * 1000)
        if dt_idem > 100:
            logger.warning(f"⚠️ SLOW IDEMPOTENCY: {dt_idem}ms for request_id={rid}")
        
        # DB CHECK (FAST: target <100ms)
        t_db = time.perf_counter()
        db = SessionLocal()
        try:
            existing_row = db.execute(text("""
                SELECT status FROM session_pack_plan WHERE session_id = :session_id
            """), {"session_id": canonical_session_id}).fetchone()
            
            dt_db_check = int((time.perf_counter() - t_db) * 1000)
            if dt_db_check > 200:
                logger.warning(f"⚠️ SLOW DB CHECK: {dt_db_check}ms for request_id={rid}")
            
            if existing_row:
                existing_status = existing_row[0]
                
                # Return current status (idempotent response)
                duration_ms = int((time.perf_counter() - t0) * 1000)
                logger.info(f"✅ IDEMPOTENT RESPONSE: {canonical_session_id[:8]} status={existing_status} in {duration_ms}ms")
                
                return JSONResponse({
                    "session_id": canonical_session_id,
                    "status": existing_status,
                    "message": f"Session {existing_status} (idempotent response)",
                    "id_source": "idempotency_cache",
                    "response_type": "idempotent"
                }, status_code=202)
        finally:
            db.close()
        
        # CREATE PLANNING ROW (FAST: target <100ms)
        t_insert = time.perf_counter()
        db = SessionLocal()
        try:
            db.execute(text("""
                INSERT INTO session_pack_plan (session_id, user_id, status, selection_method, created_at)
                VALUES (:session_id, :user_id, 'planning', 'coverage_v1', NOW())
            """), {"session_id": canonical_session_id, "user_id": req_user_id})
            db.commit()
            dt_insert = int((time.perf_counter() - t_insert) * 1000)
            if dt_insert > 200:
                logger.warning(f"⚠️ SLOW DB INSERT: {dt_insert}ms for request_id={rid}")
        except Exception as e:
            logger.error(f"❌ DB INSERT FAILED: {str(e)} for request_id={rid}")
            raise HTTPException(status_code=500, detail="Database error")
        finally:
            db.close()
        
        # TRIGGER BACKGROUND JOB (FIRE-AND-FORGET: target <10ms)
        t_bg = time.perf_counter()
        try:
            asyncio.create_task(background_plan_next_session(req_user_id, canonical_session_id))
            dt_bg = int((time.perf_counter() - t_bg) * 1000)
            if dt_bg > 50:
                logger.warning(f"⚠️ SLOW BG TRIGGER: {dt_bg}ms for request_id={rid}")
        except Exception as e:
            logger.error(f"❌ BACKGROUND JOB FAILED: {str(e)} for request_id={rid}")
            # Don't fail the request - job can be retried
        
        # RETURN 202 IMMEDIATELY
        duration_ms = int((time.perf_counter() - t0) * 1000)
        
        # PERFORMANCE ALERT: plan-next should be <500ms p50, <1000ms p95
        if duration_ms > 1000:
            logger.error(f"🚨 CRITICAL SLOW PLAN-NEXT: {duration_ms}ms for request_id={rid} session={canonical_session_id[:8]}")
        elif duration_ms > 500:
            logger.warning(f"⚠️ SLOW PLAN-NEXT: {duration_ms}ms for request_id={rid} session={canonical_session_id[:8]}")
        else:
            logger.info(f"✅ PLAN-NEXT OK: {duration_ms}ms for request_id={rid} session={canonical_session_id[:8]}")
        
        return JSONResponse({
            "session_id": canonical_session_id,
            "status": "planning", 
            "message": "Session planning started in background",
            "triggered_at": datetime.utcnow().isoformat() + 'Z',
            "id_source": "backend_generated" if not proposed_session_id else "client_proposed",
            "response_type": "new_session",
            "dt_ms": duration_ms  # Include timing in response for debugging
        }, status_code=202)
        
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.error(f"❌ ASYNC PLAN-NEXT: ERROR after {duration_ms}ms, request_id={rid}, error={str(e)}")
        raise HTTPException(status_code=500, detail={"code": "PLAN_TRIGGER_FAILED", "msg": str(e)})

async def background_plan_next_session(user_id: str, session_id: str):
    """Background job: Run coverage pipeline without blocking user"""
    try:
        logger.info(f"🔄 Background planning started for session {session_id[:8]}")
        
        # Run coverage pipeline (existing logic, 60s timeout OK)
        pipeline_result = await coverage_pipeline.plan_next_session(user_id, session_id)
        
        pack = pipeline_result.get("pack", [])
        audit = pipeline_result.get("audit", {})
        
        # Validate pack before saving
        if len(pack) != 12:
            raise ValueError(f"Pack generation failed: {len(pack)} questions instead of 12")
        
        # Update session status to 'planned' with pack data
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE session_pack_plan 
                SET pack_json = :pack_json,
                    coverage_audit = :coverage_audit,
                    status = 'planned',
                    served_at = NULL
                WHERE session_id = :session_id
            """), {
                "session_id": session_id,
                "pack_json": json.dumps(pack),
                "coverage_audit": json.dumps(audit)
            })
            db.commit()
        finally:
            db.close()
        
        logger.info(f"✅ Background planning completed for session {session_id[:8]} - {len(pack)} questions ready")
        
    except Exception as e:
        logger.error(f"❌ Background planning failed for session {session_id[:8]}: {e}")
        
        # Mark as failed so UI can show retry
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE session_pack_plan 
                SET status = 'failed',
                    coverage_audit = :error_audit
                WHERE session_id = :session_id
            """), {
                "session_id": session_id,
                "error_audit": json.dumps({
                    "error": str(e), 
                    "failed_at": datetime.utcnow().isoformat(),
                    "error_type": type(e).__name__
                })
            })
            db.commit()
        finally:
            db.close()

@router.get("/pack")
async def status_aware_pack_controller(user_id: str, session_id: str, auth_user_id: str = Depends(get_current_user)):
    """
    Status-aware pack endpoint: 200/202/500 based on planning state
    Core polling endpoint for async planning pattern
    """
    if user_id != auth_user_id:
        raise HTTPException(status_code=403, detail="Cannot access other users' packs")
    
    logger.info(f"📦 PACK: Checking status for session {session_id[:8]}")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT pack_json, status, coverage_audit, selection_method, created_at
            FROM session_pack_plan
            WHERE user_id = :user_id AND session_id = :session_id
            LIMIT 1
        """), {"user_id": user_id, "session_id": session_id}).fetchone()
        
        if not result:
            # Check if session is being created (race condition handling)
            logger.info(f"📦 PACK: Session {session_id[:8]} not found in database - checking for recent planning activity")
            raise HTTPException(status_code=404, detail="Session not found")
        
        pack_json, status, coverage_audit, selection_method, created_at = result
        
        if status == "planned":
            # Pack ready - return 200 with full data
            pack = as_json(pack_json)
            audit = as_json(coverage_audit)
            
            logger.info(f"✅ PACK: Session {session_id[:8]} ready with {len(pack)} questions")
            
            # Add pyq_distribution compatibility alias
            pyq_data = audit.get("pyq", {})
            pyq_distribution = {
                "ge_1_5": pyq_data.get("1_5", 0),
                "ge_1_0": pyq_data.get("1_0", 0)
            }
            
            return JSONResponse({
                "user_id": user_id,
                "session_id": session_id,
                "status": "planned",
                "pack": pack,
                "pack_ready": True,
                "coverage_audit": audit,
                "pyq_distribution": pyq_distribution,  # Contract requirement
                "pack_size": len(pack),
                "selection_method": selection_method,
                "meta": {
                    "selection_method": selection_method,
                    "version": "coverage_v1"
                }
            }, status_code=200)
            
        elif status == "planning":
            # Still processing - return 202 with polling info
            logger.info(f"⏳ PACK: Session {session_id[:8]} still planning")
            
            return JSONResponse({
                "user_id": user_id,
                "session_id": session_id,
                "status": "planning",
                "pack_ready": False,
                "message": "Session being prepared in background",
                "poll_after_ms": 2000,
                "created_at": created_at.isoformat() if created_at else None
            }, status_code=202)
            
        elif status == "failed":
            # Planning failed - return 500 with retry info
            audit = as_json(coverage_audit)
            error_msg = audit.get("error", "Unknown planning error")
            
            logger.warning(f"❌ PACK: Session {session_id[:8]} failed - {error_msg}")
            
            return JSONResponse({
                "user_id": user_id,
                "session_id": session_id,
                "status": "failed", 
                "pack_ready": False,
                "error": error_msg,
                "retry_available": True,
                "error_type": audit.get("error_type", "unknown")
            }, status_code=500)
            
        elif status == "served":
            # Already served - return pack data (read-only)
            pack = as_json(pack_json)
            audit = as_json(coverage_audit)
            
            logger.info(f"📋 PACK: Session {session_id[:8]} already served")
            
            return JSONResponse({
                "user_id": user_id,
                "session_id": session_id,
                "status": "served",
                "pack": pack,
                "pack_ready": True,
                "coverage_audit": audit,
                "pack_size": len(pack),
                "selection_method": selection_method,
                "meta": {
                    "selection_method": selection_method,
                    "version": "coverage_v1",
                    "read_only": True
                }
            }, status_code=200)
            
        else:
            # Unknown status
            return JSONResponse({
                "user_id": user_id,
                "session_id": session_id,
                "status": status,
                "pack_ready": False,
                "message": f"Session status: {status}"
            }, status_code=200)
            
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