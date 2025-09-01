#!/usr/bin/env python3
"""
Test SimplifiedEnrichmentService in Server Context
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment like server does
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_service_in_server_context():
    """
    Test SimplifiedEnrichmentService exactly like server calls it
    """
    try:
        logger.info("🧪 Testing SimplifiedEnrichmentService in server context")
        
        # Initialize exactly like server does
        from llm_enrichment import SimplifiedEnrichmentService
        simplified_enricher = SimplifiedEnrichmentService()
        
        logger.info(f"API Key available: {bool(simplified_enricher.openai_api_key)}")
        if simplified_enricher.openai_api_key:
            logger.info(f"API Key prefix: {simplified_enricher.openai_api_key[:20]}...")
        
        # Call exactly like server does
        logger.info("🎯 Calling enrich_with_five_fields_only like server upload...")
        
        enrichment_result = await simplified_enricher.enrich_with_five_fields_only(
            stem="What is 2+2?",
            admin_answer="4"
        )
        
        logger.info("📊 Enrichment Result:")
        logger.info(f"   Success: {enrichment_result.get('success')}")
        logger.info(f"   Error: {enrichment_result.get('error', 'None')}")
        
        if enrichment_result.get('success'):
            data = enrichment_result.get('enrichment_data', {})
            logger.info("📋 Generated Fields:")
            logger.info(f"   Right Answer: {data.get('right_answer')}")
            logger.info(f"   Category: {data.get('category')}")
            logger.info(f"   Subcategory: {data.get('subcategory')}")
            logger.info(f"   Type: {data.get('type_of_question')}")
            logger.info(f"   Difficulty: {data.get('difficulty_level')}")
            
            # Check if it's real LLM data or fallback
            if data.get('category') != 'General' and data.get('right_answer') != 'Not available':
                logger.info("✅ Real LLM data generated!")
                return True
            else:
                logger.warning("⚠️ Fallback data returned - LLM call may have failed")
                return False
        else:
            logger.error(f"❌ Enrichment failed: {enrichment_result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_service_in_server_context())
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
    if success:
        print("✅ SimplifiedEnrichmentService working correctly!")
    else:
        print("❌ SimplifiedEnrichmentService not generating real LLM content")