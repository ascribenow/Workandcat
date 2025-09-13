#!/usr/bin/env python3
"""
Individual Enrichment Stages API Endpoints
Break down the complete enrichment process into individual triggerable stages
"""

import sys
import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import SessionLocal, Question
from sqlalchemy import select, and_
from regular_enrichment_service import regular_questions_enrichment_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
stages_router = APIRouter(prefix="/api/enrichment/stages", tags=["Individual Enrichment Stages"])

class StageRequest(BaseModel):
    question_ids: Optional[List[str]] = None
    limit: Optional[int] = 10

class StageResponse(BaseModel):
    success: bool
    stage: str
    processed: int
    success_count: int
    failed_count: int
    details: dict

# =============================================================================
# STAGE 1: LLM CONSOLIDATED ENRICHMENT (Generate core fields)
# =============================================================================

@stages_router.post("/stage1-llm-enrichment", response_model=StageResponse)
async def stage1_llm_enrichment(request: StageRequest):
    """
    STAGE 1: LLM Consolidated Enrichment
    Generates: right_answer, category, subcategory, type_of_question, 
              core_concepts, solution_method, concept_difficulty, 
              operations_required, problem_structure, concept_keywords
    """
    db = SessionLocal()
    try:
        logger.info("🎯 STAGE 1: LLM Consolidated Enrichment")
        
        # Get questions to process
        if request.question_ids:
            questions = db.execute(
                select(Question).where(Question.id.in_(request.question_ids))
            ).scalars().all()
        else:
            questions = db.execute(
                select(Question)
                .where(Question.right_answer.is_(None))
                .limit(request.limit)
            ).scalars().all()
        
        processed = len(questions)
        success_count = 0
        failed_count = 0
        
        for question in questions:
            try:
                logger.info(f"🔄 Processing {question.id[:8]}... - LLM Enrichment")
                
                # Call only the consolidated LLM enrichment
                enrichment_result = await regular_questions_enrichment_service._consolidated_llm_enrichment(
                    question.stem, question.answer
                )
                
                if enrichment_result.get('success'):
                    enrichment_data = enrichment_result.get('enrichment_data', {})
                    
                    # Update only LLM-generated fields
                    llm_fields = [
                        'right_answer', 'category', 'subcategory', 'type_of_question',
                        'core_concepts', 'solution_method', 'concept_difficulty',
                        'operations_required', 'problem_structure', 'concept_keywords',
                        'difficulty_score', 'difficulty_band'
                    ]
                    
                    for field in llm_fields:
                        if field in enrichment_data:
                            setattr(question, field, enrichment_data[field])
                    
                    db.commit()
                    success_count += 1
                    logger.info(f"✅ LLM enrichment completed for {question.id[:8]}")
                    
                else:
                    failed_count += 1
                    logger.error(f"❌ LLM enrichment failed for {question.id[:8]}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error in LLM enrichment for {question.id[:8]}: {e}")
        
        return StageResponse(
            success=True,
            stage="stage1_llm_enrichment",
            processed=processed,
            success_count=success_count,
            failed_count=failed_count,
            details={
                "fields_generated": ["right_answer", "category", "subcategory", "type_of_question", 
                                   "core_concepts", "solution_method", "concept_difficulty",
                                   "operations_required", "problem_structure", "concept_keywords",
                                   "difficulty_score", "difficulty_band"]
            }
        )
        
    finally:
        db.close()

# =============================================================================
# STAGE 2: SEMANTIC TAXONOMY MATCHING
# =============================================================================

@stages_router.post("/stage2-taxonomy-matching", response_model=StageResponse)
async def stage2_taxonomy_matching(request: StageRequest):
    """
    STAGE 2: Semantic Taxonomy Matching
    Refines: category, subcategory, type_of_question using canonical taxonomy
    """
    db = SessionLocal()
    try:
        logger.info("🎯 STAGE 2: Semantic Taxonomy Matching")
        
        # Get questions with LLM enrichment but need taxonomy matching
        if request.question_ids:
            questions = db.execute(
                select(Question).where(Question.id.in_(request.question_ids))
            ).scalars().all()
        else:
            questions = db.execute(
                select(Question)
                .where(and_(
                    Question.right_answer.isnot(None),
                    Question.category.isnot(None)
                ))
                .limit(request.limit)
            ).scalars().all()
        
        processed = len(questions)
        success_count = 0
        failed_count = 0
        
        for question in questions:
            try:
                logger.info(f"🔄 Processing {question.id[:8]}... - Taxonomy Matching")
                
                # Apply semantic taxonomy matching
                canonical_category, canonical_subcategory, canonical_type = await regular_questions_enrichment_service._get_canonical_taxonomy_path_with_context(
                    question.stem,
                    question.category or '',
                    question.subcategory or '',
                    question.type_of_question or ''
                )
                
                # Update with canonical values
                question.category = canonical_category
                question.subcategory = canonical_subcategory
                question.type_of_question = canonical_type
                
                db.commit()
                success_count += 1
                logger.info(f"✅ Taxonomy matching completed: {canonical_category} → {canonical_subcategory} → {canonical_type}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error in taxonomy matching for {question.id[:8]}: {e}")
        
        return StageResponse(
            success=True,
            stage="stage2_taxonomy_matching",
            processed=processed,
            success_count=success_count,
            failed_count=failed_count,
            details={
                "fields_refined": ["category", "subcategory", "type_of_question"]
            }
        )
        
    finally:
        db.close()

# =============================================================================
# STAGE 3: PYQ FREQUENCY CALCULATION
# =============================================================================

@stages_router.post("/stage3-pyq-frequency", response_model=StageResponse)
async def stage3_pyq_frequency(request: StageRequest):
    """
    STAGE 3: PYQ Frequency Score Calculation
    Calculates: pyq_frequency_score using LLM-based semantic comparison
    """
    db = SessionLocal()
    try:
        logger.info("🎯 STAGE 3: PYQ Frequency Score Calculation")
        
        # Get questions with taxonomy but need PYQ frequency
        if request.question_ids:
            questions = db.execute(
                select(Question).where(Question.id.in_(request.question_ids))
            ).scalars().all()
        else:
            questions = db.execute(
                select(Question)
                .where(and_(
                    Question.category.isnot(None),
                    Question.subcategory.isnot(None),
                    Question.pyq_frequency_score.is_(None)
                ))
                .limit(request.limit)
            ).scalars().all()
        
        processed = len(questions)
        success_count = 0
        failed_count = 0
        
        for question in questions:
            try:
                logger.info(f"🔄 Processing {question.id[:8]}... - PYQ Frequency")
                
                # Prepare enrichment data for frequency calculation
                enrichment_data = {
                    'category': question.category,
                    'subcategory': question.subcategory,
                    'difficulty_score': question.difficulty_score or 0,
                    'problem_structure': question.problem_structure or '',
                    'concept_keywords': question.concept_keywords or '[]'
                }
                
                # Calculate PYQ frequency score
                pyq_frequency_score = await regular_questions_enrichment_service._calculate_pyq_frequency_score_llm(
                    question.stem, enrichment_data
                )
                
                question.pyq_frequency_score = pyq_frequency_score
                db.commit()
                success_count += 1
                logger.info(f"✅ PYQ frequency calculated: {pyq_frequency_score}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error in PYQ frequency calculation for {question.id[:8]}: {e}")
        
        return StageResponse(
            success=True,
            stage="stage3_pyq_frequency",
            processed=processed,
            success_count=success_count,
            failed_count=failed_count,
            details={
                "fields_calculated": ["pyq_frequency_score"]
            }
        )
        
    finally:
        db.close()

# =============================================================================
# STAGE 4: CONCEPT EXTRACTION STATUS UPDATE
# =============================================================================

@stages_router.post("/stage4-concept-status", response_model=StageResponse)
async def stage4_concept_status(request: StageRequest):
    """
    STAGE 4: Concept Extraction Status Update
    Sets: concept_extraction_status based on core_concepts availability
    """
    db = SessionLocal()
    try:
        logger.info("🎯 STAGE 4: Concept Extraction Status Update")
        
        # Get questions that need status update
        if request.question_ids:
            questions = db.execute(
                select(Question).where(Question.id.in_(request.question_ids))
            ).scalars().all()
        else:
            questions = db.execute(
                select(Question)
                .where(Question.concept_extraction_status != 'completed')
                .limit(request.limit)
            ).scalars().all()
        
        processed = len(questions)
        success_count = 0
        failed_count = 0
        
        for question in questions:
            try:
                logger.info(f"🔄 Processing {question.id[:8]}... - Concept Status")
                
                # Check if core_concepts exist and are valid
                if question.core_concepts:
                    try:
                        import json
                        concepts = json.loads(question.core_concepts) if isinstance(question.core_concepts, str) else question.core_concepts
                        if concepts and len(concepts) > 0:
                            question.concept_extraction_status = 'completed'
                            success_count += 1
                            logger.info(f"✅ Status set to 'completed' - {len(concepts)} concepts found")
                        else:
                            question.concept_extraction_status = 'pending'
                            failed_count += 1
                            logger.warning(f"⚠️ Status set to 'pending' - no valid concepts")
                    except:
                        question.concept_extraction_status = 'pending'
                        failed_count += 1
                        logger.warning(f"⚠️ Status set to 'pending' - invalid concepts format")
                else:
                    question.concept_extraction_status = 'pending'
                    failed_count += 1
                    logger.warning(f"⚠️ Status set to 'pending' - no concepts found")
                
                db.commit()
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error updating status for {question.id[:8]}: {e}")
        
        return StageResponse(
            success=True,
            stage="stage4_concept_status",
            processed=processed,
            success_count=success_count,
            failed_count=failed_count,
            details={
                "fields_updated": ["concept_extraction_status"]
            }
        )
        
    finally:
        db.close()

# =============================================================================
# STAGE 5A: COMPLETE QUALITY VERIFICATION (Original Process)
# =============================================================================

@stages_router.post("/stage5a-quality-verification", response_model=StageResponse)
async def stage5a_quality_verification(request: StageRequest):
    """
    STAGE 5A: Complete Quality Verification (Original Process)
    Performs the EXACT same quality verification as in regular_enrichment_service._perform_quality_verification
    Sets: answer_match, quality_verified, is_active
    """
    db = SessionLocal()
    try:
        logger.info("🎯 STAGE 5A: Complete Quality Verification (Original Process)")
        
        # Get questions that need quality verification
        if request.question_ids:
            questions = db.execute(
                select(Question).where(Question.id.in_(request.question_ids))
            ).scalars().all()
        else:
            questions = db.execute(
                select(Question)
                .where(and_(
                    Question.right_answer.isnot(None),
                    Question.concept_extraction_status == 'completed'
                ))
                .limit(request.limit)
            ).scalars().all()
        
        processed = len(questions)
        success_count = 0
        failed_count = 0
        
        for question in questions:
            try:
                logger.info(f"🔄 Processing {question.id[:8]}... - Quality Verification")
                
                # Prepare enrichment data exactly as in original code
                enrichment_data = {
                    'right_answer': question.right_answer,
                    'category': question.category,
                    'subcategory': question.subcategory,
                    'type_of_question': question.type_of_question,
                    'difficulty_score': question.difficulty_score,
                    'difficulty_band': question.difficulty_band,
                    'core_concepts': question.core_concepts,
                    'concept_difficulty': question.concept_difficulty,
                    'operations_required': question.operations_required,
                    'problem_structure': question.problem_structure,
                    'concept_keywords': question.concept_keywords,
                    'solution_method': question.solution_method,
                    'pyq_frequency_score': question.pyq_frequency_score,
                    'concept_extraction_status': question.concept_extraction_status
                }
                
                # Use the EXACT original quality verification process
                quality_result = await regular_questions_enrichment_service._perform_quality_verification(
                    question.stem,
                    enrichment_data,
                    question.answer,
                    question.snap_read,
                    question.solution_approach,
                    question.detailed_solution,
                    question.principle_to_remember,
                    question.mcq_options
                )
                
                # Update question with results
                question.answer_match = quality_result.get('answer_match', False)
                question.quality_verified = quality_result.get('quality_verified', False)
                
                if question.quality_verified:
                    question.is_active = True
                
                db.commit()
                
                if question.quality_verified:
                    success_count += 1
                    logger.info(f"✅ Quality verified: TRUE")
                else:
                    failed_count += 1
                    logger.info(f"❌ Quality verification failed")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error in quality verification for {question.id[:8]}: {e}")
        
        return StageResponse(
            success=True,
            stage="stage5a_quality_verification",
            processed=processed,
            success_count=success_count,
            failed_count=failed_count,
            details={
                "fields_set": ["answer_match", "quality_verified", "is_active"],
                "verification_rate": f"{(success_count/processed)*100:.1f}%" if processed > 0 else "0%",
                "criteria": "EXACT original 22-criteria quality verification process"
            }
        )
        
    finally:
        db.close()

# No additional stages - removed unauthorized alterations

# Export router for main server
__all__ = ['stages_router']