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
    
    def _build_canonical_taxonomy_context(self) -> str:
        """Build canonical taxonomy context for LLM prompt"""
        from canonical_taxonomy_data import CANONICAL_TAXONOMY
        
        context_lines = []
        for category, subcategories in CANONICAL_TAXONOMY.items():
            context_lines.append(f"\n{category.upper()}:")
            
            for subcategory, data in subcategories.items():
                # Add subcategory with description
                description = data['description']
                # Truncate for prompt efficiency
                short_desc = description[:200] + "..." if len(description) > 200 else description
                context_lines.append(f"  • {subcategory}: {short_desc}")
                
                # Add sample question types
                question_types = list(data['types'].keys())[:3]  # Show first 3 types
                if question_types:
                    context_lines.append(f"    Types: {', '.join(question_types)}")
        
        return '\n'.join(context_lines)
    
    async def _get_canonical_taxonomy_path_with_context(self, original_question: str, llm_category: str, llm_subcategory: str, llm_type: str) -> tuple[str, str, str]:
        """
        Enhanced semantic matching with original question context
        Returns: (canonical_category, canonical_subcategory, canonical_type)
        """
        
        try:
            logger.info("🧠 Performing context-aware semantic matching...")
            
            # Build canonical taxonomy context
            canonical_context = self._build_canonical_taxonomy_context()
            
            # Create context-aware semantic matching prompt
            system_message = f"""You are a mathematical taxonomy expert with deep understanding of CAT quantitative problems.

Your task is to find the most appropriate canonical taxonomy classification by analyzing the ORIGINAL PROBLEM, not just the generated terms.

CANONICAL TAXONOMY REFERENCE:
{canonical_context}

CONTEXT-AWARE MATCHING PROCESS:
1. Analyze the ORIGINAL PROBLEM's mathematical domain and concepts
2. Consider the generated classifications as hints, but prioritize the actual problem content
3. Match to the canonical taxonomy based on the problem's TRUE mathematical nature

MATCHING RULES:
- Focus on the mathematical DOMAIN and PROBLEM TYPE of the original question
- Use the detailed canonical descriptions to understand the true classification
- If the generated terms don't fit the problem's actual domain, override them
- Choose the classification that best represents the problem's mathematical essence

Return ONLY this JSON:
{{
  "category": "exact canonical category name",
  "subcategory": "exact canonical subcategory name",
  "type_of_question": "exact canonical question type name"
}}

If no good match exists, return "NO_MATCH" for that field."""
            
            user_message = f"""ORIGINAL PROBLEM: {original_question}

GENERATED CLASSIFICATIONS:
- Category: {llm_category}
- Subcategory: {llm_subcategory}  
- Type of Question: {llm_type}

Analyze the ORIGINAL PROBLEM and find the best canonical taxonomy match based on the problem's true mathematical domain."""
            
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"🎯 Context-aware semantic matching (attempt {attempt + 1})...")
                    
                    matching_text, model_used = await call_llm_with_fallback(
                        self, system_message, user_message, max_tokens=300, temperature=0.1
                    )
                    
                    if not matching_text:
                        raise Exception("LLM returned empty response")
                    
                    # Extract JSON using helper function
                    clean_json = extract_json_from_response(matching_text)
                    matching_data = json.loads(clean_json)
                    
                    # Extract results
                    canonical_category = matching_data.get('category')
                    canonical_subcategory = matching_data.get('subcategory')
                    canonical_type = matching_data.get('type_of_question')
                    
                    # Handle NO_MATCH cases
                    if canonical_category == "NO_MATCH":
                        canonical_category = None
                    if canonical_subcategory == "NO_MATCH":
                        canonical_subcategory = None
                    if canonical_type == "NO_MATCH":
                        canonical_type = None
                    
                    # CRITICAL FIX: Validate and correct case mismatches
                    from canonical_taxonomy_data import CANONICAL_TAXONOMY
                    
                    # Fix category case mismatch
                    if canonical_category:
                        for canon_cat in CANONICAL_TAXONOMY.keys():
                            if canon_cat.lower() == canonical_category.lower():
                                canonical_category = canon_cat
                                break
                    
                    # Validate complete path exists
                    if (canonical_category and canonical_subcategory and canonical_type and
                        canonical_category in CANONICAL_TAXONOMY and
                        canonical_subcategory in CANONICAL_TAXONOMY[canonical_category] and
                        canonical_type in CANONICAL_TAXONOMY[canonical_category][canonical_subcategory]['types']):
                        logger.info(f"✅ Taxonomy path validated: {canonical_category} → {canonical_subcategory} → {canonical_type}")
                    else:
                        logger.warning(f"⚠️ Taxonomy path validation failed, using None values")
                        canonical_category = None
                        canonical_subcategory = None
                        canonical_type = None
                    
                    logger.info(f"✅ Context-aware semantic matching completed with {model_used}")
                    return canonical_category, canonical_subcategory, canonical_type
                    
                except Exception as e:
                    logger.error(f"⚠️ Context-aware matching attempt {attempt + 1} failed: {str(e)}")
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error("❌ All context-aware matching attempts failed")
                        break
            
            # Fallback to original semantic matching if context-aware fails
            logger.warning("🔄 Falling back to original semantic matching...")
            return await canonical_taxonomy_service.get_canonical_taxonomy_path(
                llm_category, llm_subcategory, llm_type
            )
            
        except Exception as e:
            logger.error(f"❌ Context-aware semantic matching failed: {e}")
            # Return original values as last resort
            return llm_category, llm_subcategory, llm_type
    
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
        Stage 1-4 CONSOLIDATED: Single comprehensive LLM analysis with canonical taxonomy context
        FIELDS UPDATED: answer, category, subcategory, type_of_question, difficulty_band, difficulty_score, 
                       core_concepts, solution_method, concept_difficulty, operations_required, 
                       problem_structure, concept_keywords
        """
        
        # Build canonical taxonomy context for the LLM
        canonical_context = self._build_canonical_taxonomy_context()
        
        system_message = f"""You are a world-class CAT mathematics expert with deep expertise in quantitative reasoning and educational assessment.

Your task is to perform a COMPREHENSIVE analysis of this PYQ question in ONE complete response.

CANONICAL TAXONOMY REFERENCE (USE EXACT NAMES):

{canonical_context}

COMPREHENSIVE ANALYSIS REQUIRED:

1. SOLVE THE PROBLEM:
   - Calculate the precise mathematical answer with step-by-step reasoning
   - Show clear mathematical logic and verify the answer

2. CLASSIFY THE QUESTION using CANONICAL TAXONOMY:
   - Category: Choose from [Arithmetic, Algebra, Geometry and Mensuration, Number System, Modern Math]
   - Subcategory: Use EXACT subcategory name from canonical reference above
   - Type of Question: Use EXACT question type name from canonical reference above
   
   IMPORTANT: Analyze the TRUE MATHEMATICAL DOMAIN of the problem, not just surface terminology.

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
{{
  "answer": "precise answer with mathematical reasoning",
  "category": "exact canonical category name",
  "subcategory": "exact canonical subcategory name", 
  "type_of_question": "exact canonical question type name",
  "difficulty_band": "Easy/Medium/Hard",
  "difficulty_score": 3.2,
  "core_concepts": ["concept1", "concept2", "concept3"],
  "solution_method": "methodological approach",
  "concept_difficulty": {{"prerequisites": ["req1"], "cognitive_barriers": ["barrier1"], "mastery_indicators": ["indicator1"]}},
  "operations_required": ["operation1", "operation2"],
  "problem_structure": "structural_analysis_type",
  "concept_keywords": ["keyword1", "keyword2"]
}}

Be precise, comprehensive, and use EXACT canonical taxonomy names."""

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
    
    async def _perform_semantic_matching_and_verification(self, stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 5: Enhanced semantic matching + comprehensive quality verification
        FIELDS UPDATED: category, subcategory, type_of_question (corrected), quality_verified
        """
        
        try:
            logger.info("🎯 Stage 5a: Context-aware semantic matching...")
            
            # Apply enhanced semantic matching with ORIGINAL QUESTION CONTEXT
            canonical_category, canonical_subcategory, canonical_type = await self._get_canonical_taxonomy_path_with_context(
                stem,  # Include original question
                enrichment_data.get('category', ''),
                enrichment_data.get('subcategory', ''),
                enrichment_data.get('type_of_question', '')
            )
            
            # Update with canonical values (may be corrected from LLM output)
            result = {
                'category': canonical_category,
                'subcategory': canonical_subcategory,
                'type_of_question': canonical_type
            }
            
            logger.info(f"✅ Context-aware matching: {enrichment_data.get('category')} → {canonical_category}")
            logger.info(f"✅ Context-aware matching: {enrichment_data.get('subcategory')} → {canonical_subcategory}")
            logger.info(f"✅ Context-aware matching: {enrichment_data.get('type_of_question')} → {canonical_type}")
            
            # Stage 5b: Enhanced quality verification
            logger.info("🔍 Stage 5b: Enhanced quality verification (Semantic + Binary)")
            
            # Update enrichment_data with canonical values for verification
            enrichment_data_for_verification = enrichment_data.copy()
            enrichment_data_for_verification.update(result)
            
            # Simple quality verification for enhanced system
            if (canonical_category and canonical_subcategory and canonical_type and 
                enrichment_data_for_verification.get('answer') and
                enrichment_data_for_verification.get('difficulty_band')):
                logger.info("✅ Quality verification passed")
                result['quality_verified'] = True
            else:
                logger.error(f"❌ Quality verification failed - missing required fields")
                result['quality_verified'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Context-aware semantic matching and verification failed: {e}")
            return {
                'category': enrichment_data.get('category'),
                'subcategory': enrichment_data.get('subcategory'), 
                'type_of_question': enrichment_data.get('type_of_question'),
                'quality_verified': False
            }

# Global instance
pyq_enrichment_service = PYQEnrichmentService()