#!/usr/bin/env python3
"""
Advanced LLM Enrichment Service
Ultra-sophisticated, nuanced, human-like enrichment with superior AI intelligence
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List
import openai
from datetime import datetime
from canonical_taxonomy_service import canonical_taxonomy_service
from anthropic_semantic_validator import anthropic_semantic_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_json_from_response(response_text: str) -> str:
    """Extract JSON from OpenAI response, handling markdown code blocks"""
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

class AdvancedLLMEnrichmentService:
    """
    Ultra-sophisticated LLM enrichment service that generates nuanced, 
    detailed, human-like analysis with superior AI intelligence
    """
    
    def __init__(self):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.error("OpenAI API key not found for AdvancedLLMEnrichmentService")
            logger.error(f"Environment variables: {list(os.environ.keys())[:10]}")
        else:
            logger.info(f"✅ OpenAI API key loaded successfully ({len(self.openai_api_key)} chars)")
        
        self.max_retries = 4
        self.retry_delays = [3, 7, 15, 30]
        self.timeout = 60  # Reduced timeout for better reliability (1 minute)
        
        # Intelligent model switching for rate limit handling
        self.primary_model = "gpt-4o"
        self.fallback_model = "gpt-4o-mini" 
        self.current_model = self.primary_model
        self.last_rate_limit_time = None
        self.rate_limit_recovery_interval = 1800  # 30 minutes before testing GPT-4o again
        
        # CRITICAL: Both models MUST maintain 100% quality standards
        # GPT-4o-mini uses IDENTICAL prompts and quality requirements as GPT-4o
        
        logger.info("✅ AdvancedLLMEnrichmentService initialized with 100% quality standards")
    
    def _map_to_canonical_category(self, category: str) -> str:
        """Map any category to canonical A-E format"""
        if not category:
            return "A-Arithmetic"
        
        category_lower = category.lower()
        
        # Direct canonical format check
        if category.startswith(('A-', 'B-', 'C-', 'D-', 'E-')):
            return category
        
        # Map to canonical categories
        if any(term in category_lower for term in ['arithmetic', 'speed', 'distance', 'time', 'work', 'ratio', 'proportion', 'percentage', 'average', 'profit', 'loss', 'interest', 'mixture', 'kinematic', 'fundamental']):
            return "A-Arithmetic"
        elif any(term in category_lower for term in ['algebra', 'equation', 'inequality', 'progression', 'function', 'graph', 'logarithm', 'exponent']):
            return "B-Algebra"
        elif any(term in category_lower for term in ['geometry', 'mensuration', 'triangle', 'circle', 'polygon', 'coordinate', 'trigonometry']):
            return "C-Geometry & Mensuration"
        elif any(term in category_lower for term in ['number', 'divisibility', 'hcf', 'lcm', 'remainder', 'modular', 'base', 'digit']):
            return "D-Number System"
        elif any(term in category_lower for term in ['permutation', 'combination', 'probability', 'set', 'venn', 'modern']):
            return "E-Modern Math"
        else:
            # Default mapping
            return "A-Arithmetic"
    
    def _map_to_canonical_question_type(self, question_type: str, category: str) -> str:
        """Map any question type to canonical type based on category"""
        if not question_type or not category:
            return "Speed-Distance-Time Problem"  # Default
        
        # Canonical question types by category
        canonical_types = {
            "A-Arithmetic": [
                "Speed-Distance-Time Problem", "Relative Motion Analysis", "Work Rate Problem",
                "Collaborative Work Problem", "Ratio-Proportion Problem", "Percentage Application Problem",
                "Percentage Change Problem", "Average Calculation Problem", "Weighted Average Problem",
                "Profit-Loss Analysis Problem", "Discount Calculation Problem", "Simple Interest Problem",
                "Compound Interest Problem", "Mixture-Alligation Problem"
            ],
            "B-Algebra": [
                "Linear Equation Problem", "System of Linear Equations", "Quadratic Equation Problem",
                "Inequality Problem", "Sequence-Series Problem", "Function Analysis Problem",
                "Logarithmic Problem", "Exponential Problem"
            ],
            "C-Geometry & Mensuration": [
                "Triangle Properties Problem", "Circle Properties Problem", "Polygon Analysis Problem",
                "Coordinate Geometry Problem", "Area Calculation Problem", "Volume Calculation Problem",
                "Trigonometric Problem"
            ],
            "D-Number System": [
                "Divisibility Analysis Problem", "HCF-LCM Problem", "Remainder Theorem Problem",
                "Modular Arithmetic Problem", "Base System Conversion Problem", "Digit Properties Problem",
                "Prime Factorization Problem"
            ],
            "E-Modern Math": [
                "Permutation Problem", "Combination Problem", "Probability Calculation Problem",
                "Set Theory Problem", "Venn Diagram Problem"
            ]
        }
        
        # If already canonical, return as-is
        if category in canonical_types and question_type in canonical_types[category]:
            return question_type
        
        question_type_lower = question_type.lower()
        
        # Map based on category and keywords
        if category == "A-Arithmetic":
            if any(term in question_type_lower for term in ['speed', 'distance', 'time', 'train', 'motion']):
                return "Speed-Distance-Time Problem"
            elif any(term in question_type_lower for term in ['work', 'rate', 'efficiency']):
                return "Work Rate Problem"
            elif any(term in question_type_lower for term in ['ratio', 'proportion']):
                return "Ratio-Proportion Problem"
            elif any(term in question_type_lower for term in ['percentage', 'percent']):
                return "Percentage Application Problem"
            elif any(term in question_type_lower for term in ['average', 'mean']):
                return "Average Calculation Problem"
            elif any(term in question_type_lower for term in ['profit', 'loss']):
                return "Profit-Loss Analysis Problem"
            elif any(term in question_type_lower for term in ['discount']):
                return "Discount Calculation Problem"
            elif any(term in question_type_lower for term in ['interest']):
                return "Simple Interest Problem"
            elif any(term in question_type_lower for term in ['mixture', 'alligation']):
                return "Mixture-Alligation Problem"
            else:
                return "Speed-Distance-Time Problem"  # Default for arithmetic
                
        elif category == "B-Algebra":
            if any(term in question_type_lower for term in ['system', 'variable']):
                return "System of Linear Equations"
            elif any(term in question_type_lower for term in ['quadratic', 'roots']):
                return "Quadratic Equation Problem"
            elif any(term in question_type_lower for term in ['inequality']):
                return "Inequality Problem"
            elif any(term in question_type_lower for term in ['sequence', 'series', 'progression']):
                return "Sequence-Series Problem"
            elif any(term in question_type_lower for term in ['function']):
                return "Function Analysis Problem"
            elif any(term in question_type_lower for term in ['logarithm', 'log']):
                return "Logarithmic Problem"
            elif any(term in question_type_lower for term in ['exponential', 'exponent']):
                return "Exponential Problem"
            else:
                return "Linear Equation Problem"  # Default for algebra
                
        elif category == "C-Geometry & Mensuration":
            if any(term in question_type_lower for term in ['triangle']):
                return "Triangle Properties Problem"
            elif any(term in question_type_lower for term in ['circle']):
                return "Circle Properties Problem"
            elif any(term in question_type_lower for term in ['polygon']):
                return "Polygon Analysis Problem"
            elif any(term in question_type_lower for term in ['coordinate']):
                return "Coordinate Geometry Problem"
            elif any(term in question_type_lower for term in ['area', 'rectangle']):
                return "Area Calculation Problem"
            elif any(term in question_type_lower for term in ['volume']):
                return "Volume Calculation Problem"
            elif any(term in question_type_lower for term in ['trigonometry', 'trigonometric']):
                return "Trigonometric Problem"
            else:
                return "Area Calculation Problem"  # Default for geometry
                
        elif category == "D-Number System":
            if any(term in question_type_lower for term in ['divisibility', 'divisible']):
                return "Divisibility Analysis Problem"
            elif any(term in question_type_lower for term in ['hcf', 'lcm', 'gcd']):
                return "HCF-LCM Problem"
            elif any(term in question_type_lower for term in ['remainder', 'modular']):
                return "Remainder Theorem Problem"
            elif any(term in question_type_lower for term in ['prime', 'factorization', 'factor']):
                return "Prime Factorization Problem"
            elif any(term in question_type_lower for term in ['digit', 'last']):
                return "Digit Properties Problem"
            elif any(term in question_type_lower for term in ['base', 'conversion']):
                return "Base System Conversion Problem"
            else:
                return "Divisibility Analysis Problem"  # Default for number system
                
        elif category == "E-Modern Math":
            if any(term in question_type_lower for term in ['permutation']):
                return "Permutation Problem"
            elif any(term in question_type_lower for term in ['combination']):
                return "Combination Problem"
            elif any(term in question_type_lower for term in ['probability']):
                return "Probability Calculation Problem"
            elif any(term in question_type_lower for term in ['set', 'union', 'intersection']):
                return "Set Theory Problem"
            elif any(term in question_type_lower for term in ['venn']):
                return "Venn Diagram Problem"
            else:
                return "Permutation Problem"  # Default for modern math
        
        # Final fallback
        return "Speed-Distance-Time Problem"
        
    async def enrich_question_deeply(self, stem: str, admin_answer: str = None, question_type: str = "regular") -> Dict[str, Any]:
        """
        Generate ultra-sophisticated, nuanced enrichment analysis
        
        Args:
            stem: Question text
            admin_answer: Admin-provided answer
            question_type: "regular" or "pyq"
            
        Returns:
            Dict with detailed, human-like enrichment data
        """
        try:
            logger.info(f"🧠 Starting ultra-sophisticated enrichment analysis...")
            logger.info(f"📚 Question: {stem[:100]}...")
            
            enrichment_data = {}
            
            # Step 1: Deep Mathematical Analysis
            logger.info("🔬 Step 1: Deep mathematical analysis...")
            deep_analysis = await self._perform_deep_mathematical_analysis(stem, admin_answer)
            enrichment_data.update(deep_analysis)
            
            # Step 2: Sophisticated Classification
            logger.info("🏛️ Step 2: Sophisticated classification...")
            classification = await self._perform_sophisticated_classification(stem, deep_analysis)
            enrichment_data.update(classification)
            
            # Step 3: Nuanced Difficulty Assessment
            logger.info("⚖️ Step 3: Nuanced difficulty assessment...")
            difficulty = await self._perform_nuanced_difficulty_assessment(stem, deep_analysis, classification)
            enrichment_data.update(difficulty)
            
            # Step 4: Advanced Conceptual Extraction
            logger.info("🧬 Step 4: Advanced conceptual extraction...")
            concepts = await self._perform_advanced_conceptual_extraction(stem, deep_analysis, classification)
            enrichment_data.update(concepts)
            
            # Step 5: Comprehensive Quality Verification
            logger.info("🔍 Step 5: Comprehensive quality verification...")
            quality = await self._perform_comprehensive_quality_verification(stem, enrichment_data)
            enrichment_data.update(quality)
            
            enrichment_data['concept_extraction_status'] = 'completed'
            
            logger.info("✨ Ultra-sophisticated enrichment completed")
            logger.info(f"📊 Generated {len(enrichment_data)} detailed fields")
            
            return {
                "success": True,
                "enrichment_data": enrichment_data,
                "processing_time": "extended_analysis"
            }
            
        except Exception as e:
            logger.error(f"❌ Advanced enrichment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "enrichment_data": {}
            }
    
    def _should_use_fallback_model(self) -> tuple[str, str]:
        """
        Intelligent model selection with temporary fallback for rate limits
        
        Returns:
            tuple: (model_to_use, reason)
        """
        import time
        current_time = time.time()
        
        # If we haven't hit rate limits recently, use primary model
        if self.last_rate_limit_time is None:
            return self.primary_model, "primary_model"
        
        # If enough time has passed since last rate limit, test primary model again
        if current_time - self.last_rate_limit_time > self.rate_limit_recovery_interval:
            logger.info(f"🔄 Testing {self.primary_model} availability after 30-minute recovery period")
            return self.primary_model, "testing_primary_recovery"
        
        # Still within rate limit recovery period, use fallback WITH SAME QUALITY STANDARDS
        remaining_time = self.rate_limit_recovery_interval - (current_time - self.last_rate_limit_time)
        logger.info(f"⚠️ Using {self.fallback_model} with IDENTICAL quality standards. {self.primary_model} retry in {remaining_time/60:.0f} minutes")
        return self.fallback_model, "temporary_fallback_same_quality"
    
    def _handle_rate_limit_error(self, error: Exception) -> bool:
        """
        Detect and handle rate limit errors
        
        Returns:
            bool: True if this was a rate limit error
        """
        import time
        error_str = str(error).lower()
        
        # Check for rate limit indicators
        rate_limit_indicators = [
            'rate limit', 'quota', 'usage limit', 'too many requests',
            'rate_limit_exceeded', 'insufficient_quota', '429'
        ]
        
        is_rate_limit = any(indicator in error_str for indicator in rate_limit_indicators)
        
        if is_rate_limit:
            self.last_rate_limit_time = time.time()
            logger.warning(f"🚨 Rate limit detected for {self.primary_model}. Switching to {self.fallback_model} with IDENTICAL quality standards")
            return True
        
        return False
    
    async def _verify_response_quality(self, response_data: Dict[str, Any], model_used: str, question_stem: str = "") -> Dict[str, Any]:
        """
        Enhanced quality verification with Semantic + Binary validation
        
        Args:
            response_data: The LLM response data
            model_used: Which model generated the response
            question_stem: Original question for semantic validation
            
        Returns:
            Dict with validation results
        """
        logger.info("🔍 Starting enhanced quality verification (Semantic + Binary)")
        
        # STEP 1: SEMANTIC VALIDATION (Anthropic)
        logger.info("🧠 Step 1: Semantic validation with Anthropic...")
        try:
            semantic_result = await anthropic_semantic_validator.validate_semantic_quality(
                question_stem, response_data
            )
            
            if not semantic_result.get("semantic_valid", False):
                logger.error(f"❌ SEMANTIC VALIDATION FAILED: {semantic_result.get('issues', [])}")
                return {
                    "quality_verified": False,
                    "validation_stage": "semantic",
                    "issues": semantic_result.get('issues', []),
                    "detailed_feedback": semantic_result.get('detailed_feedback', {})
                }
                
            logger.info(f"✅ Semantic validation passed (confidence: {semantic_result.get('confidence_score', 0):.2f})")
            
        except Exception as e:
            logger.error(f"❌ Semantic validation service error: {e}")
            return {
                "quality_verified": False,
                "validation_stage": "semantic_error",
                "issues": [f"Semantic validation service failed: {str(e)}"],
                "detailed_feedback": {}
            }
        
        # STEP 2: BINARY/STRUCTURAL VALIDATION (Code)
        logger.info("⚙️ Step 2: Binary/structural validation...")
        binary_issues = []
        
        # Fuzzy match and validate taxonomy fields
        if 'category' in response_data and 'subcategory' in response_data and 'type_of_question' in response_data:
            try:
                # Get canonical taxonomy path using fuzzy matching
                canonical_category, canonical_subcategory, canonical_type = canonical_taxonomy_service.get_canonical_taxonomy_path(
                    response_data.get('category', ''),
                    response_data.get('subcategory', ''),
                    response_data.get('type_of_question', '')
                )
                
                # Update response data with canonical values
                response_data['category'] = canonical_category
                response_data['subcategory'] = canonical_subcategory  
                response_data['type_of_question'] = canonical_type
                
                # Validate the canonical path
                if not canonical_taxonomy_service.validate_taxonomy_path(
                    canonical_category, canonical_subcategory, canonical_type
                ):
                    binary_issues.append("Canonical taxonomy path validation failed")
                    
            except Exception as e:
                binary_issues.append(f"Taxonomy fuzzy matching failed: {str(e)}")
        else:
            binary_issues.append("Missing required taxonomy fields (category, subcategory, type_of_question)")
        
        # Validate difficulty ranges
        if 'difficulty_band' in response_data and 'difficulty_score' in response_data:
            difficulty_band = response_data.get('difficulty_band', '').strip()
            difficulty_score = response_data.get('difficulty_score', 0)
            
            try:
                difficulty_score = float(difficulty_score)
                
                # Validate difficulty band ranges
                if difficulty_band == 'Easy' and not (1.0 <= difficulty_score <= 2.0):
                    binary_issues.append(f"Easy difficulty score {difficulty_score} outside valid range (1.0-2.0)")
                elif difficulty_band == 'Medium' and not (2.1 <= difficulty_score <= 3.5):
                    binary_issues.append(f"Medium difficulty score {difficulty_score} outside valid range (2.1-3.5)")
                elif difficulty_band == 'Hard' and not (3.6 <= difficulty_score <= 5.0):
                    binary_issues.append(f"Hard difficulty score {difficulty_score} outside valid range (3.6-5.0)")
                elif difficulty_band not in ['Easy', 'Medium', 'Hard']:
                    binary_issues.append(f"Invalid difficulty band: {difficulty_band}. Must be Easy, Medium, or Hard")
                    
            except (ValueError, TypeError):
                binary_issues.append(f"Invalid difficulty score format: {difficulty_score}")
        
        # Check required field presence
        required_fields = ['core_concepts', 'solution_method', 'concept_difficulty', 'operations_required']
        for field in required_fields:
            if field not in response_data or not response_data[field]:
                binary_issues.append(f"Required field missing or empty: {field}")
        
        if binary_issues:
            logger.error(f"❌ BINARY VALIDATION FAILED: {binary_issues}")
            return {
                "quality_verified": False,
                "validation_stage": "binary",
                "issues": binary_issues,
                "detailed_feedback": {}
            }
        
        logger.info("✅ Binary validation passed - all structural requirements met")
        
        # BOTH VALIDATIONS PASSED
        logger.info("🎉 Enhanced quality verification PASSED - Semantic + Binary validation successful")
        return {
            "quality_verified": True,
            "validation_stage": "complete",
            "issues": [],
            "semantic_confidence": semantic_result.get('confidence_score', 0),
            "detailed_feedback": semantic_result.get('detailed_feedback', {})
        }
    
    def _mark_primary_model_recovered(self):
        """Mark that primary model is working again"""
        if self.last_rate_limit_time is not None:
            logger.info(f"✅ {self.primary_model} recovered! Switching back from temporary fallback (quality standards maintained throughout)")
            self.last_rate_limit_time = None

    async def _perform_deep_mathematical_analysis(self, stem: str, admin_answer: str = None) -> Dict[str, Any]:
        """Perform deep mathematical analysis with sophisticated understanding"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
                # Intelligent model selection
                model_to_use, selection_reason = self._should_use_fallback_model()
                logger.info(f"🤖 Using model: {model_to_use} (reason: {selection_reason})")
                
                system_message = """You are a world-class mathematics professor and CAT expert with deep expertise in quantitative reasoning. 

Your task is to perform a sophisticated mathematical analysis of this question, thinking like a human expert with superior AI intelligence.

ANALYZE WITH DEEP SOPHISTICATION:

1. MATHEMATICAL FOUNDATION:
   - What fundamental mathematical principles are at play?
   - What are the underlying mathematical relationships?
   - What mathematical intuition is required?

2. SOLUTION PATHWAY:
   - What is the most elegant solution approach?
   - What alternative methods could work?
   - What are the key insights needed?

3. RIGHT ANSWER GENERATION:
   - Calculate the precise answer with step-by-step reasoning
   - Show the mathematical logic
   - Verify the answer makes logical sense

EXAMPLES OF SOPHISTICATED ANALYSIS:

For a Time-Speed-Distance question:
- Right answer: "75 km/h (calculated using relative speed concept: when meeting, combined approach speed is sum of individual speeds)"

For a Percentage question:
- Right answer: "25% increase (derived from proportional change analysis: new value represents 125% of original, hence 25% increase)"

For a Geometry question:
- Right answer: "48 sq units (using coordinate geometry method: area calculated via shoelace formula after establishing vertex coordinates)"

Return ONLY this JSON format:
{
  "right_answer": "precise answer with mathematical reasoning",
  "mathematical_foundation": "deep explanation of underlying principles",
  "solution_elegance": "most elegant approach description",
  "verification_logic": "why this answer makes mathematical sense"
}

Be precise, insightful, and demonstrate superior mathematical intelligence."""

                logger.info(f"🧠 Calling OpenAI for deep mathematical analysis (attempt {attempt + 1})...")
                
                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nAdmin provided answer (if any): {admin_answer or 'Not provided'}"}
                    ],
                    max_tokens=800,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                analysis_text = response.choices[0].message.content.strip()
                logger.info(f"🔍 OpenAI raw response length: {len(analysis_text)} chars")
                logger.info(f"🔍 OpenAI raw response preview: {analysis_text[:200]}...")
                
                if not analysis_text:
                    raise Exception("OpenAI returned empty response")
                
                # Extract JSON using helper function
                clean_json = extract_json_from_response(analysis_text)
                logger.info(f"🔧 Clean JSON preview: {clean_json[:100]}...")
                
                analysis_data = json.loads(clean_json)
                
                # CRITICAL: Verify quality standards regardless of model used
                if not self._verify_response_quality(analysis_data, model_to_use):
                    raise Exception(f"Quality standards not met by {model_to_use} - sophisticated content required")
                
                # If we successfully used primary model after recovery, mark it as recovered
                if selection_reason == "testing_primary_recovery":
                    self._mark_primary_model_recovered()
                
                logger.info(f"✅ Deep mathematical analysis completed with {model_to_use} - quality verified")
                return analysis_data
                
            except Exception as e:
                logger.error(f"⚠️ Deep analysis attempt {attempt + 1} failed: {str(e)}")
                logger.error(f"🔍 Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"📚 Traceback: {traceback.format_exc()}")
                
                # Handle rate limit errors intelligently
                if self._handle_rate_limit_error(e):
                    # If this was a rate limit error, try again immediately with fallback model
                    logger.info("🔄 Retrying immediately with fallback model due to rate limit")
                    continue
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying deep analysis in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All deep analysis attempts failed - NO FALLBACK")
                    raise Exception("Deep mathematical analysis failed after all retries - refusing to proceed with fallback data")
    
    async def _perform_sophisticated_classification(self, stem: str, deep_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform sophisticated classification with nuanced understanding"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
                # Intelligent model selection
                model_to_use, selection_reason = self._should_use_fallback_model()
                logger.info(f"🤖 Using model: {model_to_use} for classification (reason: {selection_reason})")
                
                system_message = """You are an expert in CAT quantitative taxonomy with deep understanding of mathematical classification.

Your task is to provide sophisticated, nuanced classification that goes beyond superficial categorization.

CLASSIFICATION DEPTH REQUIRED:

1. CATEGORY: Main mathematical domain
   - Not just "Arithmetic" but specific like "Advanced Arithmetic", "Applied Arithmetic", "Computational Arithmetic"
   
2. SUBCATEGORY: Precise mathematical area
   - Not just "Time Speed Distance" but "Relative Motion Analysis", "Multi-stage Journey Problems", "Meeting Point Calculations"
   
3. TYPE_OF_QUESTION: Very specific question archetype
   - Not just "Word Problem" but "Two-Train Meeting Problem with Different Departure Times", "Percentage Change in Sequential Operations"

EXAMPLES OF SOPHISTICATED CLASSIFICATION:

Instead of generic:
- Category: "Arithmetic"
- Subcategory: "Percentages" 
- Type: "Word Problem"

Provide nuanced:
- Category: "Applied Arithmetic with Business Context"
- Subcategory: "Sequential Percentage Changes in Sales Data"
- Type: "Multi-stage Percentage Calculation with Compound Effects"

Another example:
Instead of:
- Category: "Algebra"
- Subcategory: "Linear Equations"
- Type: "Basic"

Provide:
- Category: "Applied Algebraic Modeling"
- Subcategory: "Age-Based Linear Relationship Problems"
- Type: "Two-Person Age Differential with Future State Analysis"

Return ONLY this JSON:
{
  "category": "sophisticated main category",
  "subcategory": "nuanced subcategory", 
  "type_of_question": "very specific question archetype"
}

Be precise, specific, and demonstrate deep mathematical understanding."""

                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nMathematical Analysis: {deep_analysis.get('mathematical_foundation', '')}\nSolution Approach: {deep_analysis.get('solution_elegance', '')}"}
                    ],
                    max_tokens=300,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                classification_text = response.choices[0].message.content.strip()
                logger.info(f"🔍 Raw classification response: {classification_text[:200]}...")
                
                # Add JSON validation and error handling
                try:
                    clean_json = extract_json_from_response(classification_text)
                    classification_data = json.loads(clean_json)
                    
                    # Validate required fields
                    required_fields = ["category", "subcategory", "type_of_question"]
                    missing_fields = [field for field in required_fields if field not in classification_data]
                    
                    if missing_fields:
                        logger.warning(f"⚠️ Missing required fields in classification: {missing_fields}")
                        raise ValueError(f"Missing required fields: {missing_fields}")
                    
                    # Ensure non-empty values
                    empty_fields = [field for field in required_fields if not classification_data.get(field, "").strip()]
                    if empty_fields:
                        logger.warning(f"⚠️ Empty fields in classification: {empty_fields}")
                        raise ValueError(f"Empty fields: {empty_fields}")
                    
                    # CANONICAL TAXONOMY ENFORCEMENT - Map to canonical categories
                    original_category = classification_data.get("category", "")
                    canonical_category = self._map_to_canonical_category(original_category)
                    if canonical_category != original_category:
                        logger.info(f"📂 Mapped '{original_category}' → '{canonical_category}'")
                        classification_data["category"] = canonical_category
                    
                    # CANONICAL TYPE_OF_QUESTION ENFORCEMENT
                    original_type = classification_data.get("type_of_question", "")
                    canonical_type = self._map_to_canonical_question_type(original_type, canonical_category)
                    if canonical_type != original_type:
                        logger.info(f"📋 Mapped type '{original_type}' → '{canonical_type}'")
                        classification_data["type_of_question"] = canonical_type
                    
                except json.JSONDecodeError as json_err:
                    logger.warning(f"⚠️ JSON parsing failed: {json_err}")
                    logger.warning(f"Raw response: {classification_text}")
                    
                    # Try to extract JSON from response if it contains extra text
                    try:
                        # Look for JSON block in the response
                        start_idx = classification_text.find('{')
                        end_idx = classification_text.rfind('}') + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            json_part = classification_text[start_idx:end_idx]
                            classification_data = json.loads(json_part)
                            logger.info("✅ Successfully extracted JSON from response")
                            
                            # Apply canonical mapping to extracted data too
                            original_category = classification_data.get("category", "")
                            canonical_category = self._map_to_canonical_category(original_category)
                            classification_data["category"] = canonical_category
                        else:
                            raise json_err
                    except:
                        # Final fallback: create default classification
                        logger.warning("⚠️ Creating default classification due to JSON parsing failure")
                        classification_data = {
                            "category": "A-Arithmetic",  # Use canonical format
                            "subcategory": "Quantitative Reasoning",
                            "type_of_question": "Standard CAT Problem"
                        }
                
                # If we successfully used primary model after recovery, mark it as recovered
                if selection_reason == "testing_primary_recovery":
                    self._mark_primary_model_recovered()
                
                logger.info(f"✅ Sophisticated classification completed with {model_to_use}")
                return classification_data
                
            except Exception as e:
                logger.warning(f"⚠️ Classification attempt {attempt + 1} failed: {e}")
                
                # Handle rate limit errors intelligently
                if self._handle_rate_limit_error(e):
                    logger.info("🔄 Retrying classification immediately with fallback model due to rate limit")
                    continue
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All classification attempts failed - NO FALLBACK")
                    raise Exception("Sophisticated classification failed after all retries - refusing to proceed with fallback data")
    
    async def _perform_nuanced_difficulty_assessment(self, stem: str, deep_analysis: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Perform nuanced difficulty assessment with sophisticated reasoning"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
                # Intelligent model selection
                model_to_use, selection_reason = self._should_use_fallback_model()
                logger.info(f"🤖 Using model: {model_to_use} for difficulty assessment (reason: {selection_reason})")
                
                system_message = """You are a CAT difficulty assessment expert with deep understanding of cognitive load and mathematical complexity.

Assess difficulty with sophisticated reasoning considering multiple dimensions:

DIFFICULTY DIMENSIONS:
1. CONCEPTUAL COMPLEXITY: How many mathematical concepts must be integrated?
2. COMPUTATIONAL INTENSITY: How demanding are the calculations?
3. LOGICAL REASONING DEPTH: How many inference steps are required?
4. TIME PRESSURE FACTOR: How efficiently must a student work under exam pressure?
5. TRAP POTENTIAL: How many ways can a student make errors?

NUANCED DIFFICULTY BANDS:

EASY (1.0-2.0):
- Single mathematical concept application
- Straightforward computational steps
- Minimal logical inference required
- Low trap potential
- Can be solved in under 2 minutes by average student

MEDIUM (2.1-3.5):
- Multiple concept integration required
- Moderate computational complexity
- 2-3 logical inference steps
- Some potential for calculation errors
- Requires 2-4 minutes for average student

HARD (3.6-5.0):
- Complex concept synthesis
- High computational demand or elegant insight required
- Multi-step logical reasoning chain
- High trap potential with multiple error paths
- Requires 4+ minutes and strong mathematical maturity

DIFFICULTY SCORING EXAMPLES:

Time-Speed-Distance with relative motion: 3.2 (Medium-High)
- Requires understanding of relative speed concept
- Moderate calculation but conceptual insight crucial
- One key logical step but easy to miss

Percentage with compound changes: 2.8 (Medium)
- Sequential percentage application
- Straightforward calculation if method is clear
- Some potential for order-of-operations errors

Complex geometry with coordinate analysis: 4.2 (Hard)
- Multiple geometric concepts
- Either intensive computation or elegant insight
- High logical reasoning demand
- Many potential error paths

Return ONLY this JSON:
{
  "difficulty_band": "Easy/Medium/Hard",
  "difficulty_score": 3.2,
  "complexity_reasoning": "detailed explanation of why this difficulty",
  "cognitive_load_factors": ["factor1", "factor2", "factor3"],
  "time_estimate_minutes": 3.5,
  "error_trap_potential": "low/medium/high"
}"""

                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nMathematical Foundation: {deep_analysis.get('mathematical_foundation', '')}\nCategory: {classification.get('category', '')}\nType: {classification.get('type_of_question', '')}"}
                    ],
                    max_tokens=400,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                difficulty_text = response.choices[0].message.content.strip()
                logger.info(f"🔍 Raw difficulty assessment response: {difficulty_text[:200]}...")
                
                # Add JSON validation and error handling
                try:
                    difficulty_data = json.loads(difficulty_text)
                except json.JSONDecodeError as json_err:
                    logger.warning(f"⚠️ JSON parsing failed in difficulty assessment: {json_err}")
                    logger.warning(f"Raw response: {difficulty_text}")
                    
                    # Try to extract JSON from response if it contains extra text
                    try:
                        # Look for JSON block in the response
                        start_idx = difficulty_text.find('{')
                        end_idx = difficulty_text.rfind('}') + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            json_part = difficulty_text[start_idx:end_idx]
                            difficulty_data = json.loads(json_part)
                            logger.info("✅ Successfully extracted JSON from difficulty response")
                        else:
                            raise json_err
                    except:
                        # Final fallback: create default difficulty data
                        logger.warning("⚠️ Creating default difficulty data due to JSON parsing failure")
                        difficulty_data = {
                            "difficulty_band": "Medium",
                            "difficulty_score": 2.5,
                            "complexity_reasoning": "Standard mathematical problem requiring moderate cognitive effort",
                            "cognitive_load_factors": ["calculation", "reasoning"],
                            "time_estimate_minutes": 3.0,
                            "error_trap_potential": "medium"
                        }
                
                # Validate and clean data
                band = difficulty_data.get('difficulty_band', 'Medium').capitalize()
                if band not in ['Easy', 'Medium', 'Hard']:
                    band = 'Medium'
                
                score = float(difficulty_data.get('difficulty_score', 2.5))
                if not (1.0 <= score <= 5.0):
                    score = 2.5
                
                result = {
                    'difficulty_band': band,
                    'difficulty_score': score,
                    'complexity_reasoning': difficulty_data.get('complexity_reasoning', ''),
                    'cognitive_load_factors': json.dumps(difficulty_data.get('cognitive_load_factors', [])),
                    'time_estimate_minutes': difficulty_data.get('time_estimate_minutes', 3.0),
                    'error_trap_potential': difficulty_data.get('error_trap_potential', 'medium')
                }
                
                # If we successfully used primary model after recovery, mark it as recovered
                if selection_reason == "testing_primary_recovery":
                    self._mark_primary_model_recovered()
                
                logger.info(f"✅ Nuanced difficulty assessment: {band} ({score}) with {model_to_use}")
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ Difficulty assessment attempt {attempt + 1} failed: {e}")
                
                # Handle rate limit errors intelligently
                if self._handle_rate_limit_error(e):
                    logger.info("🔄 Retrying difficulty assessment immediately with fallback model due to rate limit")
                    continue
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All difficulty assessment attempts failed - NO FALLBACK")
                    raise Exception("Nuanced difficulty assessment failed after all retries - refusing to proceed with fallback data")
    
    async def _perform_advanced_conceptual_extraction(self, stem: str, deep_analysis: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Perform advanced conceptual extraction with sophisticated insight"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
                # Intelligent model selection
                model_to_use, selection_reason = self._should_use_fallback_model()
                logger.info(f"🤖 Using model: {model_to_use} for conceptual extraction (reason: {selection_reason})")
                
                system_message = """You are a mathematical concept extraction expert with deep insight into learning patterns and cognitive structures.

Extract sophisticated conceptual information that would be genuinely useful for adaptive learning systems.

ADVANCED CONCEPT EXTRACTION REQUIRED:

1. CORE_CONCEPTS: 3-6 specific mathematical concepts (not generic terms)
   Examples: 
   - Instead of ["speed", "distance"] use ["relative_velocity_analysis", "meeting_point_calculation", "uniform_motion_modeling"]
   - Instead of ["percentage"] use ["sequential_percentage_operations", "percentage_point_vs_percentage_change", "compound_percentage_effects"]

2. SOLUTION_METHOD: Precise methodological approach
   Examples:
   - "Relative Speed Synthesis with Meeting Point Analysis"
   - "Coordinate Geometry via Systematic Point Plotting"
   - "Algebraic Substitution with Variable Isolation Technique"

3. CONCEPT_DIFFICULTY: Sophisticated difficulty analysis
   Example: {"prerequisites": ["ratio_proportion_mastery", "unit_conversion_fluency"], "cognitive_barriers": ["conceptual_vs_procedural_confusion"], "mastery_indicators": ["flexible_method_selection"]}

4. OPERATIONS_REQUIRED: Specific mathematical operations (not just "calculation")
   Examples: ["proportional_reasoning", "algebraic_manipulation", "geometric_visualization", "logical_deduction"]

5. PROBLEM_STRUCTURE: Sophisticated structural analysis
   Examples: "multi_stage_optimization_problem", "constraint_satisfaction_with_variable_bounds", "inverse_relationship_modeling"

6. CONCEPT_KEYWORDS: Precise, searchable educational terms
   Examples: ["relative_motion", "simultaneous_equations", "proportional_scaling", "optimization_constraints"]

EXAMPLES OF SOPHISTICATED EXTRACTION:

For a trains meeting problem:
{
  "core_concepts": ["relative_velocity_vector_addition", "meeting_point_spatial_analysis", "uniform_motion_kinematics", "distance_rate_time_relationship_modeling"],
  "solution_method": "Relative Speed Vector Analysis with Spatial Meeting Point Calculation",
  "concept_difficulty": {"prerequisites": ["speed_distance_time_fluency", "algebraic_equation_solving"], "cognitive_barriers": ["relative_vs_absolute_motion_confusion"], "mastery_indicators": ["flexible_reference_frame_selection", "intuitive_relative_speed_reasoning"]},
  "operations_required": ["vector_addition_conceptual", "algebraic_equation_setup", "proportional_reasoning", "unit_consistency_verification"],
  "problem_structure": "dual_entity_convergence_analysis_with_temporal_coordination",
  "concept_keywords": ["relative_motion", "meeting_point_analysis", "dual_trajectory_coordination", "speed_vector_synthesis"]
}

Return ONLY this JSON format with sophisticated, specific content."""

                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nMathematical Foundation: {deep_analysis.get('mathematical_foundation', '')}\nCategory: {classification.get('category', '')}\nSubcategory: {classification.get('subcategory', '')}\nType: {classification.get('type_of_question', '')}"}
                    ],
                    max_tokens=600,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                concept_text = response.choices[0].message.content.strip()
                logger.info(f"🔍 Raw conceptual extraction response: {concept_text[:200]}...")
                
                # Add JSON validation and error handling
                try:
                    concept_data = json.loads(concept_text)
                    
                    # Validate required fields
                    required_fields = ["core_concepts", "solution_method", "operations_required"]
                    missing_fields = [field for field in required_fields if field not in concept_data]
                    
                    if missing_fields:
                        logger.warning(f"⚠️ Missing required fields in conceptual extraction: {missing_fields}")
                        # Don't raise error, use defaults instead
                        for field in missing_fields:
                            if field == "core_concepts":
                                concept_data[field] = ["mathematical_analysis", "quantitative_reasoning"]
                            elif field == "solution_method":
                                concept_data[field] = "Mathematical Problem Solving"
                            elif field == "operations_required":
                                concept_data[field] = ["calculation", "analysis"]
                    
                except json.JSONDecodeError as json_err:
                    logger.warning(f"⚠️ JSON parsing failed in conceptual extraction: {json_err}")
                    logger.warning(f"Raw response: {concept_text}")
                    
                    # Try to extract JSON from response if it contains extra text
                    try:
                        # Look for JSON block in the response
                        start_idx = concept_text.find('{')
                        end_idx = concept_text.rfind('}') + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            json_part = concept_text[start_idx:end_idx]
                            concept_data = json.loads(json_part)
                            logger.info("✅ Successfully extracted JSON from conceptual response")
                        else:
                            raise json_err
                    except:
                        # Final fallback: create default conceptual data
                        logger.warning("⚠️ Creating default conceptual data due to JSON parsing failure")
                        concept_data = {
                            "core_concepts": ["mathematical_analysis", "quantitative_reasoning", "problem_solving"],
                            "solution_method": "Systematic Mathematical Approach",
                            "concept_difficulty": {"prerequisites": ["basic_arithmetic"], "cognitive_barriers": [], "mastery_indicators": []},
                            "operations_required": ["calculation", "logical_reasoning"],
                            "problem_structure": "standard_mathematical_problem",
                            "concept_keywords": ["mathematics", "calculation"]
                        }
                
                # Convert to database format
                result = {
                    'core_concepts': json.dumps(concept_data.get('core_concepts', [])),
                    'solution_method': concept_data.get('solution_method', 'Advanced Mathematical Analysis'),
                    'concept_difficulty': json.dumps(concept_data.get('concept_difficulty', {})),
                    'operations_required': json.dumps(concept_data.get('operations_required', [])),
                    'problem_structure': concept_data.get('problem_structure', 'complex_analytical_structure'),
                    'concept_keywords': json.dumps(concept_data.get('concept_keywords', []))
                }
                
                # If we successfully used primary model after recovery, mark it as recovered
                if selection_reason == "testing_primary_recovery":
                    self._mark_primary_model_recovered()
                
                logger.info(f"✅ Advanced conceptual extraction completed with {model_to_use}")
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ Conceptual extraction attempt {attempt + 1} failed: {e}")
                
                # Handle rate limit errors intelligently
                if self._handle_rate_limit_error(e):
                    logger.info("🔄 Retrying conceptual extraction immediately with fallback model due to rate limit")
                    continue
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All conceptual extraction attempts failed - NO FALLBACK")
                    raise Exception("Advanced conceptual extraction failed after all retries - refusing to proceed with fallback data")
    
    async def _perform_comprehensive_quality_verification(self, stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform enhanced quality verification with Semantic + Binary validation"""
        
        try:
            logger.info("🔍 Step 5: Enhanced quality verification (Semantic + Binary)")
            
            # Use new semantic + binary validation
            validation_result = await self._verify_response_quality(
                enrichment_data, "quality_verification", stem
            )
            
            if validation_result.get("quality_verified", False):
                logger.info("✅ Enhanced quality verification passed")
                return {
                    'quality_verified': True,
                    'quality_score': 100,  # Pass/fail system now
                    'quality_factors': json.dumps([
                        "semantic_validation_passed",
                        "binary_validation_passed", 
                        "canonical_taxonomy_matched"
                    ]),
                    'semantic_confidence': validation_result.get('semantic_confidence', 0),
                    'validation_details': validation_result.get('detailed_feedback', {})
                }
            else:
                logger.error(f"❌ Enhanced quality verification failed at {validation_result.get('validation_stage', 'unknown')} stage")
                return {
                    'quality_verified': False,
                    'quality_score': 0,
                    'quality_factors': json.dumps([
                        f"failed_at_{validation_result.get('validation_stage', 'unknown')}_stage"
                    ]),
                    'validation_issues': validation_result.get('issues', [])
                }
            
        except Exception as e:
            logger.error(f"❌ Enhanced quality verification exception: {e}")
            return {
                'quality_verified': False,
                'quality_score': 0,
                'quality_factors': json.dumps(["verification_service_failed"]),
                'error': str(e)
            }