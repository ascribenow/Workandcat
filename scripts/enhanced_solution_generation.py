#!/usr/bin/env python3
"""
Enhanced Solution Generation with Google Gemini Primary + OpenAI/Anthropic Fallbacks
Provides high-quality mathematical solutions with proper formatting and theoretical foundations
"""

import sys
import os
sys.path.append('/app/backend')

import asyncio
import logging
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedSolutionGenerator:
    """Generate high-quality solutions using Gemini primary + OpenAI/Anthropic fallbacks"""
    
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        logger.info("🔑 API Keys Status:")
        logger.info(f"   Google Gemini: {'✅ Available' if self.google_api_key else '❌ Missing'}")
        logger.info(f"   OpenAI: {'✅ Available' if self.openai_api_key else '❌ Missing'}")
        logger.info(f"   Anthropic: {'✅ Available' if self.anthropic_api_key else '❌ Missing'}")

    async def generate_answer_with_fallback(self, stem: str, category: str = "General", subcategory: str = "General") -> str:
        """Generate answer with Gemini primary, OpenAI/Anthropic fallbacks"""
        
        # Try Google Gemini first
        try:
            if self.google_api_key:
                logger.info("  🎯 Trying Google Gemini for answer generation...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="answer_generation",
                    system_message="""You are an expert CAT quantitative aptitude solver with exceptional mathematical precision.

TASK: Generate the exact, concise answer for the given question.

RULES:
1. Provide ONLY the final numerical answer or mathematical expression
2. Be precise and accurate with calculations
3. Use standard mathematical notation
4. For numerical answers, include appropriate units if needed
5. No explanations or steps - just the answer"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}
Category: {category}
Subcategory: {subcategory}

Provide the exact answer:""")
                
                response = await chat.send_message(user_message)
                answer = response.strip()
                
                logger.info(f"  ✅ Google Gemini generated answer: {answer}")
                return answer
                
        except Exception as gemini_error:
            logger.warning(f"  ❌ Google Gemini failed: {gemini_error}")
        
        # Fallback to OpenAI
        try:
            if self.openai_api_key:
                logger.info("  🔄 Trying OpenAI fallback for answer generation...")
                import openai
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """You are an expert CAT exam solver. Generate the correct, concise answer for the given question.

Rules:
1. Provide only the final answer (number, expression, or choice)
2. Be precise and accurate
3. Use standard mathematical notation
4. For numerical answers, include units if applicable"""},
                        {"role": "user", "content": f"Question: {stem}"}
                    ],
                    max_tokens=200
                )
                
                answer = response.choices[0].message.content.strip()
                logger.info(f"  ✅ OpenAI generated answer: {answer}")
                return answer
                
        except Exception as openai_error:
            logger.warning(f"  ❌ OpenAI failed: {openai_error}")
        
        # Final fallback to Anthropic
        try:
            if self.anthropic_api_key:
                logger.info("  🔄 Trying Anthropic fallback for answer generation...")
                import anthropic
                
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=200,
                    messages=[
                        {"role": "user", "content": f"""Generate the exact answer for this CAT question:

Question: {stem}
Category: {category}

Provide only the final numerical answer or expression."""}
                    ]
                )
                
                answer = response.content[0].text.strip()
                logger.info(f"  ✅ Anthropic generated answer: {answer}")
                return answer
                
        except Exception as anthropic_error:
            logger.error(f"  ❌ Anthropic also failed: {anthropic_error}")
        
        # Ultimate fallback
        logger.error("  ❌ All LLMs failed for answer generation!")
        return "Answer could not be generated - manual review required"

    async def generate_enhanced_solutions_with_fallback(self, stem: str, answer: str, category: str = "General", subcategory: str = "General") -> tuple:
        """Generate enhanced solutions with Gemini primary, OpenAI/Anthropic fallbacks"""
        
        # Try Google Gemini first
        try:
            if self.google_api_key:
                logger.info("  🎯 Trying Google Gemini for solution generation...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="solution_generation",
                    system_message="""You are an expert CAT quantitative aptitude tutor who creates exceptional, comprehensive explanations for mathematical problems.

TASK: Generate two types of solutions for the given question:

1. SOLUTION APPROACH: A complete 2-3 sentence strategic overview of how to solve this type of problem
2. DETAILED SOLUTION: A comprehensive step-by-step explanation with theoretical foundations

CRITICAL FORMATTING REQUIREMENTS:
- Use PLAIN TEXT only - no LaTeX, no \( \), no \[ \], no special formatting
- Write mathematical expressions in simple text (e.g., "x^2 + 3x - 5" not "\(x^2 + 3x - 5\)")
- Use standard symbols: ÷ for division, × for multiplication, ^ for exponents
- Complete all numbered points - never end abruptly with incomplete thoughts
- Keep solution approach under 300 characters to avoid truncation
- Keep detailed solution under 2000 characters total

QUALITY REQUIREMENTS:
- Clear, logical progression of steps
- Explain WHY each step is necessary
- Include relevant mathematical concepts and formulas
- Assume student needs foundational understanding
- No unwanted parentheses or formatting artifacts
- Clean, professional presentation

STRUCTURE:
SOLUTION APPROACH: [Complete strategic overview in plain text]

DETAILED SOLUTION:
Step 1: [Clear explanation with reasoning]
Step 2: [Mathematical operations with logic]  
Step 3: [Continue calculations]
Conclusion: [Final verification and insight]"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Generate both solution approach and detailed solution:""")
                
                response = await chat.send_message(user_message)
                response_text = response.strip()
                
                # Parse the response to extract approach and detailed solution
                if "DETAILED SOLUTION:" in response_text:
                    parts = response_text.split("DETAILED SOLUTION:", 1)
                    
                    # Extract approach
                    approach_part = parts[0].replace("SOLUTION APPROACH:", "").strip()
                    approach = self.clean_text(approach_part)
                    
                    # Extract detailed solution
                    detailed = self.clean_text(parts[1].strip())
                else:
                    # Fallback parsing if format is different
                    approach = f"Solve this {subcategory} problem systematically using standard mathematical principles"
                    detailed = self.clean_text(response_text)
                
                logger.info(f"  ✅ Google Gemini generated enhanced solutions")
                return approach[:300], detailed[:2000]
                
        except Exception as gemini_error:
            logger.warning(f"  ❌ Google Gemini failed for solutions: {gemini_error}")
        
        # Fallback to OpenAI
        try:
            if self.openai_api_key:
                logger.info("  🔄 Trying OpenAI fallback for solution generation...")
                import openai
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """You are an expert CAT math tutor who creates comprehensive, beginner-friendly explanations.

Guidelines:
1. SOLUTION APPROACH: Provide a concise 2-3 sentence overview of the main strategy
2. DETAILED SOLUTION: Create a step-by-step explanation that assumes the student is seeing this type of problem for the first time
   - Explains WHY each step is necessary
   - Defines any formulas or concepts used
   - Shows all calculations clearly
   - Uses simple, clear language
   - Clean formatting without unwanted parentheses"""},
                        {"role": "user", "content": f"""
Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Please provide:
1. SOLUTION APPROACH: [Brief strategy overview]
2. DETAILED SOLUTION: [Comprehensive step-by-step explanation]
"""}
                    ],
                    max_tokens=1500
                )
                
                response_text = response.choices[0].message.content.strip()
                response_text = self.clean_text(response_text)
                
                # Parse the response
                if "DETAILED SOLUTION:" in response_text:
                    parts = response_text.split("DETAILED SOLUTION:")
                    if "SOLUTION APPROACH:" in parts[0]:
                        approach = parts[0].replace("SOLUTION APPROACH:", "").strip()
                        detailed = parts[1].strip()
                    else:
                        approach = f"Solve this {subcategory} problem step by step"
                        detailed = response_text
                else:
                    approach = f"Solve this {subcategory} problem step by step"
                    detailed = response_text
                
                logger.info(f"  ✅ OpenAI generated enhanced solutions")
                return approach[:300], detailed[:2000]
                
        except Exception as openai_error:
            logger.warning(f"  ❌ OpenAI failed for solutions: {openai_error}")
        
        # Final fallback to Anthropic
        try:
            if self.anthropic_api_key:
                logger.info("  🔄 Trying Anthropic fallback for solution generation...")
                import anthropic
                
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1500,
                    messages=[
                        {"role": "user", "content": f"""You are an expert CAT math tutor. Create comprehensive explanations for this problem.

Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Please provide:
1. SOLUTION APPROACH: [Brief strategy overview]
2. DETAILED SOLUTION: [Comprehensive step-by-step explanation with mathematical reasoning]
"""}
                    ]
                )
                
                response_text = response.content[0].text.strip()
                response_text = self.clean_text(response_text)
                
                # Parse the response
                if "DETAILED SOLUTION:" in response_text:
                    parts = response_text.split("DETAILED SOLUTION:")
                    if "SOLUTION APPROACH:" in parts[0]:
                        approach = parts[0].replace("SOLUTION APPROACH:", "").strip()
                        detailed = parts[1].strip()
                    else:
                        approach = f"Solve this {subcategory} problem step by step"
                        detailed = response_text
                else:
                    approach = f"Solve this {subcategory} problem step by step"
                    detailed = response_text
                
                logger.info(f"  ✅ Anthropic generated enhanced solutions")
                return approach[:300], detailed[:2000]
                
        except Exception as anthropic_error:
            logger.error(f"  ❌ Anthropic also failed for solutions: {anthropic_error}")
        
        # Ultimate fallback
        logger.error("  ❌ All LLMs failed for solutions!")
        approach = f"Apply {subcategory} concepts systematically to solve this problem"
        detailed = f"""This is a {subcategory} problem from {category}. 

Step 1: Identify the given information and what needs to be found.
Step 2: Determine the appropriate mathematical approach or formula.
Step 3: Set up the equation or calculation method.
Step 4: Perform the calculations step by step.
Step 5: Verify the answer makes logical sense in context.

The correct answer is {answer}."""
        
        return approach, detailed

    def clean_text(self, text: str) -> str:
        """Clean text by removing unwanted formatting artifacts"""
        if not text:
            return text
            
        # Remove excessive parentheses and formatting artifacts
        cleaned = text.replace("((", "(").replace("))", ")")
        cleaned = cleaned.replace("**", "").replace("##", "")
        
        # Clean up multiple spaces and newlines
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned


# Test function
async def test_enhanced_solution_generation():
    """Test the enhanced solution generation system"""
    generator = EnhancedSolutionGenerator()
    
    # Test question
    test_stem = "A train travels 120 km in 2 hours. What is its average speed?"
    test_category = "Arithmetic"
    test_subcategory = "Time-Speed-Distance"
    
    logger.info("🧪 Testing Enhanced Solution Generation System...")
    
    # Test answer generation
    answer = await generator.generate_answer_with_fallback(test_stem, test_category, test_subcategory)
    logger.info(f"Generated Answer: {answer}")
    
    # Test solution generation
    approach, detailed = await generator.generate_enhanced_solutions_with_fallback(
        test_stem, answer, test_category, test_subcategory
    )
    
    logger.info("✅ Enhanced Solution Generation Test Complete!")
    logger.info(f"Solution Approach: {approach}")
    logger.info(f"Detailed Solution: {detailed[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_enhanced_solution_generation())