#!/usr/bin/env python3
"""
Enrich Checker Service
LLM-based quality assessment system that identifies poorly enriched questions
and triggers re-enrichment using the Advanced LLM Enrichment Service
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Tuple
import openai
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import Question, PYQQuestion
from advanced_llm_enrichment_service import AdvancedLLMEnrichmentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnrichCheckerService:
    """
    LLM-based quality checker that evaluates enrichment quality and triggers re-enrichment
    """
    
    def __init__(self):
        # Load environment variables with explicit path
        from dotenv import load_dotenv
        import os
        
        # Try to load from backend directory
        backend_env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(backend_env_path)
        
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.warning(f"Attempting to load .env from: {backend_env_path}")
            # Fallback: try loading from current directory
            load_dotenv()
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.openai_api_key:
            raise ValueError(f"OpenAI API key not found for EnrichCheckerService. Checked paths: {backend_env_path}, current directory")
        
        self.advanced_enricher = AdvancedLLMEnrichmentService()
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]
        self.timeout = 120  # Increased timeout for GPT-4o latency
        
        # Inherit intelligent model switching from Advanced LLM Service
        self.primary_model = "gpt-4o"
        self.fallback_model = "gpt-4o-mini"
        
        logger.info("✅ EnrichCheckerService initialized successfully")
    
    async def check_and_enrich_regular_questions(self, db: Session, limit: int = None) -> Dict[str, Any]:
        """
        Check regular questions for enrichment quality and re-enrich poor ones
        
        Args:
            db: Database session
            limit: Optional limit on number of questions to check
            
        Returns:
            Dict with checking and re-enrichment results
        """
        try:
            logger.info("🔍 Starting Regular Questions Enrichment Quality Check...")
            
            # Get all regular questions
            query = select(Question).where(Question.is_active == True)
            if limit:
                query = query.limit(limit)
            
            result = db.execute(query)
            questions = result.scalars().all()
            
            logger.info(f"📊 Found {len(questions)} regular questions to check")
            
            # Check each question's enrichment quality
            check_results = {
                "total_questions_checked": len(questions),
                "poor_enrichment_identified": 0,
                "re_enrichment_attempted": 0,
                "re_enrichment_successful": 0,
                "re_enrichment_failed": 0,
                "quality_scores": [],
                "detailed_results": []
            }
            
            for i, question in enumerate(questions):
                logger.info(f"🔍 Checking question {i+1}/{len(questions)}: {question.stem[:50]}...")
                
                # Assess current enrichment quality
                quality_assessment = await self._assess_regular_question_quality(question)
                
                # Update results tracking
                check_results["quality_scores"].append(1 if quality_assessment["is_acceptable"] else 0)
                
                # If quality is unacceptable, re-enrich
                if not quality_assessment["is_acceptable"]:
                    logger.warning(f"⚠️ Unacceptable enrichment detected - failed criteria: {quality_assessment['failed_criteria']}")
                    check_results["poor_enrichment_identified"] += 1
                    
                    # Trigger re-enrichment
                    re_enrichment_result = await self._re_enrich_regular_question(question, db)
                    check_results["re_enrichment_attempted"] += 1
                    
                    if re_enrichment_result["success"]:
                        check_results["re_enrichment_successful"] += 1
                        logger.info("✅ Re-enrichment successful")
                    else:
                        check_results["re_enrichment_failed"] += 1
                        logger.error(f"❌ Re-enrichment failed: {re_enrichment_result['error']}")
                    
                    check_results["detailed_results"].append({
                        "question_id": question.id,
                        "stem": question.stem[:100],
                        "failed_criteria": quality_assessment["failed_criteria"],
                        "quality_issues": quality_assessment["quality_issues"],
                        "re_enrichment_success": re_enrichment_result["success"],
                        "re_enrichment_error": re_enrichment_result.get("error")
                    })
                else:
                    logger.info(f"✅ Perfect enrichment quality - all criteria met")
            
            # Calculate summary statistics
            perfect_quality_count = sum(check_results["quality_scores"])
            perfect_quality_percentage = (perfect_quality_count / len(check_results["quality_scores"])) * 100 if check_results["quality_scores"] else 0
            improvement_rate = (check_results["re_enrichment_successful"] / check_results["re_enrichment_attempted"]) * 100 if check_results["re_enrichment_attempted"] > 0 else 0
            
            check_results.update({
                "perfect_quality_count": perfect_quality_count,
                "perfect_quality_percentage": round(perfect_quality_percentage, 2),
                "improvement_rate_percentage": round(improvement_rate, 2),
                "processing_completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info("🎉 Regular Questions Enrichment Check completed!")
            return {
                "success": True,
                "check_results": check_results
            }
            
        except Exception as e:
            logger.error(f"❌ Regular Questions Enrichment Check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_and_enrich_pyq_questions(self, db: Session, limit: int = None) -> Dict[str, Any]:
        """
        Check PYQ questions for enrichment quality and re-enrich poor ones
        
        Args:
            db: Database session
            limit: Optional limit on number of questions to check
            
        Returns:
            Dict with checking and re-enrichment results
        """
        try:
            logger.info("🔍 Starting PYQ Questions Enrichment Quality Check...")
            
            # Get all PYQ questions
            query = select(PYQQuestion).where(PYQQuestion.is_active == True)
            if limit:
                query = query.limit(limit)
            
            result = db.execute(query)
            pyq_questions = result.scalars().all()
            
            logger.info(f"📊 Found {len(pyq_questions)} PYQ questions to check")
            
            # Check each question's enrichment quality
            check_results = {
                "total_questions_checked": len(pyq_questions),
                "poor_enrichment_identified": 0,
                "re_enrichment_attempted": 0,
                "re_enrichment_successful": 0,
                "re_enrichment_failed": 0,
                "quality_scores": [],
                "detailed_results": []
            }
            
            for i, question in enumerate(pyq_questions):
                logger.info(f"🔍 Checking PYQ question {i+1}/{len(pyq_questions)}: {question.stem[:50]}...")
                
                # Assess current enrichment quality
                quality_assessment = await self._assess_pyq_question_quality(question)
                
                # Update PYQ results tracking
                check_results["quality_scores"].append(1 if quality_assessment["is_acceptable"] else 0)
                
                # If quality is unacceptable, re-enrich
                if not quality_assessment["is_acceptable"]:
                    logger.warning(f"⚠️ Unacceptable PYQ enrichment detected - failed criteria: {quality_assessment['failed_criteria']}")
                    check_results["poor_enrichment_identified"] += 1
                    
                    # Trigger re-enrichment
                    re_enrichment_result = await self._re_enrich_pyq_question(question, db)
                    check_results["re_enrichment_attempted"] += 1
                    
                    if re_enrichment_result["success"]:
                        check_results["re_enrichment_successful"] += 1
                        logger.info("✅ PYQ re-enrichment successful")
                    else:
                        check_results["re_enrichment_failed"] += 1
                        logger.error(f"❌ PYQ re-enrichment failed: {re_enrichment_result['error']}")
                    
                    check_results["detailed_results"].append({
                        "question_id": question.id,
                        "stem": question.stem[:100],
                        "failed_criteria": quality_assessment["failed_criteria"],
                        "quality_issues": quality_assessment["quality_issues"],
                        "re_enrichment_success": re_enrichment_result["success"],
                        "re_enrichment_error": re_enrichment_result.get("error")
                    })
                else:
                    logger.info(f"✅ Perfect PYQ enrichment quality - all criteria met")
            
            # Calculate PYQ summary statistics
            perfect_quality_count = sum(check_results["quality_scores"])
            perfect_quality_percentage = (perfect_quality_count / len(check_results["quality_scores"])) * 100 if check_results["quality_scores"] else 0
            improvement_rate = (check_results["re_enrichment_successful"] / check_results["re_enrichment_attempted"]) * 100 if check_results["re_enrichment_attempted"] > 0 else 0
            
            check_results.update({
                "perfect_quality_count": perfect_quality_count,
                "perfect_quality_percentage": round(perfect_quality_percentage, 2),
                "improvement_rate_percentage": round(improvement_rate, 2),
                "processing_completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info("🎉 PYQ Questions Enrichment Check completed!")
            return {
                "success": True,
                "check_results": check_results
            }
            
        except Exception as e:
            logger.error(f"❌ PYQ Questions Enrichment Check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _assess_regular_question_quality(self, question: Question) -> Dict[str, Any]:
        """
        Use LLM to assess the quality of a regular question's enrichment
        """
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
                # Use intelligent model selection from Advanced LLM Service
                model_to_use, selection_reason = self.advanced_enricher._should_use_fallback_model()
                logger.info(f"🤖 Quality assessment using model: {model_to_use} (reason: {selection_reason})")
                
                # Prepare enrichment data for assessment
                enrichment_data = {
                    "right_answer": question.right_answer,
                    "category": question.category,
                    "subcategory": question.subcategory,
                    "type_of_question": question.type_of_question,
                    "difficulty_band": question.difficulty_band,
                    "core_concepts": question.core_concepts,
                    "solution_method": question.solution_method,
                    "operations_required": question.operations_required,
                    "problem_structure": question.problem_structure,
                    "concept_keywords": question.concept_keywords
                }
                
                system_message = """You are an expert AI quality assessor specializing in educational content enrichment evaluation.

Your task is to evaluate the quality of question enrichment data and identify if it meets sophisticated educational standards.

QUALITY CRITERIA FOR ASSESSMENT:

1. RIGHT ANSWER QUALITY (25 points):
   - ❌ Poor: Just the answer (e.g., "3 hours")
   - ✅ Good: Detailed with reasoning (e.g., "3 hours (calculated using relative speed concept: combined approach speed is sum of individual speeds)")

2. CATEGORY SOPHISTICATION (20 points):
   - ❌ Poor: Generic terms ("Arithmetic", "Algebra", "Mathematics")
   - ✅ Good: Specific domains ("Advanced Kinematics in One Dimension", "Applied Percentage Analysis with Business Context")

3. SUBCATEGORY SPECIFICITY (15 points):
   - ❌ Poor: Basic terms ("Time Speed Distance", "Percentages")
   - ✅ Good: Precise areas ("Relative Motion Analysis in Opposite Directions", "Sequential Percentage Operations with Profit Margins")

4. CORE CONCEPTS DEPTH (20 points):
   - ❌ Poor: Generic/repetitive (["calculation"], ["mathematics"], ["basic_problem"])
   - ✅ Good: Specific mathematical concepts (["relative_velocity_vector_addition", "meeting_point_spatial_analysis"])

5. SOLUTION METHOD DETAIL (10 points):
   - ❌ Poor: Generic ("general_approach", "standard_method", "calculation")
   - ✅ Good: Specific methodology ("Relative Speed Vector Analysis with Spatial Meeting Point Calculation")

6. OPERATIONS SPECIFICITY (10 points):
   - ❌ Poor: Generic (["calculation"], ["basic_math"])
   - ✅ Good: Specific operations (["vector_addition_conceptual", "algebraic_equation_setup", "proportional_reasoning"])

ASSESSMENT GUIDELINES:
- ALL CRITERIA MUST BE MET 100% - NO COMPROMISES
- RIGHT ANSWER: Must include detailed mathematical reasoning (not just the answer)
- CATEGORY: Must be sophisticated and specific (not generic terms like "Arithmetic", "Algebra", "Mathematics")
- SUBCATEGORY: Must be precise and detailed (not basic terms like "Percentages", "Time Speed Distance")
- CORE CONCEPTS: Must be specific mathematical concepts (not generic like ["calculation"], ["mathematics"])
- SOLUTION METHOD: Must be detailed methodology (not generic like "general_approach", "standard_method")
- OPERATIONS: Must be specific operations (not generic like ["calculation"], ["basic_math"])

ANY GENERIC OR REPETITIVE CONTENT = UNACCEPTABLE (needs re-enrichment)
ONLY SOPHISTICATED, DETAILED, SPECIFIC CONTENT = ACCEPTABLE

Return ONLY this JSON:
{
  "is_acceptable": false,
  "failed_criteria": ["list of specific criteria that failed"],
  "quality_issues": ["detailed list of quality issues"],
  "assessment_reasoning": "detailed explanation of why unacceptable"
}"""

                response = client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Question: {question.stem}\n\nEnrichment Data to Assess:\n{json.dumps(enrichment_data, indent=2)}"}
                    ],
                    max_tokens=400,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                assessment_text = response.choices[0].message.content.strip()
                assessment_data = json.loads(assessment_text)
                
                # If we successfully used primary model after recovery, mark it as recovered
                if selection_reason == "testing_primary_recovery":
                    self.advanced_enricher._mark_primary_model_recovered()
                
                return assessment_data
                
            except Exception as e:
                logger.warning(f"⚠️ Quality assessment attempt {attempt + 1} failed: {e}")
                
                # Handle rate limit errors intelligently
                if self.advanced_enricher._handle_rate_limit_error(e):
                    logger.info("🔄 Retrying quality assessment immediately with fallback model due to rate limit")
                    continue
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # If all attempts fail, assume unacceptable quality for re-processing
                    return {
                        "is_acceptable": False,
                        "failed_criteria": ["Quality assessment failed - technical issue"],
                        "quality_issues": ["Unable to assess enrichment quality due to technical problems"],
                        "assessment_reasoning": "Technical issue during assessment - flagged for re-enrichment to ensure quality"
                    }
    
    async def _assess_pyq_question_quality(self, question: PYQQuestion) -> Dict[str, Any]:
        """
        Use LLM to assess the quality of a PYQ question's enrichment
        """
        for attempt in range(self.max_retries):
            try:
                client = openai.OpenAI(api_key=self.openai_api_key, timeout=self.timeout)
                
                # Prepare PYQ enrichment data for assessment
                enrichment_data = {
                    "subcategory": question.subcategory,
                    "type_of_question": question.type_of_question,
                    "difficulty_band": question.difficulty_band,
                    "core_concepts": question.core_concepts,
                    "solution_method": question.solution_method,
                    "operations_required": question.operations_required,
                    "problem_structure": question.problem_structure,
                    "concept_keywords": question.concept_keywords,
                    "quality_verified": question.quality_verified
                }
                
                system_message = """You are an expert AI quality assessor specializing in PYQ (Previous Year Questions) enrichment evaluation.

Your task is to evaluate the quality of PYQ question enrichment data for sophisticated educational analysis.

PYQ QUALITY CRITERIA FOR ASSESSMENT - 100% STRICT STANDARDS:

1. RIGHT ANSWER QUALITY:
   - ❌ UNACCEPTABLE: Just the answer (e.g., "3 hours")
   - ✅ REQUIRED: Detailed with reasoning (e.g., "3 hours (calculated using relative speed concept: combined approach speed is sum of individual speeds)")

2. SUBCATEGORY SPECIFICITY:
   - ❌ UNACCEPTABLE: Generic terms ("Time Speed Distance", "Algebra", "Basic", "Percentages")
   - ✅ REQUIRED: Precise PYQ areas ("Relative Motion Analysis in Competitive Context", "Sequential Percentage Operations with Profit Margins")

3. TYPE CLASSIFICATION DEPTH:
   - ❌ UNACCEPTABLE: Basic types ("Word Problem", "Calculation", "Basic")
   - ✅ REQUIRED: Specific PYQ archetypes ("Two-Train Meeting Problem with Variable Speeds", "Multi-stage Percentage Calculation with Compound Effects")

4. CORE CONCEPTS SOPHISTICATION:
   - ❌ UNACCEPTABLE: Generic/repetitive (["calculation"], ["mathematics"], ["standard_problem"])
   - ✅ REQUIRED: PYQ-specific concepts (["competitive_exam_optimization_strategies", "relative_velocity_vector_addition"])

5. SOLUTION METHOD SPECIFICITY:
   - ❌ UNACCEPTABLE: Generic ("general_approach", "standard_method")
   - ✅ REQUIRED: PYQ-optimized methods ("Speed-Accuracy Balance Method for Competitive Scenarios")

6. OPERATIONS PRECISION:
   - ❌ UNACCEPTABLE: Generic (["calculation"], ["basic_operations"])
   - ✅ REQUIRED: PYQ-relevant operations (["competitive_shortcut_application", "pattern_recognition_based_solving"])

ASSESSMENT STANDARDS - 100% STRICT:
- ALL CRITERIA MUST BE MET PERFECTLY - NO EXCEPTIONS
- ANY generic, repetitive, or basic content = IMMEDIATE REJECTION
- Only sophisticated, detailed, PYQ-specific content = ACCEPTABLE

Return ONLY this JSON:
{
  "is_acceptable": false,
  "failed_criteria": ["list of specific criteria that failed"],
  "quality_issues": ["detailed list of quality issues"],
  "assessment_reasoning": "detailed explanation of why unacceptable"
}"""

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"PYQ Question: {question.stem}\n\nPYQ Enrichment Data to Assess:\n{json.dumps(enrichment_data, indent=2)}"}
                    ],
                    max_tokens=400,
                    temperature=0.1,
                    timeout=self.timeout
                )
                
                assessment_text = response.choices[0].message.content.strip()
                assessment_data = json.loads(assessment_text)
                
                return assessment_data
                
            except Exception as e:
                logger.warning(f"⚠️ PYQ quality assessment attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                else:
                    # If all attempts fail, assume unacceptable quality for re-processing  
                    return {
                        "is_acceptable": False,
                        "failed_criteria": ["PYQ quality assessment failed - technical issue"],
                        "quality_issues": ["Unable to assess PYQ enrichment quality due to technical problems"],
                        "assessment_reasoning": "Technical issue during PYQ assessment - flagged for re-enrichment to ensure quality"
                    }
    
    async def _re_enrich_regular_question(self, question: Question, db: Session) -> Dict[str, Any]:
        """
        Re-enrich a regular question using Advanced LLM Enrichment Service
        """
        try:
            logger.info(f"🔄 Re-enriching regular question: {question.stem[:50]}...")
            
            # Use Advanced LLM Enrichment Service
            enrichment_result = await self.advanced_enricher.enrich_question_deeply(
                stem=question.stem,
                admin_answer=question.answer,
                question_type="regular"
            )
            
            if enrichment_result["success"]:
                enrichment_data = enrichment_result["enrichment_data"]
                
                # Update question with new enrichment data
                question.right_answer = enrichment_data.get("right_answer")
                question.category = enrichment_data.get("category")
                question.subcategory = enrichment_data.get("subcategory")
                question.type_of_question = enrichment_data.get("type_of_question")
                question.difficulty_band = enrichment_data.get("difficulty_band")
                question.difficulty_score = enrichment_data.get("difficulty_score")
                question.core_concepts = enrichment_data.get("core_concepts")
                question.solution_method = enrichment_data.get("solution_method")
                question.concept_difficulty = enrichment_data.get("concept_difficulty")
                question.operations_required = enrichment_data.get("operations_required")
                question.problem_structure = enrichment_data.get("problem_structure")
                question.concept_keywords = enrichment_data.get("concept_keywords")
                question.quality_verified = enrichment_data.get("quality_verified", True)
                
                # Update metadata
                question.llm_difficulty_assessment_method = 'llm_verified'
                question.last_llm_assessment_date = datetime.utcnow()
                question.llm_assessment_error = None
                
                db.commit()
                
                logger.info("✅ Regular question re-enrichment successful")
                return {"success": True}
            else:
                logger.error(f"❌ Regular question re-enrichment failed: {enrichment_result.get('error')}")
                return {
                    "success": False,
                    "error": enrichment_result.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"❌ Regular question re-enrichment exception: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _re_enrich_pyq_question(self, question: PYQQuestion, db: Session) -> Dict[str, Any]:
        """
        Re-enrich a PYQ question using Advanced LLM Enrichment Service
        """
        try:
            logger.info(f"🔄 Re-enriching PYQ question: {question.stem[:50]}...")
            
            # Use Advanced LLM Enrichment Service for PYQ
            enrichment_result = await self.advanced_enricher.enrich_question_deeply(
                stem=question.stem,
                admin_answer=question.answer,
                question_type="pyq"
            )
            
            if enrichment_result["success"]:
                enrichment_data = enrichment_result["enrichment_data"]
                
                # Update PYQ question with new enrichment data
                question.subcategory = enrichment_data.get("subcategory", question.subcategory)
                question.type_of_question = enrichment_data.get("type_of_question")
                question.difficulty_band = enrichment_data.get("difficulty_band")
                question.difficulty_score = enrichment_data.get("difficulty_score")
                question.core_concepts = enrichment_data.get("core_concepts")
                question.solution_method = enrichment_data.get("solution_method")
                question.concept_difficulty = enrichment_data.get("concept_difficulty")
                question.operations_required = enrichment_data.get("operations_required")
                question.problem_structure = enrichment_data.get("problem_structure")
                question.concept_keywords = enrichment_data.get("concept_keywords")
                question.quality_verified = enrichment_data.get("quality_verified", True)
                
                # Update PYQ metadata
                question.concept_extraction_status = 'completed'
                question.last_updated = datetime.utcnow()
                question.is_active = True
                
                db.commit()
                
                logger.info("✅ PYQ question re-enrichment successful")
                return {"success": True}
            else:
                logger.error(f"❌ PYQ question re-enrichment failed: {enrichment_result.get('error')}")
                return {
                    "success": False,
                    "error": enrichment_result.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"❌ PYQ question re-enrichment exception: {e}")
            return {
                "success": False,
                "error": str(e)
            }