#!/usr/bin/env python3
"""
Test SimplifiedEnrichmentService directly
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simplified_enrichment():
    """
    Test SimplifiedEnrichmentService directly
    """
    try:
        from llm_enrichment import SimplifiedEnrichmentService
        
        logger.info("🧪 Testing SimplifiedEnrichmentService")
        
        # Check API key
        api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"API Key loaded: {api_key[:20]}..." if api_key else "No API key found")
        
        # Initialize service
        service = SimplifiedEnrichmentService()
        logger.info(f"Service API Key: {service.openai_api_key[:20]}..." if service.openai_api_key else "No API key in service")
        
        # Test enrichment
        result = await service.enrich_with_five_fields_only("What is 2+2?", "4")
        
        logger.info("📊 Enrichment Result:")
        logger.info(f"   Success: {result.get('success')}")
        logger.info(f"   Error: {result.get('error', 'None')}")
        
        if result.get('enrichment_data'):
            data = result['enrichment_data']
            logger.info(f"   Right Answer: {data.get('right_answer')}")
            logger.info(f"   Category: {data.get('category')}")
            logger.info(f"   Subcategory: {data.get('subcategory')}")
            logger.info(f"   Type: {data.get('type_of_question')}")
            logger.info(f"   Difficulty: {data.get('difficulty_level')}")
        
        return result.get('success', False)
        
    except Exception as e:
        logger.error(f"❌ Error testing SimplifiedEnrichmentService: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simplified_enrichment())
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")