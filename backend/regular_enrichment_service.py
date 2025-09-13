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
from sqlalchemy import and_, or_
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
    
    async def enrich_regular_question(self, stem: str, current_answer: str = None, snap_read: str = None, solution_approach: str = None, detailed_solution: str = None, principle_to_remember: str = None, mcq_options: str = None) -> Dict[str, Any]:
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
            
            # APPLY SEMANTIC TAXONOMY MATCHING (SAME AS PYQ)
            logger.info("🎯 Applying context-aware semantic matching (same as PYQ)...")
            canonical_category, canonical_subcategory, canonical_type = await self._get_canonical_taxonomy_path_with_context(
                stem,  # Include original question
                enrichment_data.get('category', ''),
                enrichment_data.get('subcategory', ''),
                enrichment_data.get('type_of_question', '')
            )
            
            # Update with canonical values (same as PYQ)
            enrichment_data['category'] = canonical_category
            enrichment_data['subcategory'] = canonical_subcategory
            enrichment_data['type_of_question'] = canonical_type
            
            logger.info(f"✅ Semantic matching: {canonical_category} → {canonical_subcategory} → {canonical_type}")
            
            # Calculate PYQ frequency score (NEW FEATURE)
            logger.info("📊 Calculating PYQ frequency score using LLM...")
            pyq_frequency_result = await self._calculate_pyq_frequency_score_llm(stem, enrichment_data)
            enrichment_data['pyq_frequency_score'] = pyq_frequency_result
            
            # STAGE 4: Set concept extraction status based on core_concepts field (MUST BE BEFORE QUALITY VERIFICATION)
            core_concepts = enrichment_data.get('core_concepts', [])
            if core_concepts and len(core_concepts) > 0:
                enrichment_data['concept_extraction_status'] = 'completed'
                logger.info(f"✅ Concept extraction completed - found {len(core_concepts)} core concepts")
            else:
                enrichment_data['concept_extraction_status'] = 'pending'
                logger.warning(f"⚠️ Concept extraction incomplete - no core concepts found")
            
            # STAGE 5: QUALITY VERIFICATION (22 criteria including concept_extraction_status check)
            logger.info("🔍 Performing quality verification...")
            quality_result = await self._perform_quality_verification(
                stem, enrichment_data, current_answer, snap_read, solution_approach, 
                detailed_solution, principle_to_remember, mcq_options
            )
            enrichment_data.update(quality_result)
            
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
  "right_answer": "precise answer with mathematical reasoning",
  "category": "exact canonical category name",
  "subcategory": "exact canonical subcategory name",
  "type_of_question": "exact canonical question type name",
  "difficulty_band": "Easy/Medium/Hard",
  "difficulty_score": 3.2,
  "core_concepts": ["concept1", "concept2", "concept3"],
  "solution_method": "methodological approach",
  "concept_difficulty": {"prerequisites": ["req1"], "cognitive_barriers": ["barrier1"], "mastery_indicators": ["indicator1"]},
  "operations_required": ["operation1", "operation2"],
  "problem_structure": "structural_analysis_type",
  "concept_keywords": ["keyword1", "keyword2"]
}

Be precise, comprehensive, and use EXACT canonical taxonomy names."""

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
                
                # Apply 3-STEP CATEGORY POPULATION LOGIC (SAME AS PYQ)
                logger.info("🎯 Applying 3-step category population logic...")
                
                # Step 1: Context-aware semantic matching for all fields
                canonical_category, canonical_subcategory, canonical_type = await self._get_canonical_taxonomy_path_with_context(
                    stem,  # Include original question context
                    enrichment_data.get('category', ''),
                    enrichment_data.get('subcategory', ''),
                    enrichment_data.get('type_of_question', '')
                )
                
                # Step 2: If context-aware matching succeeded, use results directly
                if canonical_category and canonical_subcategory and canonical_type:
                    logger.info(f"✅ Context-aware matching successful: {canonical_category} → {canonical_subcategory} → {canonical_type}")
                else:
                    # Step 3: Fallback to subcategory → type → category lookup logic
                    logger.info("🔄 Using fallback subcategory → type → category lookup...")
                    
                    # Match subcategory without category constraint
                    canonical_subcategory = await canonical_taxonomy_service.match_subcategory_without_category(
                        enrichment_data.get('subcategory', '')
                    )
                    
                    # Match question type within found subcategory  
                    canonical_type = await canonical_taxonomy_service.match_question_type_within_subcategory(
                        enrichment_data.get('type_of_question', ''), 
                        canonical_subcategory
                    )
                    
                    # Code-based category lookup using subcategory + type combination
                    canonical_category = canonical_taxonomy_service.lookup_category_by_combination(
                        canonical_subcategory, 
                        canonical_type
                    )
                    
                    logger.info(f"✅ 3-step lookup: Subcategory({canonical_subcategory}) + Type({canonical_type}) → Category({canonical_category})")
                
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
        Filters PYQ questions by: category x subcategory match (only compares if regular question difficulty_score > 1.5)
        """
        try:
            from database import get_async_compatible_db, PYQQuestion
            from sqlalchemy import select
            import json
            
            # Get category, subcategory, and difficulty from enrichment data
            category = enrichment_data.get('category', '')
            subcategory = enrichment_data.get('subcategory', '')
            regular_difficulty = enrichment_data.get('difficulty_score', 0)
            
            # CRITICAL FIX: Apply difficulty filter to REGULAR question, not PYQ questions
            if regular_difficulty <= 1.5:
                logger.info(f"🎯 Regular question difficulty ({regular_difficulty}) ≤ 1.5, skipping PYQ frequency calculation")
                return 0.5  # Return default LOW frequency for easy questions
            
            logger.info(f"🔍 Getting qualifying PYQ questions for category='{category}', subcategory='{subcategory}'")
            logger.info(f"🎯 Regular question difficulty: {regular_difficulty} > 1.5 ✅")
            
            # Get database session using SessionLocal directly (synchronous approach)
            from database import SessionLocal
            db = SessionLocal()
            try:
                # Get qualifying PYQ questions from database - REMOVED difficulty filter on PYQ questions
                result = db.execute(
                    select(PYQQuestion).where(
                        and_(
                            # REMOVED: PYQQuestion.difficulty_score > 1.5,  # This was the bug!
                            PYQQuestion.category == category,              # Category match
                            PYQQuestion.subcategory == subcategory,        # Subcategory match
                            PYQQuestion.is_active == True,
                            PYQQuestion.quality_verified == True,
                            PYQQuestion.problem_structure.isnot(None),
                            PYQQuestion.concept_keywords.isnot(None)
                        )
                    )
                )
                qualifying_pyqs = result.scalars().all()
                
                if not qualifying_pyqs:
                    logger.warning(f"⚠️ No qualifying PYQ questions found for category='{category}', subcategory='{subcategory}'")
                    return 0.5  # Default to LOW
                
                logger.info(f"📊 Found {len(qualifying_pyqs)} category x subcategory filtered PYQ questions")
                
                # Prepare regular question data (now includes category x subcategory)
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
                db.close()
                
        except Exception as e:
            logger.error(f"❌ PYQ frequency calculation failed: {e}")
            return 0.5  # Default to LOW on error

    async def _perform_semantic_answer_matching(self, llm_right_answer: str, csv_answer: str) -> bool:
        """
        Perform semantic matching between LLM right_answer and CSV answer
        Returns True if semantic match found, False otherwise
        """
        try:
            logger.info("🧠 Performing semantic answer matching...")
            
            if not llm_right_answer or not csv_answer:
                logger.warning("⚠️ Missing answer data for semantic matching")
                return False
            
            system_message = """You are a mathematical answer verification expert.

Your task is to determine if two mathematical answers are semantically equivalent, even if they differ in format or presentation.

SEMANTIC MATCHING CRITERIA:
- Same mathematical value/result
- Equivalent mathematical expressions
- Same units (if applicable)
- Different formats but same meaning (e.g., "2.5" vs "5/2" vs "2½")
- Different presentation but same solution (e.g., detailed vs concise)

EXAMPLES OF MATCHES:
- "48 km/h" ↔ "48 kilometers per hour"
- "2.5 hours" ↔ "2 hours 30 minutes"  
- "₹2,490" ↔ "Rs. 2490"
- "12.5%" ↔ "12.5 percent"
- "30" ↔ "30 units"

Return ONLY:
- "MATCH" if the answers are semantically equivalent
- "NO_MATCH" if the answers are different or incompatible"""

            user_message = f"""CSV Answer: {csv_answer}
LLM Answer: {llm_right_answer}

Are these two answers semantically equivalent?"""

            for attempt in range(self.max_retries):
                try:
                    logger.info(f"🧠 Semantic matching attempt {attempt + 1}...")
                    
                    matching_text, model_used = await call_llm_with_fallback(
                        self, system_message, user_message, max_tokens=50, temperature=0.1
                    )
                    
                    if not matching_text:
                        raise Exception("LLM returned empty response")
                    
                    response = matching_text.strip().upper()
                    
                    if response == "MATCH":
                        logger.info(f"✅ Semantic match found: '{csv_answer}' ↔ '{llm_right_answer}' ({model_used})")
                        return True
                    elif response == "NO_MATCH":
                        logger.info(f"❌ No semantic match: '{csv_answer}' ≠ '{llm_right_answer}' ({model_used})")
                        return False
                    else:
                        logger.warning(f"⚠️ Invalid LLM response: '{response}' (attempt {attempt + 1})")
                        if attempt == self.max_retries - 1:
                            return False
                        continue
                        
                except Exception as e:
                    logger.error(f"⚠️ Semantic matching attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.max_retries - 1:
                        logger.error("❌ All semantic matching attempts failed")
                        return False
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Semantic answer matching failed: {e}")
            return False

    async def _perform_quality_verification(self, stem: str, enrichment_data: Dict[str, Any], csv_answer: str = None, snap_read: str = None, solution_approach: str = None, detailed_solution: str = None, principle_to_remember: str = None, mcq_options: str = None) -> Dict[str, Any]:
        """
        Perform comprehensive quality verification
        Checks 20 fields + answer_match = 21 total criteria
        """
        
        try:
            logger.info("🔍 Comprehensive quality verification (21 criteria)")
            
            # STEP 1: Semantic Answer Matching
            logger.info("🧠 Step 1: Semantic answer matching...")
            llm_right_answer = enrichment_data.get('right_answer', '')
            answer_match = await self._perform_semantic_answer_matching(llm_right_answer, csv_answer or '')
            enrichment_data['answer_match'] = answer_match
            
            # STEP 2: Check all 20 required fields are present and meaningful
            logger.info("📋 Step 2: Checking 20 required fields...")
            required_fields = [
                # CSV Upload Fields (8 fields)
                'stem', 'snap_read', 'solution_approach', 'detailed_solution', 
                'principle_to_remember', 'answer', 'mcq_options',
                
                # LLM Generated Fields (12 fields)  
                'right_answer', 'category', 'subcategory', 'type_of_question',
                'difficulty_score', 'difficulty_band', 'core_concepts', 'concept_difficulty',
                'operations_required', 'problem_structure', 'concept_keywords', 
                'solution_method', 'pyq_frequency_score'
            ]
            
            # Add all CSV fields to enrichment_data for verification  
            enrichment_data['stem'] = stem
            enrichment_data['answer'] = csv_answer or ''
            enrichment_data['snap_read'] = snap_read or ''
            enrichment_data['solution_approach'] = solution_approach or ''
            enrichment_data['detailed_solution'] = detailed_solution or ''
            enrichment_data['principle_to_remember'] = principle_to_remember or ''
            enrichment_data['mcq_options'] = mcq_options or ''
            
            missing_or_invalid_fields = []
            for field in required_fields:
                value = enrichment_data.get(field)
                
                # Check: Not Null AND Not Empty String AND Not Placeholder
                if (value is None or 
                    value == '' or 
                    value in ['To be classified by LLM', 'N/A', 'null', 'None']):
                    missing_or_invalid_fields.append(field)
            
            # STEP 3: Check answer_match = True
            logger.info("🎯 Step 3: Checking answer_match = True...")
            if not answer_match:
                logger.error("❌ Quality verification failed - answer_match is False")
                return {'quality_verified': False, 'answer_match': False}
            
            # STEP 4: Final verification + concept_extraction_status check
            if missing_or_invalid_fields:
                logger.error(f"❌ Quality verification failed - missing/invalid fields: {missing_or_invalid_fields}")
                return {'quality_verified': False, 'answer_match': answer_match}
            
            # NEW: Check that concept_extraction_status is 'completed' (don't set it, just verify)
            concept_status = enrichment_data.get('concept_extraction_status', '')
            if concept_status != 'completed':
                logger.error(f"❌ Quality verification failed - concept_extraction_status is '{concept_status}', expected 'completed'")
                return {'quality_verified': False, 'answer_match': answer_match}
            
            logger.info("✅ Quality verification passed - all 22 criteria met (21 fields + concept_extraction_status = 'completed')")
            return {'quality_verified': True, 'answer_match': True}
            
        except Exception as e:
            logger.error(f"❌ Quality verification exception: {e}")
            return {
                'quality_verified': False
            }

    async def trigger_manual_enrichment(self, db) -> Dict[str, Any]:
        """
        Trigger manual enrichment process for untouched regular questions
        """
        try:
            logger.info("🚀 Starting manual enrichment trigger for regular questions...")
            
            # Get questions that need enrichment (correct criteria!)
            from sqlalchemy import select, and_, or_
            from database import Question
            
            result = db.execute(
                select(Question).where(
                    or_(
                        Question.subcategory == 'To be enriched',
                        Question.subcategory == 'null',
                        Question.subcategory == '',
                        Question.subcategory.is_(None)
                    )
                )
            )
            
            untouched_questions = result.scalars().all()
            untouched_count = len(untouched_questions)
            
            logger.info(f"📊 Found {untouched_count} questions needing enrichment (subcategory = 'To be enriched')")
            
            if untouched_count == 0:
                return {
                    "status": "success",
                    "message": "No questions found needing enrichment (subcategory criteria)",
                    "details": {
                        "questions_found": 0,
                        "questions_processed": 0
                    }
                }
            
            # Process each question
            processed_count = 0
            failed_count = 0
            
            for question in untouched_questions:
                try:
                    logger.info(f"🔄 Processing question ID: {question.id[:8]}...")
                    
                    # Enrich the question
                    enrichment_result = await self.enrich_regular_question(
                        stem=question.stem,
                        current_answer=question.answer,  # Use CSV answer field, not right_answer
                        snap_read=question.snap_read,
                        solution_approach=question.solution_approach,
                        detailed_solution=question.detailed_solution,
                        principle_to_remember=question.principle_to_remember,
                        mcq_options=question.mcq_options  # Add missing mcq_options parameter
                    )
                    
                    # Always update enrichment data from LLM (regardless of quality verification)
                    for field, value in enrichment_result.get('enrichment_data', {}).items():
                        if hasattr(question, field) and field not in ['quality_verified', 'concept_extraction_status']:
                            setattr(question, field, value)
                    
                    # Commit enrichment data immediately (incremental commits)
                    db.commit()
                    logger.info(f"✅ Committed enrichment data for question {question.id[:8]}")
                    
                    if enrichment_result.get('quality_verified'):
                        # Only set quality flags if verification passed
                        question.quality_verified = True
                        question.concept_extraction_status = 'completed'
                        question.is_active = True  # Activate the question
                        
                        # Commit quality verification flags
                        db.commit()
                        logger.info(f"✅ Successfully enriched and activated question {question.id[:8]}")
                        processed_count += 1
                    else:
                        # Enrichment data is saved, but quality verification failed
                        logger.warning(f"⚠️ Question {question.id[:8]} enriched but failed quality verification")
                        failed_count += 1
                
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Error processing question {question.id[:8]}: {e}")
            
            # Final summary (no final commit needed - already committed incrementally)
            logger.info(f"🎉 Manual enrichment completed: {processed_count} processed, {failed_count} failed")
            
            return {
                "status": "success", 
                "message": f"Manual enrichment completed successfully",
                "details": {
                    "questions_found": untouched_count,
                    "questions_processed": processed_count,
                    "questions_failed": failed_count,
                    "success_rate": f"{(processed_count/untouched_count)*100:.1f}%" if untouched_count > 0 else "0%"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Manual enrichment trigger failed: {e}")
            return {
                "status": "error",
                "message": f"Manual enrichment failed: {str(e)}"
            }

    async def get_enrichment_status(self, db) -> Dict[str, Any]:
        """
        Get current enrichment status for regular questions
        """
        try:
            from sqlalchemy import select, func
            from database import Question
            
            # Total questions
            total_result = db.execute(select(func.count(Question.id)))
            total_questions = total_result.scalar()
            
            # Quality verified questions
            verified_result = db.execute(
                select(func.count(Question.id)).where(Question.quality_verified == True)
            )
            verified_questions = verified_result.scalar()
            
            # Completed questions
            completed_result = db.execute(
                select(func.count(Question.id)).where(Question.concept_extraction_status == 'completed')
            )
            completed_questions = completed_result.scalar()
            
            # Questions needing enrichment (correct criteria)
            needing_enrichment_result = db.execute(
                select(func.count(Question.id)).where(
                    or_(
                        Question.subcategory == 'To be enriched',
                        Question.subcategory == 'null',
                        Question.subcategory == '',
                        Question.subcategory.is_(None)
                    )
                )
            )
            needing_enrichment = needing_enrichment_result.scalar()
            
            return {
                "status": "success",
                "data": {
                    "total_questions": total_questions,
                    "quality_verified": verified_questions,
                    "concept_completed": completed_questions,
                    "untouched": needing_enrichment,
                    "verification_rate": f"{(verified_questions/total_questions)*100:.1f}%" if total_questions > 0 else "0%",
                    "completion_rate": f"{(completed_questions/total_questions)*100:.1f}%" if total_questions > 0 else "0%"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting enrichment status: {e}")
            return {
                "status": "error",
                "message": f"Failed to get enrichment status: {str(e)}"
            }

# Global instance
regular_questions_enrichment_service = RegularQuestionsEnrichmentService()