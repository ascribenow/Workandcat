"""
Coverage Pipeline Service
Orchestrates the entire session planning flow using the new coverage services
Main entry point for generating coverage-based sessions
"""

import asyncio
import json
import logging
import time
from typing import Dict, List
import psycopg2
import os
from dotenv import load_dotenv
from services.learner_notebook import learner_notebook_service
from services.inventory_digest import inventory_digest_service 
from services.coverage_planner import coverage_planner
from services.coverage_selector import coverage_selector

load_dotenv()

logger = logging.getLogger(__name__)

class CoveragePipeline:
    """
    Main orchestrator for coverage-based session planning
    Single pipeline (coverage_v1) with no legacy fallbacks
    """
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Initialize all coverage services
        self.notebook_service = learner_notebook_service
        self.digest_service = inventory_digest_service
        self.planner = coverage_planner
        self.selector = coverage_selector
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def plan_next_session(self, user_id: str, session_id: str) -> Dict:
        """
        Single pipeline - coverage_v1 only (no fallbacks)
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Complete session plan with pack and audit data
        """
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Coverage Pipeline starting for user {user_id[:8]}, session {session_id[:8]}")
            
            # 1. Get current notebook (or default)
            step1_start = time.time()
            notebook = await self.notebook_service.read_or_default(user_id)
            step1_time = int((time.time() - step1_start) * 1000)
            logger.info(f"📖 Notebook loaded: {len(notebook.get('skills', []))} skills ({step1_time}ms)")
            
            # 2. Build inventory digest over eligible questions
            step2_start = time.time()
            digest = await self.digest_service.build_digest(user_id, notebook)
            step2_time = int((time.time() - step2_start) * 1000)
            logger.info(f"📊 Digest built: {digest.get('metadata', {}).get('total_eligible', 0)} eligible questions ({step2_time}ms)")
            
            # 3. Get selection recipe from planner
            step3_start = time.time()
            recipe = await self.planner.create_selection_recipe(notebook, digest)
            step3_time = int((time.time() - step3_start) * 1000)
            planner_model = recipe.get("telemetry", {}).get("llm_model_used", "unknown")
            logger.info(f"🎯 Recipe generated: {planner_model} ({step3_time}ms)")
            
            # 4. Deterministic selection
            step4_start = time.time()
            pack, audit = await self.selector.select_pack(user_id, session_id, notebook, recipe)
            step4_time = int((time.time() - step4_start) * 1000)
            logger.info(f"📦 Pack selected: {len(pack)} questions ({step4_time}ms)")
            
            # 5. Normalize pack to use canonical 'id' field for questions
            normalized_pack = self._normalize_pack_question_ids(pack)
            
            # 6. Save pack with create-or-update (proper upsert)
            save_success = await self._save_pack_to_pack_json(user_id, session_id, normalized_pack, audit)
            
            # Calculate total time
            total_time = int((time.time() - start_time) * 1000)
            
            # Build response with comprehensive telemetry
            response = {
                "pack": normalized_pack,
                "audit": audit,
                "processing_time_ms": total_time,
                "pipeline_telemetry": {
                    "notebook_load_ms": step1_time,
                    "digest_build_ms": step2_time, 
                    "planner_ms": step3_time,
                    "selector_ms": step4_time,
                    "total_ms": total_time,
                    "planner_model": planner_model,
                    "save_success": save_success,
                    "pipeline_version": "coverage_v1"
                },
                "session_metadata": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "notebook_skills": len(notebook.get("skills", [])),
                    "eligible_questions": digest.get("metadata", {}).get("total_eligible", 0)
                }
            }
            
            # Emit coverage telemetry
            try:
                from services.telemetry import telemetry_service
                telemetry_service.emit_coverage_session_metrics(user_id, response)
            except Exception as telemetry_error:
                logger.warning(f"⚠️ Failed to emit coverage telemetry: {telemetry_error}")
            
            logger.info(f"✅ Coverage Pipeline completed ({total_time}ms)")
            return response
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"❌ Coverage Pipeline failed for user {user_id[:8]} after {total_time}ms: {e}")
            
            # Return error response
            return {
                "pack": [],
                "audit": {"error": str(e), "shape": {"easy": 0, "medium": 0, "hard": 0}, "pyq": {}},
                "processing_time_ms": total_time,
                "pipeline_telemetry": {
                    "total_ms": total_time,
                    "error": str(e),
                    "pipeline_version": "coverage_v1"
                }
            }
    
    def _normalize_pack_question_ids(self, pack: List[Dict]) -> List[Dict]:
        """Canonicalize question id and add 1..N position for UI/reporting."""
        normalized = []
        for idx, item in enumerate(pack, start=1):
            it = item.copy()

            # Canonical id only
            if 'item_id' in it:
                if 'id' not in it:
                    it['id'] = it.pop('item_id')
                else:
                    it.pop('item_id')

            # NEW: explicit 1..12 position (avoid reserved 'order')
            it['position'] = idx

            normalized.append(it)
        return normalized
    
    async def _save_pack_to_pack_json(self, user_id: str, session_id: str, pack: List[Dict], audit: Dict) -> bool:
        """Create-or-update pack row using unique constraint"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO session_pack_plan (session_id, user_id, pack_json, coverage_audit, selection_method, status)
                VALUES (%s, %s, %s, %s, 'coverage_v1', 'planned')
                ON CONFLICT (session_id) DO UPDATE SET
                    pack_json = EXCLUDED.pack_json,
                    coverage_audit = EXCLUDED.coverage_audit,
                    selection_method = 'coverage_v1',
                    status = CASE WHEN session_pack_plan.status='served' THEN 'served' ELSE 'planned' END
            """, (session_id, user_id, json.dumps(pack), json.dumps(audit)))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"💾 Pack saved for session {session_id[:8]}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save pack for session {session_id[:8]}: {e}")
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            return False

# Global instance
coverage_pipeline = CoveragePipeline()

# Test function
async def test_coverage_pipeline():
    """Test the complete coverage pipeline"""
    print("🧪 Testing Complete Coverage Pipeline...")
    
    # Test with realistic user and session IDs
    import uuid
    test_user_id = str(uuid.uuid4())
    test_session_id = str(uuid.uuid4())
    
    # Get a real user ID for more realistic testing
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        cur.execute('SELECT id FROM users LIMIT 1')
        real_user = cur.fetchone()
        cur.close()
        conn.close()
        
        if real_user:
            test_user_id = real_user[0]
            logger.info(f"Using real user ID: {test_user_id[:8]}...")
    except:
        logger.warning("Could not get real user ID, using generated UUID")
    
    # Test complete pipeline
    result = await coverage_pipeline.plan_next_session(test_user_id, test_session_id)
    
    print(f"📦 Pipeline result:")
    print(f"   Pack size: {len(result.get('pack', []))}")
    print(f"   Processing time: {result.get('processing_time_ms', 0)}ms")
    print(f"   Audit: {result.get('audit', {})}")
    print(f"   Pipeline telemetry: {result.get('pipeline_telemetry', {})}")
    
    return len(result.get('pack', [])) > 0

if __name__ == "__main__":
    asyncio.run(test_coverage_pipeline())