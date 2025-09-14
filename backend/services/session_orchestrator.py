#!/usr/bin/env python3
"""
Session Orchestration Service
Single entry point for all session planning operations in Phase 4
Handles idempotency, concurrency safety, and state transitions
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, Tuple
from database import SessionLocal
from sqlalchemy import text
from services.pipeline import plan_next_session
from services.telemetry import telemetry_service
from datetime import datetime

logger = logging.getLogger(__name__)

class ConflictError(Exception):
    """Raised when there's a concurrency conflict"""
    pass

def try_user_lock(user_id: str) -> bool:
    """
    Try to acquire an advisory lock for a user to prevent concurrent planning
    
    Args:
        user_id: User identifier
        
    Returns:
        True if lock acquired, False otherwise
    """
    db = SessionLocal()
    try:
        # Use PostgreSQL advisory locks with user_id hash
        result = db.execute(text("SELECT pg_try_advisory_xact_lock(hashtext(:user_id))"), 
                          {'user_id': user_id}).scalar()
        return bool(result)
    except Exception as e:
        logger.error(f"Error acquiring user lock for {user_id}: {e}")
        return False
    finally:
        db.close()

def load_pack(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load an existing session pack plan from database
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        Pack data or None if not found
    """
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT pack, constraint_report, status, created_at
            FROM session_pack_plan 
            WHERE user_id = :user_id AND session_id = :session_id
        """), {'user_id': user_id, 'session_id': session_id}).fetchone()
        
        if not result:
            return None
            
        return {
            'user_id': user_id,
            'session_id': session_id,
            'pack_json': result.pack if isinstance(result.pack, list) else json.loads(result.pack or '[]'),
            'constraint_report_json': result.constraint_report if isinstance(result.constraint_report, dict) else json.loads(result.constraint_report or '{}'),
            'status': result.status,
            'created_at': result.created_at
        }
    except Exception as e:
        logger.error(f"Error loading pack for {user_id}/{session_id}: {e}")
        return None
    finally:
        db.close()

def save_pack(user_id: str, session_id: str, plan: Dict[str, Any], constraint_report: Dict[str, Any], request_id: str = None) -> bool:
    """
    Save a session pack plan to database
    
    Args:
        user_id: User identifier
        session_id: Session identifier  
        plan: Planned session data
        constraint_report: Planning constraints and validation results
        request_id: Optional request correlation ID for diagnostic tracing
        
    Returns:
        True if saved successfully
    """
    db = SessionLocal()
    try:
        # Extract pack from plan
        pack_data = plan.get('pack', [])
        
        # Insert session record with race-safe sess_seq calculation using proper FOR UPDATE pattern
        db.execute(text("""
            WITH locked_sessions AS (
                SELECT sess_seq
                FROM sessions
                WHERE user_id = :user_id
                FOR UPDATE  -- lock existing rows for this user
            ),
            next AS (
                SELECT COALESCE(MAX(sess_seq), 0) + 1 AS next_sess_seq
                FROM locked_sessions
            )
            INSERT INTO sessions (user_id, session_id, sess_seq, status, created_at)
            SELECT :user_id, :session_id, next_sess_seq, 'planned', NOW()
            FROM next
            ON CONFLICT (session_id) DO UPDATE
                SET status = EXCLUDED.status  -- don't touch created_at; keep original
        """), {
            'user_id': user_id,
            'session_id': session_id
        })
        
        # Insert or update session pack plan
        db.execute(text("""
            INSERT INTO session_pack_plan (
                user_id, session_id, pack, constraint_report, status, 
                cold_start_mode, planning_strategy, created_at,
                llm_model_used, processing_time_ms
            ) VALUES (
                :user_id, :session_id, :pack, :constraint_report, 'planned',
                :cold_start_mode, :planning_strategy, NOW(),
                :llm_model_used, :processing_time_ms
            )
            ON CONFLICT (user_id, session_id) DO UPDATE SET
                pack = EXCLUDED.pack,
                constraint_report = EXCLUDED.constraint_report,
                status = EXCLUDED.status,
                cold_start_mode = EXCLUDED.cold_start_mode,
                planning_strategy = EXCLUDED.planning_strategy,
                created_at = EXCLUDED.created_at,
                llm_model_used = EXCLUDED.llm_model_used,
                processing_time_ms = EXCLUDED.processing_time_ms
        """), {
            'user_id': user_id,
            'session_id': session_id,
            'pack': json.dumps(pack_data),
            'constraint_report': json.dumps(constraint_report),
            'cold_start_mode': plan.get('cold_start_mode', False),
            'planning_strategy': plan.get('pipeline_path', 'unknown'),
            'llm_model_used': constraint_report.get('meta', {}).get('model_used'),
            'processing_time_ms': constraint_report.get('meta', {}).get('processing_time_ms')
        })
        
        db.commit()
        logger.info(f"✅ Saved pack for user {user_id[:8]}, session {session_id[:8]}")
        return True
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving pack for {user_id}/{session_id}: {e}")
        return False
    finally:
        db.close()

def transition_pack_to_served(user_id: str, session_id: str) -> bool:
    """
    Transition a pack from 'planned' to 'served' status
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        
    Returns:
        True if transition successful
    """
    db = SessionLocal()
    try:
        # Update session pack plan with server-side timestamp
        result = db.execute(text("""
            UPDATE session_pack_plan 
            SET status = 'served', served_at = NOW()
            WHERE user_id = :user_id AND session_id = :session_id 
            AND status = 'planned'
            RETURNING user_id
        """), {
            'user_id': user_id,
            'session_id': session_id
        })
        
        updated = result.fetchone()
        if updated:
            # Also update session status with server-side timestamp
            db.execute(text("""
                UPDATE sessions 
                SET status = 'in_progress', served_at = NOW()
                WHERE user_id = :user_id AND session_id = :session_id
            """), {
                'user_id': user_id,
                'session_id': session_id
            })
            
            db.commit()
            logger.info(f"✅ Transitioned pack to served for user {user_id[:8]}, session {session_id[:8]}")
            return True
        else:
            logger.warning(f"⚠️ Pack transition failed - not in 'planned' state for {user_id[:8]}/{session_id[:8]}")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error transitioning pack for {user_id}/{session_id}: {e}")
        return False
    finally:
        db.close()

def plan_next(user_id: str, last_session_id: str, next_session_id: str, idem_key: str = None, request_id: str = None) -> Dict[str, Any]:
    """
    Main orchestration function for planning next session - WITH DIAGNOSTIC TRACING
    
    Args:
        user_id: User identifier
        last_session_id: Previous session identifier 
        next_session_id: Next session identifier to plan
        idem_key: Optional idempotency key for request deduplication
        request_id: Request correlation ID for diagnostic tracing
        
    Returns:
        Session plan with pack and metadata + timing information
        
    Raises:
        ConflictError: If another planning operation is in progress
    """
    import time
    
    # DIAGNOSTIC TIMING SETUP
    t0 = time.perf_counter()
    timing_meta = {"db_candidates": 0, "llm_planner": 0, "db_write": 0, "retries": {"llm": 0, "db": 0}}
    rid_log = f"request_id={request_id}" if request_id else ""
    
    logger.info(f"🚀 Orchestrating session planning for user {user_id[:8]}, next session {next_session_id[:8]} {rid_log}")
    
    # Step 1: Check for existing planned session (idempotency)
    existing = load_pack(user_id, next_session_id)
    if existing and existing["status"] == "planned":
        logger.info(f"📋 Returning existing planned session for user {user_id[:8]} {rid_log}")
        existing["timing_meta"] = timing_meta  # Add empty timing for consistency
        return existing
    
    # Step 2: Acquire advisory lock for concurrency safety  
    acquired = try_user_lock(user_id)
    if not acquired:
        raise ConflictError("Planning already in progress for user")
    
    try:
        # Step 3: Run session-scoped pipeline (Phase 3 implementation) - WITH TIMING
        logger.info(f"🧠 Running pipeline planning for user {user_id[:8]} {rid_log}")
        
        t_pipeline_start = time.perf_counter()
        # Call the existing pipeline function - this includes candidate selection and LLM
        pipeline_result = plan_next_session(user_id, force_cold_start=False, request_id=request_id)
        pipeline_dur_ms = int((time.perf_counter() - t_pipeline_start) * 1000)
        
        if not pipeline_result.get('success'):
            raise Exception(f"Pipeline planning failed: {pipeline_result.get('error')}")
        
        # Extract timing from pipeline if available
        pipeline_timing = pipeline_result.get('timing_meta', {})
        timing_meta["db_candidates"] = pipeline_timing.get("db_candidates", 0)
        timing_meta["llm_planner"] = pipeline_timing.get("llm_planner", 0) 
        timing_meta["retries"] = pipeline_timing.get("retries", {"llm": 0, "db": 0})
        
        # Step 4: Extract plan and constraint report
        plan = pipeline_result.get('plan', {})
        constraint_report = plan.get('constraint_report', {})
        
        # Add metadata from pipeline result
        constraint_report.setdefault('meta', {}).update({
            'pipeline_path': pipeline_result.get('pipeline_path', 'unknown'),
            'cold_start_mode': pipeline_result.get('cold_start_mode', False),
            'session_sequence': pipeline_result.get('session_sequence', 1),
            'candidate_pool_size': pipeline_result.get('metadata', {}).get('candidate_pool_size', 0),
            'pipeline_dur_ms': pipeline_dur_ms
        })
        
        # Step 5: Save pack in database transaction - WITH TIMING  
        t_db_write = time.perf_counter()
        success = save_pack(user_id, next_session_id, plan, constraint_report, request_id=request_id)
        if not success:
            raise Exception("Failed to save session pack")
        timing_meta["db_write"] = int((time.perf_counter() - t_db_write) * 1000)
        
        # Step 6: Emit telemetry
        telemetry_service.emit_session_planned(
            constraint_report, 
            cold_start=pipeline_result.get('cold_start_mode', False),
            pool_expanded=constraint_report.get('meta', {}).get('pool_expanded', False)
        )
        
        # Step 7: Return planned session data WITH TIMING
        total_dur_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(f"✅ Session planning completed for user {user_id[:8]} in {total_dur_ms}ms {rid_log}")
        
        return {
            "user_id": user_id,
            "session_id": next_session_id, 
            "status": "planned",
            "constraint_report_json": constraint_report,
            "timing_meta": timing_meta,
            "total_orchestration_ms": total_dur_ms
        }
        
    except Exception as e:
        logger.error(f"❌ Session planning failed for user {user_id[:8]}: {e}")
        raise e