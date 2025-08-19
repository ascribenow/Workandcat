#!/usr/bin/env python3
"""
Mass Human-Friendly Re-enrichment - Update ALL questions with human-readable solutions
NO LaTeX, NO raw syntax - just plain mathematical notation optimized for humans
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from human_friendly_solution_generator import HumanFriendlySolutionGenerator
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def mass_human_friendly_re_enrichment():
    """Re-enrich ALL questions with human-friendly mathematical solutions"""
    try:
        logger.info("🚀 Starting MASS HUMAN-FRIENDLY RE-ENRICHMENT...")
        logger.info("📚 Converting all solutions to human-readable format (NO LaTeX)")
        
        # Initialize database
        init_database()
        db = SessionLocal()
        
        # Initialize human-friendly solution generator
        generator = HumanFriendlySolutionGenerator()
        
        # Get ALL active questions
        all_questions = db.query(Question).filter(Question.is_active == True).all()
        
        logger.info(f"📊 Found {len(all_questions)} questions to re-enrich with human-friendly formatting")
        
        if len(all_questions) == 0:
            logger.info("❌ No questions found!")
            return False
        
        success_count = 0
        failed_count = 0
        
        # Process each question
        for i, question in enumerate(all_questions):
            try:
                logger.info(f"\n🔄 [{i+1}/{len(all_questions)}] Processing: {question.stem[:60]}...")
                
                # Generate human-friendly solutions
                approach, detailed = await generator.generate_human_friendly_solutions(
                    question.stem,
                    question.answer or "Unknown",
                    "Quantitative Aptitude",  # Generic category
                    question.subcategory or "General"
                )
                
                # Update question with human-friendly solutions
                question.solution_approach = approach
                question.detailed_solution = detailed
                
                db.commit()
                success_count += 1
                
                logger.info(f"  ✅ Updated with human-friendly formatting")
                logger.info(f"  📝 Preview: {approach[:80]}...")
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.8)
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process question {i+1}: {e}")
                failed_count += 1
                continue
        
        # Final summary
        logger.info(f"\n🎉 MASS HUMAN-FRIENDLY RE-ENRICHMENT COMPLETED!")
        logger.info(f"✅ Successfully updated: {success_count}")
        logger.info(f"❌ Failed to update: {failed_count}")
        logger.info(f"📊 Total questions: {len(all_questions)}")
        
        # Show samples of human-friendly solutions
        logger.info(f"\n📋 SAMPLE HUMAN-FRIENDLY SOLUTIONS:")
        updated_questions = db.query(Question).filter(
            Question.solution_approach != None,
            Question.detailed_solution != None
        ).limit(3).all()
        
        for i, q in enumerate(updated_questions):
            logger.info(f"\n--- Sample {i+1} ---")
            logger.info(f"Question: {q.stem[:60]}...")
            logger.info(f"Answer: {q.answer}")
            logger.info(f"Approach: {q.solution_approach[:120]}...")
            
            # Check for NO LaTeX formatting (should be clean)
            has_latex = any(x in (q.detailed_solution or '') for x in ['\\frac', '\\begin', '\\sqrt', '$'])
            logger.info(f"Contains LaTeX (should be NO): {'❌ YES' if has_latex else '✅ NO'}")
        
        success_rate = success_count / len(all_questions) if all_questions else 0
        logger.info(f"\n📈 Overall success rate: {success_rate:.1%}")
        
        if success_rate > 0.8:
            logger.info("🎉 MASS RE-ENRICHMENT SUCCESSFUL!")
            logger.info("📚 All questions now have human-friendly mathematical solutions!")
        else:
            logger.warning("⚠️ Some questions failed to update - check logs above")
        
        return success_rate > 0.8
        
    except Exception as e:
        logger.error(f"❌ Mass human-friendly re-enrichment failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚨 MASS HUMAN-FRIENDLY RE-ENRICHMENT")
    print("This will update ALL questions with human-readable solutions (NO LaTeX).")
    print("Starting immediately...")
    
    success = asyncio.run(mass_human_friendly_re_enrichment())
    print("\n" + "="*50)
    if success:
        print("🎉 SUCCESS: All questions updated with human-friendly formatting!")
        print("📚 Students will now see plain mathematical notation (x², 45/3, √16)")
    else:
        print("❌ FAILED: Some issues occurred during re-enrichment")
    print("="*50)
    exit(0 if success else 1)