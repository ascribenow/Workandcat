#!/usr/bin/env python3
"""
Enhanced PYQ Enrichment Service
Comprehensive LLM-based enrichment for PYQ questions with difficulty assessment and concept extraction
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedPYQEnrichmentService:
    """
    Complete PYQ enrichment service with:
    1. Difficulty assessment with retry logic
    2. Deep concept extraction for matching
    3. Quality validation for reliability
    4. Full integration with database constraints
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.error("OpenAI API key not found for EnhancedPYQEnrichmentService")
    
    async def full_pyq_enrichment(self, pyq_question) -> Dict[str, Any]:
        """
        Complete PYQ enrichment pipeline with all missing components
        """
        try:
            logger.info(f"🚀 Starting full PYQ enrichment for question {pyq_question.id}")
            
            enrichment_results = {
                "success": False,
                "question_id": str(pyq_question.id),
                "steps_completed": [],
                "errors": []
            }
            
            # STEP 1: Difficulty Assessment with Retry Logic
            logger.info(f"📊 STEP 1: Difficulty assessment for PYQ {pyq_question.id}")
            difficulty_result = await self._assess_pyq_difficulty_with_retry(pyq_question)
            
            if difficulty_result["success"]:
                pyq_question.difficulty_band = difficulty_result["difficulty_band"]
                pyq_question.difficulty_score = self._convert_difficulty_band_to_score(difficulty_result["difficulty_band"])
                enrichment_results["steps_completed"].append("difficulty_assessment")
                logger.info(f"✅ Difficulty assessment: {difficulty_result['difficulty_band']}")
            else:
                enrichment_results["errors"].append(f"Difficulty assessment failed: {difficulty_result['error']}")
                logger.error(f"❌ Difficulty assessment failed")
            
            # STEP 2: Deep Concept Extraction
            logger.info(f"🧠 STEP 2: Deep concept extraction for PYQ {pyq_question.id}")
            concepts_result = await self._extract_deep_concepts(pyq_question)
            
            if concepts_result["success"]:
                pyq_question.core_concepts = json.dumps(concepts_result["core_concepts"])
                pyq_question.solution_method = concepts_result["solution_method"]
                pyq_question.concept_difficulty = json.dumps(concepts_result["complexity_indicators"])
                pyq_question.operations_required = json.dumps(concepts_result["operations"])
                pyq_question.problem_structure = concepts_result["structure_type"]
                pyq_question.concept_keywords = json.dumps(concepts_result["concept_keywords"])
                enrichment_results["steps_completed"].append("concept_extraction")
                logger.info(f"✅ Concepts extracted: {len(concepts_result['core_concepts'])} concepts")
            else:
                enrichment_results["errors"].append(f"Concept extraction failed: {concepts_result['error']}")
                logger.error(f"❌ Concept extraction failed")
            
            # STEP 3: Quality Validation
            logger.info(f"🔍 STEP 3: Quality validation for PYQ {pyq_question.id}")
            quality_result = await self._validate_pyq_quality(pyq_question)
            
            if quality_result["success"]:
                pyq_question.quality_verified = quality_result["quality_verified"]
                enrichment_results["steps_completed"].append("quality_validation")
                logger.info(f"✅ Quality validation: {quality_result['quality_score']}/100")
            else:
                enrichment_results["errors"].append(f"Quality validation failed: {quality_result['error']}")
                logger.error(f"❌ Quality validation failed")
            
            # STEP 4: Final Status Update
            if len(enrichment_results["steps_completed"]) >= 2:  # At least difficulty + concepts
                pyq_question.concept_extraction_status = 'completed'
                pyq_question.is_active = True
                pyq_question.last_updated = datetime.utcnow()
                enrichment_results["success"] = True
                logger.info(f"🎉 Full PYQ enrichment completed successfully for question {pyq_question.id}")
            else:
                pyq_question.concept_extraction_status = 'failed'
                pyq_question.is_active = False
                enrichment_results["success"] = False
                logger.error(f"💥 PYQ enrichment failed - insufficient successful steps")
            
            return enrichment_results
            
        except Exception as e:
            logger.error(f"❌ Full PYQ enrichment failed with exception: {e}")
            pyq_question.concept_extraction_status = 'failed'
            pyq_question.is_active = False
            return {
                "success": False,
                "error": str(e),
                "question_id": str(pyq_question.id)
            }
    
    async def _assess_pyq_difficulty_with_retry(self, pyq_question) -> Dict[str, Any]:
        """
        Assess PYQ difficulty using same enhanced retry logic as regular questions
        """
        max_retries = 3
        retry_delays = [2, 5, 10]
        
        for attempt in range(max_retries):
            try:
                import openai
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                system_message = """You are an expert in CAT quantitative ability difficulty assessment for PYQ questions.
Analyze this historical CAT question and determine its difficulty level based on:
- Conceptual complexity required
- Number of calculation steps
- Problem-solving approach sophistication
- Time pressure considerations for CAT exam

Difficulty Levels:
- Easy: Basic concepts, straightforward calculations, single-step problems
- Medium: Multiple concepts, moderate calculations, 2-3 step problems
- Hard: Advanced concepts, complex calculations, multi-step reasoning requiring sophisticated approach

Return ONLY one word: Easy, Medium, or Hard"""

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"PYQ Question: {pyq_question.stem}\nAnswer: {pyq_question.answer}"}
                    ],
                    max_tokens=50,
                    temperature=0.1
                )
                
                difficulty = response.choices[0].message.content.strip()
                
                if difficulty.lower() in ['easy', 'medium', 'hard']:
                    difficulty = difficulty.capitalize()
                    logger.info(f"✅ PYQ difficulty assessed: {difficulty} (attempt {attempt + 1})")
                    return {
                        "success": True,
                        "difficulty_band": difficulty,
                        "attempts": attempt + 1
                    }
                else:
                    raise ValueError(f"Invalid LLM difficulty response: {difficulty}")
                    
            except Exception as e:
                logger.warning(f"⚠️ PYQ difficulty assessment attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"❌ All {max_retries} PYQ difficulty assessment attempts failed")
                    return {
                        "success": False,
                        "error": f"PYQ difficulty assessment failed after {max_retries} attempts: {e}"
                    }
    
    async def _extract_deep_concepts(self, pyq_question) -> Dict[str, Any]:
        """
        Extract deep mathematical concepts from PYQ questions for conceptual matching
        """
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            concept_prompt = f"""Analyze this CAT PYQ question and extract precise mathematical concepts for pattern matching:

Question: {pyq_question.stem}
Answer: {pyq_question.answer}
Subcategory: {pyq_question.subcategory}

Extract the following for advanced conceptual matching:

1. Core Mathematical Concepts: Specific mathematical ideas, not generic topic names
   Examples: "relative_speed", "compound_interest_formula", "triangle_similarity", "ratio_proportion"

2. Solution Methodology: Primary approach required to solve
   Examples: "substitution_method", "unitary_method", "algebraic_manipulation", "geometric_construction"

3. Mathematical Operations: Specific operations involved
   Examples: ["multiplication", "division", "square_root", "percentage_calculation"]

4. Problem Structure Type: Overall structure pattern
   Examples: "word_problem_single_entity", "comparison_problem", "optimization_problem", "sequence_problem"

5. Complexity Indicators: What makes this problem challenging
   Examples: ["multiple_variables", "indirect_relationships", "time_dependency", "conditional_logic"]

6. Searchable Keywords: Key terms for matching
   Examples: ["speed", "distance", "overtake", "meeting_point", "relative_motion"]

Return as JSON with exact keys: core_concepts, solution_method, operations, structure_type, complexity_indicators, concept_keywords"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert mathematical concept analyzer for CAT questions. Extract precise, searchable concepts for pattern matching."},
                    {"role": "user", "content": concept_prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            concept_text = response.choices[0].message.content.strip()
            
            try:
                concepts_data = json.loads(concept_text)
                
                # Validate required fields
                required_fields = ["core_concepts", "solution_method", "operations", "structure_type", "complexity_indicators", "concept_keywords"]
                for field in required_fields:
                    if field not in concepts_data:
                        concepts_data[field] = [] if field != "solution_method" and field != "structure_type" else "general_approach"
                
                logger.info(f"✅ Concepts extracted successfully: {len(concepts_data['core_concepts'])} core concepts")
                return {
                    "success": True,
                    **concepts_data
                }
                
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Could not parse concept JSON, using fallback extraction")
                return await self._fallback_concept_extraction(pyq_question)
                
        except Exception as e:
            logger.error(f"❌ Deep concept extraction failed: {e}")
            return await self._fallback_concept_extraction(pyq_question)
    
    async def _fallback_concept_extraction(self, pyq_question) -> Dict[str, Any]:
        """
        Fallback concept extraction using keyword analysis
        """
        try:
            stem_lower = pyq_question.stem.lower()
            subcategory = pyq_question.subcategory.lower()
            
            # Enhanced keyword mapping for mathematical concepts
            concept_mappings = {
                'time_speed_distance': {
                    'keywords': ['speed', 'distance', 'time', 'train', 'car', 'travel', 'meet', 'overtake'],
                    'core_concepts': ['relative_speed', 'distance_formula', 'time_calculation'],
                    'solution_method': 'speed_distance_analysis',
                    'operations': ['division', 'multiplication', 'subtraction'],
                    'structure_type': 'motion_problem'
                },
                'percentage': {
                    'keywords': ['percent', '%', 'increase', 'decrease', 'change'],
                    'core_concepts': ['percentage_calculation', 'proportional_change'],
                    'solution_method': 'percentage_formula',
                    'operations': ['multiplication', 'division', 'percentage'],
                    'structure_type': 'percentage_problem'
                },
                'profit_loss': {
                    'keywords': ['profit', 'loss', 'cost', 'selling', 'discount', 'markup'],
                    'core_concepts': ['cost_price_analysis', 'profit_margin', 'discount_calculation'],
                    'solution_method': 'commercial_mathematics',
                    'operations': ['subtraction', 'percentage', 'ratio'],
                    'structure_type': 'business_problem'
                }
            }
            
            # Find matching concept category
            matched_category = None
            for category, data in concept_mappings.items():
                if any(keyword in stem_lower for keyword in data['keywords']) or category in subcategory:
                    matched_category = data
                    break
            
            if matched_category:
                return {
                    "success": True,
                    "core_concepts": matched_category['core_concepts'],
                    "solution_method": matched_category['solution_method'],
                    "operations": matched_category['operations'],
                    "structure_type": matched_category['structure_type'],
                    "complexity_indicators": ["standard_approach"],
                    "concept_keywords": matched_category['keywords'][:5]
                }
            else:
                # Generic fallback
                return {
                    "success": True,
                    "core_concepts": ["mathematical_problem"],
                    "solution_method": "general_approach",
                    "operations": ["calculation"],
                    "structure_type": "standard_problem",
                    "complexity_indicators": ["basic"],
                    "concept_keywords": ["mathematics"]
                }
                
        except Exception as e:
            logger.error(f"❌ Fallback concept extraction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _validate_pyq_quality(self, pyq_question) -> Dict[str, Any]:
        """
        Validate PYQ question quality for reliability in frequency analysis
        """
        try:
            quality_score = 50  # Base score
            
            # Question completeness (30 points)
            if len(pyq_question.stem.strip()) > 20:
                quality_score += 15
            if len(pyq_question.stem.strip()) > 50:
                quality_score += 15
            
            # Answer quality (25 points)
            if pyq_question.answer and pyq_question.answer != "To be generated by LLM":
                quality_score += 25
            
            # Subcategory classification (25 points)
            if pyq_question.subcategory and pyq_question.subcategory != "To be classified by LLM":
                quality_score += 25
            
            # No obvious errors (20 points)
            if not any(error_phrase in pyq_question.stem.lower() for error_phrase in ['error', 'mistake', 'unclear', 'invalid']):
                quality_score += 20
            
            quality_verified = quality_score >= 75
            
            return {
                "success": True,
                "quality_score": min(100, quality_score),
                "quality_verified": quality_verified,
                "quality_threshold": 75
            }
            
        except Exception as e:
            logger.error(f"❌ PYQ quality validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "quality_verified": False
            }
    
    def _convert_difficulty_band_to_score(self, difficulty_band: str) -> float:
        """
        Convert difficulty band to numeric score for analysis
        """
        conversion_map = {
            "Easy": 1.5,
            "Medium": 3.0,
            "Hard": 4.5
        }
        return conversion_map.get(difficulty_band, 3.0)  # Default to Medium

# Utility functions for integration
async def enhance_single_pyq(pyq_question_id: str):
    """
    Utility function to enhance a single PYQ question
    """
    try:
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            from database import PYQQuestion
            pyq_question = db.query(PYQQuestion).filter(PYQQuestion.id == pyq_question_id).first()
            
            if not pyq_question:
                logger.error(f"PYQ Question {pyq_question_id} not found")
                return False
            
            enhancer = EnhancedPYQEnrichmentService()
            result = await enhancer.full_pyq_enrichment(pyq_question)
            
            db.commit()
            return result["success"]
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error enhancing single PYQ: {e}")
        return False

if __name__ == "__main__":
    # Test the service
    import asyncio
    
    async def test_enhancement():
        enhancer = EnhancedPYQEnrichmentService()
        print("✅ Enhanced PYQ Enrichment Service initialized successfully")
    
    asyncio.run(test_enhancement())