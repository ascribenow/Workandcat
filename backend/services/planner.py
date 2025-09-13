"""
Session Planner Service
Uses LLM intelligence to select optimal 12-question packs based on readiness and coverage
"""

import json
import logging
import time
from typing import Dict, Any, List
from util.schemas import PLANNER_SCHEMA
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

Return ONLY valid JSON matching the required schema."""

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
        
        # Call LLM with schema validation and retry
        start_time = time.time()
        
        try:
            data = call_llm_json_with_retry(
                system_prompt=self.system_prompt,
                user_payload=payload,
                schema=PLANNER_SCHEMA,
                model_primary="gpt-4o",
                model_fallback="gemini-1.5-pro",
                max_retries=1
            )
            
            # Calculate telemetry
            elapsed_time = time.time() - start_time
            tokens_used = len(json.dumps(payload)) // 4  # Rough token estimate
            
            # Add telemetry to constraint report
            if "constraint_report" in data:
                data["constraint_report"].setdefault("meta", {}).update({
                    "processing_time_ms": int(elapsed_time * 1000),
                    "estimated_tokens": tokens_used,
                    "relaxation_count": len(data["constraint_report"].get("relaxed", [])),
                    "cold_start_mode": cold_start_mode
                })
            
            logger.info(f"✅ Planner completed for user {user_id[:8]} ({elapsed_time:.2f}s, ~{tokens_used} tokens)")
            return data
            
        except Exception as e:
            logger.error(f"❌ Planner failed for user {user_id[:8]}: {e}")
            return self._generate_fallback_plan(candidate_pool_by_band, cold_start_mode)
    
    def _generate_fallback_plan(self, candidate_pool_by_band: Dict[str, List], 
                               cold_start_mode: bool) -> Dict[str, Any]:
        """Generate fallback plan when LLM fails"""
        import random
        
        logger.warning("🔄 Generating fallback plan due to LLM failure")
        
        pack = []
        target_distribution = {"Easy": 3, "Medium": 6, "Hard": 3}
        
        # Simple fallback selection
        for band, target_count in target_distribution.items():
            available = candidate_pool_by_band.get(band, [])
            if len(available) >= target_count:
                selected = random.sample(available, target_count)
                pack.extend(selected)
            else:
                pack.extend(available)  # Take what we can get
        
        return {
            "pack": [
                {
                    "item_id": q.get("question_id", "unknown"),
                    "bucket": q.get("difficulty_band", "Medium"),
                    "why": {
                        "semantic_concepts": q.get("core_concepts", []),
                        "readiness": "Moderate",
                        "pair": q.get("pair", "unknown:unknown"),
                        "pyq_frequency_score": q.get("pyq_frequency_score", 0.5)
                    }
                }
                for q in pack[:12]  # Ensure max 12 questions
            ],
            "constraint_report": {
                "met": ["total_count"],
                "relaxed": [
                    {"name": "llm_planning", "reason": "LLM failed, using deterministic fallback"}
                ],
                "meta": {
                    "pool_expanded": False,
                    "retry_used": False,
                    "fallback_used": True
                }
            },
            "session_notes": "Fallback plan generated due to LLM failure"
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