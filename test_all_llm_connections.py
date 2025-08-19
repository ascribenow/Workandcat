#!/usr/bin/env python3
"""
Test all LLM connections to identify any issues
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_google_gemini():
    """Test Google Gemini connection"""
    try:
        load_dotenv('/app/backend/.env')
        google_api_key = os.getenv('GOOGLE_API_KEY')
        
        logger.info(f"🔍 Testing Google Gemini...")
        logger.info(f"   API Key: {google_api_key[:20]}..." if google_api_key else "   API Key: NOT FOUND")
        
        if not google_api_key:
            return {"success": False, "error": "No Google API key found"}
        
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=google_api_key,
            session_id="connection_test",
            system_message="You are a test assistant. Respond with exactly: 'Gemini connection working'"
        ).with_model("gemini", "gemini-2.0-flash")
        
        user_message = UserMessage(text="Test connection")
        response = await chat.send_message(user_message)
        
        logger.info(f"   ✅ Google Gemini Response: {response[:100]}")
        return {"success": True, "response": response}
        
    except Exception as e:
        logger.error(f"   ❌ Google Gemini Failed: {e}")
        return {"success": False, "error": str(e)}

async def test_anthropic_claude():
    """Test Anthropic Claude connection"""
    try:
        load_dotenv('/app/backend/.env')
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        logger.info(f"🔍 Testing Anthropic Claude...")
        logger.info(f"   API Key: {anthropic_api_key[:20]}..." if anthropic_api_key else "   API Key: NOT FOUND")
        
        if not anthropic_api_key:
            return {"success": False, "error": "No Anthropic API key found"}
        
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=anthropic_api_key,
            session_id="connection_test",
            system_message="You are a test assistant. Respond with exactly: 'Anthropic connection working'"
        ).with_model("anthropic", "claude-3-5-sonnet-20241022")
        
        user_message = UserMessage(text="Test connection")
        response = await chat.send_message(user_message)
        
        logger.info(f"   ✅ Anthropic Claude Response: {response[:100]}")
        return {"success": True, "response": response}
        
    except Exception as e:
        logger.error(f"   ❌ Anthropic Claude Failed: {e}")
        return {"success": False, "error": str(e)}

async def test_openai_gpt():
    """Test OpenAI GPT connection"""
    try:
        load_dotenv('/app/backend/.env')
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        logger.info(f"🔍 Testing OpenAI GPT...")
        logger.info(f"   API Key: {openai_api_key[:20]}..." if openai_api_key else "   API Key: NOT FOUND")
        
        if not openai_api_key:
            return {"success": False, "error": "No OpenAI API key found"}
        
        import openai
        
        client = openai.OpenAI(api_key=openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a test assistant. Respond with exactly: 'OpenAI connection working'"},
                {"role": "user", "content": "Test connection"}
            ],
            max_tokens=50
        )
        
        response_text = response.choices[0].message.content
        logger.info(f"   ✅ OpenAI GPT Response: {response_text}")
        return {"success": True, "response": response_text}
        
    except Exception as e:
        logger.error(f"   ❌ OpenAI GPT Failed: {e}")
        return {"success": False, "error": str(e)}

async def test_emergent_llm():
    """Test EMERGENT_LLM_KEY connection"""
    try:
        load_dotenv('/app/backend/.env')
        emergent_key = os.getenv('EMERGENT_LLM_KEY')
        
        logger.info(f"🔍 Testing EMERGENT_LLM_KEY...")
        logger.info(f"   API Key: {emergent_key[:20]}..." if emergent_key else "   API Key: NOT FOUND")
        
        if not emergent_key:
            return {"success": False, "error": "No EMERGENT_LLM_KEY found"}
        
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=emergent_key,
            session_id="connection_test",
            system_message="You are a test assistant. Respond with exactly: 'EMERGENT LLM connection working'"
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text="Test connection")
        response = await chat.send_message(user_message)
        
        logger.info(f"   ✅ EMERGENT LLM Response: {response[:100]}")
        return {"success": True, "response": response}
        
    except Exception as e:
        logger.error(f"   ❌ EMERGENT LLM Failed: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """Test all LLM connections"""
    logger.info("🚀 TESTING ALL LLM CONNECTIONS")
    logger.info("=" * 60)
    
    results = {}
    
    # Test Google Gemini
    results["google_gemini"] = await test_google_gemini()
    
    # Test Anthropic Claude
    results["anthropic_claude"] = await test_anthropic_claude()
    
    # Test OpenAI GPT
    results["openai_gpt"] = await test_openai_gpt()
    
    # Test EMERGENT LLM
    results["emergent_llm"] = await test_emergent_llm()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 LLM CONNECTION TEST RESULTS")
    logger.info("=" * 60)
    
    all_working = True
    for llm_name, result in results.items():
        status = "✅ WORKING" if result["success"] else "❌ FAILED"
        logger.info(f"{llm_name.upper()}: {status}")
        if not result["success"]:
            logger.info(f"   Error: {result['error']}")
            all_working = False
    
    if all_working:
        logger.info("\n🎉 ALL LLM CONNECTIONS ARE WORKING!")
    else:
        logger.error("\n❌ SOME LLM CONNECTIONS HAVE ISSUES!")
        
        # Provide specific fixes
        logger.info("\n🔧 RECOMMENDED FIXES:")
        for llm_name, result in results.items():
            if not result["success"]:
                error = result["error"]
                if "authentication" in error.lower() or "invalid" in error.lower():
                    logger.info(f"   {llm_name.upper()}: Check API key validity")
                elif "not found" in error.lower():
                    logger.info(f"   {llm_name.upper()}: Add API key to .env file")
                else:
                    logger.info(f"   {llm_name.upper()}: {error}")
    
    return all_working

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)