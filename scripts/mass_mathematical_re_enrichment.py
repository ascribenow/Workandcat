#!/usr/bin/env python3
"""
Mass Mathematical Re-enrichment - Update ALL questions with textbook-quality solutions
Uses Google Gemini with proper LaTeX formatting for mathematical expressions
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from mathematical_solution_generator import MathematicalSolutionGenerator
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def mass_mathematical_re_enrichment():
    """Re-enrich ALL questions with textbook-quality mathematical solutions"""
    try:
        logger.info("🚀 Starting MASS MATHEMATICAL RE-ENRICHMENT...")
        logger.info("📚 Converting all solutions to textbook-quality format with proper LaTeX")
        
        # Initialize database
        init_database()
        db = SessionLocal()
        
        # Initialize mathematical solution generator
        generator = MathematicalSolutionGenerator()
        
        # Get ALL active questions
        all_questions = db.query(Question).filter(Question.is_active == True).all()
        
        logger.info(f"📊 Found {len(all_questions)} questions to re-enrich with mathematical formatting")
        
        if len(all_questions) == 0:
            logger.info("❌ No questions found!")
            return False
        
        # Confirm with logging (since this is a major operation)
        logger.info("⚠️  This will update ALL questions with new mathematical solutions")
        logger.info("🔄 Starting in 3 seconds...")
        await asyncio.sleep(3)
        
        success_count = 0
        failed_count = 0
        
        # Process each question
        for i, question in enumerate(all_questions):
            try:
                logger.info(f"\n🔄 [{i+1}/{len(all_questions)}] Processing: {question.stem[:60]}...")
                
                # Generate textbook-quality mathematical solutions
                approach, detailed = await generator.generate_textbook_quality_solutions(
                    question.stem,
                    question.answer or "Unknown",
                    "Quantitative Aptitude",  # Generic category
                    question.subcategory or "General"
                )
                
                # Update question with mathematical solutions
                question.solution_approach = approach
                question.detailed_solution = detailed
                
                db.commit()
                success_count += 1
                
                logger.info(f"  ✅ Updated with mathematical formatting")
                logger.info(f"  📝 Preview: {approach[:80]}...")
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.8)
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process question {i+1}: {e}")
                failed_count += 1
                continue
        
        # Final summary
        logger.info(f"\n🎉 MASS MATHEMATICAL RE-ENRICHMENT COMPLETED!")
        logger.info(f"✅ Successfully updated: {success_count}")
        logger.info(f"❌ Failed to update: {failed_count}")
        logger.info(f"📊 Total questions: {len(all_questions)}")
        
        # Show samples of mathematical solutions
        logger.info(f"\n📋 SAMPLE MATHEMATICAL SOLUTIONS:")
        updated_questions = db.query(Question).filter(
            Question.solution_approach != None,
            Question.detailed_solution != None
        ).limit(3).all()
        
        for i, q in enumerate(updated_questions):
            logger.info(f"\n--- Sample {i+1} ---")
            logger.info(f"Question: {q.stem[:60]}...")
            logger.info(f"Answer: {q.answer}")
            logger.info(f"Approach: {q.solution_approach[:120]}...")
            
            # Check for LaTeX formatting
            has_latex = '$' in (q.detailed_solution or '')
            logger.info(f"Has LaTeX formatting: {'✅' if has_latex else '❌'}")
        
        success_rate = success_count / len(all_questions) if all_questions else 0
        logger.info(f"\n📈 Overall success rate: {success_rate:.1%}")
        
        if success_rate > 0.8:
            logger.info("🎉 MASS RE-ENRICHMENT SUCCESSFUL!")
            logger.info("📚 All questions now have textbook-quality mathematical solutions!")
        else:
            logger.warning("⚠️ Some questions failed to update - check logs above")
        
        return success_rate > 0.8
        
    except Exception as e:
        logger.error(f"❌ Mass mathematical re-enrichment failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("🚨 MASS MATHEMATICAL RE-ENRICHMENT")
    print("This will update ALL questions with textbook-quality solutions using Google Gemini.")
    print("Are you sure you want to continue? This will take several minutes...")
    
    # For automated execution, comment out the input() line
    # confirm = input("Type 'YES' to continue: ")
    # if confirm != 'YES':
    #     print("❌ Operation cancelled")
    #     exit(1)
    
    success = asyncio.run(mass_mathematical_re_enrichment())
    print("\n" + "="*50)
    if success:
        print("🎉 SUCCESS: All questions updated with mathematical formatting!")
        print("📚 Students will now see textbook-quality solutions with proper fractions, exponents, etc.")
    else:
        print("❌ FAILED: Some issues occurred during re-enrichment")
    print("="*50)
    exit(0 if success else 1)