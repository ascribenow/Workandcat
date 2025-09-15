"""
V2 Planner Service - CLEAN IMPLEMENTATION

Only supports V2 contract. NO legacy V1 parsing.
Planner receives 12 IDs, returns them in optimized order.
Timeout/failure → deterministic fallback (part of spec).
"""

import json
import logging
import time
import hashlib
from typing import Dict, Any, List, Optional
from util.v2_contract import (
    V2PlannerResponse, V2_PLANNER_SCHEMA, V2_PLANNER_PROMPT,
    validate_membership_equality, PlannerStatus
)
from util.llm_guarded import call_llm_json_with_retry

logger = logging.getLogger(__name__)

class V2PlannerService:
    """
    V2 Planner - CANONICAL IMPLEMENTATION
    
    Core contract: Receives 12 candidate IDs, returns optimized order.
    NO membership changes. NO full objects. ID ordering only.
    """
    
    def __init__(self):
        self.timeout_ms = 15000  # 15s max LLM time
        self.max_retries = 1     # Single retry max
        
    def plan_ids(self, candidate_ids: List[str], user_id: str, sess_seq: int) -> Dict[str, Any]:
        """
        V2 Main Planning Function
        
        Args:
            candidate_ids: Exactly 12 candidate UUIDs
            user_id: User identifier (for seeded fallback)
            sess_seq: Session sequence (for seeded fallback)
            
        Returns:
            {
                "order": List[str],           # 12 UUIDs in optimized order
                "status": PlannerStatus,      # success|timeout|fallback_used etc
                "planner_fallback": bool,     # True if deterministic fallback used
                "processing_time_ms": int,    # Total time taken
                "retry_used": int,            # Number of retries used
                "llm_model_used": str        # Model identifier
            }
        """
        if len(candidate_ids) != 12:
            raise ValueError(f"V2 requires exactly 12 candidate IDs, got {len(candidate_ids)}")
        
        start_time = time.time()
        
        logger.info(f"V2 Planner: Processing {len(candidate_ids)} candidates for user {user_id[:8]}")
        
        # Attempt LLM planning with timeout
        try:
            llm_result = self._call_llm_planner(candidate_ids, user_id)
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Validate membership equality (core V2 rule)
            if not validate_membership_equality(candidate_ids, llm_result["order"]):
                logger.warning(f"V2 Planner: Membership violation detected, using fallback")
                return self._generate_deterministic_fallback(
                    candidate_ids, user_id, sess_seq, 
                    processing_time_ms, PlannerStatus.MEMBERSHIP_VIOLATION
                )
            
            logger.info(f"V2 Planner: LLM success in {processing_time_ms}ms")
            return {
                "order": llm_result["order"],
                "status": PlannerStatus.SUCCESS,
                "planner_fallback": False,
                "processing_time_ms": processing_time_ms,
                "retry_used": 0,
                "llm_model_used": "gpt-4o-mini"
            }
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"V2 Planner: LLM failed after {processing_time_ms}ms: {e}")
            
            # Determine failure type
            if "timeout" in str(e).lower():
                status = PlannerStatus.TIMEOUT
            elif "schema" in str(e).lower() or "validation" in str(e).lower():
                status = PlannerStatus.SCHEMA_INVALID
            else:
                status = PlannerStatus.FALLBACK_USED
            
            return self._generate_deterministic_fallback(
                candidate_ids, user_id, sess_seq, processing_time_ms, status
            )
    
    def _call_llm_planner(self, candidate_ids: List[str], user_id: str) -> Dict[str, Any]:
        """Call LLM with V2 contract and timeout"""
        
        # Minimal payload for faster processing
        payload = {
            "user": user_id[-8:],  # Last 8 chars for brevity
            "candidates": candidate_ids,
            "task": "Reorder these 12 question IDs for optimal adaptive learning progression"
        }
        
        # Call LLM with V2 schema and timeout
        response = call_llm_json_with_retry(
            system_prompt=V2_PLANNER_PROMPT,
            user_payload=payload,
            schema=V2_PLANNER_SCHEMA,
            model_primary="gpt-4o-mini",      # Faster model
            model_fallback="gemini-1.5-flash", # Faster fallback
            max_retries=self.max_retries,
            timeout_ms=self.timeout_ms
        )
        
        # Validate V2 response
        validated = V2PlannerResponse(**response)
        return validated.dict()
    
    def _generate_deterministic_fallback(self, 
                                       candidate_ids: List[str],
                                       user_id: str, 
                                       sess_seq: int,
                                       processing_time_ms: int,
                                       status: PlannerStatus) -> Dict[str, Any]:
        """
        V2 Deterministic Fallback - Part of the specification
        
        Uses seeded ordering based on user + session for reproducibility.
        This is NOT an emergency measure - it's part of the V2 contract.
        """
        logger.info(f"V2 Planner: Using deterministic fallback (status: {status})")
        
        # Generate seed for deterministic ordering
        seed_string = f"{user_id}:{sess_seq}:fallback"
        seed = abs(int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16))
        
        # Sort candidates by seeded hash for deterministic order
        def seeded_sort_key(candidate_id: str) -> int:
            combined = f"{candidate_id}:{seed}"
            return abs(int(hashlib.md5(combined.encode()).hexdigest()[:8], 16))
        
        ordered_ids = sorted(candidate_ids, key=seeded_sort_key)
        
        logger.info(f"V2 Planner: Deterministic fallback generated for user {user_id[:8]}")
        
        return {
            "order": ordered_ids,
            "status": status,
            "planner_fallback": True,
            "processing_time_ms": processing_time_ms,
            "retry_used": 0,
            "llm_model_used": "deterministic_fallback_v2"
        }

# Global instance
v2_planner_service = V2PlannerService()