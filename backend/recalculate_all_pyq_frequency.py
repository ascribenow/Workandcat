#!/usr/bin/env python3
"""
Re-run corrected PYQ frequency calculation on ALL quality verified questions
Uses the fixed logic that properly handles difficulty filtering
"""

import asyncio
from database import SessionLocal, Question
from sqlalchemy import select
from regular_enrichment_service import regular_questions_enrichment_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def recalculate_all_pyq_frequency():
    print("🚀 RECALCULATING PYQ FREQUENCY FOR ALL QUESTIONS")
    print("=" * 55)
    print("Using CORRECTED method that:")
    print("  ✅ Easy questions (≤1.5): Returns 0.5 immediately")
    print("  ✅ Hard questions (>1.5): Compares against ALL category-matched PYQs")
    print()
    
    db = SessionLocal()
    try:
        # Get all quality verified questions
        result = db.execute(
            select(Question).where(Question.quality_verified == True)
        )
        all_questions = result.scalars().all()
        
        total_questions = len(all_questions)
        print(f"📊 Found {total_questions} quality verified questions to process")
        print()
        
        processed_count = 0
        updated_count = 0
        easy_count = 0
        hard_count = 0
        
        for i, question in enumerate(all_questions, 1):
            try:
                print(f"🔄 Processing {i}/{total_questions}: {question.id[:8]}...")
                
                # Prepare enrichment data for the corrected method
                enrichment_data = {
                    'category': question.category,
                    'subcategory': question.subcategory,
                    'difficulty_score': float(question.difficulty_score or 0),
                    'core_concepts': question.core_concepts or [],
                    'problem_structure': question.problem_structure or [],
                    'concept_keywords': question.concept_keywords or []
                }
                
                # Get current PYQ frequency
                old_frequency = float(question.pyq_frequency_score or 0)
                
                # Run corrected PYQ frequency calculation
                new_frequency = await regular_questions_enrichment_service._calculate_pyq_frequency_score_llm(
                    question.stem, enrichment_data
                )
                
                # Track difficulty categories
                if enrichment_data['difficulty_score'] <= 1.5:
                    easy_count += 1
                else:
                    hard_count += 1
                
                # Update if different
                if abs(new_frequency - old_frequency) > 0.01:  # Account for floating point precision
                    question.pyq_frequency_score = new_frequency
                    updated_count += 1
                    print(f"   ✅ Updated: {old_frequency} → {new_frequency}")
                else:
                    print(f"   = No change: {old_frequency}")
                
                processed_count += 1
                
                # Commit every 10 questions to avoid losing progress
                if processed_count % 10 == 0:
                    db.commit()
                    print(f"   💾 Committed batch (processed: {processed_count})")
                
            except Exception as e:
                logger.error(f"❌ Error processing question {question.id[:8]}: {e}")
                continue
        
        # Final commit
        db.commit()
        
        print()
        print("🎉 RECALCULATION COMPLETE!")
        print("=" * 35)
        print(f"📊 Total processed: {processed_count}/{total_questions}")
        print(f"📊 Questions updated: {updated_count}")
        print(f"📊 Easy questions (≤1.5): {easy_count}")
        print(f"📊 Hard questions (>1.5): {hard_count}")
        print(f"📊 Success rate: {(processed_count/total_questions)*100:.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Recalculation failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(recalculate_all_pyq_frequency())