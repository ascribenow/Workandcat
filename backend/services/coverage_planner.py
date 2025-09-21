"""
Coverage Planner Service
LLM service that generates Selection Recipes based on Learner Notebook and Inventory Digest
Uses OpenAI GPT-4o-mini primary with Gemini fallback and structured fallback recipe
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
import os
from dotenv import load_dotenv
from util.llm_guarded import call_llm_json_with_retry

load_dotenv()

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """
Plan a 12-item Coverage session:
• Buckets: Easy=3 from Weak, Medium=6 from Moderate, Hard=3 from Strong.
• If a bucket is short, borrow in this order:
  Easy ← Moderate ← Strong
  Medium ← Weak ← Strong  
  Hard ← Moderate ← Weak
• Aim best-effort for ≥2 items with pyq=1.5 and ≥2 items with pyq=1.0.
• For each bucket, list 2–3 priority skill phrases chosen ONLY from the notebook labels.
Return JSON only in the schema.
"""

PLANNER_SCHEMA = {
    "type": "object",
    "properties": {
        "easy": {
            "type": "object",
            "properties": {
                "priority_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3
                }
            },
            "required": ["priority_skills"]
        },
        "medium": {
            "type": "object", 
            "properties": {
                "priority_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 3
                }
            },
            "required": ["priority_skills"]
        },
        "hard": {
            "type": "object",
            "properties": {
                "priority_skills": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "maxItems": 3
                }
            },
            "required": ["priority_skills"]
        },
        "borrow_order": {
            "type": "object",
            "properties": {
                "easy": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["moderate", "strong"]},
                    "maxItems": 2
                },
                "medium": {
                    "type": "array", 
                    "items": {"type": "string", "enum": ["weak", "strong"]},
                    "maxItems": 2
                },
                "hard": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["moderate", "weak"]}, 
                    "maxItems": 2
                }
            },
            "required": ["easy", "medium", "hard"]
        },
        "pyq_intent": {
            "type": "object",
            "properties": {
                "need_pyq_1_5": {"type": "integer", "minimum": 0, "maximum": 12},
                "need_pyq_1_0": {"type": "integer", "minimum": 0, "maximum": 12}
            },
            "required": ["need_pyq_1_5", "need_pyq_1_0"]
        }
    },
    "required": ["easy", "medium", "hard", "borrow_order", "pyq_intent"]
}

# EXACT default recipe when LLM fails after 1 retry
DEFAULT_RECIPE = {
    "easy": {"priority_skills": []},
    "medium": {"priority_skills": []},
    "hard": {"priority_skills": []},
    "borrow_order": {
        "easy": ["moderate", "strong"],
        "medium": ["weak", "strong"],
        "hard": ["moderate", "weak"]
    },
    "pyq_intent": {"need_pyq_1_5": 2, "need_pyq_1_0": 2}
}

class CoveragePlanner:
    """
    LLM-powered service that generates selection recipes for Coverage Selector
    Uses OpenAI GPT-4o-mini primary with Gemini fallback
    """
    
    def __init__(self):
        pass
    
    async def create_selection_recipe(self, notebook: Dict, digest: Dict) -> Dict:
        """
        Generate selection recipe with fallback to default
        
        Args:
            notebook: Learner notebook with skill statuses
            digest: Inventory digest with question statistics
            
        Returns:
            Selection recipe dictionary or default recipe on failure
        """
        start_time = time.time()
        
        try:
            logger.info("🎯 Coverage Planner generating selection recipe...")
            
            # Prepare payload for LLM
            payload = self._build_planner_payload(notebook, digest)
            logger.debug(f"📋 Payload includes {len(payload.get('available_skills', []))} available skills")
            
            # Use existing LLM infrastructure with OpenAI primary + Gemini fallback
            response = call_llm_json_with_retry(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_payload=payload,
                schema=PLANNER_SCHEMA,
                model_primary="gpt-4o-mini",      # OpenAI primary
                model_fallback="gemini-1.5-pro", # Gemini fallback  
                max_retries=1,
                timeout_ms=15000
            )
            
            # Validate and clean response
            recipe = self._validate_and_clean_recipe(response, notebook)
            
            # Add telemetry
            elapsed_time = time.time() - start_time
            recipe["telemetry"] = {
                "processing_time_ms": int(elapsed_time * 1000),
                "llm_model_used": "gpt-4o-mini",
                "notebook_skills": len(notebook.get("skills", [])),
                "recipe_type": "llm_generated"
            }
            
            logger.info(f"✅ Coverage Planner completed ({elapsed_time:.2f}s)")
            return recipe
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.warning(f"⚠️ Coverage Planner LLM failed after retry, using default recipe: {e}")
            
            # Return default recipe (still coverage_v1, not legacy fallback)
            default_recipe = DEFAULT_RECIPE.copy()
            default_recipe["telemetry"] = {
                "processing_time_ms": int(elapsed_time * 1000),
                "llm_model_used": "default_fallback",
                "error": str(e),
                "recipe_type": "default_fallback"
            }
            
            return default_recipe
    
    def _build_planner_payload(self, notebook: Dict, digest: Dict) -> Dict[str, Any]:
        """
        Build payload for Coverage Planner LLM
        
        Args:
            notebook: Learner notebook
            digest: Inventory digest
            
        Returns:
            Payload dictionary for LLM
        """
        # Extract available skills from notebook
        available_skills = []
        skill_status_map = {}
        
        for skill in notebook.get("skills", []):
            label = skill.get("label", "").strip()
            status = skill.get("status", "moderate")
            
            if label:
                available_skills.append(label)
                skill_status_map[label] = status
        
        # Extract digest statistics
        skill_views = digest.get("skill_views", {})
        difficulty_bands = digest.get("difficulty_bands", {})
        pyq_stats = digest.get("pyq_statistics", {})
        
        return {
            "learner_notebook": {
                "skills": notebook.get("skills", []),
                "skill_count_by_status": {
                    "weak": len([s for s in notebook.get("skills", []) if s.get("status") == "weak"]),
                    "moderate": len([s for s in notebook.get("skills", []) if s.get("status") == "moderate"]),
                    "strong": len([s for s in notebook.get("skills", []) if s.get("status") == "strong"])
                }
            },
            "inventory_digest": {
                "total_eligible_questions": digest.get("metadata", {}).get("total_eligible", 0),
                "skill_view_availability": {
                    "weak_questions": skill_views.get("weak", {}).get("total_questions", 0),
                    "moderate_questions": skill_views.get("moderate", {}).get("total_questions", 0),
                    "strong_questions": skill_views.get("strong", {}).get("total_questions", 0)
                },
                "difficulty_availability": {
                    "easy_total": difficulty_bands.get("easy", {}).get("total", 0),
                    "medium_total": difficulty_bands.get("medium", {}).get("total", 0),
                    "hard_total": difficulty_bands.get("hard", {}).get("total", 0)
                },
                "pyq_availability": {
                    "high_pyq_count": pyq_stats.get("high_pyq_count", 0),
                    "med_pyq_count": pyq_stats.get("med_pyq_count", 0),
                    "total_pyq_viable": pyq_stats.get("high_pyq_count", 0) + pyq_stats.get("med_pyq_count", 0)
                }
            },
            "available_skills": available_skills,
            "constraints": {
                "total_questions_needed": 12,
                "difficulty_distribution": {"easy": 3, "medium": 6, "hard": 3},
                "pyq_targets": {"min_pyq_1_5": 2, "min_pyq_1_0": 2}
            },
            "instructions": {
                "skill_vocabulary": "Use ONLY skills from available_skills - do not invent new ones",
                "priority_guidance": "Select 2-3 priority skills per difficulty band based on learner needs",
                "borrowing_rules": "Follow the exact borrow order specified in system prompt"
            }
        }
    
    def _validate_and_clean_recipe(self, response: Dict, notebook: Dict) -> Dict:
        """
        Validate LLM response and apply safety constraints
        
        Args:
            response: Raw LLM response
            notebook: Original notebook for skill validation
            
        Returns:
            Cleaned and validated recipe
        """
        # Get available skills from notebook for validation
        available_skills = set()
        for skill in notebook.get("skills", []):
            label = skill.get("label", "").strip().lower()
            if label:
                available_skills.add(label)
        
        # Validate each difficulty band
        validated_recipe = {}
        
        for band in ["easy", "medium", "hard"]:
            band_data = response.get(band, {})
            priority_skills = band_data.get("priority_skills", [])
            
            # Validate and filter skills
            validated_skills = []
            for skill in priority_skills[:3]:  # Max 3 skills
                skill_normalized = skill.strip().lower()
                if skill_normalized in available_skills:
                    validated_skills.append(skill_normalized)
            
            validated_recipe[band] = {"priority_skills": validated_skills}
        
        # Validate borrow order
        borrow_order = response.get("borrow_order", {})
        validated_borrow = {
            "easy": ["moderate", "strong"],  # Default safe values
            "medium": ["weak", "strong"],
            "hard": ["moderate", "weak"]
        }
        
        # Override with LLM response if valid
        for band in ["easy", "medium", "hard"]:
            if band in borrow_order and isinstance(borrow_order[band], list):
                validated_borrow[band] = borrow_order[band][:2]  # Max 2 borrow sources
        
        validated_recipe["borrow_order"] = validated_borrow
        
        # Validate PYQ intent
        pyq_intent = response.get("pyq_intent", {})
        validated_recipe["pyq_intent"] = {
            "need_pyq_1_5": min(max(pyq_intent.get("need_pyq_1_5", 2), 0), 12),
            "need_pyq_1_0": min(max(pyq_intent.get("need_pyq_1_0", 2), 0), 12)
        }
        
        return validated_recipe

# Global instance
coverage_planner = CoveragePlanner()

# Test function
async def test_coverage_planner():
    """Test the coverage planner service"""
    print("🧪 Testing Coverage Planner Service...")
    
    # Sample notebook and digest
    sample_notebook = {
        "skills": [
            {"label": "relative speed", "status": "weak"},
            {"label": "ratio scaling", "status": "moderate"},
            {"label": "unit conversion", "status": "strong"}
        ],
        "notes": "Sample notebook"
    }
    
    sample_digest = {
        "skill_views": {
            "weak": {"total_questions": 100, "skills_in_view": ["relative speed"]},
            "moderate": {"total_questions": 200, "skills_in_view": ["ratio scaling"]},
            "strong": {"total_questions": 50, "skills_in_view": ["unit conversion"]}
        },
        "difficulty_bands": {
            "easy": {"total": 100, "pyq_count": 20},
            "medium": {"total": 200, "pyq_count": 60},
            "hard": {"total": 100, "pyq_count": 40}
        },
        "pyq_statistics": {"high_pyq_count": 50, "med_pyq_count": 70, "total_questions": 400},
        "metadata": {"total_eligible": 400}
    }
    
    # Test planner
    recipe = await coverage_planner.create_selection_recipe(sample_notebook, sample_digest)
    
    print(f"📋 Generated recipe:")
    print(f"   Easy skills: {recipe.get('easy', {}).get('priority_skills', [])}")
    print(f"   Medium skills: {recipe.get('medium', {}).get('priority_skills', [])}")
    print(f"   Hard skills: {recipe.get('hard', {}).get('priority_skills', [])}")
    print(f"   PYQ intent: {recipe.get('pyq_intent', {})}")
    print(f"   Telemetry: {recipe.get('telemetry', {})}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_coverage_planner())