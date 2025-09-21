"""
Coverage Summarizer Service
LLM service that processes session attempts and updates the Learner Notebook
Runs exactly once per session after 12 attempts with OpenAI primary + Gemini fallback
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from util.llm_guarded import call_llm_json_with_retry
from services.learner_notebook import learner_notebook_service

load_dotenv()

logger = logging.getLogger(__name__)

SUMMARIZER_SYSTEM_PROMPT = """
You are Twelvr Summarizer.
Update a Learner Notebook using ONLY labels already present in the attempts' anchors (do not invent new labels; merge obvious synonyms into an existing label if present).
Apply the status rule EXACTLY:
- tot < 2 → moderate
- correct ≥ (incorrect + skipped) AND mh_correct ≥ 1 → strong
- (incorrect + skipped) > correct → weak
- else → moderate
Where mh_correct = number of correct answers on Medium or Hard difficulty.
Return JSON only in the schema.
"""

SUMMARIZER_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "status": {"type": "string", "enum": ["weak", "moderate", "strong"]},
                    "counts": {
                        "type": "object",
                        "properties": {
                            "correct": {"type": "integer"},
                            "incorrect": {"type": "integer"},
                            "skipped": {"type": "integer"},
                            "mh_correct": {"type": "integer"}
                        },
                        "required": ["correct", "incorrect", "skipped", "mh_correct"]
                    }
                },
                "required": ["label", "status", "counts"]
            }
        },
        "notes": {"type": "string"}
    },
    "required": ["skills", "notes"]
}

class CoverageSummarizer:
    """
    LLM-powered service that analyzes session attempts and updates Learner Notebook
    Uses OpenAI GPT-4o-mini primary with Gemini fallback
    """
    
    def __init__(self):
        self.notebook_service = learner_notebook_service
    
    async def summarize_session(self, user_id: str, sess_seq: int, attempts: List[Dict]) -> Dict:
        """
        Post-session analysis with notebook backup
        Exactly one call per session after 12 attempts
        
        Args:
            user_id: User identifier
            sess_seq: Session sequence number  
            attempts: List of attempt records with anchors, difficulty, correctness
            
        Returns:
            Updated notebook data or error info
        """
        start_time = time.time()
        
        try:
            logger.info(f"🧠 Starting Coverage Summarizer for user {user_id[:8]}, sess_seq {sess_seq}")
            logger.info(f"📊 Processing {len(attempts)} attempts")
            
            # Get current notebook before update
            notebook_before = await self.notebook_service.read_or_default(user_id)
            logger.debug(f"📖 Current notebook has {len(notebook_before.get('skills', []))} skills")
            
            # Prepare payload for LLM
            payload = self._build_summarizer_payload(user_id, sess_seq, attempts, notebook_before)
            
            # Run LLM summarizer with OpenAI primary + Gemini fallback
            response = call_llm_json_with_retry(
                system_prompt=SUMMARIZER_SYSTEM_PROMPT,
                user_payload=payload,
                schema=SUMMARIZER_SCHEMA,
                model_primary="gpt-4o-mini",      # OpenAI primary
                model_fallback="gemini-1.5-pro", # Gemini fallback
                max_retries=1,
                timeout_ms=15000
            )
            
            # Validate and clean response
            notebook_after = self._validate_and_clean_response(response, notebook_before)
            
            # Update notebook with backup to session_summary_llm
            update_success = await self.notebook_service.update_notebook_with_backup(
                user_id, sess_seq, notebook_before, notebook_after
            )
            
            if not update_success:
                logger.error(f"❌ Failed to update notebook for user {user_id[:8]}")
                raise Exception("Notebook update failed")
            
            # Calculate telemetry
            elapsed_time = time.time() - start_time
            
            # Add telemetry to response
            notebook_after.setdefault("telemetry", {}).update({
                "processing_time_ms": int(elapsed_time * 1000),
                "llm_model_used": "gpt-4o-mini",  # Track primary model usage
                "session_processed": sess_seq,
                "attempts_analyzed": len(attempts),
                "skills_updated": len(notebook_after.get("skills", [])),
                "notebook_version": "coverage_v1"
            })
            
            logger.info(f"✅ Coverage Summarizer completed for user {user_id[:8]} ({elapsed_time:.2f}s)")
            logger.info(f"📈 Updated {len(notebook_after.get('skills', []))} skills")
            
            return notebook_after
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Coverage Summarizer failed for user {user_id[:8]} after {elapsed_time:.2f}s: {e}")
            
            # Return safe fallback - keep existing notebook
            fallback_notebook = await self.notebook_service.read_or_default(user_id)
            fallback_notebook["telemetry"] = {
                "processing_time_ms": int(elapsed_time * 1000),
                "llm_model_used": "fallback",
                "error": str(e),
                "session_processed": sess_seq,
                "attempts_analyzed": len(attempts)
            }
            
            return fallback_notebook
    
    def _build_summarizer_payload(self, user_id: str, sess_seq: int, attempts: List[Dict], 
                                current_notebook: Dict) -> Dict[str, Any]:
        """
        Build payload for LLM summarizer
        
        Args:
            user_id: User identifier
            sess_seq: Session sequence number
            attempts: List of attempt records
            current_notebook: Current notebook state
            
        Returns:
            Payload dictionary for LLM
        """
        # Extract all anchor labels from attempts for vocabulary constraint
        anchor_vocabulary = set()
        formatted_attempts = []
        
        for attempt in attempts:
            # Parse anchors from attempt (should be from served pack snapshot)
            anchors = attempt.get('anchors', [])
            if isinstance(anchors, str):
                try:
                    anchors = json.loads(anchors)
                except:
                    anchors = []
            
            # Add to vocabulary
            for anchor in anchors:
                if anchor and isinstance(anchor, str):
                    anchor_vocabulary.add(anchor.lower())
            
            # Format attempt for LLM
            formatted_attempts.append({
                "question_id": attempt.get('question_id', 'unknown'),
                "was_correct": attempt.get('was_correct', False),
                "skipped": attempt.get('skipped', False),
                "difficulty_band": attempt.get('difficulty_band', 'medium'),
                "anchors": anchors,
                "subcategory": attempt.get('subcategory', 'Unknown'),
                "type_of_question": attempt.get('type_of_question', 'Unknown')
            })
        
        return {
            "user_id": user_id[-8:],  # Last 8 chars for privacy
            "sess_seq": sess_seq,
            "attempts": formatted_attempts,
            "current_notebook": current_notebook,
            "anchor_vocabulary": sorted(list(anchor_vocabulary)),
            "analysis_instructions": {
                "vocabulary_constraint": "Use ONLY labels from anchor_vocabulary - do not invent new labels",
                "status_rules": {
                    "weak": "(incorrect + skipped) > correct",
                    "strong": "correct ≥ (incorrect + skipped) AND mh_correct ≥ 1", 
                    "moderate": "default case or tot < 2"
                },
                "merge_guidance": "Merge obvious synonyms into existing labels when possible"
            }
        }
    
    def _validate_and_clean_response(self, response: Dict, notebook_before: Dict) -> Dict:
        """
        Validate LLM response and apply safety constraints
        
        Args:
            response: Raw LLM response
            notebook_before: Previous notebook state
            
        Returns:
            Cleaned and validated notebook data
        """
        # Ensure required fields exist
        skills = response.get("skills", [])
        notes = response.get("notes", "Updated by Coverage Summarizer")
        
        # Validate each skill
        validated_skills = []
        for skill in skills:
            if not isinstance(skill, dict):
                continue
                
            label = skill.get("label", "").strip().lower()
            status = skill.get("status", "moderate")
            counts = skill.get("counts", {})
            
            # Validate label
            if not label or len(label) < 2:
                continue
            
            # Validate status
            if status not in ["weak", "moderate", "strong"]:
                status = "moderate"
            
            # Validate counts
            validated_counts = {
                "correct": max(0, counts.get("correct", 0)),
                "incorrect": max(0, counts.get("incorrect", 0)),
                "skipped": max(0, counts.get("skipped", 0)),
                "mh_correct": max(0, counts.get("mh_correct", 0))
            }
            
            validated_skills.append({
                "label": label,
                "status": status,
                "counts": validated_counts
            })
        
        # Remove duplicates (keep first occurrence)
        seen_labels = set()
        deduped_skills = []
        for skill in validated_skills:
            if skill["label"] not in seen_labels:
                seen_labels.add(skill["label"])
                deduped_skills.append(skill)
        
        return {
            "skills": deduped_skills,
            "notes": notes[:500]  # Truncate notes if too long
        }

# Global instance
coverage_summarizer = CoverageSummarizer()

# Test function
async def test_coverage_summarizer():
    """Test the coverage summarizer service"""
    print("🧪 Testing Coverage Summarizer Service...")
    
    # Get a real user ID
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    cur.execute('SELECT id FROM users LIMIT 1')
    real_user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not real_user:
        print("❌ No users found for testing")
        return
    
    user_id = real_user[0]
    
    # Mock attempt data
    sample_attempts = [
        {
            "question_id": "q1",
            "was_correct": True,
            "skipped": False,
            "difficulty_band": "medium",
            "anchors": ["relative speed"],
            "subcategory": "Time-Speed-Distance",
            "type_of_question": "Application"
        },
        {
            "question_id": "q2", 
            "was_correct": False,
            "skipped": False,
            "difficulty_band": "hard",
            "anchors": ["relative speed"],
            "subcategory": "Time-Speed-Distance",
            "type_of_question": "Complex"
        },
        {
            "question_id": "q3",
            "was_correct": True,
            "skipped": False,
            "difficulty_band": "easy",
            "anchors": ["ratio scaling"],
            "subcategory": "Ratios",
            "type_of_question": "Basic"
        }
    ]
    
    # Test summarizer
    result = await coverage_summarizer.summarize_session(user_id, 998, sample_attempts)
    print(f"✅ Summarizer result: {result}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_coverage_summarizer())