#!/usr/bin/env python3
"""
Test OpenAI API Connection
"""

import os
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_openai_connection():
    """
    Test OpenAI API connection
    """
    try:
        # Check if API key exists
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            return False
        
        logger.info(f"✅ OPENAI_API_KEY found: {api_key[:20]}...")
        
        # Test simple OpenAI call
        try:
            import openai
            
            client = openai.AsyncOpenAI(api_key=api_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Say 'Hello' if you can hear me."}
                ],
                max_tokens=10
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ OpenAI API test successful: {result}")
            return True
            
        except Exception as openai_error:
            logger.error(f"❌ OpenAI API test failed: {openai_error}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error testing OpenAI connection: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_openai_connection())
    if result:
        print("✅ OpenAI connection working!")
    else:
        print("❌ OpenAI connection failed!")