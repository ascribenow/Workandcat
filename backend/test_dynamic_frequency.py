#!/usr/bin/env python3
"""
Test Dynamic Frequency Calculation
"""

import os
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_async_compatible_db, Question, PYQQuestion
from dynamic_frequency_calculator import DynamicFrequencyCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_dynamic_frequency():
    """
    Test the dynamic frequency calculation
    """
    try:
        logger.info("🧪 Testing Dynamic Frequency Calculation")
        
        # Get database session
        db_gen = get_async_compatible_db()
        db = await db_gen.__anext__()
        
        # Get a sample regular question
        regular_question_result = await db.execute(
            select(Question).where(Question.is_active == True).limit(1)
        )
        regular_question = regular_question_result.scalar_one_or_none()
        
        if not regular_question:
            logger.error("❌ No regular questions found for testing")
            return
        
        logger.info(f"📊 Testing with regular question: {regular_question.stem[:50]}...")
        logger.info(f"   Category: {regular_question.category}")
        logger.info(f"   Subcategory: {regular_question.subcategory}")
        logger.info(f"   Current PYQ frequency: {regular_question.pyq_frequency_score}")
        
        # Check PYQ questions available
        pyq_questions_result = await db.execute(
            select(PYQQuestion).where(PYQQuestion.is_active == True)
        )
        pyq_questions = pyq_questions_result.scalars().all()
        
        logger.info(f"📊 Available PYQ questions: {len(pyq_questions)}")
        
        if pyq_questions:
            sample_pyq = pyq_questions[0]
            logger.info(f"   Sample PYQ: {sample_pyq.stem[:50]}...")
            logger.info(f"   Difficulty band: {getattr(sample_pyq, 'difficulty_band', 'None')}")
            logger.info(f"   Core concepts: {getattr(sample_pyq, 'core_concepts', 'None')}")
            logger.info(f"   Is active: {getattr(sample_pyq, 'is_active', 'None')}")
        
        # Test the dynamic frequency calculator
        logger.info("🧮 Testing Dynamic Frequency Calculator...")
        calculator = DynamicFrequencyCalculator()
        
        frequency_result = await calculator.calculate_true_pyq_frequency(regular_question, db)
        
        logger.info("📊 Dynamic Frequency Calculation Results:")
        logger.info(f"   Frequency Score: {frequency_result.get('frequency_score', 'None')}")
        logger.info(f"   Conceptual Matches: {frequency_result.get('conceptual_matches_count', 'None')}")
        logger.info(f"   Total PYQ Analyzed: {frequency_result.get('total_pyq_analyzed', 'None')}")
        logger.info(f"   Average Similarity: {frequency_result.get('average_similarity', 'None')}")
        logger.info(f"   Confidence Score: {frequency_result.get('confidence_score', 'None')}")
        
        if frequency_result.get('frequency_score', 0) > 0:
            logger.info("✅ Dynamic frequency calculation working!")
        else:
            logger.warning("⚠️ Dynamic frequency calculation returned 0 - may need PYQ enrichment")
        
        # Close database session
        await db.close()
        
    except Exception as e:
        logger.error(f"❌ Error testing dynamic frequency: {e}")

if __name__ == "__main__":
    asyncio.run(test_dynamic_frequency())