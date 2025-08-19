#!/usr/bin/env python3
"""
Fix Solution Formatting Issues - Remove LaTeX, fix truncation, improve quality
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from enhanced_solution_generation import EnhancedSolutionGenerator
import logging
import asyncio
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def has_formatting_issues(approach: str, detailed: str) -> bool:
    """Check if solutions have formatting issues that need fixing"""
    if not approach or not detailed:
        return True
        
    # Check for LaTeX artifacts
    latex_artifacts = ['\\(', '\\)', '\\[', '\\]', '$$', '$']
    has_latex = any(artifact in approach + detailed for artifact in latex_artifacts)
    
    # Check for truncation issues (ending with numbers)
    truncation_pattern = r'\d+\.\s*$'
    has_truncation = bool(re.search(truncation_pattern, approach)) or bool(re.search(truncation_pattern, detailed))
    
    # Check for very short approaches (likely truncated)
    too_short = len(approach) < 50
    
    # Check for generic/poor solutions
    generic_indicators = ['failed', 'could not', 'unable to', 'error', 'Alternative 1']
    has_generic = any(indicator.lower() in (approach + detailed).lower() for indicator in generic_indicators)
    
    return has_latex or has_truncation or too_short or has_generic

async def fix_solution_formatting():
    """Fix all questions with formatting issues"""
    try:
        logger.info("🔧 Starting Solution Formatting Fix...")
        
        # Initialize database and generator
        init_database()
        db = SessionLocal()
        generator = EnhancedSolutionGenerator()
        
        # Get questions with formatting issues
        all_questions = db.query(Question).filter(Question.is_active == True).all()
        
        questions_to_fix = []
        for q in all_questions:
            if has_formatting_issues(q.solution_approach or "", q.detailed_solution or ""):
                questions_to_fix.append(q)
        
        logger.info(f"📊 Found {len(questions_to_fix)} questions with formatting issues out of {len(all_questions)} total")
        
        if len(questions_to_fix) == 0:
            logger.info("✅ No formatting issues found!")
            return True
        
        # Show samples of issues
        logger.info("\n🔍 Sample issues found:")
        for i, q in enumerate(questions_to_fix[:3]):
            logger.info(f"\n--- Question {i+1} ---")
            logger.info(f"Stem: {q.stem[:60]}...")
            
            # Check specific issues
            issues = []
            if '\\(' in (q.solution_approach or '') + (q.detailed_solution or ''):
                issues.append("LaTeX formatting")
            if re.search(r'\d+\.\s*$', q.solution_approach or ''):
                issues.append("Truncated approach")
            if len(q.solution_approach or '') < 50:
                issues.append("Too short approach")
                
            logger.info(f"Issues: {', '.join(issues)}")
            logger.info(f"Current approach: {q.solution_approach}")
        
        # Fix each question
        success_count = 0
        failed_count = 0
        
        for i, question in enumerate(questions_to_fix):
            try:
                logger.info(f"\n🔄 [{i+1}/{len(questions_to_fix)}] Fixing: {question.stem[:50]}...")
                
                # Generate new enhanced solutions
                enhanced_approach, enhanced_detailed = await generator.generate_enhanced_solutions_with_fallback(
                    question.stem,
                    question.answer or "Unknown",
                    "Quantitative Aptitude",  # Use generic category 
                    question.subcategory or "General"
                )
                
                # Update question with fixed solutions
                question.solution_approach = enhanced_approach
                question.detailed_solution = enhanced_detailed
                
                db.commit()
                success_count += 1
                
                logger.info(f"  ✅ Fixed formatting issues")
                logger.info(f"  📝 New approach: {enhanced_approach[:100]}...")
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ Failed to fix question {i+1}: {e}")
                failed_count += 1
                continue
        
        # Final summary
        logger.info(f"\n🎉 SOLUTION FORMATTING FIX COMPLETED!")
        logger.info(f"✅ Successfully fixed: {success_count}")
        logger.info(f"❌ Failed to fix: {failed_count}")
        logger.info(f"📊 Issues addressed: LaTeX removal, truncation fixes, quality improvement")
        
        # Verify fixes
        logger.info(f"\n🔍 POST-FIX VERIFICATION:")
        remaining_issues = 0
        for q in questions_to_fix:
            db.refresh(q)  # Refresh from database
            if has_formatting_issues(q.solution_approach or "", q.detailed_solution or ""):
                remaining_issues += 1
        
        logger.info(f"📊 Remaining issues: {remaining_issues}/{len(questions_to_fix)}")
        
        if remaining_issues == 0:
            logger.info("🎉 All formatting issues resolved!")
        else:
            logger.info(f"⚠️ {remaining_issues} questions still have issues")
        
        success_rate = success_count / len(questions_to_fix) if questions_to_fix else 1.0
        logger.info(f"📈 Overall success rate: {success_rate:.1%}")
        
        return success_rate > 0.8
        
    except Exception as e:
        logger.error(f"❌ Solution formatting fix failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(fix_solution_formatting())
    exit(0 if success else 1)