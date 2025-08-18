#!/usr/bin/env python3
"""
Re-enrich all questions using direct OpenAI API instead of EMERGENT_LLM_KEY
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from llm_enrichment import LLMEnrichmentPipeline
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def re_enrich_all_questions():
    """Re-enrich all questions using OpenAI API"""
    try:
        logger.info("🤖 Starting re-enrichment with OpenAI API...")
        
        # Initialize database
        init_database()
        db = SessionLocal()
        
        # Check API keys
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not openai_key or not anthropic_key:
            logger.error("Required API keys not found")
            return False
        
        logger.info("✅ API keys found, initializing LLM pipeline...")
        
        # Initialize enrichment pipeline (will use direct API keys now)
        enrichment_pipeline = LLMEnrichmentPipeline(llm_api_key="dummy") # Not used anymore
        
        # Get all questions
        questions = db.query(Question).all()
        logger.info(f"Found {len(questions)} questions to re-enrich")
        
        enriched_count = 0
        failed_count = 0
        
        # Track diversity
        subcategory_counts = {}
        type_counts = {}
        
        for i, question in enumerate(questions):
            try:
                logger.info(f"Re-enriching question {i+1}/{len(questions)}: {question.stem[:50]}...")
                
                # Use LLM to categorize question
                category, subcategory, type_of_question = await enrichment_pipeline.categorize_question(
                    stem=question.stem,
                    hint_category=None,
                    hint_subcategory=None
                )
                
                logger.info(f"  New Classification: {category} > {subcategory} > {type_of_question}")
                
                # Update question with new classification
                question.subcategory = subcategory
                question.type_of_question = type_of_question
                
                # Track diversity
                subcategory_counts[subcategory] = subcategory_counts.get(subcategory, 0) + 1
                type_counts[type_of_question] = type_counts.get(type_of_question, 0) + 1
                
                # Find appropriate topic_id based on category
                topic = db.query(Topic).filter(
                    Topic.category.like(f"%{category}%")
                ).first()
                
                if topic:
                    question.topic_id = topic.id
                
                enriched_count += 1
                
                # Commit in batches
                if enriched_count % 10 == 0:
                    logger.info(f"✅ Re-enriched {enriched_count} questions...")
                    db.commit()
                    
                    # Show current diversity stats
                    logger.info(f"  Current diversity: {len(subcategory_counts)} subcategories, {len(type_counts)} types")
                
                # Small delay to be nice to API
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to re-enrich question {i+1}: {e}")
                failed_count += 1
                continue
        
        # Final commit
        db.commit()
        
        logger.info("\\n🎉 RE-ENRICHMENT COMPLETED!")
        logger.info(f"✅ Successfully re-enriched: {enriched_count} questions")
        logger.info(f"❌ Failed to re-enrich: {failed_count} questions")
        
        logger.info(f"\\n📊 FINAL DIVERSITY RESULTS:")
        logger.info(f"✅ Unique subcategories: {len(subcategory_counts)}")
        logger.info(f"✅ Unique types: {len(type_counts)}")
        
        logger.info(f"\\n📊 Top subcategories:")
        for subcat, count in sorted(subcategory_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {subcat}: {count} questions")
        
        logger.info(f"\\n📊 Top types:")
        for qtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {qtype}: {count} questions")
        
        # Success if we have good diversity
        diversity_success = len(subcategory_counts) >= 6 and len(type_counts) >= 8
        
        if diversity_success:
            logger.info("\\n🎯 DIVERSITY TARGET ACHIEVED!")
            logger.info("✅ Ready for dual-dimension diversity testing")
        else:
            logger.info("\\n⚠️  Limited diversity - but should be better than before")
            
        return diversity_success
        
    except Exception as e:
        logger.error(f"Re-enrichment failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(re_enrich_all_questions())
    exit(0 if success else 1)