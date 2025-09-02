#!/usr/bin/env python3
"""
Enhanced Enrichment Checker Service
Comprehensive validation system that ensures 100% compliance with canonical taxonomy
and sophisticated enrichment standards for both Regular and PYQ questions
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

class EnhancedEnrichmentCheckerService:
    """
    Enhanced LLM-based quality checker with 100% compliance standards
    Validates all enrichment fields against canonical taxonomy and sophisticated criteria
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
            raise ValueError(f"OpenAI API key not found for EnhancedEnrichmentCheckerService. Checked paths: {backend_env_path}, current directory")
        
        self.advanced_enricher = AdvancedLLMEnrichmentService()
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]
        self.timeout = 120
        
        # Inherit intelligent model switching from Advanced LLM Service
        self.primary_model = "gpt-4o"
        self.fallback_model = "gpt-4o-mini"
        
        # Define canonical taxonomy structure
        self.canonical_categories = [
            "A-Arithmetic",
            "B-Algebra",
            "C-Geometry & Mensuration", 
            "D-Number System",
            "E-Modern Math"
        ]
        
        self.canonical_subcategories = {
            "A-Arithmetic": [
                "Time–Speed–Distance (TSD)", "Time & Work", "Ratio–Proportion–Variation",
                "Percentages", "Averages & Alligation", "Profit–Loss–Discount (PLD)",
                "Simple & Compound Interest (SI–CI)", "Mixtures & Solutions"
            ],
            "B-Algebra": [
                "Linear Equations", "Quadratic Equations", "Inequalities", "Progressions",
                "Functions & Graphs", "Logarithms & Exponents", "Special Algebraic Identities"
            ],
            "C-Geometry & Mensuration": [
                "Triangles", "Circles", "Polygons", "Coordinate Geometry",
                "Mensuration (2D & 3D)", "Trigonometry in Geometry"
            ],
            "D-Number System": [
                "Divisibility", "HCF–LCM", "Remainders & Modular Arithmetic",
                "Base Systems", "Digit Properties"
            ],
            "E-Modern Math": [
                "Permutation–Combination (P&C)", "Probability", "Set Theory & Venn Diagrams"
            ]
        }
        
        # CANONICAL QUESTION TYPES TAXONOMY
        self.canonical_question_types = {
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
        
        # Forbidden generic terms for rejection
        self.forbidden_generic_terms = [
            "calculation", "basic", "mathematics", "basic_problem", "standard_problem",
            "general_approach", "standard_method", "basic_math", "simple_calculation"
        ]
        
        # Define our concept difficulty definition
        self.concept_difficulty_definition = """
        Concept Difficulty Definition:
        - Prerequisites: Prior mathematical concepts needed to understand this problem
        - Cognitive Barriers: Common misconceptions or mental blocks students face
        - Mastery Indicators: Skills/insights that demonstrate true understanding of the concept
        
        This must be evaluated contextually for the specific question's mathematical domain.
        """
        
        logger.info("✅ EnhancedEnrichmentCheckerService initialized successfully")
    
    async def check_and_enrich_regular_questions(self, db: Session, limit: int = None) -> Dict[str, Any]:
        """
        Enhanced regular questions quality check with 100% compliance standards
        
        Args:
            db: Database session
            limit: Optional limit on number of questions to check
            
        Returns:
            Dict with comprehensive checking and re-enrichment results
        """
        try:
            logger.info("🔍 Starting Enhanced Regular Questions Quality Check (100% Compliance)...")
            
            # Get all regular questions
            query = select(Question).where(Question.is_active == True)
            if limit:
                query = query.limit(limit)
            
            result = db.execute(query)
            questions = result.scalars().all()
            
            logger.info(f"📊 Found {len(questions)} regular questions to check")
            
            # Enhanced check results tracking
            check_results = {
                "total_questions_checked": len(questions),
                "poor_enrichment_identified": 0,
                "re_enrichment_attempted": 0,
                "re_enrichment_successful": 0,
                "re_enrichment_failed": 0,
                "quality_scores": [],
                "detailed_results": [],
                "canonical_taxonomy_violations": 0,
                "generic_content_rejections": 0,
                "difficulty_consistency_failures": 0
            }
            
            for i, question in enumerate(questions):
                logger.info(f"🔍 Enhanced checking question {i+1}/{len(questions)}: {question.stem[:50]}...")
                
                # Comprehensive quality assessment
                quality_assessment = await self._assess_regular_question_enhanced(question)
                
                # Update results tracking
                check_results["quality_scores"].append(1 if quality_assessment["is_acceptable"] else 0)
                
                # Track specific violation types
                if not quality_assessment["is_acceptable"]:
                    if "canonical_taxonomy" in str(quality_assessment["failed_criteria"]):
                        check_results["canonical_taxonomy_violations"] += 1
                    if "generic_content" in str(quality_assessment["failed_criteria"]):
                        check_results["generic_content_rejections"] += 1
                    if "difficulty_consistency" in str(quality_assessment["failed_criteria"]):
                        check_results["difficulty_consistency_failures"] += 1
                
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
                        "canonical_violations": quality_assessment.get("canonical_violations", []),
                        "generic_content_found": quality_assessment.get("generic_content_found", []),
                        "re_enrichment_success": re_enrichment_result["success"],
                        "re_enrichment_error": re_enrichment_result.get("error")
                    })
                else:
                    logger.info(f"✅ Perfect enrichment quality - 100% compliance achieved")
            
            # Calculate comprehensive summary statistics
            perfect_quality_count = sum(check_results["quality_scores"])
            perfect_quality_percentage = (perfect_quality_count / len(check_results["quality_scores"])) * 100 if check_results["quality_scores"] else 0
            improvement_rate = (check_results["re_enrichment_successful"] / check_results["re_enrichment_attempted"]) * 100 if check_results["re_enrichment_attempted"] > 0 else 0
            
            check_results.update({
                "perfect_quality_count": perfect_quality_count,
                "perfect_quality_percentage": round(perfect_quality_percentage, 2),
                "improvement_rate_percentage": round(improvement_rate, 2),
                "canonical_compliance_rate": round(((len(questions) - check_results["canonical_taxonomy_violations"]) / len(questions)) * 100, 2) if questions else 100,
                "generic_content_rejection_rate": round((check_results["generic_content_rejections"] / len(questions)) * 100, 2) if questions else 0,
                "processing_completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info("🎉 Enhanced Regular Questions Enrichment Check completed!")
            return {
                "success": True,
                "check_results": check_results
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced Regular Questions Enrichment Check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_and_enrich_pyq_questions(self, db: Session, limit: int = None) -> Dict[str, Any]:
        """
        Enhanced PYQ questions quality check with 100% compliance standards
        
        Args:
            db: Database session
            limit: Optional limit on number of questions to check
            
        Returns:
            Dict with comprehensive checking and re-enrichment results
        """
        try:
            logger.info("🔍 Starting Enhanced PYQ Questions Quality Check (100% Compliance)...")
            
            # Get all PYQ questions
            query = select(PYQQuestion).where(PYQQuestion.is_active == True)
            if limit:
                query = query.limit(limit)
            
            result = db.execute(query)
            questions = result.scalars().all()
            
            logger.info(f"📊 Found {len(questions)} PYQ questions to check")
            
            # Enhanced check results tracking
            check_results = {
                "total_questions_checked": len(questions),
                "poor_enrichment_identified": 0,
                "re_enrichment_attempted": 0,
                "re_enrichment_successful": 0,
                "re_enrichment_failed": 0,
                "quality_scores": [],
                "detailed_results": [],
                "canonical_taxonomy_violations": 0,
                "generic_content_rejections": 0,
                "difficulty_consistency_failures": 0
            }
            
            for i, question in enumerate(questions):
                logger.info(f"🔍 Enhanced checking PYQ question {i+1}/{len(questions)}: {question.stem[:50]}...")
                
                # Comprehensive PYQ quality assessment
                quality_assessment = await self._assess_pyq_question_enhanced(question)
                
                # Update results tracking
                check_results["quality_scores"].append(1 if quality_assessment["is_acceptable"] else 0)
                
                # Track specific violation types
                if not quality_assessment["is_acceptable"]:
                    if "canonical_taxonomy" in str(quality_assessment["failed_criteria"]):
                        check_results["canonical_taxonomy_violations"] += 1
                    if "generic_content" in str(quality_assessment["failed_criteria"]):
                        check_results["generic_content_rejections"] += 1
                    if "difficulty_consistency" in str(quality_assessment["failed_criteria"]):
                        check_results["difficulty_consistency_failures"] += 1
                
                # If quality is unacceptable, re-enrich
                if not quality_assessment["is_acceptable"]:
                    logger.warning(f"⚠️ Unacceptable PYQ enrichment detected - failed criteria: {quality_assessment['failed_criteria']}")
                    check_results["poor_enrichment_identified"] += 1
                    
                    # Trigger re-enrichment
                    re_enrichment_result = await self._re_enrich_pyq_question(question, db)
                    check_results["re_enrichment_attempted"] += 1
                    
                    if re_enrichment_result["success"]:
                        check_results["re_enrichment_successful"] += 1
                        logger.info("✅ PYQ Re-enrichment successful")
                    else:
                        check_results["re_enrichment_failed"] += 1
                        logger.error(f"❌ PYQ Re-enrichment failed: {re_enrichment_result['error']}")
                    
                    check_results["detailed_results"].append({
                        "question_id": question.id,
                        "stem": question.stem[:100],
                        "failed_criteria": quality_assessment["failed_criteria"],
                        "quality_issues": quality_assessment["quality_issues"],
                        "canonical_violations": quality_assessment.get("canonical_violations", []),
                        "generic_content_found": quality_assessment.get("generic_content_found", []),
                        "re_enrichment_success": re_enrichment_result["success"],
                        "re_enrichment_error": re_enrichment_result.get("error")
                    })
                else:
                    logger.info(f"✅ Perfect PYQ enrichment quality - 100% compliance achieved")
            
            # Calculate comprehensive summary statistics
            perfect_quality_count = sum(check_results["quality_scores"])
            perfect_quality_percentage = (perfect_quality_count / len(check_results["quality_scores"])) * 100 if check_results["quality_scores"] else 0
            improvement_rate = (check_results["re_enrichment_successful"] / check_results["re_enrichment_attempted"]) * 100 if check_results["re_enrichment_attempted"] > 0 else 0
            
            check_results.update({
                "perfect_quality_count": perfect_quality_count,
                "perfect_quality_percentage": round(perfect_quality_percentage, 2),
                "improvement_rate_percentage": round(improvement_rate, 2),
                "canonical_compliance_rate": round(((len(questions) - check_results["canonical_taxonomy_violations"]) / len(questions)) * 100, 2) if questions else 100,
                "generic_content_rejection_rate": round((check_results["generic_content_rejections"] / len(questions)) * 100, 2) if questions else 0,
                "processing_completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info("🎉 Enhanced PYQ Questions Enrichment Check completed!")
            return {
                "success": True,
                "check_results": check_results
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced PYQ Questions Enrichment Check failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _assess_regular_question_enhanced(self, question: Question) -> Dict[str, Any]:
        """
        Enhanced quality assessment for regular questions with 100% compliance validation
        """
        try:
            logger.info(f"🔍 Enhanced assessment for regular question: {question.stem[:50]}...")
            
            # Initialize assessment results
            failed_criteria = []
            quality_issues = []
            canonical_violations = []
            generic_content_found = []
            is_acceptable = True
            
            # 1. CHECK QUALITY_VERIFIED - MUST BE TRUE
            if not question.quality_verified:
                failed_criteria.append("quality_verified_false")
                quality_issues.append("quality_verified field is False - automatic rejection")
                is_acceptable = False
            
            # 2. CHECK CANONICAL TAXONOMY COMPLIANCE
            
            # Category validation
            if not question.category or question.category not in self.canonical_categories:
                failed_criteria.append("canonical_taxonomy_category_violation")
                canonical_violations.append(f"Category '{question.category}' not in canonical list: {self.canonical_categories}")
                is_acceptable = False
            
            # Subcategory validation
            if question.category and question.category in self.canonical_subcategories:
                valid_subcategories = self.canonical_subcategories[question.category]
                if not question.subcategory or question.subcategory not in valid_subcategories:
                    failed_criteria.append("canonical_taxonomy_subcategory_violation")
                    canonical_violations.append(f"Subcategory '{question.subcategory}' not valid for category '{question.category}'. Valid options: {valid_subcategories}")
                    is_acceptable = False
            
            # 3. CHECK RIGHT_ANSWER QUALITY
            if not question.right_answer:
                failed_criteria.append("right_answer_missing")
                quality_issues.append("right_answer field is empty")
                is_acceptable = False
            elif len(question.right_answer) < 10:
                failed_criteria.append("right_answer_too_short")
                quality_issues.append("right_answer must include normalized value + short reasoning")
                is_acceptable = False
            
            # 4. CHECK DIFFICULTY CONSISTENCY
            if not question.difficulty_band or question.difficulty_band not in ['Easy', 'Medium', 'Hard']:
                failed_criteria.append("difficulty_band_invalid")
                quality_issues.append(f"difficulty_band must be exactly Easy/Medium/Hard, got: {question.difficulty_band}")
                is_acceptable = False
            
            if not question.difficulty_score or not (1.0 <= question.difficulty_score <= 5.0):
                failed_criteria.append("difficulty_score_invalid")
                quality_issues.append(f"difficulty_score must be 1.0-5.0, got: {question.difficulty_score}")
                is_acceptable = False
            
            # Check band-score alignment
            if question.difficulty_band and question.difficulty_score:
                if question.difficulty_band == 'Easy' and not (1.0 <= question.difficulty_score <= 2.0):
                    failed_criteria.append("difficulty_consistency_easy")
                    quality_issues.append(f"Easy questions must have score 1.0-2.0, got: {question.difficulty_score}")
                    is_acceptable = False
                elif question.difficulty_band == 'Medium' and not (2.1 <= question.difficulty_score <= 3.5):
                    failed_criteria.append("difficulty_consistency_medium")
                    quality_issues.append(f"Medium questions must have score 2.1-3.5, got: {question.difficulty_score}")
                    is_acceptable = False
                elif question.difficulty_band == 'Hard' and not (3.6 <= question.difficulty_score <= 5.0):
                    failed_criteria.append("difficulty_consistency_hard")
                    quality_issues.append(f"Hard questions must have score 3.6-5.0, got: {question.difficulty_score}")
                    is_acceptable = False
            
            # 5. CHECK FOR GENERIC CONTENT
            
            # Core concepts validation
            if question.core_concepts:
                try:
                    core_concepts = json.loads(question.core_concepts) if isinstance(question.core_concepts, str) else question.core_concepts
                    if isinstance(core_concepts, list):
                        for concept in core_concepts:
                            if any(generic_term in concept.lower() for generic_term in self.forbidden_generic_terms):
                                failed_criteria.append("generic_core_concepts")
                                generic_content_found.append(f"Generic concept found: {concept}")
                                is_acceptable = False
                        
                        if len(core_concepts) < 3:
                            failed_criteria.append("insufficient_core_concepts")
                            quality_issues.append(f"Must have at least 3 core concepts, got: {len(core_concepts)}")
                            is_acceptable = False
                except:
                    failed_criteria.append("core_concepts_invalid_format")
                    quality_issues.append("core_concepts field has invalid JSON format")
                    is_acceptable = False
            else:
                failed_criteria.append("core_concepts_missing")
                quality_issues.append("core_concepts field is empty")
                is_acceptable = False
            
            # Solution method validation
            if not question.solution_method:
                failed_criteria.append("solution_method_missing")
                quality_issues.append("solution_method field is empty")
                is_acceptable = False
            elif any(generic_term in question.solution_method.lower() for generic_term in self.forbidden_generic_terms):
                failed_criteria.append("generic_solution_method")
                generic_content_found.append(f"Generic solution method: {question.solution_method}")
                is_acceptable = False
            
            # Operations required validation
            if question.operations_required:
                try:
                    operations = json.loads(question.operations_required) if isinstance(question.operations_required, str) else question.operations_required
                    if isinstance(operations, list):
                        for operation in operations:
                            if any(generic_term in operation.lower() for generic_term in self.forbidden_generic_terms):
                                failed_criteria.append("generic_operations_required")
                                generic_content_found.append(f"Generic operation found: {operation}")
                                is_acceptable = False
                except:
                    failed_criteria.append("operations_required_invalid_format")
                    quality_issues.append("operations_required field has invalid JSON format")
                    is_acceptable = False
            else:
                failed_criteria.append("operations_required_missing")
                quality_issues.append("operations_required field is empty")
                is_acceptable = False
            
            # 6. CHECK CONCEPT_DIFFICULTY
            if not question.concept_difficulty:
                failed_criteria.append("concept_difficulty_missing")
                quality_issues.append("concept_difficulty field is empty - must be evaluated based on our definition")
                is_acceptable = False
            else:
                try:
                    concept_diff = json.loads(question.concept_difficulty) if isinstance(question.concept_difficulty, str) else question.concept_difficulty
                    required_keys = ['prerequisites', 'cognitive_barriers', 'mastery_indicators']
                    missing_keys = [key for key in required_keys if key not in concept_diff]
                    if missing_keys:
                        failed_criteria.append("concept_difficulty_incomplete")
                        quality_issues.append(f"concept_difficulty missing required keys: {missing_keys}")
                        is_acceptable = False
                except:
                    failed_criteria.append("concept_difficulty_invalid_format")
                    quality_issues.append("concept_difficulty field has invalid JSON format")
                    is_acceptable = False
            
            # 7. CHECK PROBLEM_STRUCTURE
            if not question.problem_structure:
                failed_criteria.append("problem_structure_missing")
                quality_issues.append("problem_structure field must be listed in detail")
                is_acceptable = False
            
            # 8. CHECK CONCEPT_KEYWORDS
            if not question.concept_keywords:
                failed_criteria.append("concept_keywords_missing")
                quality_issues.append("concept_keywords field must be checked and be precise")
                is_acceptable = False
            else:
                try:
                    keywords = json.loads(question.concept_keywords) if isinstance(question.concept_keywords, str) else question.concept_keywords
                    if not isinstance(keywords, list) or len(keywords) < 2:
                        failed_criteria.append("concept_keywords_insufficient")
                        quality_issues.append("concept_keywords must have at least 2 precise keywords")
                        is_acceptable = False
                except:
                    failed_criteria.append("concept_keywords_invalid_format")
                    quality_issues.append("concept_keywords field has invalid JSON format")
                    is_acceptable = False
            
            logger.info(f"✅ Enhanced assessment completed. Acceptable: {is_acceptable}")
            
            return {
                "is_acceptable": is_acceptable,
                "failed_criteria": failed_criteria,
                "quality_issues": quality_issues,
                "canonical_violations": canonical_violations,
                "generic_content_found": generic_content_found,
                "assessment_type": "enhanced_regular_question_validation"
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced regular question assessment failed: {e}")
            return {
                "is_acceptable": False,
                "failed_criteria": ["assessment_technical_failure"],
                "quality_issues": [f"Technical issue during enhanced assessment: {str(e)}"],
                "canonical_violations": [],
                "generic_content_found": [],
                "assessment_type": "enhanced_regular_question_validation"
            }
    
    async def _assess_pyq_question_enhanced(self, question: PYQQuestion) -> Dict[str, Any]:
        """
        Enhanced quality assessment for PYQ questions with 100% compliance validation
        """
        try:
            logger.info(f"🔍 Enhanced PYQ assessment for question: {question.stem[:50]}...")
            
            # Initialize assessment results
            failed_criteria = []
            quality_issues = []
            canonical_violations = []
            generic_content_found = []
            is_acceptable = True
            
            # 1. CHECK QUALITY_VERIFIED - MUST BE TRUE
            if not question.quality_verified:
                failed_criteria.append("quality_verified_false")
                quality_issues.append("quality_verified field is False - automatic rejection")
                is_acceptable = False
            
            # 2. CHECK CANONICAL TAXONOMY COMPLIANCE
            
            # Find category from subcategory for validation
            category_for_subcategory = None
            for cat, subcats in self.canonical_subcategories.items():
                if question.subcategory in subcats:
                    category_for_subcategory = cat
                    break
            
            # Subcategory validation
            all_valid_subcategories = []
            for subcats in self.canonical_subcategories.values():
                all_valid_subcategories.extend(subcats)
            
            if not question.subcategory or question.subcategory not in all_valid_subcategories:
                failed_criteria.append("canonical_taxonomy_subcategory_violation")
                canonical_violations.append(f"Subcategory '{question.subcategory}' not in canonical taxonomy. Valid options: {all_valid_subcategories}")
                is_acceptable = False
            
            # 3. CHECK DIFFICULTY CONSISTENCY
            if not question.difficulty_band or question.difficulty_band not in ['Easy', 'Medium', 'Hard']:
                failed_criteria.append("difficulty_band_invalid")
                quality_issues.append(f"difficulty_band must be exactly Easy/Medium/Hard, got: {question.difficulty_band}")
                is_acceptable = False
            
            if not question.difficulty_score or not (1.0 <= question.difficulty_score <= 5.0):
                failed_criteria.append("difficulty_score_invalid")
                quality_issues.append(f"difficulty_score must be 1.0-5.0, got: {question.difficulty_score}")
                is_acceptable = False
            
            # Check band-score alignment
            if question.difficulty_band and question.difficulty_score:
                if question.difficulty_band == 'Easy' and not (1.0 <= question.difficulty_score <= 2.0):
                    failed_criteria.append("difficulty_consistency_easy")
                    quality_issues.append(f"Easy PYQ questions must have score 1.0-2.0, got: {question.difficulty_score}")
                    is_acceptable = False
                elif question.difficulty_band == 'Medium' and not (2.1 <= question.difficulty_score <= 3.5):
                    failed_criteria.append("difficulty_consistency_medium")
                    quality_issues.append(f"Medium PYQ questions must have score 2.1-3.5, got: {question.difficulty_score}")
                    is_acceptable = False
                elif question.difficulty_band == 'Hard' and not (3.6 <= question.difficulty_score <= 5.0):
                    failed_criteria.append("difficulty_consistency_hard")
                    quality_issues.append(f"Hard PYQ questions must have score 3.6-5.0, got: {question.difficulty_score}")
                    is_acceptable = False
            
            # 4. CHECK FOR GENERIC CONTENT
            
            # Core concepts validation
            if question.core_concepts:
                try:
                    core_concepts = json.loads(question.core_concepts) if isinstance(question.core_concepts, str) else question.core_concepts
                    if isinstance(core_concepts, list):
                        for concept in core_concepts:
                            if any(generic_term in concept.lower() for generic_term in self.forbidden_generic_terms):
                                failed_criteria.append("generic_core_concepts")
                                generic_content_found.append(f"Generic PYQ concept found: {concept}")
                                is_acceptable = False
                        
                        if len(core_concepts) < 3:
                            failed_criteria.append("insufficient_core_concepts")
                            quality_issues.append(f"PYQ must have at least 3 detailed core concepts, got: {len(core_concepts)}")
                            is_acceptable = False
                except:
                    failed_criteria.append("core_concepts_invalid_format")
                    quality_issues.append("core_concepts field has invalid JSON format")
                    is_acceptable = False
            else:
                failed_criteria.append("core_concepts_missing")
                quality_issues.append("core_concepts field is empty")
                is_acceptable = False
            
            # Solution method validation
            if not question.solution_method:
                failed_criteria.append("solution_method_missing")
                quality_issues.append("solution_method field is empty")
                is_acceptable = False
            elif any(generic_term in question.solution_method.lower() for generic_term in self.forbidden_generic_terms):
                failed_criteria.append("generic_solution_method")
                generic_content_found.append(f"Generic PYQ solution method: {question.solution_method}")
                is_acceptable = False
            
            # Operations required validation
            if question.operations_required:
                try:
                    operations = json.loads(question.operations_required) if isinstance(question.operations_required, str) else question.operations_required
                    if isinstance(operations, list):
                        for operation in operations:
                            if any(generic_term in operation.lower() for generic_term in self.forbidden_generic_terms):
                                failed_criteria.append("generic_operations_required")
                                generic_content_found.append(f"Generic PYQ operation found: {operation}")
                                is_acceptable = False
                except:
                    failed_criteria.append("operations_required_invalid_format")
                    quality_issues.append("operations_required field has invalid JSON format")
                    is_acceptable = False
            else:
                failed_criteria.append("operations_required_missing")
                quality_issues.append("operations_required field is empty")
                is_acceptable = False
            
            # 5. CHECK CONCEPT_DIFFICULTY
            if not question.concept_difficulty:
                failed_criteria.append("concept_difficulty_missing")
                quality_issues.append("concept_difficulty field is empty - must be calculated based on our definition")
                is_acceptable = False
            else:
                try:
                    concept_diff = json.loads(question.concept_difficulty) if isinstance(question.concept_difficulty, str) else question.concept_difficulty
                    required_keys = ['prerequisites', 'cognitive_barriers', 'mastery_indicators']
                    missing_keys = [key for key in required_keys if key not in concept_diff]
                    if missing_keys:
                        failed_criteria.append("concept_difficulty_incomplete")
                        quality_issues.append(f"PYQ concept_difficulty missing required keys: {missing_keys}")
                        is_acceptable = False
                except:
                    failed_criteria.append("concept_difficulty_invalid_format")
                    quality_issues.append("concept_difficulty field has invalid JSON format")
                    is_acceptable = False
            
            # 6. CHECK PROBLEM_STRUCTURE
            if not question.problem_structure:
                failed_criteria.append("problem_structure_missing")
                quality_issues.append("PYQ problem_structure should be checked and detailed")
                is_acceptable = False
            
            # 7. CHECK CONCEPT_KEYWORDS
            if not question.concept_keywords:
                failed_criteria.append("concept_keywords_missing")
                quality_issues.append("PYQ concept_keywords must be checked and precise")
                is_acceptable = False
            else:
                try:
                    keywords = json.loads(question.concept_keywords) if isinstance(question.concept_keywords, str) else question.concept_keywords
                    if not isinstance(keywords, list) or len(keywords) < 2:
                        failed_criteria.append("concept_keywords_insufficient")
                        quality_issues.append("PYQ concept_keywords must have at least 2 precise keywords")
                        is_acceptable = False
                except:
                    failed_criteria.append("concept_keywords_invalid_format")
                    quality_issues.append("concept_keywords field has invalid JSON format")
                    is_acceptable = False
            
            logger.info(f"✅ Enhanced PYQ assessment completed. Acceptable: {is_acceptable}")
            
            return {
                "is_acceptable": is_acceptable,
                "failed_criteria": failed_criteria,
                "quality_issues": quality_issues,
                "canonical_violations": canonical_violations,
                "generic_content_found": generic_content_found,
                "assessment_type": "enhanced_pyq_question_validation"
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced PYQ question assessment failed: {e}")
            return {
                "is_acceptable": False,
                "failed_criteria": ["assessment_technical_failure"],
                "quality_issues": [f"Technical issue during enhanced PYQ assessment: {str(e)}"],
                "canonical_violations": [],
                "generic_content_found": [],
                "assessment_type": "enhanced_pyq_question_validation"
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