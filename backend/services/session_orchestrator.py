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

def save_pack(user_id: str, session_id: str, plan: Dict[str, Any], constraint_report: Dict[str, Any]) -> bool:
    """
    Save a session pack plan to database
    
    Args:
        user_id: User identifier
        session_id: Session identifier  
        plan: Planned session data
        constraint_report: Planning constraints and validation results
        
    Returns:
        True if saved successfully
    """
    db = SessionLocal()
    try:
        # Extract pack from plan
        pack_data = plan.get('pack', [])
        
        # Insert session record with race-safe sess_seq calculation (inside existing transaction)
        db.execute(text("""
            WITH next AS (
                SELECT COALESCE(MAX(sess_seq), 0) + 1 AS next_sess_seq
                FROM sessions
                WHERE user_id = :user_id
                FOR UPDATE  -- prevent race on MAX+1
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
                :cold_start_mode, :planning_strategy, :created_at,
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
            'created_at': text('NOW()'),  # Use server-side timestamp
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
                SET status = 'in_progress', started_at = NOW()
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

def plan_next(user_id: str, last_session_id: str, next_session_id: str, idem_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Main orchestration function for planning next session
    
    Implements idempotency, concurrency safety, and dual-path logic
    
    Args:
        user_id: User identifier
        last_session_id: Previous session identifier 
        next_session_id: Next session identifier to plan
        idem_key: Optional idempotency key for request deduplication
        
    Returns:
        Session plan with pack and metadata
        
    Raises:
        ConflictError: If another planning operation is in progress
    """
    logger.info(f"🚀 Orchestrating session planning for user {user_id[:8]}, next session {next_session_id[:8]}")
    
    # Step 1: Check for existing planned session (idempotency)
    existing = load_pack(user_id, next_session_id)
    if existing and existing["status"] == "planned":
        logger.info(f"📋 Returning existing planned session for user {user_id[:8]}")
        return existing
    
    # Step 2: Acquire advisory lock for concurrency safety  
    acquired = try_user_lock(user_id)
    if not acquired:
        raise ConflictError("Planning already in progress for user")
    
    try:
        # Step 3: Run session-scoped pipeline (Phase 3 implementation)
        logger.info(f"🧠 Running pipeline planning for user {user_id[:8]}")
        
        # Call the existing pipeline function
        pipeline_result = plan_next_session(user_id, force_cold_start=False)
        
        if not pipeline_result.get('success'):
            raise Exception(f"Pipeline planning failed: {pipeline_result.get('error')}")
        
        # Step 4: Extract plan and constraint report
        plan = pipeline_result.get('plan', {})
        constraint_report = plan.get('constraint_report', {})
        
        # Add metadata from pipeline result
        constraint_report.setdefault('meta', {}).update({
            'pipeline_path': pipeline_result.get('pipeline_path', 'unknown'),
            'cold_start_mode': pipeline_result.get('cold_start_mode', False),
            'session_sequence': pipeline_result.get('session_sequence', 1),
            'candidate_pool_size': pipeline_result.get('metadata', {}).get('candidate_pool_size', 0)
        })
        
        # Step 5: Save pack in database transaction
        success = save_pack(user_id, next_session_id, plan, constraint_report)
        if not success:
            raise Exception("Failed to save session pack")
        
        # Step 6: Emit telemetry
        telemetry_service.emit_session_planned(
            constraint_report, 
            cold_start=pipeline_result.get('cold_start_mode', False),
            pool_expanded=constraint_report.get('meta', {}).get('pool_expanded', False)
        )
        
        # Step 7: Return planned session data
        return load_pack(user_id, next_session_id)
        
    except Exception as e:
        logger.error(f"❌ Session planning failed for user {user_id[:8]}: {e}")
        raise e