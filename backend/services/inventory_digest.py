"""
Inventory Digest Service
Builds a summary of eligible questions grouped by skill view and difficulty band
Provides statistics for Coverage Planner LLM
"""

import asyncio
import json
import logging
import psycopg2
from typing import Dict, List, Set
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class InventoryDigestService:
    """
    Service that builds inventory digest for Coverage Planner
    Summarizes eligible questions by skill anchors and difficulty bands
    """
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def build_digest(self, user_id: str, notebook: Dict) -> Dict:
        """
        Build inventory digest over eligible questions with skill view mapping
        
        Args:
            user_id: User identifier (for served count tracking)
            notebook: Current learner notebook with skill statuses
            
        Returns:
            Inventory digest with question statistics by skill and difficulty
        """
        try:
            logger.info(f"📊 Building inventory digest for user {user_id[:8]}")
            
            # Get eligible questions with null safety
            eligible_questions = await self._get_eligible_questions()
            logger.info(f"📋 Found {len(eligible_questions)} eligible questions")
            
            # Extract skill sets from notebook
            skill_sets = self._extract_skill_sets_from_notebook(notebook)
            logger.debug(f"🎯 Skill sets: weak={len(skill_sets['weak'])}, moderate={len(skill_sets['moderate'])}, strong={len(skill_sets['strong'])}")
            
            # Tag questions with skill view membership
            tagged_questions = self._tag_questions_with_skill_views(eligible_questions, skill_sets)
            
            # Build digest statistics
            digest = self._build_digest_statistics(tagged_questions, skill_sets)
            
            # Add metadata
            digest["metadata"] = {
                "user_id": user_id[-8:],
                "total_eligible": len(eligible_questions),
                "notebook_skills": len(notebook.get("skills", [])),
                "digest_timestamp": "NOW()",
                "skill_distribution": {
                    "weak_skills": len(skill_sets["weak"]),
                    "moderate_skills": len(skill_sets["moderate"]),
                    "strong_skills": len(skill_sets["strong"])
                }
            }
            
            logger.info(f"✅ Inventory digest built successfully")
            return digest
            
        except Exception as e:
            logger.error(f"❌ Failed to build inventory digest for user {user_id[:8]}: {e}")
            return self._generate_empty_digest(user_id, str(e))
    
    async def _get_eligible_questions(self) -> List[Dict]:
        """
        Get all eligible questions with null safety and optimized query
        Uses the eligibility index created in migrations
        
        Returns:
            List of eligible question dictionaries
        """
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Null-safe query using the eligibility index
            cur.execute("""
                SELECT id, anchors, difficulty_band, subcategory, type_of_question,
                       pyq_frequency_score, core_concepts, operations_required
                FROM questions
                WHERE is_active = TRUE 
                AND quality_verified = TRUE 
                AND difficulty_band IS NOT NULL
                AND anchors IS NOT NULL 
                AND anchors != '[]'::jsonb
                ORDER BY pyq_frequency_score DESC, id
            """)
            
            results = cur.fetchall()
            cur.close()
            conn.close()
            
            # Convert to dictionaries with null safety
            questions = []
            for row in results:
                try:
                    # Parse anchors with safety
                    anchors = row[1]
                    if isinstance(anchors, str):
                        anchors = json.loads(anchors)
                    if not isinstance(anchors, list):
                        anchors = []
                    
                    # Parse core_concepts with safety
                    core_concepts = row[6]
                    if isinstance(core_concepts, str):
                        core_concepts = json.loads(core_concepts)
                    if not isinstance(core_concepts, list):
                        core_concepts = []
                    
                    # Parse operations_required with safety
                    operations_required = row[7]
                    if isinstance(operations_required, str):
                        operations_required = json.loads(operations_required)
                    if not isinstance(operations_required, list):
                        operations_required = []
                    
                    questions.append({
                        "id": row[0],
                        "anchors": anchors,
                        "difficulty_band": row[2].lower() if row[2] else 'medium',
                        "subcategory": row[3] or 'Unknown',
                        "type_of_question": row[4] or 'Unknown',
                        "pyq_frequency_score": float(row[5]) if row[5] else 0.0,
                        "core_concepts": core_concepts,
                        "operations_required": operations_required
                    })
                except Exception as parse_error:
                    logger.warning(f"Failed to parse question {row[0]}: {parse_error}")
                    continue
            
            return questions
            
        except Exception as e:
            logger.error(f"Failed to get eligible questions: {e}")
            return []
    
    def _extract_skill_sets_from_notebook(self, notebook: Dict) -> Dict[str, Set[str]]:
        """
        Extract weak/moderate/strong skill sets from notebook
        
        Args:
            notebook: Learner notebook dictionary
            
        Returns:
            Dictionary with skill sets by status
        """
        skill_sets = {"weak": set(), "moderate": set(), "strong": set()}
        
        for skill in notebook.get("skills", []):
            label = skill.get("label", "").strip().lower()
            status = skill.get("status", "moderate")
            
            if label and status in skill_sets:
                skill_sets[status].add(label)
        
        return skill_sets
    
    def _tag_questions_with_skill_views(self, questions: List[Dict], skill_sets: Dict[str, Set[str]]) -> List[Dict]:
        """
        Tag questions with skill view membership (multi-label allowed)
        
        Args:
            questions: List of eligible questions
            skill_sets: Skill sets by status from notebook
            
        Returns:
            Questions tagged with view membership
        """
        tagged_questions = []
        
        for question in questions:
            question_anchors = set(anchor.lower() for anchor in question.get("anchors", []))
            
            # Tag with view membership (multi-label allowed)
            question["hits_weak"] = bool(question_anchors & skill_sets["weak"])
            question["hits_moderate"] = bool(question_anchors & skill_sets["moderate"])
            question["hits_strong"] = bool(question_anchors & skill_sets["strong"])
            
            # If no hits and empty notebook, everything hits moderate (first session behavior)
            if not any([question["hits_weak"], question["hits_moderate"], question["hits_strong"]]):
                if not any(skill_sets.values()):  # Empty notebook
                    question["hits_moderate"] = True
                    logger.debug("Empty notebook detected - treating all questions as moderate")
            
            tagged_questions.append(question)
        
        return tagged_questions
    
    def _build_digest_statistics(self, tagged_questions: List[Dict], skill_sets: Dict[str, Set[str]]) -> Dict:
        """
        Build statistical digest for Coverage Planner
        
        Args:
            tagged_questions: Questions tagged with skill view membership
            skill_sets: Skill sets by status
            
        Returns:
            Statistical digest dictionary
        """
        digest = {
            "skill_views": {},
            "difficulty_bands": {},
            "pyq_statistics": {},
            "skill_coverage": {}
        }
        
        # Initialize band counters
        for band in ["easy", "medium", "hard"]:
            digest["difficulty_bands"][band] = {
                "total": 0,
                "weak_eligible": 0,
                "moderate_eligible": 0,
                "strong_eligible": 0,
                "pyq_count": 0
            }
        
        # Process each question
        for question in tagged_questions:
            band = question["difficulty_band"]
            pyq_score = question.get("pyq_frequency_score", 0.0)
            
            # Update band statistics
            if band in digest["difficulty_bands"]:
                digest["difficulty_bands"][band]["total"] += 1
                
                if question.get("hits_weak"):
                    digest["difficulty_bands"][band]["weak_eligible"] += 1
                if question.get("hits_moderate"):
                    digest["difficulty_bands"][band]["moderate_eligible"] += 1
                if question.get("hits_strong"):
                    digest["difficulty_bands"][band]["strong_eligible"] += 1
                
                if pyq_score >= 1.0:
                    digest["difficulty_bands"][band]["pyq_count"] += 1
        
        # Build skill view statistics
        for view_name in ["weak", "moderate", "strong"]:
            view_questions = [q for q in tagged_questions if q.get(f"hits_{view_name}")]
            
            digest["skill_views"][view_name] = {
                "total_questions": len(view_questions),
                "skills_in_view": list(skill_sets[view_name]),
                "difficulty_breakdown": {
                    "easy": len([q for q in view_questions if q["difficulty_band"] == "easy"]),
                    "medium": len([q for q in view_questions if q["difficulty_band"] == "medium"]),
                    "hard": len([q for q in view_questions if q["difficulty_band"] == "hard"])
                },
                "pyq_breakdown": {
                    "high_pyq": len([q for q in view_questions if q.get("pyq_frequency_score", 0) >= 1.5]),
                    "med_pyq": len([q for q in view_questions if 1.0 <= q.get("pyq_frequency_score", 0) < 1.5]),
                    "low_pyq": len([q for q in view_questions if q.get("pyq_frequency_score", 0) < 1.0])
                }
            }
        
        # Overall PYQ statistics
        all_pyq_scores = [q.get("pyq_frequency_score", 0.0) for q in tagged_questions]
        digest["pyq_statistics"] = {
            "total_questions": len(tagged_questions),
            "high_pyq_count": len([s for s in all_pyq_scores if s >= 1.5]),
            "med_pyq_count": len([s for s in all_pyq_scores if 1.0 <= s < 1.5]),
            "low_pyq_count": len([s for s in all_pyq_scores if s < 1.0]),
            "avg_pyq_score": sum(all_pyq_scores) / len(all_pyq_scores) if all_pyq_scores else 0.0
        }
        
        return digest
    
    def _generate_empty_digest(self, user_id: str, error_msg: str) -> Dict:
        """Generate safe empty digest on error"""
        return {
            "skill_views": {
                "weak": {"total_questions": 0, "skills_in_view": [], "difficulty_breakdown": {"easy": 0, "medium": 0, "hard": 0}},
                "moderate": {"total_questions": 0, "skills_in_view": [], "difficulty_breakdown": {"easy": 0, "medium": 0, "hard": 0}},
                "strong": {"total_questions": 0, "skills_in_view": [], "difficulty_breakdown": {"easy": 0, "medium": 0, "hard": 0}}
            },
            "difficulty_bands": {
                "easy": {"total": 0, "weak_eligible": 0, "moderate_eligible": 0, "strong_eligible": 0, "pyq_count": 0},
                "medium": {"total": 0, "weak_eligible": 0, "moderate_eligible": 0, "strong_eligible": 0, "pyq_count": 0},
                "hard": {"total": 0, "weak_eligible": 0, "moderate_eligible": 0, "strong_eligible": 0, "pyq_count": 0}
            },
            "pyq_statistics": {"total_questions": 0, "high_pyq_count": 0, "med_pyq_count": 0, "low_pyq_count": 0, "avg_pyq_score": 0.0},
            "metadata": {"user_id": user_id[-8:], "error": error_msg, "total_eligible": 0}
        }

# Global instance
inventory_digest_service = InventoryDigestService()

# Test function
async def test_inventory_digest_service():
    """Test the inventory digest service"""
    print("🧪 Testing Inventory Digest Service...")
    
    # Test with sample notebook
    sample_notebook = {
        "skills": [
            {"label": "relative speed", "status": "weak"},
            {"label": "ratio scaling", "status": "moderate"},
            {"label": "unit conversion", "status": "strong"}
        ],
        "notes": "Sample notebook for testing"
    }
    
    # Test digest generation
    digest = await inventory_digest_service.build_digest("test_user_123", sample_notebook)
    
    print(f"📊 Digest metadata: {digest.get('metadata', {})}")
    print(f"🎯 Skill views: {list(digest.get('skill_views', {}).keys())}")
    print(f"📋 Difficulty bands: {list(digest.get('difficulty_bands', {}).keys())}")
    
    # Show sample statistics
    for view_name, view_data in digest.get("skill_views", {}).items():
        total_q = view_data.get("total_questions", 0)
        skills = view_data.get("skills_in_view", [])
        print(f"   {view_name}: {total_q} questions, skills: {skills}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_inventory_digest_service())