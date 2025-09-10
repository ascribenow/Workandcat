#!/usr/bin/env python3
"""
PYQ Enrichment Service
Specialized enrichment service for PYQ Questions table (21 columns)
Replicates the advanced LLM enrichment process for PYQ questions
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List
import openai
import google.generativeai as genai
from datetime import datetime
from canonical_taxonomy_service import canonical_taxonomy_service
from anthropic_semantic_validator import anthropic_semantic_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_json_from_response(response_text: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks"""
    response_text = response_text.strip()
    
    # Handle JSON wrapped in markdown code blocks
    if "```json" in response_text:
        start_idx = response_text.find("```json") + 7
        end_idx = response_text.find("```", start_idx)
        if end_idx > start_idx:
            return response_text[start_idx:end_idx].strip()
    elif "```" in response_text:
        # Handle generic code blocks
        start_idx = response_text.find("```") + 3
        end_idx = response_text.find("```", start_idx)
        if end_idx > start_idx:
            return response_text[start_idx:end_idx].strip()
    
    # Return as-is if no code blocks found
    return response_text

async def call_llm_with_fallback(service_instance, system_message: str, user_message: str, max_tokens: int = 800, temperature: float = 0.1) -> tuple[str, str]:
    """
    Call LLM with fallback logic: OpenAI → Gemini
    Returns: (response_text, model_used)
    """
    # Try OpenAI first
    try:
        client = openai.OpenAI(api_key=service_instance.openai_api_key)
        
        # Try primary model first
        model_to_use = service_instance.primary_model
        if service_instance.primary_model_failures >= service_instance.max_failures_before_degradation:
            model_to_use = service_instance.fallback_model
            
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=service_instance.timeout
        )
        
        response_text = response.choices[0].message.content.strip()
        if response_text:
            # Reset failure count on success
            service_instance.openai_consecutive_failures = 0
            return response_text, f"openai-{model_to_use}"
        else:
            raise Exception("Empty response from OpenAI")
            
    except Exception as openai_error:
        logger.warning(f"⚠️ OpenAI failed: {str(openai_error)[:100]}...")
        service_instance.openai_consecutive_failures += 1
        
        # If OpenAI fails too many times, try Gemini
        if service_instance.openai_consecutive_failures >= service_instance.max_openai_failures_before_gemini:
            if service_instance.google_api_key:
                try:
                    logger.info("🔄 Falling back to Google Gemini...")
                    
                    # Initialize Gemini model
                    model = genai.GenerativeModel(service_instance.gemini_model)
                    
                    # Combine system and user messages for Gemini
                    combined_prompt = f"{system_message}\n\nUser Request: {user_message}"
                    
                    response = model.generate_content(
                        combined_prompt,
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature,
                        )
                    )
                    
                    response_text = response.text.strip()
                    if response_text:
                        logger.info("✅ Gemini fallback successful")
                        return response_text, f"gemini-{service_instance.gemini_model}"
                    else:
                        raise Exception("Empty response from Gemini")
                        
                except Exception as gemini_error:
                    logger.error(f"❌ Gemini fallback also failed: {str(gemini_error)[:100]}...")
                    raise Exception(f"Both OpenAI and Gemini failed. OpenAI: {str(openai_error)[:50]}, Gemini: {str(gemini_error)[:50]}")
            else:
                raise Exception(f"OpenAI failed and no Gemini fallback available: {str(openai_error)}")
        else:
            # Re-raise OpenAI error if we haven't hit the fallback threshold
            raise openai_error

class PYQEnrichmentService:
    """
    Specialized PYQ enrichment service for pyq_questions table
    Handles 21-column schema with focus on PYQ-specific enrichment
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
        
        logger.info("✅ PYQEnrichmentService initialized with OpenAI + Gemini fallback")
    
    async def enrich_pyq_question(self, stem: str, current_answer: str = None) -> Dict[str, Any]:
        """
        Generate sophisticated enrichment analysis for PYQ questions
        
        Args:
            stem: Question text
            current_answer: Current answer (may be placeholder)
            
        Returns:
            Dict with enrichment data for pyq_questions table (21 columns)
        """
        try:
            logger.info(f"🧠 Starting PYQ enrichment analysis...")
            logger.info(f"📚 Question: {stem[:100]}...")
            
            enrichment_data = {}
            
            # Stage 1-4: Single Comprehensive Analysis (CONSOLIDATED)
            logger.info("🚀 Stage 1-4: Comprehensive analysis (single LLM call)...")
            comprehensive_analysis = await self._perform_comprehensive_analysis(stem, current_answer)
            enrichment_data.update(comprehensive_analysis)
            
            # Stage 5: Semantic Matching + Quality Verification (SEPARATE)
            logger.info("🔍 Stage 5: Semantic matching + quality verification...")
            verification_result = await self._perform_semantic_matching_and_verification(stem, enrichment_data)
            enrichment_data.update(verification_result)
            
            enrichment_data['concept_extraction_status'] = 'completed'
            
            logger.info("✨ PYQ enrichment completed (EFFICIENT)")
            logger.info(f"📊 Generated {len(enrichment_data)} detailed fields")
            
            return {
                "success": True,
                "enrichment_data": enrichment_data,
                "processing_time": "efficient_analysis"
            }
            
        except Exception as e:
            logger.error(f"❌ PYQ enrichment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "enrichment_data": {}
            }
    
    async def _perform_comprehensive_analysis(self, stem: str, current_answer: str = None) -> Dict[str, Any]:
        """
        Stage 1-4 CONSOLIDATED: Single comprehensive LLM analysis
        FIELDS UPDATED: answer, category, subcategory, type_of_question, difficulty_band, difficulty_score, 
                       core_concepts, solution_method, concept_difficulty, operations_required, 
                       problem_structure, concept_keywords
        """
        
        system_message = """You are a world-class CAT mathematics expert with deep expertise in quantitative reasoning and educational assessment.

Your task is to perform a COMPREHENSIVE analysis of this PYQ question in ONE complete response.

COMPREHENSIVE ANALYSIS REQUIRED:

1. SOLVE THE PROBLEM:
   - Calculate the precise mathematical answer with step-by-step reasoning
   - Show clear mathematical logic and verify the answer

2. CLASSIFY THE QUESTION:
   - Category: Main mathematical domain
   - Subcategory: Specific mathematical area  
   - Type of Question: Very specific question archetype

3. SELF-ASSESS DIFFICULTY based on YOUR solving experience:
   - Conceptual Complexity: How many concepts did you integrate?
   - Computational Intensity: What algebra/transformations did you need?
   - Reasoning Depth: How many inference steps/branches did you use?
   
   Rate 1.0-5.0 using these anchors:
   • Easy (1.0–2.0): single concept, ≤2 clean steps, light arithmetic
   • Medium (2.1–3.5): 2 concepts OR 1 concept with nontrivial manipulation, 3–5 steps
   • Hard (3.6–5.0): synthesis of concepts OR non-obvious insight, ≥6 steps OR tricky algebra

4. EXTRACT CONCEPTS:
   - Core mathematical concepts involved
   - Solution methodology used
   - Required operations and problem structure
   - Key mathematical keywords

Return ONLY this JSON format:
{
  "answer": "precise answer with mathematical reasoning",
  "category": "mathematical domain",
  "subcategory": "specific area", 
  "type_of_question": "question archetype",
  "difficulty_band": "Easy/Medium/Hard",
  "difficulty_score": 3.2,
  "core_concepts": ["concept1", "concept2", "concept3"],
  "solution_method": "methodological approach",
  "concept_difficulty": {"prerequisites": ["req1"], "cognitive_barriers": ["barrier1"], "mastery_indicators": ["indicator1"]},
  "operations_required": ["operation1", "operation2"],
  "problem_structure": "structural_analysis_type",
  "concept_keywords": ["keyword1", "keyword2"]
}

Be precise, comprehensive, and demonstrate superior mathematical intelligence."""

        user_message = f"PYQ Question: {stem}\nCurrent answer (if any): {current_answer or 'Not provided'}"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🚀 Calling LLM for comprehensive analysis (attempt {attempt + 1})...")
                
                analysis_text, model_used = await call_llm_with_fallback(
                    self, system_message, user_message, max_tokens=1200, temperature=0.1
                )
                
                if not analysis_text:
                    raise Exception("LLM returned empty response")
                
                # Extract JSON using helper function
                clean_json = extract_json_from_response(analysis_text)
                analysis_data = json.loads(clean_json)
                
                # Validate and clean difficulty data
                band = analysis_data.get('difficulty_band', 'Medium').capitalize()
                if band not in ['Easy', 'Medium', 'Hard']:
                    band = 'Medium'
                
                score = float(analysis_data.get('difficulty_score', 2.5))
                if not (1.0 <= score <= 5.0):
                    score = 2.5
                
                analysis_data['difficulty_band'] = band
                analysis_data['difficulty_score'] = score
                
                # Convert complex fields to JSON strings for database storage
                analysis_data['core_concepts'] = json.dumps(analysis_data.get('core_concepts', []))
                analysis_data['concept_difficulty'] = json.dumps(analysis_data.get('concept_difficulty', {}))
                analysis_data['operations_required'] = json.dumps(analysis_data.get('operations_required', []))
                analysis_data['concept_keywords'] = json.dumps(analysis_data.get('concept_keywords', []))
                
                logger.info(f"✅ Comprehensive analysis completed with {model_used}")
                logger.info(f"📊 Difficulty: {band} ({score})")
                
                return analysis_data
                
            except Exception as e:
                logger.error(f"⚠️ Comprehensive analysis attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying comprehensive analysis in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All comprehensive analysis attempts failed")
                    raise Exception("Comprehensive analysis failed after all retries")
    
    async def _perform_sophisticated_classification(self, stem: str, deep_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Perform sophisticated classification
        FIELDS UPDATED: category, subcategory, type_of_question (through enhanced semantic matching)
        """
        
        system_message = """You are an expert in CAT quantitative taxonomy with deep understanding of mathematical classification.

Your task is to provide sophisticated, nuanced classification that goes beyond superficial categorization.

CLASSIFICATION DEPTH REQUIRED:

1. CATEGORY: Main mathematical domain
2. SUBCATEGORY: Precise mathematical area  
3. TYPE_OF_QUESTION: Very specific question archetype

Return ONLY this JSON:
{
  "category": "main category",
  "subcategory": "specific subcategory", 
  "type_of_question": "specific question archetype"
}

Be precise, specific, and demonstrate deep mathematical understanding."""

        user_message = f"PYQ Question: {stem}\nMathematical Analysis: {deep_analysis.get('answer', '')}"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🏛️ Calling LLM for sophisticated classification (attempt {attempt + 1})...")
                
                classification_text, model_used = await call_llm_with_fallback(
                    self, system_message, user_message, max_tokens=300, temperature=0.1
                )
                
                if not classification_text:
                    raise Exception("LLM returned empty response")
                
                clean_json = extract_json_from_response(classification_text)
                classification_data = json.loads(clean_json)
                
                # Apply enhanced semantic matching here (NEW FLOW)
                logger.info("🎯 Applying enhanced semantic matching...")
                canonical_category, canonical_subcategory, canonical_type = await canonical_taxonomy_service.get_canonical_taxonomy_path(
                    classification_data.get('category', ''),
                    classification_data.get('subcategory', ''),
                    classification_data.get('type_of_question', '')
                )
                
                # Update with canonical values
                classification_data['category'] = canonical_category
                classification_data['subcategory'] = canonical_subcategory  
                classification_data['type_of_question'] = canonical_type
                
                logger.info(f"✅ Sophisticated classification completed with {model_used}")
                return classification_data
                
            except Exception as e:
                logger.error(f"⚠️ Classification attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All classification attempts failed")
                    raise Exception("Sophisticated classification failed after all retries")
    
    async def _perform_nuanced_difficulty_assessment(self, stem: str, deep_analysis: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Perform nuanced difficulty assessment
        FIELDS UPDATED: difficulty_band, difficulty_score
        """
        
        system_message = """You are a CAT difficulty assessment expert with deep understanding of cognitive load and mathematical complexity.

Assess difficulty with sophisticated reasoning considering multiple dimensions:

NUANCED DIFFICULTY BANDS:

EASY (1.0-2.0):
- Single mathematical concept application
- Straightforward computational steps
- Can be solved in under 2 minutes

MEDIUM (2.1-3.5):
- Multiple concept integration required
- Moderate computational complexity
- Requires 2-4 minutes for average student

HARD (3.6-5.0):
- Complex concept synthesis
- High computational demand or elegant insight required
- Requires 4+ minutes and strong mathematical maturity

Return ONLY this JSON:
{
  "difficulty_band": "Easy/Medium/Hard",
  "difficulty_score": 3.2
}"""

        user_message = f"PYQ Question: {stem}\nMathematical Foundation: {deep_analysis.get('answer', '')}\nCategory: {classification.get('category', '')}"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"⚖️ Calling LLM for difficulty assessment (attempt {attempt + 1})...")
                
                difficulty_text, model_used = await call_llm_with_fallback(
                    self, system_message, user_message, max_tokens=400, temperature=0.1
                )
                
                if not difficulty_text:
                    raise Exception("LLM returned empty response")
                
                clean_json = extract_json_from_response(difficulty_text)
                difficulty_data = json.loads(clean_json)
                
                # Validate and clean data
                band = difficulty_data.get('difficulty_band', 'Medium').capitalize()
                if band not in ['Easy', 'Medium', 'Hard']:
                    band = 'Medium'
                
                score = float(difficulty_data.get('difficulty_score', 2.5))
                if not (1.0 <= score <= 5.0):
                    score = 2.5
                
                result = {
                    'difficulty_band': band,
                    'difficulty_score': score
                }
                
                logger.info(f"✅ Nuanced difficulty assessment: {band} ({score}) with {model_used}")
                return result
                
            except Exception as e:
                logger.error(f"⚠️ Difficulty assessment attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All difficulty assessment attempts failed")
                    raise Exception("Nuanced difficulty assessment failed after all retries")
    
    async def _perform_advanced_conceptual_extraction(self, stem: str, deep_analysis: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 4: Perform advanced conceptual extraction
        FIELDS UPDATED: core_concepts, solution_method, concept_difficulty, operations_required, problem_structure, concept_keywords
        """
        
        system_message = """You are a mathematical concept extraction expert with deep insight into learning patterns and cognitive structures.

Extract sophisticated conceptual information for adaptive learning systems.

Return ONLY this JSON format:
{
  "core_concepts": ["concept1", "concept2", "concept3"],
  "solution_method": "Precise methodological approach",
  "concept_difficulty": {"prerequisites": ["req1"], "cognitive_barriers": ["barrier1"], "mastery_indicators": ["indicator1"]},
  "operations_required": ["operation1", "operation2"],
  "problem_structure": "structural_analysis_type",
  "concept_keywords": ["keyword1", "keyword2"]
}"""

        user_message = f"PYQ Question: {stem}\nMathematical Foundation: {deep_analysis.get('answer', '')}\nCategory: {classification.get('category', '')}\nSubcategory: {classification.get('subcategory', '')}"
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🧬 Calling LLM for conceptual extraction (attempt {attempt + 1})...")
                
                concept_text, model_used = await call_llm_with_fallback(
                    self, system_message, user_message, max_tokens=600, temperature=0.1
                )
                
                if not concept_text:
                    raise Exception("LLM returned empty response")
                
                clean_json = extract_json_from_response(concept_text)
                concept_data = json.loads(clean_json)
                
                # Convert to database format (JSON strings)
                result = {
                    'core_concepts': json.dumps(concept_data.get('core_concepts', [])),
                    'solution_method': concept_data.get('solution_method', 'Advanced Mathematical Analysis'),
                    'concept_difficulty': json.dumps(concept_data.get('concept_difficulty', {})),
                    'operations_required': json.dumps(concept_data.get('operations_required', [])),
                    'problem_structure': concept_data.get('problem_structure', 'complex_analytical_structure'),
                    'concept_keywords': json.dumps(concept_data.get('concept_keywords', []))
                }
                
                logger.info(f"✅ Advanced conceptual extraction completed with {model_used}")
                return result
                
            except Exception as e:
                logger.error(f"⚠️ Conceptual extraction attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All conceptual extraction attempts failed")
                    raise Exception("Advanced conceptual extraction failed after all retries")
    
    async def _perform_comprehensive_quality_verification(self, stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 5: Perform comprehensive quality verification
        FIELDS UPDATED: quality_verified
        """
        
        try:
            logger.info("🔍 Step 5: Enhanced quality verification (Semantic + Binary)")
            
            # Use enhanced semantic + binary validation from advanced service
            from advanced_llm_enrichment_service import AdvancedLLMEnrichmentService
            temp_service = AdvancedLLMEnrichmentService()
            
            validation_result = await temp_service._verify_response_quality(
                enrichment_data, "quality_verification", stem
            )
            
            if validation_result.get("quality_verified", False):
                logger.info("✅ Enhanced quality verification passed")
                return {
                    'quality_verified': True
                }
            else:
                logger.error(f"❌ Enhanced quality verification failed")
                return {
                    'quality_verified': False
                }
            
        except Exception as e:
            logger.error(f"❌ Enhanced quality verification exception: {e}")
            return {
                'quality_verified': False
            }

# Global instance
pyq_enrichment_service = PYQEnrichmentService()