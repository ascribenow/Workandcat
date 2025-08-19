#!/usr/bin/env python3
"""
Test both fixes: 
1. Remove $ signs from solutions
2. Ensure Approach and Explanation are distinct
"""

import sys
import os
sys.path.append('/app/backend')

import logging
import asyncio
from standardized_enrichment_engine import standardized_enricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_both_fixes():
    """Test both the $ sign removal and Approach vs Explanation distinction"""
    try:
        logger.info("🧪 TESTING BOTH FIXES")
        logger.info("=" * 60)
        logger.info("Fix 1: Remove irrelevant $ signs from solutions")
        logger.info("Fix 2: Ensure Approach and Explanation are distinct")
        
        # Test with a sample question
        test_question = "Find the smallest number that leaves a remainder of 4 on division by 5, 5 on division by 6, 6 on division by 7, 7 on division by 8 and 8 on division by 9?"
        test_answer = "2519"
        
        logger.info(f"\n📝 Test Question: {test_question[:60]}...")
        logger.info(f"✅ Answer: {test_answer}")
        
        # Generate enrichment with both fixes
        result = await standardized_enricher.enrich_question_solution(
            question_stem=test_question,
            answer=test_answer,
            subcategory="Number Theory",
            question_type="Remainder Problems"
        )
        
        if result["success"]:
            logger.info(f"\n✅ Enrichment successful!")
            logger.info(f"🎯 Workflow: {result.get('workflow', 'Unknown')}")
            logger.info(f"📊 Quality Score: {result.get('quality_score', 'N/A')}")
            
            approach = result.get('approach', '')
            detailed_solution = result.get('detailed_solution', '')
            
            # Extract explanation from detailed solution
            explanation = ""
            if "KEY INSIGHT:" in detailed_solution:
                explanation = detailed_solution.split("KEY INSIGHT:")[-1].strip()
            elif "EXPLANATION:" in detailed_solution:
                explanation = detailed_solution.split("EXPLANATION:")[-1].strip()
            
            logger.info(f"\n📋 GENERATED CONTENT ANALYSIS:")
            logger.info("=" * 50)
            
            # Test Fix 1: Check for $ signs
            logger.info(f"\n🔍 FIX 1 VERIFICATION: $ SIGN REMOVAL")
            has_dollar_signs_approach = '$' in approach
            has_dollar_signs_detailed = '$' in detailed_solution
            has_dollar_signs_explanation = '$' in explanation
            
            logger.info(f"   Approach has $ signs: {has_dollar_signs_approach}")
            logger.info(f"   Detailed solution has $ signs: {has_dollar_signs_detailed}")
            logger.info(f"   Explanation has $ signs: {has_dollar_signs_explanation}")
            
            if not (has_dollar_signs_approach or has_dollar_signs_detailed or has_dollar_signs_explanation):
                logger.info("   ✅ FIX 1 SUCCESS: No $ signs found in content")
            else:
                logger.info("   ❌ FIX 1 FAILED: $ signs still present")
            
            # Test Fix 2: Check Approach vs Explanation distinction
            logger.info(f"\n🔍 FIX 2 VERIFICATION: APPROACH vs EXPLANATION DISTINCTION")
            logger.info(f"APPROACH ({len(approach)} chars):")
            logger.info(f"   {approach[:200]}...")
            
            logger.info(f"\nEXPLANATION ({len(explanation)} chars):")
            logger.info(f"   {explanation[:200]}...")
            
            # Check if they are different
            are_similar = approach.lower() in explanation.lower() or explanation.lower() in approach.lower()
            approach_words = set(approach.lower().split())
            explanation_words = set(explanation.lower().split())
            overlap_ratio = len(approach_words.intersection(explanation_words)) / max(len(approach_words), len(explanation_words), 1)
            
            logger.info(f"\nDistinction Analysis:")
            logger.info(f"   Are similar/overlapping: {are_similar}")
            logger.info(f"   Word overlap ratio: {overlap_ratio:.2f}")
            logger.info(f"   Length difference: {abs(len(approach) - len(explanation))} chars")
            
            if not are_similar and overlap_ratio < 0.7 and abs(len(approach) - len(explanation)) > 20:
                logger.info("   ✅ FIX 2 SUCCESS: Approach and Explanation are distinct")
            else:
                logger.info("   ❌ FIX 2 FAILED: Approach and Explanation are too similar")
            
            # Show Anthropic validation if available
            if 'anthropic_validation' in result:
                anthropic_val = result['anthropic_validation']
                logger.info(f"\n🔍 ANTHROPIC VALIDATION:")
                logger.info(f"   Approach Quality: {anthropic_val.get('approach_quality', 'N/A')}")
                logger.info(f"   Explanation Quality: {anthropic_val.get('explanation_quality', 'N/A')}")
                logger.info(f"   Approach-Explanation Distinct: {anthropic_val.get('approach_explanation_distinct', 'N/A')}")
                logger.info(f"   Overall Score: {anthropic_val.get('overall_score', 'N/A')}/10")
                logger.info(f"   Recommendation: {anthropic_val.get('recommendation', 'N/A')}")
            
            return True
        else:
            logger.error(f"❌ Enrichment failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test execution"""
    logger.info("🧪 Testing fixes for $ signs and Approach vs Explanation distinction...")
    
    success = await test_both_fixes()
    
    if success:
        logger.info("\n🎉 FIXES TESTING COMPLETED!")
    else:
        logger.error("\n❌ FIXES TESTING FAILED!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)