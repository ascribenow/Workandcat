#!/usr/bin/env python3
"""
Regular Questions Enrichment Service
Specialized enrichment service for Questions table - using same logic as PYQ enrichment
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List
import openai
import google.generativeai as genai
from datetime import datetime
from sqlalchemy import and_
from canonical_taxonomy_service import canonical_taxonomy_service
from anthropic_semantic_validator import anthropic_semantic_validator
from llm_utils import call_llm_with_fallback, extract_json_from_response, calculate_pyq_frequency_score_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RegularQuestionsEnrichmentService:
    """
    Specialized enrichment service for regular questions table
    Uses SAME LOGIC as PYQ enrichment for consistency
    """
    
    def __init__(self):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize OpenAI client
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.error("❌ OpenAI API key not found")
            raise ValueError("OPENAI_API_KEY environment variable required")
        
        # Initialize Google Gemini client (fallback)
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)
            logger.info("✅ Google Gemini configured as fallback")
        else:
            logger.warning("⚠️ Google API key not found - no Gemini fallback available")
        
        logger.info(f"✅ OpenAI API key loaded successfully ({len(self.openai_api_key)} chars)")
        
        self.max_retries = 4
        self.retry_delays = [3, 7, 15, 30]
        self.timeout = 60
        
        # Model configuration with fallback
        self.primary_model = "gpt-4o"
        self.fallback_model = "gpt-4o-mini"
        self.gemini_model = "gemini-pro"
        self.current_model = self.primary_model
        self.last_rate_limit_time = None
        self.rate_limit_recovery_interval = 1800  # 30 minutes
        
        # Model degradation tracking
        self.primary_model_failures = 0
        self.max_failures_before_degradation = 3
        self.openai_consecutive_failures = 0
        self.max_openai_failures_before_gemini = 2
        
        logger.info("✅ RegularQuestionsEnrichmentService initialized with OpenAI + Gemini fallback")
    
    async def enrich_regular_question(self, stem: str, current_answer: str = None) -> Dict[str, Any]:
        """
        Generate comprehensive enrichment analysis for regular questions
        SAME LOGIC AS PYQ ENRICHMENT for consistency
        
        Args:
            stem: Question text
            current_answer: Current answer (from CSV)
            
        Returns:
            Dict with enrichment data for questions table
        """
        try:
            logger.info(f"🧠 Starting CONSOLIDATED regular question enrichment analysis...")
            logger.info(f"📚 Question: {stem[:100]}...")
            
            # CONSOLIDATED LLM CALL (same as PYQ)
            logger.info("🎯 Performing consolidated LLM enrichment (stages 1-4)...")
            enrichment_result = await self._consolidated_llm_enrichment(stem, current_answer)
            
            if not enrichment_result["success"]:
                logger.error(f"❌ Consolidated enrichment failed: {enrichment_result.get('error')}")
                return enrichment_result
            
            enrichment_data = enrichment_result["enrichment_data"]
            
            # QUALITY VERIFICATION (same as PYQ)
            logger.info("🔍 Performing quality verification...")
            quality_result = await self._perform_quality_verification(stem, enrichment_data)
            enrichment_data.update(quality_result)
            
            # NEW: LLM-BASED PYQ FREQUENCY CALCULATION
            logger.info("📊 Calculating PYQ frequency score using LLM...")
            pyq_frequency_result = await self._calculate_pyq_frequency_score_llm(stem, enrichment_data)
            enrichment_data['pyq_frequency_score'] = pyq_frequency_result
            
            enrichment_data['concept_extraction_status'] = 'completed'
            
            logger.info(f"✨ Regular question enrichment completed successfully")
            logger.info(f"📊 Generated enrichment for all required fields")
            
            return {
                "success": True,
                "enrichment_data": enrichment_data,
                "processing_time": "consolidated_analysis"
            }
            
        except Exception as e:
            logger.error(f"❌ Regular question enrichment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "enrichment_data": {}
            }
    
    async def _consolidated_llm_enrichment(self, stem: str, current_answer: str = None) -> Dict[str, Any]:
        """
        Consolidated LLM enrichment call (stages 1-4 combined)
        SAME LOGIC AS PYQ ENRICHMENT
        """
        
        system_message = """You are a world-class mathematics professor and CAT expert with deep expertise in quantitative reasoning.

Your task is to perform COMPREHENSIVE enrichment analysis of this regular question in a single comprehensive response.

COMPREHENSIVE ANALYSIS REQUIRED:

1. ENHANCED ANSWER ANALYSIS:
   - Provide detailed step-by-step mathematical reasoning
   - If current answer provided, enhance with comprehensive explanation
   - If no answer, calculate precise answer with mathematical logic

2. SOPHISTICATED CLASSIFICATION:
   - Determine precise category (main mathematical domain)
   - Identify specific subcategory (precise mathematical area)
   - Classify exact type_of_question (specific question archetype)

3. DIFFICULTY ASSESSMENT:
   - Assess complexity using multiple dimensions
   - Determine difficulty band (Easy/Medium/Hard)
   - Provide numerical difficulty score (1.0-5.0)

4. CONCEPTUAL EXTRACTION:
   - Extract core mathematical concepts
   - Identify solution methodology
   - Analyze operations required
   - Determine problem structure
   - Generate concept keywords

Return ONLY this JSON format:
{
  "right_answer": "enhanced detailed answer with step-by-step reasoning",
  "category": "main category",
  "subcategory": "specific subcategory",
  "type_of_question": "specific question archetype",
  "difficulty_band": "Easy/Medium/Hard",
  "difficulty_score": 3.2,
  "core_concepts": ["concept1", "concept2", "concept3"],
  "solution_method": "precise methodological approach",
  "concept_difficulty": {"prerequisites": ["req1"], "cognitive_barriers": ["barrier1"], "mastery_indicators": ["indicator1"]},
  "operations_required": ["operation1", "operation2"],
  "problem_structure": "structural_analysis_type",
  "concept_keywords": ["keyword1", "keyword2"]
}

Be precise, comprehensive, and demonstrate superior mathematical intelligence."""

        user_message = f"Regular Question: {stem}\nCurrent answer (if any): {current_answer or 'Not provided'}"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🧠 Calling LLM for consolidated enrichment (attempt {attempt + 1})...")
                
                enrichment_text, model_used = await call_llm_with_fallback(
                    self, system_message, user_message, max_tokens=1200, temperature=0.1
                )
                
                if not enrichment_text:
                    raise Exception("LLM returned empty response")
                
                # Extract JSON using helper function
                clean_json = extract_json_from_response(enrichment_text)
                enrichment_data = json.loads(clean_json)
                
                # Apply enhanced semantic matching (SAME AS PYQ)
                logger.info("🎯 Applying enhanced semantic matching...")
                canonical_category, canonical_subcategory, canonical_type = await canonical_taxonomy_service.get_canonical_taxonomy_path(
                    enrichment_data.get('category', ''),
                    enrichment_data.get('subcategory', ''),
                    enrichment_data.get('type_of_question', '')
                )
                
                # Update with canonical values
                enrichment_data['category'] = canonical_category
                enrichment_data['subcategory'] = canonical_subcategory  
                enrichment_data['type_of_question'] = canonical_type
                
                # Convert complex fields to JSON strings for database storage
                enrichment_data['core_concepts'] = json.dumps(enrichment_data.get('core_concepts', []))
                enrichment_data['concept_difficulty'] = json.dumps(enrichment_data.get('concept_difficulty', {}))
                enrichment_data['operations_required'] = json.dumps(enrichment_data.get('operations_required', []))
                enrichment_data['concept_keywords'] = json.dumps(enrichment_data.get('concept_keywords', []))
                
                # Validate and clean difficulty data
                difficulty_band = enrichment_data.get('difficulty_band', 'Medium').capitalize()
                if difficulty_band not in ['Easy', 'Medium', 'Hard']:
                    difficulty_band = 'Medium'
                enrichment_data['difficulty_band'] = difficulty_band
                
                difficulty_score = float(enrichment_data.get('difficulty_score', 2.5))
                if not (1.0 <= difficulty_score <= 5.0):
                    difficulty_score = 2.5
                enrichment_data['difficulty_score'] = difficulty_score
                
                logger.info(f"✅ Consolidated enrichment completed with {model_used}")
                logger.info(f"🎯 Taxonomy: {canonical_category} → {canonical_subcategory} → {canonical_type}")
                logger.info(f"⚖️ Difficulty: {difficulty_band} ({difficulty_score})")
                
                return {
                    "success": True,
                    "enrichment_data": enrichment_data
                }
                
            except Exception as e:
                logger.error(f"⚠️ Consolidated enrichment attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying consolidated enrichment in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All consolidated enrichment attempts failed")
                    return {
                        "success": False,
                        "error": "Consolidated enrichment failed after all retries",
                        "enrichment_data": {}
                    }
    
    async def _calculate_pyq_frequency_score_llm(self, stem: str, enrichment_data: Dict[str, Any]) -> float:
        """
        Calculate PYQ frequency score using LLM-based semantic comparison
        Filters PYQ questions by: difficulty_score > 1.5 AND category×subcategory match
        """
        try:
            from database import get_async_compatible_db, PYQQuestion
            from sqlalchemy import select
            import json
            
            # Get category and subcategory from enrichment data
            category = enrichment_data.get('category', '')
            subcategory = enrichment_data.get('subcategory', '')
            
            logger.info(f"🔍 Getting qualifying PYQ questions for category='{category}', subcategory='{subcategory}'")
            
            # Get async database session  
            db_gen = get_async_compatible_db()
            db = await db_gen.__anext__()
            try:
                # Get qualifying PYQ questions from database with improved filtering
                result = await db.execute(
                    select(PYQQuestion).where(
                        and_(
                            PYQQuestion.difficulty_score > 1.5,
                            PYQQuestion.category == category,              # NEW: Category match
                            PYQQuestion.subcategory == subcategory,        # NEW: Subcategory match
                            PYQQuestion.is_active == True,
                            PYQQuestion.quality_verified == True,
                            PYQQuestion.problem_structure.isnot(None),
                            PYQQuestion.concept_keywords.isnot(None)
                        )
                    )
                )
                qualifying_pyqs = result.scalars().all()
                
                if not qualifying_pyqs:
                    logger.warning(f"⚠️ No qualifying PYQ questions found for category='{category}', subcategory='{subcategory}' with difficulty_score > 1.5")
                    return 0.5  # Default to LOW
                
                logger.info(f"📊 Found {len(qualifying_pyqs)} category×subcategory filtered PYQ questions")
                
                # Prepare regular question data (now includes category×subcategory)
                regular_question_data = {
                    'stem': stem,
                    'category': category,
                    'subcategory': subcategory,
                    'problem_structure': enrichment_data.get('problem_structure', ''),
                    'concept_keywords': enrichment_data.get('concept_keywords', '[]')
                }
                
                # Prepare PYQ questions data
                pyq_questions_data = []
                for pyq in qualifying_pyqs:
                    pyq_data = {
                        'stem': pyq.stem,
                        'problem_structure': pyq.problem_structure or '',
                        'concept_keywords': pyq.concept_keywords or '[]'
                    }
                    pyq_questions_data.append(pyq_data)
                
                # Call LLM-based calculation with ALL filtered questions (no scaling)
                pyq_frequency_score = await calculate_pyq_frequency_score_llm(
                    self, regular_question_data, pyq_questions_data
                )
                
                logger.info(f"✅ PYQ frequency score calculated: {pyq_frequency_score}")
                logger.info(f"🎯 Processed {len(qualifying_pyqs)} questions with raw matching (no scaling)")
                return pyq_frequency_score
                
            finally:
                await db.aclose()
                
        except Exception as e:
            logger.error(f"❌ PYQ frequency calculation failed: {e}")
            return 0.5  # Default to LOW on error

    async def _perform_quality_verification(self, stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform quality verification
        SAME LOGIC AS PYQ ENRICHMENT
        """
        
        try:
            logger.info("🔍 Enhanced quality verification (Semantic + Binary)")
            
            # Check required fields are present and meaningful
            required_fields = [
                'right_answer', 'category', 'subcategory', 'type_of_question', 
                'difficulty_band', 'core_concepts', 'solution_method'
            ]
            
            missing_fields = []
            for field in required_fields:
                value = enrichment_data.get(field)
                if not value or value in ['To be classified by LLM', 'N/A', '', 'null']:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.error(f"❌ Quality verification failed - missing/invalid fields: {missing_fields}")
                return {'quality_verified': False}
            
            # Check for meaningful content (not just placeholders)
            if len(enrichment_data.get('right_answer', '')) < 10:
                logger.error(f"❌ Quality verification failed - answer too short")
                return {'quality_verified': False}
                
            logger.info("✅ Quality verification passed - all required fields present with meaningful content")
            return {'quality_verified': True}
            
        except Exception as e:
            logger.error(f"❌ Quality verification exception: {e}")
            return {
                'quality_verified': False
            }

# Global instance
regular_questions_enrichment_service = RegularQuestionsEnrichmentService()