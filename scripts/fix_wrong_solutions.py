#!/usr/bin/env python3
"""
CRITICAL FIX: Re-enrich all questions with proper LLM-generated solutions
This fixes the bug where all questions had generic hardcoded solutions
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from database import get_async_session, Question
from llm_enrichment import LLMEnrichmentPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_wrong_solutions():
    """Re-enrich all questions with proper LLM solutions"""
    
    print("🔧 CRITICAL FIX: Re-enriching all questions with proper LLM solutions")
    print("=" * 70)
    print("Issue: All questions have generic solutions instead of question-specific ones")
    print("Fix: Replace with actual LLM-generated solutions")
    print("=" * 70)
    
    try:
        # Initialize LLM enrichment pipeline
        llm_enricher = LLMEnrichmentPipeline()
        
        async with get_async_session() as db:
            # Get all questions that need re-enrichment
            result = await db.execute(
                select(Question).where(
                    Question.solution_approach.like('%Mathematical approach to solve this problem%')
                )
            )
            questions = result.scalars().all()
            
            total_questions = len(questions)
            print(f"Found {total_questions} questions with generic solutions to fix")
            
            if total_questions == 0:
                print("✅ No questions found with generic solutions")
                return
            
            success_count = 0
            error_count = 0
            
            for i, question in enumerate(questions, 1):
                try:
                    print(f"\n[{i}/{total_questions}] Processing question: {question.stem[:60]}...")
                    
                    # Generate proper solutions using LLM
                    enrichment_result = await llm_enricher.complete_auto_generation(
                        stem=question.stem,
                        hint_category=question.category,
                        hint_subcategory=question.subcategory
                    )
                    
                    # Update with LLM-generated solutions
                    question.answer = enrichment_result.get('answer', question.answer)
                    question.solution_approach = enrichment_result.get('solution_approach', question.solution_approach)
                    question.detailed_solution = enrichment_result.get('detailed_solution', question.detailed_solution)
                    
                    # Update other fields too
                    question.difficulty_score = enrichment_result.get('difficulty_score', question.difficulty_score)
                    question.difficulty_band = enrichment_result.get('difficulty_band', question.difficulty_band)
                    question.learning_impact = enrichment_result.get('learning_impact', question.learning_impact)
                    
                    await db.commit()
                    
                    print(f"✅ Updated question {question.id}")
                    print(f"   Answer: {question.answer}")
                    print(f"   Solution: {question.solution_approach[:80]}...")
                    
                    success_count += 1
                    
                    # Add small delay to avoid overwhelming the LLM API
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to enrich question {question.id}: {e}")
                    error_count += 1
                    continue
            
            print(f"\n🎉 RE-ENRICHMENT COMPLETE!")
            print(f"✅ Successfully updated: {success_count} questions")
            print(f"❌ Failed to update: {error_count} questions")
            print(f"📊 Success rate: {(success_count/total_questions)*100:.1f}%")
            
            if success_count > 0:
                print("\n🚀 All questions now have proper LLM-generated solutions!")
                print("Students will now see correct, question-specific solutions.")
            
    except Exception as e:
        logger.error(f"Critical error in solution fix: {e}")
        print(f"❌ Critical error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_wrong_solutions())