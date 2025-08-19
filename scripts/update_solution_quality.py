#!/usr/bin/env python3
"""
Update Solution Quality - Re-enrich questions with Google Gemini + enhanced solution generation
Fixes solution quality issues and improves mathematical explanations
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from enhanced_solution_generation import EnhancedSolutionGenerator
import logging
import asyncio
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_solution_quality():
    """Update solution quality for all questions using enhanced Gemini-based generation"""
    try:
        logger.info("🚀 Starting Solution Quality Enhancement with Google Gemini...")
        
        # Initialize database
        init_database()
        db = SessionLocal()
        
        # Initialize enhanced solution generator
        generator = EnhancedSolutionGenerator()
        
        # Get all questions that need solution quality improvement
        # Focus on questions with poor solutions or missing detailed explanations
        questions = db.query(Question).filter(
            Question.is_active == True
        ).all()
        
        logger.info(f"📊 Found {len(questions)} questions to enhance")
        
        success_count = 0
        improvement_count = 0
        failed_count = 0
        
        # Process each question
        for i, question in enumerate(questions):
            try:
                logger.info(f"\n🔄 [{i+1}/{len(questions)}] Enhancing: {question.stem[:50]}...")
                
                # Check if solution needs improvement
                needs_improvement = (
                    not question.solution_approach or 
                    len(question.solution_approach) < 10 or
                    not question.detailed_solution or 
                    len(question.detailed_solution) < 20 or
                    "failed" in (question.solution_approach or "").lower() or
                    "failed" in (question.detailed_solution or "").lower() or
                    "((" in (question.detailed_solution or "") or  # Remove unwanted parentheses
                    "))" in (question.detailed_solution or "")
                )
                
                if needs_improvement:
                    logger.info("  🔧 Solution needs improvement - regenerating with Gemini...")
                    
                    # Generate enhanced solutions using Gemini
                    enhanced_approach, enhanced_detailed = await generator.generate_enhanced_solutions_with_fallback(
                        question.stem,
                        question.answer or "Unknown",
                        question.subcategory or "General",
                        question.subcategory or "General"
                    )
                    
                    # Update question with enhanced solutions
                    question.solution_approach = enhanced_approach
                    question.detailed_solution = enhanced_detailed
                    
                    db.commit()
                    improvement_count += 1
                    logger.info(f"  ✅ Enhanced solution quality")
                else:
                    logger.info("  ℹ️ Solution already good quality")
                
                success_count += 1
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"  ❌ Failed to enhance question {i+1}: {e}")
                failed_count += 1
                continue
        
        # Final summary
        logger.info(f"\n🎉 SOLUTION QUALITY ENHANCEMENT COMPLETED!")
        logger.info(f"✅ Successfully processed: {success_count}")
        logger.info(f"🔧 Solutions improved: {improvement_count}")
        logger.info(f"❌ Failed enhancements: {failed_count}")
        logger.info(f"📊 Total questions: {len(questions)}")
        
        # Sample enhanced solutions
        logger.info(f"\n📋 SAMPLE ENHANCED SOLUTIONS:")
        enhanced_questions = db.query(Question).filter(
            Question.solution_approach != None,
            Question.detailed_solution != None
        ).limit(2).all()
        
        for i, q in enumerate(enhanced_questions):
            logger.info(f"\n--- Sample {i+1} ---")
            logger.info(f"Question: {q.stem[:80]}...")
            logger.info(f"Answer: {q.answer}")
            logger.info(f"Approach: {q.solution_approach[:100]}...")
            logger.info(f"Detailed: {q.detailed_solution[:150]}...")
        
        success_rate = success_count / len(questions) if questions else 0
        logger.info(f"\n📈 Overall success rate: {success_rate:.1%}")
        
        return success_rate > 0.8  # 80% success rate required
        
    except Exception as e:
        logger.error(f"❌ Solution quality enhancement failed: {e}")
        return False
    finally:
        db.close()

async def test_sample_solution_generation():
    """Test enhanced solution generation with a sample question"""
    logger.info("🧪 Testing Sample Solution Generation...")
    
    generator = EnhancedSolutionGenerator()
    
    # Sample questions from different categories
    test_questions = [
        {
            "stem": "Find the compound interest on Rs. 8000 at 15% per annum for 2 years compounded annually.",
            "answer": "Rs. 2520",
            "category": "Arithmetic", 
            "subcategory": "Simple and Compound Interest"
        },
        {
            "stem": "A train 240m long crosses a platform 360m long in 40 seconds. What is the speed of the train?",
            "answer": "54 km/hr",
            "category": "Arithmetic",
            "subcategory": "Time-Speed-Distance"
        }
    ]
    
    for i, q in enumerate(test_questions):
        logger.info(f"\n🔍 Testing Question {i+1}: {q['stem'][:50]}...")
        
        approach, detailed = await generator.generate_enhanced_solutions_with_fallback(
            q['stem'], q['answer'], q['category'], q['subcategory']
        )
        
        logger.info(f"✅ Solution Approach: {approach}")
        logger.info(f"✅ Detailed Solution: {detailed[:200]}...")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update solution quality with enhanced Gemini generation")
    parser.add_argument("--test", action="store_true", help="Run test only")
    parser.add_argument("--update", action="store_true", help="Update all question solutions")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_sample_solution_generation())
    elif args.update:
        success = asyncio.run(update_solution_quality())
        exit(0 if success else 1)
    else:
        print("Usage: python3 update_solution_quality.py --test | --update")
        exit(1)