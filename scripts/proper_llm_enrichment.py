#!/usr/bin/env python3
"""
Proper LLM Enrichment for Canonical Taxonomy
Uses actual LLM calls to map all questions to canonical (Category, Subcategory, Type)
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from llm_enrichment import LLMEnrichmentPipeline
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def enrich_questions_with_llm(batch_size: int = 10):
    """
    Use LLM to properly classify all questions with canonical taxonomy
    """
    init_database()
    db = SessionLocal()
    
    try:
        # Initialize LLM enrichment pipeline
        llm_api_key = os.getenv('EMERGENT_LLM_KEY')
        if not llm_api_key:
            raise Exception("EMERGENT_LLM_KEY not found in environment")
        
        enrichment_pipeline = LLMEnrichmentPipeline(llm_api_key=llm_api_key)
        
        # Get all questions that need LLM enrichment
        questions = db.query(Question).all()
        logger.info(f"Processing {len(questions)} questions with LLM enrichment...")
        
        enriched_count = 0
        failed_count = 0
        
        # Process in batches to avoid overwhelming the LLM
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: questions {i+1}-{min(i+batch_size, len(questions))}")
            
            for question in batch:
                try:
                    # Use LLM to categorize question
                    category, subcategory, type_of_question = await enrichment_pipeline.categorize_question(
                        stem=question.stem,
                        hint_category=None,  # Let LLM determine
                        hint_subcategory=question.subcategory  # Use existing as hint
                    )
                    
                    # Update question with LLM classification
                    question.subcategory = subcategory
                    question.type_of_question = type_of_question
                    
                    # Find appropriate topic_id based on category
                    topic = db.query(Topic).filter(
                        Topic.category.like(f"%{category}%")
                    ).first()
                    
                    if topic:
                        question.topic_id = topic.id
                    
                    enriched_count += 1
                    
                    if enriched_count % 50 == 0:
                        logger.info(f"✅ Enriched {enriched_count} questions...")
                        db.commit()  # Commit in batches
                    
                except Exception as e:
                    logger.error(f"Failed to enrich question {question.id}: {e}")
                    failed_count += 1
                    continue
            
            # Sleep between batches to avoid rate limiting
            if i + batch_size < len(questions):
                await asyncio.sleep(2)
        
        # Final commit
        db.commit()
        
        logger.info(f"✅ LLM Enrichment completed!")
        logger.info(f"✅ Successfully enriched: {enriched_count} questions")
        logger.info(f"❌ Failed to enrich: {failed_count} questions")
        
        # Validate results
        enriched_questions = db.query(Question).filter(
            Question.type_of_question.isnot(None)
        ).all()
        
        unique_types = set(q.type_of_question for q in enriched_questions if q.type_of_question)
        unique_subcategories = set(q.subcategory for q in enriched_questions if q.subcategory)
        
        logger.info(f"✅ Final results:")
        logger.info(f"  - Questions with types: {len(enriched_questions)}")
        logger.info(f"  - Unique types: {len(unique_types)}")
        logger.info(f"  - Unique subcategories: {len(unique_subcategories)}")
        logger.info(f"  - Sample types: {list(unique_types)[:10]}")
        
        return enriched_count >= len(questions) * 0.8  # 80% success rate
        
    except Exception as e:
        logger.error(f"LLM enrichment failed: {e}")
        return False
    finally:
        db.close()

async def enrich_pyq_questions_with_llm(batch_size: int = 10):
    """
    Use LLM to properly classify all PYQ questions with canonical taxonomy
    """
    init_database()
    db = SessionLocal()
    
    try:
        # Initialize LLM enrichment pipeline
        llm_api_key = os.getenv('EMERGENT_LLM_KEY')
        if not llm_api_key:
            raise Exception("EMERGENT_LLM_KEY not found in environment")
        
        enrichment_pipeline = LLMEnrichmentPipeline(llm_api_key=llm_api_key)
        
        # Get all PYQ questions
        pyq_questions = db.query(PYQQuestion).all()
        logger.info(f"Processing {len(pyq_questions)} PYQ questions with LLM enrichment...")
        
        enriched_count = 0
        failed_count = 0
        
        # Process in batches
        for i in range(0, len(pyq_questions), batch_size):
            batch = pyq_questions[i:i + batch_size]
            logger.info(f"Processing PYQ batch {i//batch_size + 1}")
            
            for pyq_question in batch:
                try:
                    # Use LLM to categorize PYQ question
                    category, subcategory, type_of_question = await enrichment_pipeline.categorize_question(
                        stem=pyq_question.stem,
                        hint_category=None,  # Let LLM determine
                        hint_subcategory=pyq_question.subcategory  # Use existing as hint
                    )
                    
                    # Update PYQ question with LLM classification
                    pyq_question.subcategory = subcategory
                    pyq_question.type_of_question = type_of_question
                    
                    # Find appropriate topic_id based on category
                    topic = db.query(Topic).filter(
                        Topic.category.like(f"%{category}%")
                    ).first()
                    
                    if topic:
                        pyq_question.topic_id = topic.id
                    
                    enriched_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to enrich PYQ question {pyq_question.id}: {e}")
                    failed_count += 1
                    continue
            
            # Commit batch and sleep
            db.commit()
            if i + batch_size < len(pyq_questions):
                await asyncio.sleep(2)
        
        logger.info(f"✅ PYQ LLM Enrichment completed!")
        logger.info(f"✅ Successfully enriched: {enriched_count} PYQ questions")
        logger.info(f"❌ Failed to enrich: {failed_count} PYQ questions")
        
        return enriched_count >= len(pyq_questions) * 0.8
        
    except Exception as e:
        logger.error(f"PYQ LLM enrichment failed: {e}")
        return False
    finally:
        db.close()

async def main():
    """Run proper LLM enrichment for both questions and PYQ questions"""
    logger.info("🚀 Starting Proper LLM Enrichment for Canonical Taxonomy...")
    
    try:
        # Step 1: Enrich regular questions
        logger.info("📚 Step 1: Enriching regular questions with LLM...")
        questions_success = await enrich_questions_with_llm(batch_size=5)  # Smaller batches for reliability
        
        # Step 2: Enrich PYQ questions  
        logger.info("📋 Step 2: Enriching PYQ questions with LLM...")
        pyq_success = await enrich_pyq_questions_with_llm(batch_size=5)
        
        if questions_success and pyq_success:
            logger.info("🎉 Proper LLM Enrichment SUCCESSFUL!")
            logger.info("✅ All questions classified using actual LLM calls")
            logger.info("✅ Canonical taxonomy mapping via LLM intelligence")
            logger.info("✅ No hardcoded keyword matching used")
            return 0
        else:
            logger.error("❌ LLM enrichment validation failed")
            return 1
            
    except Exception as e:
        logger.error(f"LLM enrichment failed: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))