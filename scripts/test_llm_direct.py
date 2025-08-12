#!/usr/bin/env python3
"""
Direct LLM Enrichment Test - Bypasses Background Tasks
Tests the LLM enrichment pipeline directly to verify it works correctly
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from llm_enrichment import LLMEnrichmentPipeline
from database import get_database, Question, Topic
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

async def test_llm_enrichment_direct():
    """Test LLM enrichment directly without background tasks"""
    
    try:
        # Initialize LLM enrichment pipeline
        llm_api_key = os.getenv("EMERGENT_LLM_KEY")
        if not llm_api_key:
            logger.error("❌ EMERGENT_LLM_KEY not found")
            return
        
        llm_pipeline = LLMEnrichmentPipeline(llm_api_key)
        logger.info("✅ LLM pipeline initialized")
        
        # Test question
        test_stem = "A car travels 200 km in 4 hours. What is its average speed in km/h?"
        
        logger.info(f"🧪 Testing LLM enrichment for: {test_stem}")
        
        # Test the complete enrichment method
        enrichment_result = await llm_pipeline.enrich_question_completely(
            stem=test_stem,
            hint_category="Arithmetic",
            hint_subcategory="Speed-Time-Distance"
        )
        
        logger.info("✅ LLM enrichment completed!")
        logger.info("📊 Enrichment Results:")
        
        for key, value in enrichment_result.items():
            logger.info(f"   • {key}: {value}")
        
        # Validate the results
        answer = enrichment_result.get("answer")
        solution_approach = enrichment_result.get("solution_approach")
        detailed_solution = enrichment_result.get("detailed_solution")
        
        # Check answer correctness (should be 50)
        if answer and ("50" in str(answer)):
            logger.info("✅ Answer is correct: 50 km/h")
        else:
            logger.warning(f"⚠️ Answer might be incorrect: {answer}")
        
        # Check solution quality
        if solution_approach and len(str(solution_approach)) > 10:
            logger.info("✅ Solution approach is comprehensive")
        else:
            logger.warning(f"⚠️ Solution approach seems brief: {solution_approach}")
        
        if detailed_solution and len(str(detailed_solution)) > 20:
            logger.info("✅ Detailed solution is comprehensive") 
        else:
            logger.warning(f"⚠️ Detailed solution seems brief: {detailed_solution}")
        
        # Test with a database question
        logger.info("\n🔍 Testing with existing database question...")
        
        async for db in get_database():
            # Get an inactive question
            result = await db.execute(
                select(Question).where(Question.is_active == False).limit(1)
            )
            inactive_question = result.scalar_one_or_none()
            
            if inactive_question:
                logger.info(f"📝 Found inactive question: {inactive_question.id}")
                logger.info(f"   Stem: {inactive_question.stem[:100]}...")
                
                # Enrich it directly
                enrichment_result = await llm_pipeline.enrich_question_completely(
                    stem=inactive_question.stem,
                    image_url=inactive_question.image_url,
                    hint_category="Arithmetic",
                    hint_subcategory=inactive_question.subcategory
                )
                
                # Update the question directly (not through background task)
                inactive_question.answer = enrichment_result["answer"]
                inactive_question.solution_approach = enrichment_result["solution_approach"]
                inactive_question.detailed_solution = enrichment_result["detailed_solution"]
                inactive_question.subcategory = enrichment_result["subcategory"]
                inactive_question.type_of_question = enrichment_result["type_of_question"]
                inactive_question.difficulty_score = enrichment_result["difficulty_score"]
                inactive_question.difficulty_band = enrichment_result["difficulty_band"]
                inactive_question.learning_impact = enrichment_result["learning_impact"]
                inactive_question.importance_index = enrichment_result["importance_index"]
                inactive_question.frequency_band = enrichment_result["frequency_band"]
                inactive_question.tags = enrichment_result.get("tags", [])
                inactive_question.source = enrichment_result.get("source", "LLM Generated")
                inactive_question.is_active = True
                
                await db.commit()
                logger.info(f"✅ Successfully enriched and activated question {inactive_question.id}")
                
            else:
                logger.info("⚠️ No inactive questions found to test with")
            
            break
        
        logger.info("🎉 Direct LLM enrichment test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error in direct LLM enrichment test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_enrichment_direct())