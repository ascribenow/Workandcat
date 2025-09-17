"""
Post-Session Summarizer Service
Analyzes user attempt history to extract concept dominance and readiness patterns
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List
from database import SessionLocal
from sqlalchemy import text
from util.schemas import SUMMARIZER_SCHEMA
from util.llm_guarded import call_llm_json_with_retry
from services.deterministic_kernels import stable_semantic_id

logger = logging.getLogger(__name__)

class SummarizerService:
    """Post-session qualitative analysis using LLM"""
    
    def __init__(self):
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load summarizer system prompt"""
        return """You are an expert at analyzing student performance in CAT preparation to identify concept mastery patterns.

TASK: Analyze the student's attempt history and provide qualitative insights about concept dominance, readiness, and coverage patterns.

OUTPUT REQUIREMENTS:
1. **Concept Alias Mapping**: Normalize raw concept strings, reuse existing aliases when possible, only create provisional new concepts when necessary
2. **Dominance Analysis**: For each question attempt, identify 1-2 dominant concepts that drove the solution approach
3. **Readiness Assessment**: Evaluate concept mastery based on performance patterns (skipped, wrong streaks, correct patterns)
4. **Coverage Debt**: Identify concept pairs that need more practice based on recency and exposure

NORMALIZATION RULES:
- Reuse existing alias when ANY normalized member matches
- Only create "provisional": true new concepts when absolutely necessary
- Maintain consistency in concept identification

DOMINANCE RULES:
- High confidence + 1 dominant → 0.7/0.3 weight split
- High confidence + 2 dominants → 0.5/0.5 weight split
- Otherwise → equal split 1/k

READINESS CRITERIA:
- "skipped": High skip rate indicates avoidance
- "forever_wrong": Never got correct, indicates fundamental gap
- "wrong_1_to_3": Recent wrong streak, needs reinforcement
- "wrong_gt_3": Extended wrong streak, serious difficulty
- "cold_start": New concept, needs foundation building

Return ONLY valid JSON matching the required schema."""

    async def run(self, user_id: str, session_id: str = None, sess_seq: int = None) -> Dict[str, Any]:
        """
        Run post-session analysis for a user
        
        Args:
            user_id: User identifier  
            session_id: Session UUID (optional, will resolve to sess_seq)
            sess_seq: Session sequence number (optional)
            
        Returns:
            Summarizer analysis results
        """
        from services.telemetry import telemetry_service as telemetry
        from database import SessionLocal
        
        logger.info(f"🧠 Running Summarizer for user {user_id[:8]}...")
        
        db = SessionLocal()
        try:
            # 1) Resolve sess_seq from sessions if not given
            if sess_seq is None:
                row = db.execute(text("""
                    SELECT sess_seq
                    FROM sessions
                    WHERE user_id = :user_id AND session_id = :session_id
                    LIMIT 1
                """), {"user_id": user_id, "session_id": session_id}).fetchone()
                if not row:
                    telemetry.emit("summarizer_missing_session", {"user_id": user_id, "session_id": session_id})
                    return self._generate_empty_summary()  # no-op: don't fail pipeline
                sess_seq = row.sess_seq  # Fix: Use attribute access instead of dict access

            # 2) Fetch attempts by (user_id, sess_seq_at_serve)
            attempts = db.execute(text("""
                SELECT *
                FROM attempt_events
                WHERE user_id = :user_id AND sess_seq_at_serve = :sess_seq
                ORDER BY created_at ASC, id ASC
            """), {"user_id": user_id, "sess_seq": sess_seq}).fetchall()

            if not attempts:
                telemetry.emit("summarizer_no_attempts", {"user_id": user_id, "sess_seq": sess_seq, "session_id": session_id})
                return self._generate_empty_summary()  # nothing to summarize

            # Build payload with attempt history for this session
            payload = self._build_summarizer_payload_from_attempts(user_id, attempts)
            
            # Call LLM with schema validation and retry
            start_time = time.time()
            tokens_used = 0
            
            try:
                # Use dedicated summarizer LLM service  
                from services.summarizer_llm_service import summarizer_llm_service
                
                # Call LLM using dedicated service
                raw_response, model_used = await summarizer_llm_service.call_for_concept_analysis(
                    system_prompt=self.system_prompt,
                    user_payload=payload
                )
                
                # Validate response using dedicated service
                ok, data, errors = summarizer_llm_service.validate_json_response(raw_response, SUMMARIZER_SCHEMA)
                
                if not ok:
                    logger.warning(f"Summarizer LLM returned invalid JSON: {errors}")
                    return self._generate_empty_summary()
                
                # Calculate telemetry
                elapsed_time = time.time() - start_time
                tokens_used = len(json.dumps(payload)) // 4  # Rough token estimate
                
                # Add telemetry to response with actual model used
                data.setdefault("telemetry", {}).update({
                    "processing_time_ms": int(elapsed_time * 1000),
                    "estimated_tokens": tokens_used,
                    "llm_model_used": model_used,  # Use actual model from dedicated service
                    "alias_reuse_rate": self._calculate_alias_reuse_rate(data),
                    "provisional_new_count": self._count_provisional_concepts(data),
                })
                
                # 3) Persist session summary ONLY if meaningful LLM analysis was performed
                model_used = data.get("telemetry", {}).get("llm_model_used", "none")
                if model_used != "none" and model_used != "unknown":
                    logger.info(f"📊 Persisting session summary to database...")
                    try:
                        db.execute(text("""
                            INSERT INTO session_summary_llm
                                (session_id, user_id,
                                 concept_alias_map, dominance, readiness_reasons, coverage_labels,
                                 llm_model_used, created_at)
                            VALUES
                                (:session_id, :user_id, :concept_alias_map_json::jsonb, :dominance_json::jsonb, 
                                 :readiness_reasons_json::jsonb, :coverage_labels_json::jsonb, :llm_model_used, NOW())
                        """), {
                            "session_id": session_id,
                            "user_id": user_id,
                            "concept_alias_map_json": json.dumps(data.get("concept_alias_map_updated", [])),
                            "dominance_json": json.dumps(data.get("dominance_by_item", {})),
                            "readiness_reasons_json": json.dumps(data.get("concept_readiness_labels", [])),
                            "coverage_labels_json": json.dumps(data.get("pair_coverage_labels", [])),
                            "llm_model_used": model_used
                        })
                        logger.info(f"✅ Session summary persisted successfully")
                    except Exception as persist_error:
                        logger.error(f"❌ Session summary persistence failed: {persist_error}")
                        raise persist_error

                    # 4) Upsert per-user alias map ONLY if meaningful data exists
                    if data.get("concept_alias_map_updated"):
                        logger.info(f"📊 Upserting concept alias map...")
                        try:
                            db.execute(text("""
                                INSERT INTO concept_alias_map_latest (user_id, alias_map_json, updated_at)
                                VALUES (:user_id, :alias_map_json::jsonb, NOW())
                                ON CONFLICT (user_id) DO UPDATE
                                  SET alias_map_json = EXCLUDED.alias_map_json,
                                      updated_at = EXCLUDED.updated_at
                            """), {
                                "user_id": user_id, 
                                "alias_map_json": json.dumps(data.get("concept_alias_map_updated", []))
                            })
                            logger.info(f"✅ Concept alias map upserted successfully")
                        except Exception as alias_error:
                            logger.error(f"❌ Concept alias map upsert failed: {alias_error}")
                            raise alias_error
                else:
                    logger.info(f"⚠️ No meaningful LLM analysis performed - skipping database persistence")
                    logger.info(f"   Session can be processed later when LLM is available")

                db.commit()
                
                telemetry.emit("summarizer_ok", {
                    "user_id": user_id, "session_id": session_id, "sess_seq": sess_seq,
                    "llm_model_used": data.get("telemetry", {}).get("llm_model_used", "unknown")
                })
                
                logger.info(f"✅ Summarizer completed for user {user_id[:8]} ({elapsed_time:.2f}s, ~{tokens_used} tokens)")
                return data
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Summarizer failed for user {user_id[:8]}: {e}")
                return self._generate_empty_summary()
                
        finally:
            db.close()
    
    def _build_summarizer_payload_from_attempts(self, user_id: str, attempts: List) -> Dict[str, Any]:
        """Build payload for summarizer LLM call from attempt records"""
        # Format attempt history
        attempt_history = []
        for attempt in attempts:
            # Parse core concepts
            try:
                if isinstance(attempt.core_concepts, list):
                    concepts = attempt.core_concepts
                elif isinstance(attempt.core_concepts, str):
                    concepts = json.loads(attempt.core_concepts)
                else:
                    concepts = []
            except:
                concepts = []
            
            attempt_history.append({
                "question_id": attempt.question_id,
                "was_correct": attempt.was_correct,
                "skipped": attempt.skipped,
                "response_time_ms": attempt.response_time_ms,
                "sess_seq": attempt.sess_seq_at_serve,
                "difficulty_band": attempt.difficulty_band,
                "pair": f"{attempt.subcategory}:{attempt.type_of_question}",
                "core_concepts": concepts,
                "pyq_frequency_score": float(attempt.pyq_frequency_score) if attempt.pyq_frequency_score else 0.5
            })
        
        # Get existing concept alias map (if any)
        existing_aliases = self._get_existing_concept_aliases(user_id)
        
        return {
            "user_id": user_id,
            "attempt_history": attempt_history,
            "existing_concept_aliases": existing_aliases,
            "analysis_instructions": {
                "focus_areas": [
                    "Identify recurring concept patterns",
                    "Assess confidence levels by difficulty band",
                    "Detect avoidance behaviors (skipping patterns)",
                    "Evaluate concept coverage gaps"
                ]
            }
        }
    
    def _get_existing_concept_aliases(self, user_id: str) -> List[Dict[str, Any]]:
        """Get existing concept alias mappings for the user"""
        db = SessionLocal()
        try:
            # Check if we have any existing alias mappings
            aliases = db.execute(text("""
                SELECT alias_map_json
                FROM concept_alias_map_latest
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT 1
            """), {"user_id": user_id}).fetchone()
            
            if aliases and aliases.alias_map_json:
                try:
                    return json.loads(aliases.alias_map_json) if isinstance(aliases.alias_map_json, str) else aliases.alias_map_json
                except:
                    return []
            return []
            
        except Exception as e:
            logger.warning(f"Could not load existing aliases for user {user_id[:8]}: {e}")
            return []
        finally:
            db.close()
    
    def _generate_empty_summary(self) -> Dict[str, Any]:
        """Generate empty summary when no meaningful analysis can be performed"""
        return {
            "concept_alias_map_updated": [],
            "dominance_by_item": {},
            "concept_readiness_labels": [],
            "pair_coverage_labels": [],
            "notes": "No attempt history available for analysis",
            "telemetry": {
                "processing_time_ms": 0,
                "estimated_tokens": 0,
                "llm_model_used": "none",
                "alias_reuse_rate": 0.0,
                "provisional_new_count": 0
            }
        }
    
    def _calculate_alias_reuse_rate(self, data: Dict[str, Any]) -> float:
        """Calculate the rate of alias reuse vs new concept creation"""
        concept_map = data.get("concept_alias_map_updated", [])
        if not concept_map:
            return 0.0
        
        reused_count = sum(1 for concept in concept_map if not concept.get("provisional", False))
        total_count = len(concept_map)
        
        return reused_count / total_count if total_count > 0 else 0.0
    
    def _count_provisional_concepts(self, data: Dict[str, Any]) -> int:
        """Count the number of provisional (new) concepts created"""
        concept_map = data.get("concept_alias_map_updated", [])
        return sum(1 for concept in concept_map if concept.get("provisional", False))
    
# Global instance
summarizer_service = SummarizerService()

# Legacy wrapper for compatibility
async def run_summarizer(user_id: str, session_id: str) -> Dict[str, Any]:
    """Legacy wrapper for the summarizer run method"""
    return await summarizer_service.run(user_id=user_id, session_id=session_id)