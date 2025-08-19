#!/usr/bin/env python3
"""
Test the improved Maker-Checker system with stricter validation
"""

import sys
import os
sys.path.append('/app/backend')

import logging
import asyncio
from standardized_enrichment_engine import standardized_enricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_improved_maker_checker():
    """Test the improved system on a real problem"""
    try:
        logger.info("🧪 TESTING IMPROVED MAKER-CHECKER SYSTEM")
        logger.info("=" * 70)
        
        # Use a real problem that was failing before
        test_question = "The integers 573921 and 575713 when divided by a 3 digit number leave the same remainder. What is that 3 digit number?"
        test_answer = "896"
        
        logger.info(f"📝 Test Question: {test_question}")
        logger.info(f"✅ Expected Answer: {test_answer}")
        
        # Test the improved system
        result = await standardized_enricher.enrich_question_solution(
            question_stem=test_question,
            answer=test_answer,
            subcategory="Number Theory",
            question_type="Remainder Problems"
        )
        
        if result["success"]:
            logger.info(f"\n✅ System Test Successful!")
            logger.info(f"🎯 Workflow: {result.get('workflow', 'Unknown')}")
            logger.info(f"📊 Quality Score: {result.get('quality_score', 'N/A')}")
            
            approach = result.get('approach', '')
            detailed_solution = result.get('detailed_solution', '')
            
            # Extract explanation
            explanation = ""
            if "KEY INSIGHT:" in detailed_solution:
                parts = detailed_solution.split("KEY INSIGHT:", 1)
                solution_only = parts[0].strip()
                explanation = parts[1].strip()
            else:
                solution_only = detailed_solution
                explanation = "No explanation found"
            
            logger.info(f"\n📋 GENERATED CONTENT ANALYSIS:")
            logger.info("=" * 50)
            
            # Check for specific improvements
            logger.info(f"\n🔍 APPROACH ({len(approach)} chars):")
            logger.info(f"{approach}")
            
            # Check if approach is specific
            is_specific_approach = not any(generic in approach.lower() for generic in [
                "apply systematic", "standard method", "general approach", "mathematical reasoning"
            ])
            logger.info(f"   Specific to problem: {'✅ Yes' if is_specific_approach else '❌ No - still generic'}")
            
            logger.info(f"\n🔍 DETAILED SOLUTION ({len(solution_only)} chars):")
            logger.info(f"{solution_only[:300]}{'...' if len(solution_only) > 300 else ''}")
            
            # Check if solution is teaching-focused
            has_teaching_language = any(phrase in solution_only.lower() for phrase in [
                "let's", "we need", "now we", "we can", "we find"
            ])
            logger.info(f"   Uses teaching language: {'✅ Yes' if has_teaching_language else '❌ No - not student-focused'}")
            
            logger.info(f"\n🔍 EXPLANATION ({len(explanation)} chars):")
            logger.info(f"{explanation}")
            
            # Check if explanation is conceptual and different from approach
            is_different = approach.lower() not in explanation.lower() and explanation.lower() not in approach.lower()
            logger.info(f"   Different from approach: {'✅ Yes' if is_different else '❌ No - too similar'}")
            
            # Overall assessment
            improvements = []
            issues = []
            
            if is_specific_approach:
                improvements.append("Approach is problem-specific")
            else:
                issues.append("Approach is still generic")
                
            if has_teaching_language:
                improvements.append("Solution uses teaching language")
            else:
                issues.append("Solution doesn't feel like teaching")
                
            if is_different and len(explanation) > 30:
                improvements.append("Explanation is distinct and conceptual")
            else:
                issues.append("Explanation not distinct or missing")
            
            # Show Anthropic assessment
            if 'anthropic_validation' in result:
                anthropic_val = result['anthropic_validation']
                logger.info(f"\n🔍 ANTHROPIC STRICT VALIDATION:")
                logger.info(f"   Sections Distinct: {anthropic_val.get('sections_are_distinct', 'N/A')}")
                logger.info(f"   Content Specific: {anthropic_val.get('content_is_specific', 'N/A')}")
                logger.info(f"   Teaching Style: {anthropic_val.get('teaching_style', 'N/A')}")
                logger.info(f"   Recommendation: {anthropic_val.get('recommendation', 'N/A')}")
                logger.info(f"   Overall Score: {anthropic_val.get('overall_score', 'N/A')}/10")
                
                if anthropic_val.get('specific_feedback'):
                    logger.info(f"   Feedback: {anthropic_val.get('specific_feedback')}")
            
            logger.info(f"\n📊 IMPROVEMENT ASSESSMENT:")
            if improvements:
                logger.info("   ✅ Improvements:")
                for improvement in improvements:
                    logger.info(f"      • {improvement}")
            
            if issues:
                logger.info("   ❌ Remaining Issues:")
                for issue in issues:
                    logger.info(f"      • {issue}")
            
            if len(improvements) >= 2 and len(issues) <= 1:
                logger.info(f"\n🎉 SYSTEM IMPROVEMENT: SUCCESS")
                return True
            else:
                logger.info(f"\n⚠️ SYSTEM IMPROVEMENT: PARTIAL - needs more work")
                return False
        else:
            logger.error(f"❌ System test failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test execution"""
    logger.info("🧪 Testing the improved Maker-Checker system...")
    
    success = await test_improved_maker_checker()
    
    if success:
        logger.info("\n🎉 IMPROVED SYSTEM WORKING WELL!")
    else:
        logger.error("\n❌ SYSTEM STILL NEEDS MORE IMPROVEMENT!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)