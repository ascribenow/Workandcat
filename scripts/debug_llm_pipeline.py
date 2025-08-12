#!/usr/bin/env python3
"""
Debug LLM Enrichment Pipeline
Step-by-step debugging of each component
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import traceback

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from emergentintegrations.llm.chat import LlmChat, UserMessage
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

async def debug_llm_pipeline():
    """Debug each step of the LLM enrichment pipeline"""
    
    try:
        llm_api_key = os.getenv("EMERGENT_LLM_KEY")
        if not llm_api_key:
            logger.error("❌ EMERGENT_LLM_KEY not found")
            return
        
        logger.info("✅ LLM API key found")
        
        # Test stem
        test_stem = "A car travels 200 km in 4 hours. What is its average speed in km/h?"
        
        # Step 1: Test generate_answer method
        logger.info("🔍 Step 1: Testing answer generation...")
        
        try:
            system_message = """You are an expert CAT quantitative aptitude problem solver. 
Given a question, provide ONLY the final numerical answer or short answer.

RULES:
1. Provide ONLY the answer - no explanation, no working
2. For numerical answers, provide just the number
3. For multiple choice, provide just the letter (A, B, C, D)
4. For word answers, keep it very brief (1-3 words max)
5. If it's a speed problem, give answer in specified units (km/h, m/s, etc.)"""

            chat = LlmChat(
                api_key=llm_api_key,
                session_id="debug_answer",
                system_message=system_message
            ).with_model("claude", "claude-3-5-sonnet-20241022")

            user_message = UserMessage(text=f"Question: {test_stem}")
            response = await chat.send_message(user_message)
            
            logger.info(f"✅ Raw LLM response: {response}")
            
            # Clean up the response
            answer = response.strip()
            prefixes_to_remove = [
                "Answer:", "The answer is:", "Final answer:", 
                "Solution:", "Result:", "Therefore,", "Hence,", "So,"
            ]
            
            for prefix in prefixes_to_remove:
                if answer.startswith(prefix):
                    answer = answer[len(prefix):].strip()
            
            answer = answer[:50]
            logger.info(f"✅ Cleaned answer: {answer}")
            
        except Exception as e:
            logger.error(f"❌ Step 1 failed: {e}")
            traceback.print_exc()
            return
        
        # Step 2: Test categorization
        logger.info("🔍 Step 2: Testing categorization...")
        
        try:
            system_message_cat = """You are an expert CAT question classifier. 
Given a quantitative aptitude question, classify it into category and subcategory.

Return a JSON object with:
{
  "category": "Arithmetic",  
  "subcategory": "Speed-Time-Distance",
  "type_of_question": "Average Speed Calculation",
  "confidence": 0.95
}"""

            chat_cat = LlmChat(
                api_key=llm_api_key,
                session_id="debug_category",
                system_message=system_message_cat
            ).with_model("openai", "gpt-4o")

            user_message_cat = UserMessage(text=f"Question: {test_stem}")
            response_cat = await chat_cat.send_message(user_message_cat)
            
            logger.info(f"✅ Categorization response: {response_cat}")
            
            import json
            try:
                cat_result = json.loads(response_cat)
                logger.info(f"✅ Parsed categorization: {cat_result}")
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Could not parse JSON: {response_cat}")
                
        except Exception as e:
            logger.error(f"❌ Step 2 failed: {e}")
            traceback.print_exc()
            return
        
        # Step 3: Test solution generation
        logger.info("🔍 Step 3: Testing solution generation...")
        
        try:
            system_message_sol = """You are an expert CAT math tutor. 
Given a question and its answer, explain the solution approach and provide detailed steps.

Format your response as JSON:
{
  "solution_approach": "brief method description",
  "detailed_solution": "step by step solution",
  "difficulty_justification": "why this difficulty level"
}"""

            chat_sol = LlmChat(
                api_key=llm_api_key,
                session_id="debug_solution",
                system_message=system_message_sol
            ).with_model("claude", "claude-3-5-sonnet-20241022")

            user_message_sol = UserMessage(text=f"Question: {test_stem}\nAnswer: {answer}")
            response_sol = await chat_sol.send_message(user_message_sol)
            
            logger.info(f"✅ Solution response: {response_sol}")
            
            try:
                sol_result = json.loads(response_sol)
                logger.info(f"✅ Parsed solution: {sol_result}")
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Could not parse solution JSON: {response_sol}")
                
        except Exception as e:
            logger.error(f"❌ Step 3 failed: {e}")
            traceback.print_exc()
            return
        
        logger.info("🎉 All LLM pipeline steps completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Debug pipeline failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_llm_pipeline())