#!/usr/bin/env python3
"""
Test Gemini (Maker) → OpenAI (Checker) fallback methodology
"""

import sys
import os
sys.path.append('/app/backend')

import logging
import asyncio
import psycopg2
from dotenv import load_dotenv
from standardized_enrichment_engine import standardized_enricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_fallback_methodology():
    """Test the fallback methodology with OpenAI as checker"""
    try:
        logger.info("🧪 TESTING GEMINI (MAKER) → OPENAI (CHECKER) FALLBACK")
        logger.info("=" * 70)
        
        # Test sample question
        test_question = "Find the smallest number that leaves a remainder of 4 on division by 5, 5 on division by 6, 6 on division by 7, 7 on division by 8 and 8 on division by 9?"
        test_answer = "2519"
        
        logger.info(f"Test Question: {test_question[:60]}...")
        logger.info(f"Test Answer: {test_answer}")
        
        # Run enrichment with fallback
        result = await standardized_enricher.enrich_question_solution(
            question_stem=test_question,
            answer=test_answer,
            subcategory="Number Theory",
            question_type="Remainder Problems"
        )
        
        if result["success"]:
            logger.info(f"✅ Fallback methodology successful!")
            logger.info(f"🎯 Workflow: {result.get('workflow', 'Unknown')}")
            logger.info(f"📊 Quality Score: {result.get('quality_score', 'N/A')}")
            logger.info(f"🔧 LLM Used: {result.get('llm_used', 'Unknown')}")
            
            # Show generated content
            logger.info(f"\n📋 GENERATED CONTENT:")
            logger.info("=" * 50)
            
            approach = result.get('approach', '')
            detailed = result.get('detailed_solution', '')
            
            logger.info(f"APPROACH:\n{approach[:200]}...")
            logger.info(f"\nDETAILED SOLUTION:\n{detailed[:300]}...")
            
            # Show quality assessment
            if 'anthropic_validation' in result:
                assessment = result['anthropic_validation']
                logger.info(f"\n🔍 QUALITY ASSESSMENT:")
                logger.info(f"   Recommendation: {assessment.get('recommendation', 'N/A')}")
                logger.info(f"   Overall Score: {assessment.get('overall_score', 'N/A')}/10")
                logger.info(f"   Checker Used: {assessment.get('checker_used', 'Unknown')}")
            
            return True
        else:
            logger.error(f"❌ Fallback methodology failed: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

async def main():
    """Main test execution"""
    logger.info("🔧 Testing LLM connections with fallback methodology...")
    
    success = await test_fallback_methodology()
    
    if success:
        logger.info("\n🎉 FALLBACK METHODOLOGY WORKING!")
        logger.info("🔧 OpenAI is successfully acting as quality checker")
        logger.info("📊 System is functional while Anthropic issue is resolved")
    else:
        logger.error("\n❌ FALLBACK METHODOLOGY FAILED!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)