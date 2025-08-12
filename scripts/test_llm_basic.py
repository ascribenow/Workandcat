#!/usr/bin/env python3
"""
Simple LLM API Test
Tests basic LLM connectivity and API functionality
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

async def test_llm_basic():
    """Test basic LLM API connectivity"""
    
    try:
        from emergentintegrations import LlmChat, UserMessage
        
        llm_api_key = os.getenv("EMERGENT_LLM_KEY")
        if not llm_api_key:
            logger.error("❌ EMERGENT_LLM_KEY not found")
            return
        
        logger.info("🔑 Found LLM API key")
        
        # Test basic chat functionality
        logger.info("🧪 Testing basic LLM chat...")
        
        chat = LlmChat(
            api_key=llm_api_key,
            session_id="test_session"
        ).with_model("claude", "claude-3-5-sonnet-20241022")
        
        user_message = UserMessage(text="What is 200 divided by 4?")
        response = await chat.send_message(user_message)
        
        logger.info(f"✅ LLM Response: {response}")
        
        # Test a math question
        logger.info("🔢 Testing math problem solving...")
        
        math_message = UserMessage(text="A car travels 200 km in 4 hours. What is its average speed in km/h? Answer with just the number.")
        math_response = await chat.send_message(math_message)
        
        logger.info(f"✅ Math Response: {math_response}")
        
        if "50" in str(math_response):
            logger.info("✅ LLM correctly solved the math problem!")
        else:
            logger.warning(f"⚠️ LLM response might be unexpected: {math_response}")
        
        logger.info("🎉 Basic LLM test completed successfully!")
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("   Missing emergentintegrations library?")
    except Exception as e:
        logger.error(f"❌ LLM test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm_basic())