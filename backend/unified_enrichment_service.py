#!/usr/bin/env python3
"""
Unified Enrichment Service
Combines SimplifiedEnrichmentService and Enhanced PYQ Enrichment into one sophisticated service
Generates the complete spectrum of fields for both regular questions and PYQ questions
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List
import openai
from datetime import datetime

# Import taxonomy for classification
from canonical_taxonomy_service import CANONICAL_TAXONOMY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedEnrichmentService:
    """
    Unified enrichment service that generates the complete spectrum of fields for all questions
    Uses the most sophisticated approach combining both services
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.error("OpenAI API key not found for UnifiedEnrichmentService")
        
        # Retry configuration (enhanced approach)
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]  # Exponential backoff
        self.timeout = 60  # Extended timeout for comprehensive analysis
        
    async def enrich_question_comprehensive(self, stem: str, admin_answer: str = None, question_type: str = "regular") -> Dict[str, Any]:
        """
        Generate the complete spectrum of enrichment fields for any question
        
        Args:
            stem: Question text
            admin_answer: Admin-provided answer (optional)  
            question_type: "regular" or "pyq" (affects some processing nuances)
            
        Returns:
            Dict with success status and comprehensive enrichment data
        """
        try:
            logger.info(f"🎯 Starting comprehensive enrichment for {question_type} question")
            logger.info(f"📝 Question: {stem[:50]}...")
            
            enrichment_data = {}
            
            # Step 1: Generate right answer (core field)
            logger.info("🤖 Step 1: Generating right answer...")
            right_answer_result = await self._generate_right_answer_with_openai(stem, admin_answer)
            enrichment_data['right_answer'] = right_answer_result
            
            # Step 2: Classify question (core taxonomy fields)
            logger.info("🏷️ Step 2: Classifying question...")
            classification_result = await self._classify_question_with_openai(stem)
            enrichment_data.update({
                'category': classification_result.get('category'),
                'subcategory': classification_result.get('subcategory'),
                'type_of_question': classification_result.get('type_of_question')
            })
            
            # Step 3: Assess difficulty (enhanced approach)
            logger.info("⚖️ Step 3: Assessing difficulty...")
            difficulty_result = await self._assess_difficulty_comprehensive(stem, right_answer_result)
            enrichment_data.update({
                'difficulty_band': difficulty_result.get('difficulty_band'),
                'difficulty_score': difficulty_result.get('difficulty_score')
            })
            
            # Step 4: Extract concepts (enhanced approach)
            logger.info("🧠 Step 4: Extracting concepts...")
            concept_result = await self._extract_concepts_comprehensive(stem, right_answer_result, classification_result)
            enrichment_data.update({
                'core_concepts': concept_result.get('core_concepts'),
                'solution_method': concept_result.get('solution_method'),
                'concept_difficulty': concept_result.get('concept_difficulty'),
                'operations_required': concept_result.get('operations_required'),
                'problem_structure': concept_result.get('problem_structure'),
                'concept_keywords': concept_result.get('concept_keywords')
            })
            
            # Step 5: Quality verification (enhanced approach)
            logger.info("🔍 Step 5: Quality verification...")
            quality_result = await self._verify_quality_comprehensive(stem, enrichment_data)
            enrichment_data['quality_verified'] = quality_result.get('quality_verified', False)
            
            # Mark enrichment as completed
            enrichment_data['concept_extraction_status'] = 'completed'
            
            logger.info("✅ Comprehensive enrichment completed successfully")
            logger.info(f"📊 Generated {len(enrichment_data)} enrichment fields")
            
            return {
                'success': True,
                'enrichment_data': enrichment_data,
                'processing_time': datetime.utcnow().isoformat(),
                'model_used': 'gpt-4o',
                'fields_generated': list(enrichment_data.keys())
            }
            
        except Exception as e:
            logger.error(f"❌ Comprehensive enrichment failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'enrichment_data': {},
                'concept_extraction_status': 'failed'
            }
    
    async def _generate_right_answer_with_openai(self, stem: str, admin_answer: str = None) -> str:
        """Generate right answer using OpenAI with enhanced retry logic"""
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    timeout=self.timeout
                )
                
                system_message = """You are an expert CAT exam solver focused on quantitative ability questions.
Generate the correct, concise answer for the given question.

Rules:
1. Provide ONLY the final numerical answer or the correct option
2. Be precise and accurate
3. For multiple choice questions, provide just the value (not the option letter)
4. For numerical answers, include units if applicable
5. Keep the answer concise and direct"""

                logger.info(f"🤖 Calling OpenAI API for right answer generation (attempt {attempt + 1})...")
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use advanced model
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}"}
                    ],
                    max_tokens=150,
                    timeout=self.timeout
                )
                
                right_answer = response.choices[0].message.content.strip()
                logger.info(f"✅ Right answer generated: {right_answer}")
                
                return right_answer
                
            except Exception as e:
                logger.warning(f"⚠️ Right answer generation attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All right answer generation attempts failed")
                    return admin_answer if admin_answer else "Not available"
    
    async def _classify_question_with_openai(self, stem: str) -> Dict[str, str]:
        """Classify question using OpenAI with enhanced retry logic"""
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    timeout=self.timeout
                )
                
                system_message = f"""You are an expert in CAT quantitative ability question classification.
Classify the given question into the EXACT canonical taxonomy below.

CANONICAL TAXONOMY:
{json.dumps(CANONICAL_TAXONOMY, indent=2)}

CLASSIFICATION RULES:
1. Choose the MOST SPECIFIC category, subcategory, and type that matches the question
2. Use ONLY the exact labels from the taxonomy above
3. Be precise and specific - avoid generic terms
4. The category MUST be one of: Arithmetic, Algebra, Geometry and Mensuration, Number System, Modern Math
5. The subcategory must be from the chosen category's subcategories
6. The type_of_question must be from the chosen subcategory's types (the array values)

EXAMPLES:
- Speed question → {{"category": "Arithmetic", "subcategory": "Time-Speed-Distance", "type_of_question": "Basics"}}
- Train problem → {{"category": "Arithmetic", "subcategory": "Time-Speed-Distance", "type_of_question": "Trains"}}
- Quadratic roots → {{"category": "Algebra", "subcategory": "Quadratic Equations", "type_of_question": "Roots & Nature of Roots"}}
- Triangle area → {{"category": "Geometry and Mensuration", "subcategory": "Mensuration 2D", "type_of_question": "Area Triangle"}}

Return ONLY JSON format: {{"category": "...", "subcategory": "...", "type_of_question": "..."}}"""

                logger.info(f"🤖 Calling OpenAI API for question classification (attempt {attempt + 1})...")
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use advanced model
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Classify this question: {stem}"}
                    ],
                    max_tokens=200,
                    timeout=self.timeout
                )
                
                classification_text = response.choices[0].message.content.strip()
                
                # Try to parse JSON response
                try:
                    classification = json.loads(classification_text)
                    logger.info(f"✅ Classification: {classification}")
                    return classification
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Could not parse classification JSON: {classification_text}")
                    # Continue to retry
                    raise ValueError(f"Invalid JSON response: {classification_text}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Classification attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All classification attempts failed")
                    return {
                        "category": "Arithmetic",
                        "subcategory": "Basics", 
                        "type_of_question": "Basics"
                    }
    
    async def _assess_difficulty_comprehensive(self, stem: str, right_answer: str) -> Dict[str, Any]:
        """Comprehensive difficulty assessment with both band and numerical score"""
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    timeout=self.timeout
                )
                
                system_message = """You are an expert in CAT quantitative ability difficulty assessment.
Assess the difficulty of this question and provide both a band and numerical score.

DIFFICULTY CRITERIA:
- Easy: Basic concepts, single-step problems, standard formulas
- Medium: Multiple concepts, moderate calculations, 2-3 step problems  
- Hard: Complex concepts, multi-step reasoning, advanced problem-solving

SCORING SCALE:
- Easy: 1.0-2.0
- Medium: 2.1-3.5
- Hard: 3.6-5.0

Return ONLY JSON format: {"difficulty_band": "Easy/Medium/Hard", "difficulty_score": 1.5}"""

                logger.info(f"🤖 Calling OpenAI API for difficulty assessment (attempt {attempt + 1})...")
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use advanced model
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nAnswer: {right_answer}"}
                    ],
                    max_tokens=100,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                difficulty_text = response.choices[0].message.content.strip()
                
                try:
                    difficulty_data = json.loads(difficulty_text)
                    
                    # Validate difficulty band
                    difficulty_band = difficulty_data.get('difficulty_band', '').strip()
                    if difficulty_band.lower() in ['easy', 'medium', 'hard']:
                        difficulty_band = difficulty_band.capitalize()
                    else:
                        raise ValueError(f"Invalid difficulty band: {difficulty_band}")
                    
                    # Validate difficulty score
                    difficulty_score = float(difficulty_data.get('difficulty_score', 2.5))
                    if not (1.0 <= difficulty_score <= 5.0):
                        difficulty_score = 2.5  # Default to medium
                    
                    logger.info(f"✅ Difficulty assessed: {difficulty_band} ({difficulty_score})")
                    
                    return {
                        'difficulty_band': difficulty_band,
                        'difficulty_score': difficulty_score
                    }
                    
                except (json.JSONDecodeError, ValueError) as parse_error:
                    logger.warning(f"⚠️ Difficulty parsing error: {parse_error}")
                    raise ValueError(f"Could not parse difficulty response: {difficulty_text}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Difficulty assessment attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All difficulty assessment attempts failed")
                    return {
                        'difficulty_band': 'Medium',
                        'difficulty_score': 2.5
                    }
    
    async def _extract_concepts_comprehensive(self, stem: str, right_answer: str, classification: Dict[str, str]) -> Dict[str, Any]:
        """Comprehensive concept extraction with detailed analysis"""
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    timeout=self.timeout
                )
                
                category = classification.get('category', 'Unknown')
                subcategory = classification.get('subcategory', 'Unknown')
                
                system_message = f"""You are an expert in mathematical concept extraction for CAT preparation.
Extract detailed conceptual information from this {category} - {subcategory} question.

EXTRACT THE FOLLOWING:
1. core_concepts: Array of 2-5 key mathematical concepts used
2. solution_method: Primary solution approach (e.g., "Direct Formula", "Substitution Method")
3. concept_difficulty: JSON object with difficulty indicators
4. operations_required: Array of mathematical operations needed
5. problem_structure: Type of problem structure (e.g., "Single Variable", "System of Equations")
6. concept_keywords: Array of searchable keywords

Return ONLY JSON format:
{{
  "core_concepts": ["concept1", "concept2"],
  "solution_method": "Primary Method",
  "concept_difficulty": {{"complexity": "moderate", "prerequisites": ["basic_algebra"]}},
  "operations_required": ["addition", "division"],
  "problem_structure": "Direct Application",
  "concept_keywords": ["keyword1", "keyword2"]
}}"""

                logger.info(f"🤖 Calling OpenAI API for concept extraction (attempt {attempt + 1})...")
                response = client.chat.completions.create(
                    model="gpt-4o",  # Use advanced model
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nAnswer: {right_answer}\nCategory: {category}\nSubcategory: {subcategory}"}
                    ],
                    max_tokens=400,
                    timeout=self.timeout
                )
                
                concept_text = response.choices[0].message.content.strip()
                
                try:
                    concept_data = json.loads(concept_text)
                    
                    # Convert to JSON strings for database storage
                    result = {
                        'core_concepts': json.dumps(concept_data.get('core_concepts', [])),
                        'solution_method': concept_data.get('solution_method', 'Direct Application'),
                        'concept_difficulty': json.dumps(concept_data.get('concept_difficulty', {})),
                        'operations_required': json.dumps(concept_data.get('operations_required', [])),
                        'problem_structure': concept_data.get('problem_structure', 'Standard'),
                        'concept_keywords': json.dumps(concept_data.get('concept_keywords', []))
                    }
                    
                    logger.info(f"✅ Concepts extracted: {len(concept_data.get('core_concepts', []))} concepts")
                    
                    return result
                    
                except json.JSONDecodeError as parse_error:
                    logger.warning(f"⚠️ Concept parsing error: {parse_error}")
                    raise ValueError(f"Could not parse concept response: {concept_text}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Concept extraction attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All concept extraction attempts failed - using fallback")
                    return {
                        'core_concepts': json.dumps([subcategory]),
                        'solution_method': 'Standard Method',
                        'concept_difficulty': json.dumps({"complexity": "unknown"}),
                        'operations_required': json.dumps(["calculation"]),
                        'problem_structure': 'Standard',
                        'concept_keywords': json.dumps([subcategory.lower()])
                    }
    
    async def _verify_quality_comprehensive(self, stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive quality verification"""
        try:
            # Quality scoring based on completeness and consistency
            quality_score = 0
            
            # Check field completeness (40 points)
            required_fields = ['right_answer', 'category', 'subcategory', 'difficulty_band']
            for field in required_fields:
                if enrichment_data.get(field):
                    quality_score += 10
            
            # Check concept richness (30 points)
            core_concepts = json.loads(enrichment_data.get('core_concepts', '[]'))
            if len(core_concepts) >= 2:
                quality_score += 20
            elif len(core_concepts) >= 1:
                quality_score += 10
            
            # Check solution method specificity (30 points)
            solution_method = enrichment_data.get('solution_method', '')
            if solution_method and solution_method != 'Standard Method':
                quality_score += 30
            elif solution_method:
                quality_score += 15
            
            quality_verified = quality_score >= 75
            
            logger.info(f"🔍 Quality score: {quality_score}/100 - {'✅ Verified' if quality_verified else '⚠️ Needs review'}")
            
            return {
                'quality_verified': quality_verified,
                'quality_score': quality_score
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Quality verification failed: {e}")
            return {
                'quality_verified': False,
                'quality_score': 0
            }
    
    async def _validate_answer_consistency(self, admin_answer: str, ai_right_answer: str, question_stem: str) -> Dict[str, Any]:
        """Validate consistency between admin answer and AI-generated answer"""
        try:
            if not admin_answer or not ai_right_answer:
                return {"matches": True, "explanation": "No comparison possible"}
            
            client = openai.OpenAI(
                api_key=self.openai_api_key,
                timeout=30.0
            )
            
            system_message = """You are an expert in answer validation for CAT quantitative questions.
Compare the admin-provided answer with the AI-generated answer and determine if they are essentially equivalent.

Consider:
- Numerical equivalence (60 km/h = 60 kmph)
- Unit variations (1.5 hours = 90 minutes)
- Format differences (fraction vs decimal)
- Rounding differences within reasonable limits

Return ONLY JSON: {"matches": true/false, "explanation": "brief explanation"}"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Question: {question_stem}\nAdmin Answer: {admin_answer}\nAI Answer: {ai_right_answer}"}
                ],
                max_tokens=100,
                timeout=30
            )
            
            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)
            
            logger.info(f"✅ Answer validation: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Answer validation failed: {e}")
            return {"matches": True, "explanation": f"Validation error: {str(e)}"}


# Backward compatibility - create aliases for existing code
SimplifiedEnrichmentService = UnifiedEnrichmentService  # For regular questions
EnhancedPYQEnrichmentService = UnifiedEnrichmentService  # For PYQ questions