#!/usr/bin/env python3
"""
Test Script: Conceptual Frequency Analysis
Tests the new LLM-powered conceptual frequency calculation system
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from database import get_database, Question
from llm_enrichment import LLMEnrichmentPipeline  
from conceptual_frequency_analyzer import ConceptualFrequencyAnalyzer
from sqlalchemy import select
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

async def test_conceptual_frequency_analysis():
    """Test the conceptual frequency analysis system"""
    
    try:
        # Initialize LLM pipeline
        llm_api_key = os.getenv("EMERGENT_LLM_KEY")
        if not llm_api_key:
            logger.error("❌ EMERGENT_LLM_KEY not found in environment")
            return
        
        llm_pipeline = LLMEnrichmentPipeline(llm_api_key)
        frequency_analyzer = ConceptualFrequencyAnalyzer(llm_pipeline)
        
        logger.info("✅ Initialized conceptual frequency analyzer")
        
        # Get a sample question from database
        async for db in get_database():
            # Get a few sample questions
            result = await db.execute(
                select(Question).where(Question.is_active == True).limit(3)
            )
            questions = result.scalars().all()
            
            if not questions:
                logger.warning("⚠️  No active questions found in database")
                return
            
            # Test pattern analysis for first question
            test_question = questions[0]
            logger.info(f"🔍 Testing pattern analysis for question: {test_question.stem[:100]}...")
            
            # Analyze question pattern
            pattern = await frequency_analyzer.analyze_question_pattern(test_question)
            
            logger.info("✅ Question Pattern Analysis Results:")
            logger.info(f"   • Category: {pattern.category}")
            logger.info(f"   • Subcategory: {pattern.subcategory}")
            logger.info(f"   • Type: {pattern.type_of_question}")
            logger.info(f"   • Concept Keywords: {pattern.concept_keywords}")
            logger.info(f"   • Solution Approach: {pattern.solution_approach}")
            logger.info(f"   • Mathematical Concepts: {pattern.mathematical_concepts}")
            
            # Test conceptual frequency calculation
            logger.info("🔍 Testing conceptual frequency calculation...")
            
            freq_result = await frequency_analyzer.calculate_conceptual_frequency(
                db, test_question, years_window=10
            )
            
            logger.info("✅ Conceptual Frequency Analysis Results:")
            logger.info(f"   • Frequency Score: {freq_result.get('frequency_score', 0.0):.4f}")
            logger.info(f"   • Conceptual Matches: {freq_result.get('conceptual_matches', 0)}")
            logger.info(f"   • Total PYQ Analyzed: {freq_result.get('total_pyq_analyzed', 0)}")
            logger.info(f"   • Top Matching Concepts: {freq_result.get('top_matching_concepts', [])}")
            logger.info(f"   • Analysis Method: {freq_result.get('analysis_method', 'unknown')}")
            
            # Test batch processing with multiple questions
            if len(questions) > 1:
                logger.info("🔍 Testing batch frequency calculation...")
                
                batch_results = await frequency_analyzer.batch_calculate_frequencies(
                    db, questions[:2], years_window=10
                )
                
                logger.info(f"✅ Batch processing completed for {len(batch_results)} questions")
                for question_id, result in batch_results.items():
                    logger.info(f"   • Question {question_id[:8]}...: Score={result.get('frequency_score', 0):.3f}, Matches={result.get('conceptual_matches', 0)}")
            
            logger.info("🎉 Conceptual frequency analysis test completed successfully!")
            break
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conceptual_frequency_analysis())