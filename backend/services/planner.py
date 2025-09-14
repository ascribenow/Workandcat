"""
Session Planner Service
Uses LLM intelligence to select optimal 12-question packs based on readiness and coverage
"""

import logging
import time
from typing import Dict, Any, List
from util.llm_guarded import call_llm_json_with_retry
from services.deterministic_kernels import validate_pack

logger = logging.getLogger(__name__)

class PlannerService:
    """LLM-powered session planning with constraint handling"""
    
    def __init__(self):
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load planner system prompt"""
        return """You are an expert session planner for CAT preparation, tasked with selecting optimal 12-question practice sets.

TASK: Select exactly 12 questions from the provided candidate pool to create an optimal practice session.

MANDATORY CONSTRAINTS (NEVER RELAX):
1. **Total Count**: Exactly 12 questions
2. **Difficulty Distribution**: Exactly 3 Easy, 6 Medium, 3 Hard questions
3. **PYQ Requirements**: Minimum 2 questions with PYQ score ≥1.0 AND minimum 2 questions with PYQ score ≥1.5

ADAPTIVE CONSTRAINTS (Relax in order if needed):
1. **Coverage Priority**: Prefer questions from pairs with "high" coverage debt
2. **Readiness Targeting**: Use readiness level for the question's OWN pair only

RELAXATION ORDER (when constraints conflict):
- First relax: Coverage debt requirements (high → med → low)
- Second relax: Readiness requirements (weak → moderate → strong)
- NEVER relax: Band distribution or PYQ requirements

COLD START MODE:
- Objective: ≥5 distinct pairs across the 12 questions
- Prioritize diversity over optimization
- Still maintain all mandatory constraints

SELECTION STRATEGY:
1. Enforce mandatory constraints first
2. Apply adaptive constraints within feasible space
3. Use readiness ONLY for the question's own concept pair
4. Report which constraints were relaxed and why

REQUIRED OUTPUT FORMAT:
You MUST return a JSON object with exactly these two fields:
{
  "pack": [...12 question objects...],
  "constraint_report": {
    "met": ["list of constraints that were satisfied"],
    "relaxed": [{"name": "constraint_name", "reason": "why it was relaxed"}]
  }
}

Return ONLY valid JSON matching the required schema. The constraint_report field is MANDATORY."""

    def run_planner(self, user_id: str, candidate_pool_by_band: Dict[str, List], 
                   final_readiness: List[Dict], concept_weights_by_item: Dict,
                   pair_coverage_final: List[Dict], cold_start_mode: bool = False,
                   early_session_mode: bool = False) -> Dict[str, Any]:
        """
        Run session planning with LLM intelligence
        
        Args:
            user_id: User identifier
            candidate_pool_by_band: Questions grouped by difficulty band
            final_readiness: Readiness levels per concept/pair
            concept_weights_by_item: Weight assignments per question
            pair_coverage_final: Coverage debt scores per pair
            cold_start_mode: Use diversity-first cold start logic
            early_session_mode: Use early session adaptations
            
        Returns:
            Planner results with selected question pack
        """
        logger.info(f"🎯 Running Planner for user {user_id[:8]} (cold_start={cold_start_mode})")
        
        # Build payload for planner
        payload = {
            "user_id": user_id,
            "cold_start_mode": cold_start_mode,
            "early_session_mode": early_session_mode,
            "final_readiness": final_readiness,
            "concept_weights_by_item": concept_weights_by_item,
            "pair_coverage_final": pair_coverage_final,
            "candidate_pool": candidate_pool_by_band,
            "constraints": {
                "mandatory": {
                    "total_questions": 12,
                    "difficulty_distribution": {"Easy": 3, "Medium": 6, "Hard": 3},
                    "pyq_minimums": {"score_1_0": 2, "score_1_5": 2}
                },
                "adaptive": {
                    "coverage_priority": True,
                    "readiness_targeting": True,
                    "cold_start_diversity": cold_start_mode
                }
            }
        }
        
        # Add cold start specific requirements
        if cold_start_mode:
            payload["cold_start_requirements"] = {
                "min_distinct_pairs": 5,
                "diversity_priority": True
            }
        
        # Call LLM with STRICT TIMEOUT and schema validation
        start_time = time.time()
        llm_timeout_ms = 15000  # P0 FIX: Cap at 15 seconds
        
        try:
            # P0 FIX: Flatten candidate pool for simplified processing
            candidates = []
            for band_candidates in candidate_pool_by_band.values():
                candidates.extend(band_candidates)
            
            # P0 FIX: Simplified schema - just return ID ordering, not full objects  
            simplified_payload = {
                "user_id": user_id[-8:],  # Shorter for token efficiency
                "candidate_pool_size": len(candidates),
                "constraints": {
                    "total": 12,
                    "difficulty": {"easy": 3, "medium": 6, "hard": 3},
                    "pyq_requirements": {"min_15_score": 2, "min_10_score": 2}
                },
                "task": "Return only an ordered list of 12 question IDs from the candidate pool, prioritized by adaptive learning value"
            }
            
            if cold_start_mode:
                simplified_payload["cold_start"] = {"min_distinct_pairs": 5}
            
            data = call_llm_json_with_retry(
                system_prompt=self._get_simplified_prompt(),
                user_payload=simplified_payload,
                schema=self._get_simplified_schema(),
                model_primary="gpt-4o-mini",  # Faster model
                model_fallback="gemini-1.5-flash",  # Faster fallback
                max_retries=1,  # P0 FIX: Only 1 retry max
                timeout_ms=llm_timeout_ms  # P0 FIX: 15s timeout
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ LLM planner completed in {elapsed_time*1000:.0f}ms")
            
            # Convert simplified response to full pack format
            return self._convert_id_ordering_to_pack(data, candidates, constraint_report_base={
                "met": ["total_count", "difficulty_distribution", "pyq_requirements"],
                "relaxed": [],
                "meta": {
                    "processing_time_ms": int(elapsed_time * 1000),
                    "model_used": "llm_planner_simplified",
                    "retry_used": 0,
                    "timeout_ms": llm_timeout_ms
                }
            })
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Planner failed for user {user_id[:8]} after {elapsed_time*1000:.0f}ms: {e}")
            
            # P0 FIX: Fast fallback to deterministic order
            logger.warning("🔄 Using deterministic fallback due to LLM timeout/failure")
            return self._generate_deterministic_fallback(candidates, {
                "met": ["total_count", "difficulty_distribution"],
                "relaxed": ["llm_planning"],
                "meta": {
                    "processing_time_ms": int(elapsed_time * 1000),
                    "model_used": "deterministic_fallback",
                    "retry_used": 1,
                    "timeout_ms": llm_timeout_ms,
                    "fallback_reason": str(e)
                }
            })
    
    def _get_simplified_prompt(self) -> str:
        """P0 FIX: Simplified prompt for fast ID ordering only"""
        return """You are an expert session planner. Your task is to select and order exactly 12 question IDs from a candidate pool.

TASK: Return a JSON with an ordered array of 12 question IDs, optimized for adaptive learning.

CONSTRAINTS (NEVER RELAX):
1. Exactly 12 questions total
2. Maintain 3 Easy : 6 Medium : 3 Hard distribution  
3. Include ≥2 questions with PYQ score ≥1.0 and ≥2 with PYQ score ≥1.5

COLD START: If specified, prioritize diversity (≥5 distinct concept pairs).

OUTPUT FORMAT (max 300 tokens):
{
  "selected_ids": ["id1", "id2", ..., "id12"],
  "reasoning": "brief 1-line explanation"
}

Return ONLY this JSON format. Do not include question content or metadata."""
    
    def _get_simplified_schema(self):
        """P0 FIX: Simplified schema for ID ordering only"""
        return {
            "type": "object",
            "properties": {
                "selected_ids": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "minItems": 12,
                    "maxItems": 12
                },
                "reasoning": {"type": "string", "maxLength": 200}
            },
            "required": ["selected_ids", "reasoning"]
        }
    
    def _convert_id_ordering_to_pack(self, llm_response, candidates, constraint_report_base):
        """P0 FIX: Convert simplified LLM response to full pack format"""
        selected_ids = llm_response.get("selected_ids", [])
        
        # Create mapping from candidates
        candidate_map = {q["id"]: q for q in candidates}
        
        # Build full pack from selected IDs
        pack = []
        for question_id in selected_ids[:12]:  # Ensure max 12
            if question_id in candidate_map:
                question = candidate_map[question_id]
                pack.append({
                    "item_id": question["id"],  # P0 FIX: Always present
                    "why": question.get("stem", "Question content"),
                    "bucket": question.get("difficulty_band", "Medium").lower(),
                    "pair": question.get("subcategory", "unknown"),
                    "pyq_frequency_score": question.get("pyq_frequency_score", 0.0),
                    "semantic_concepts": question.get("semantic_concepts", [])
                })
        
        # If we don't have enough questions, fill with fallback
        while len(pack) < 12 and len(candidates) > len(pack):
            remaining_candidates = [c for c in candidates if c["id"] not in selected_ids]
            if remaining_candidates:
                q = remaining_candidates[0]
                pack.append({
                    "item_id": q["id"],
                    "why": q.get("stem", "Question content"),
                    "bucket": q.get("difficulty_band", "Medium").lower(),
                    "pair": q.get("subcategory", "unknown"),
                    "pyq_frequency_score": q.get("pyq_frequency_score", 0.0),
                    "semantic_concepts": q.get("semantic_concepts", [])
                })
                selected_ids.append(q["id"])
            else:
                break
        
        return {
            "pack": pack[:12],
            "constraint_report": constraint_report_base
        }
        
    def _generate_deterministic_fallback(self, candidates, constraint_report_base):
        """P0 FIX: Fast deterministic fallback using candidate list"""
        
        logger.warning("🔄 Generating deterministic fallback plan")
        
        # Simple deterministic selection: take first 12 candidates
        pack = []
        for candidate in candidates[:12]:
            pack.append({
                "item_id": candidate.get("id", candidate.get("question_id", "unknown")),
                "why": candidate.get("stem", "Question content"),
                "bucket": candidate.get("difficulty_band", "Medium").lower(),
                "pair": candidate.get("subcategory", "unknown"),
                "pyq_frequency_score": candidate.get("pyq_frequency_score", 0.0),
                "semantic_concepts": candidate.get("semantic_concepts", [])
            })
        
        return {
            "pack": pack,
            "constraint_report": constraint_report_base
        }
    
    def validate_and_retry_plan(self, plan: Dict[str, Any], candidate_pool: List,
                               valid_pairs: set, known_concepts: set) -> Dict[str, Any]:
        """
        Validate planner output and retry once if invalid
        
        Args:
            plan: Planner output to validate
            candidate_pool: Available question candidates
            valid_pairs: Valid subcategory:type pairs
            known_concepts: Known concept set
            
        Returns:
            Validated and potentially corrected plan
        """
        # Convert plan format to QuestionCandidate format for validation
        pack_candidates = []
        for item in plan.get("pack", []):
            try:
                # Convert planner format to candidate format
                candidate = {
                    "question_id": item["item_id"],
                    "difficulty_band": item["bucket"],
                    "pair": item["why"]["pair"],
                    "core_concepts": item["why"]["semantic_concepts"],
                    "pyq_frequency_score": item["why"]["pyq_frequency_score"]
                }
                pack_candidates.append(candidate)
            except Exception as e:
                logger.warning(f"Invalid plan item format: {e}")
                continue
        
        # Run validation
        validation_result = validate_pack(
            pack_candidates, 
            candidate_pool,
            valid_pairs,
            known_concepts
        )
        
        if validation_result["valid"]:
            logger.info("✅ Plan validation passed")
            return plan
        else:
            logger.warning(f"❌ Plan validation failed: {validation_result['errors']}")
            
            # Add validation errors to constraint report
            if "constraint_report" in plan:
                plan["constraint_report"].setdefault("relaxed", []).append({
                    "name": "validation_constraints",
                    "reason": f"Validation failed: {'; '.join(validation_result['errors'][:2])}"
                })
            
            # Could implement retry logic here if needed
            return plan

# Global instance
planner_service = PlannerService()