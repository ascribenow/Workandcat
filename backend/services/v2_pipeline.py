"""
V2 Session Pipeline - CLEAN ORCHESTRATION

Main V2 pipeline orchestrating all services:
1. select_candidates() -> 12 IDs (fast, indexed)
2. plan_ids() -> optimized order (15s timeout, fallback)  
3. assemble_pack() -> heavy fields (single query)
4. persist_pack() -> save with telemetry

NO legacy paths. NO V1 compatibility. Pure V2 implementation.
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from database import SessionLocal
from sqlalchemy import text
from services.v2_candidate_selector import v2_candidate_selector
from services.v2_planner import v2_planner_service
from services.v2_pack_assembly import v2_pack_assembly
from util.v2_contract import V2ConstraintReport

logger = logging.getLogger(__name__)

class V2SessionPipeline:
    """
    V2 Session Pipeline - Complete orchestration
    
    Implements the clean V2 flow with no legacy paths:
    candidate_selection -> id_planning -> pack_assembly -> persistence
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def plan_next_session(self, user_id: str, session_id: str, request_id: str = None) -> Dict[str, Any]:
        """
        V2 Main Pipeline Entry Point
        
        Args:
            user_id: User UUID
            session_id: External session ID (string)  
            request_id: Request correlation ID
            
        Returns:
            Complete session plan with pack and telemetry
        """
        pipeline_start = time.time()
        rid_log = f"request_id={request_id}" if request_id else ""
        
        logger.info(f"V2 Pipeline: Starting session planning for user {user_id[:8]}, "
                   f"session {session_id[:8]} {rid_log}")
        
        try:
            # Step 1: Resolve session_id to sess_seq (internal canonical)
            sess_seq = self._resolve_session_sequence(user_id, session_id)
            
            # Step 2: Fast candidate selection (12 IDs, indexed)
            selection_start = time.time()
            candidate_selection = v2_candidate_selector.select_candidates(user_id, sess_seq)
            selection_time_ms = int((time.time() - selection_start) * 1000)
            
            logger.info(f"V2 Pipeline: Selected {len(candidate_selection.ids)} candidates in {selection_time_ms}ms")
            
            # Step 3: LLM planning (ID ordering, 15s timeout, fallback)
            planning_start = time.time()
            planning_result = v2_planner_service.plan_ids(
                candidate_selection.ids, user_id, sess_seq
            )
            planning_time_ms = int((time.time() - planning_start) * 1000)
            
            logger.info(f"V2 Pipeline: Planning completed in {planning_time_ms}ms, "
                       f"fallback={planning_result['planner_fallback']}")
            
            # Step 4: Pack assembly (heavy fields, single query)
            assembly_start = time.time()
            assembly_result = v2_pack_assembly.assemble_pack(planning_result["order"])
            assembly_time_ms = int((time.time() - assembly_start) * 1000)
            
            logger.info(f"V2 Pipeline: Pack assembled in {assembly_time_ms}ms, "
                       f"violations={len(assembly_result['constraint_validation'].violated)}")
            
            # Step 5: Persist pack with V2 telemetry
            persistence_start = time.time()
            persistence_result = self._persist_v2_pack(
                user_id=user_id,
                session_id=session_id, 
                sess_seq=sess_seq,
                pack=assembly_result["pack"],
                planning_result=planning_result,
                selection_meta=candidate_selection.selection_meta,
                constraint_validation=assembly_result["constraint_validation"]
            )
            persistence_time_ms = int((time.time() - persistence_start) * 1000)
            
            # Total pipeline timing
            total_time_ms = int((time.time() - pipeline_start) * 1000)
            
            logger.info(f"V2 Pipeline: Complete in {total_time_ms}ms "
                       f"(select={selection_time_ms}, plan={planning_time_ms}, "
                       f"assemble={assembly_time_ms}, persist={persistence_time_ms})")
            
            # Return V2 response
            return {
                "success": True,
                "user_id": user_id,
                "session_id": session_id,
                "sess_seq": sess_seq,
                "status": "planned",
                "pack": assembly_result["pack"].dict(),
                "constraint_report": assembly_result["constraint_validation"].dict(),
                "v2_telemetry": {
                    "total_time_ms": total_time_ms,
                    "selection_time_ms": selection_time_ms,
                    "planning_time_ms": planning_time_ms,
                    "assembly_time_ms": assembly_time_ms,
                    "persistence_time_ms": persistence_time_ms,
                    "planner_fallback": planning_result["planner_fallback"],
                    "constraint_violations": len(assembly_result["constraint_validation"].violated)
                },
                "pipeline_version": "v2"
            }
            
        except Exception as e:
            total_time_ms = int((time.time() - pipeline_start) * 1000)
            logger.error(f"V2 Pipeline: Failed after {total_time_ms}ms: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id,
                "session_id": session_id,
                "v2_telemetry": {
                    "total_time_ms": total_time_ms,
                    "error": str(e),
                    "pipeline_version": "v2"
                }
            }
    
    def _resolve_session_sequence(self, user_id: str, session_id: str) -> int:
        """
        V2 Internal: Resolve external session_id to internal sess_seq
        
        Uses the sessions table to maintain compatibility with frontend
        while using integer sess_seq internally for performance.
        """
        db = SessionLocal()
        try:
            # Try to find existing session
            result = db.execute(text("""
                SELECT sess_seq FROM sessions 
                WHERE session_id = :session_id AND user_id = :user_id
                LIMIT 1
            """), {"session_id": session_id, "user_id": user_id}).fetchone()
            
            if result:
                return result[0]
            
            # Get next sequence number for user
            next_seq_result = db.execute(text("""
                SELECT COALESCE(MAX(sess_seq), 0) + 1 as next_sess_seq
                FROM sessions 
                WHERE user_id = :user_id
            """), {"user_id": user_id}).fetchone()
            
            next_sess_seq = next_seq_result[0] if next_seq_result else 1
            
            # Create new session record
            db.execute(text("""
                INSERT INTO sessions (session_id, user_id, sess_seq, status, created_at)
                VALUES (:session_id, :user_id, :sess_seq, 'planned', NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    sess_seq = EXCLUDED.sess_seq,
                    status = EXCLUDED.status
            """), {
                "session_id": session_id,
                "user_id": user_id, 
                "sess_seq": next_sess_seq
            })
            
            db.commit()
            logger.info(f"V2 Pipeline: Created session {session_id[:8]} -> sess_seq {next_sess_seq}")
            return next_sess_seq
            
        finally:
            db.close()
    
    def _persist_v2_pack(self, 
                        user_id: str,
                        session_id: str,
                        sess_seq: int,
                        pack: Any,  # V2Pack
                        planning_result: Dict[str, Any],
                        selection_meta: Dict[str, Any],
                        constraint_validation: Any) -> Dict[str, Any]:  # V2ConstraintReport
        """
        V2 Persistence - Save pack with complete V2 telemetry
        """
        db = SessionLocal()
        try:
            # Convert pack to JSON for storage
            pack_json = pack.dict() if hasattr(pack, 'dict') else pack
            
            # Insert/update pack with V2 telemetry
            db.execute(text("""
                INSERT INTO session_pack_plan (
                    user_id, session_id, sess_seq, pack_json, constraint_report,
                    status, created_at, 
                    planner_fallback, retry_used, llm_model_used, processing_time_ms
                )
                VALUES (
                    :user_id, :session_id, :sess_seq, :pack_json, :constraint_report,
                    'planned', NOW(),
                    :planner_fallback, :retry_used, :llm_model_used, :processing_time_ms
                )
                ON CONFLICT (user_id, sess_seq) DO UPDATE SET
                    pack_json = EXCLUDED.pack_json,
                    constraint_report = EXCLUDED.constraint_report,
                    planner_fallback = EXCLUDED.planner_fallback,
                    retry_used = EXCLUDED.retry_used,
                    llm_model_used = EXCLUDED.llm_model_used,
                    processing_time_ms = EXCLUDED.processing_time_ms,
                    status = 'planned'
            """), {
                "user_id": user_id,
                "session_id": session_id,
                "sess_seq": sess_seq,
                "pack_json": json.dumps(pack_json),
                "constraint_report": json.dumps(constraint_validation.dict() if hasattr(constraint_validation, 'dict') else constraint_validation),
                "planner_fallback": planning_result["planner_fallback"],
                "retry_used": planning_result["retry_used"],
                "llm_model_used": planning_result["llm_model_used"],
                "processing_time_ms": planning_result["processing_time_ms"]
            })
            
            db.commit()
            
            logger.info(f"V2 Pipeline: Persisted pack for user {user_id[:8]}, sess_seq {sess_seq}")
            
            return {
                "persisted": True,
                "sess_seq": sess_seq,
                "pack_size": len(pack_json.get("items", [])) if isinstance(pack_json, dict) else 0
            }
            
        finally:
            db.close()

# Global instance  
v2_session_pipeline = V2SessionPipeline()