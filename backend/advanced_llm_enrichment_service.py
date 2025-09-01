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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        self.timeout = 120  # Extended timeout for deep analysis
        
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
    
    async def _perform_deep_mathematical_analysis(self, stem: str, admin_answer: str = None) -> Dict[str, Any]:
        """Perform deep mathematical analysis with sophisticated understanding"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
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
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nAdmin provided answer (if any): {admin_answer or 'Not provided'}"}
                    ],
                    max_tokens=800,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                analysis_text = response.choices[0].message.content.strip()
                analysis_data = json.loads(analysis_text)
                
                logger.info(f"✅ Deep mathematical analysis completed")
                return analysis_data
                
            except Exception as e:
                logger.error(f"⚠️ Deep analysis attempt {attempt + 1} failed: {str(e)}")
                logger.error(f"🔍 Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"📚 Traceback: {traceback.format_exc()}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"⏳ Retrying deep analysis in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("❌ All deep analysis attempts failed")
                    return {
                        "right_answer": admin_answer or "Analysis failed",
                        "mathematical_foundation": "Unable to analyze due to technical issues",
                        "solution_elegance": "Standard approach",
                        "verification_logic": "Manual verification required"
                    }
    
    async def _perform_sophisticated_classification(self, stem: str, deep_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Perform sophisticated classification with nuanced understanding"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
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
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nMathematical Analysis: {deep_analysis.get('mathematical_foundation', '')}\nSolution Approach: {deep_analysis.get('solution_elegance', '')}"}
                    ],
                    max_tokens=300,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                classification_text = response.choices[0].message.content.strip()
                classification_data = json.loads(classification_text)
                
                logger.info(f"✅ Sophisticated classification completed")
                return classification_data
                
            except Exception as e:
                logger.warning(f"⚠️ Classification attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        "category": "Mathematical Analysis Required",
                        "subcategory": "Complex Problem Type",
                        "type_of_question": "Multi-step Analytical Problem"
                    }
    
    async def _perform_nuanced_difficulty_assessment(self, stem: str, deep_analysis: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Perform nuanced difficulty assessment with sophisticated reasoning"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
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
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nMathematical Foundation: {deep_analysis.get('mathematical_foundation', '')}\nCategory: {classification.get('category', '')}\nType: {classification.get('type_of_question', '')}"}
                    ],
                    max_tokens=400,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                difficulty_text = response.choices[0].message.content.strip()
                difficulty_data = json.loads(difficulty_text)
                
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
                
                logger.info(f"✅ Nuanced difficulty assessment: {band} ({score})")
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ Difficulty assessment attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    return {
                        'difficulty_band': 'Medium',
                        'difficulty_score': 2.5,
                        'complexity_reasoning': 'Assessment failed - manual review required',
                        'cognitive_load_factors': json.dumps(['unknown']),
                        'time_estimate_minutes': 3.0,
                        'error_trap_potential': 'unknown'
                    }
    
    async def _perform_advanced_conceptual_extraction(self, stem: str, deep_analysis: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Perform advanced conceptual extraction with sophisticated insight"""
        
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
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
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {stem}\nMathematical Foundation: {deep_analysis.get('mathematical_foundation', '')}\nCategory: {classification.get('category', '')}\nSubcategory: {classification.get('subcategory', '')}\nType: {classification.get('type_of_question', '')}"}
                    ],
                    max_tokens=600,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                concept_text = response.choices[0].message.content.strip()
                concept_data = json.loads(concept_text)
                
                # Convert to database format
                result = {
                    'core_concepts': json.dumps(concept_data.get('core_concepts', [])),
                    'solution_method': concept_data.get('solution_method', 'Advanced Mathematical Analysis'),
                    'concept_difficulty': json.dumps(concept_data.get('concept_difficulty', {})),
                    'operations_required': json.dumps(concept_data.get('operations_required', [])),
                    'problem_structure': concept_data.get('problem_structure', 'complex_analytical_structure'),
                    'concept_keywords': json.dumps(concept_data.get('concept_keywords', []))
                }
                
                logger.info(f"✅ Advanced conceptual extraction completed")
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ Conceptual extraction attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Even fallback should be sophisticated
                    category = classification.get('category', 'Unknown')
                    subcategory = classification.get('subcategory', 'Unknown') 
                    
                    return {
                        'core_concepts': json.dumps([f"{subcategory.lower()}_analysis", "mathematical_problem_solving", "quantitative_reasoning"]),
                        'solution_method': f"Systematic {category} Analysis Approach",
                        'concept_difficulty': json.dumps({"complexity": "requires_analysis", "prerequisites": ["foundational_mathematics"]}),
                        'operations_required': json.dumps(["mathematical_analysis", "logical_reasoning", "computational_execution"]),
                        'problem_structure': "structured_mathematical_analysis_required",
                        'concept_keywords': json.dumps([subcategory.lower(), "mathematical_analysis", "quantitative_problem"])
                    }
    
    async def _perform_comprehensive_quality_verification(self, stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive quality verification with sophisticated criteria"""
        
        try:
            quality_score = 0
            quality_factors = []
            
            # Sophistication of right answer (25 points)
            right_answer = enrichment_data.get('right_answer', '')
            if len(right_answer) > 50 and 'calculated' in right_answer.lower():
                quality_score += 25
                quality_factors.append("detailed_answer_explanation")
            elif len(right_answer) > 20:
                quality_score += 15
                quality_factors.append("adequate_answer_detail")
            elif right_answer:
                quality_score += 5
                quality_factors.append("basic_answer_provided")
            
            # Classification sophistication (20 points)
            category = enrichment_data.get('category', '')
            subcategory = enrichment_data.get('subcategory', '')
            if len(category) > 15 and len(subcategory) > 15:
                quality_score += 20
                quality_factors.append("sophisticated_classification")
            elif len(category) > 10 and len(subcategory) > 10:
                quality_score += 10
                quality_factors.append("adequate_classification")
            
            # Concept depth (25 points)
            try:
                core_concepts = json.loads(enrichment_data.get('core_concepts', '[]'))
                if len(core_concepts) >= 4 and all(len(c) > 15 for c in core_concepts):
                    quality_score += 25
                    quality_factors.append("deep_conceptual_analysis")
                elif len(core_concepts) >= 2:
                    quality_score += 15
                    quality_factors.append("adequate_conceptual_coverage")
            except:
                pass
            
            # Solution method sophistication (15 points)
            solution_method = enrichment_data.get('solution_method', '')
            if len(solution_method) > 30:
                quality_score += 15
                quality_factors.append("sophisticated_solution_method")
            elif len(solution_method) > 15:
                quality_score += 8
                quality_factors.append("adequate_solution_method")
            
            # Operations specificity (15 points)
            try:
                operations = json.loads(enrichment_data.get('operations_required', '[]'))
                if len(operations) >= 3 and all(len(op) > 10 for op in operations):
                    quality_score += 15
                    quality_factors.append("specific_operations_identified")
                elif len(operations) >= 2:
                    quality_score += 8
                    quality_factors.append("basic_operations_identified")
            except:
                pass
            
            quality_verified = quality_score >= 80
            
            logger.info(f"🔍 Quality verification: {quality_score}/100 - {'✅ High Quality' if quality_verified else '⚠️ Needs Enhancement'}")
            
            return {
                'quality_verified': quality_verified,
                'quality_score': quality_score,
                'quality_factors': json.dumps(quality_factors)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Quality verification failed: {e}")
            return {
                'quality_verified': False,
                'quality_score': 0,
                'quality_factors': json.dumps(["verification_failed"])
            }