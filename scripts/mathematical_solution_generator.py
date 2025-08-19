#!/usr/bin/env python3
"""
Mathematical Solution Generator with Proper Formatting
Creates textbook-quality solutions with proper mathematical notation
"""

import sys
import os
sys.path.append('/app/backend')

import asyncio
import logging
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv('/app/backend/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MathematicalSolutionGenerator:
    """Generate solutions with proper mathematical formatting and spacing"""
    
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        logger.info("🔑 API Keys Status:")
        logger.info(f"   Google Gemini: {'✅ Available' if self.google_api_key else '❌ Missing'}")
        logger.info(f"   OpenAI: {'✅ Available' if self.openai_api_key else '❌ Missing'}")
        logger.info(f"   Anthropic: {'✅ Available' if self.anthropic_api_key else '❌ Missing'}")

    async def generate_textbook_quality_solutions(self, stem: str, answer: str, category: str = "Quantitative Aptitude", subcategory: str = "General") -> tuple:
        """Generate textbook-quality solutions with proper mathematical formatting"""
        
        # Try Google Gemini first (primary)
        try:
            if self.google_api_key:
                logger.info("  🎯 Generating textbook-quality solutions with Google Gemini...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="textbook_solution_generation",
                    system_message="""You are an expert CAT mathematics tutor who creates TEXTBOOK-QUALITY solutions with perfect mathematical formatting.

CRITICAL FORMATTING REQUIREMENTS:

1. **MATHEMATICAL NOTATION**: Use LaTeX/MathJax notation for all mathematical expressions:
   - Fractions: Use $\\frac{numerator}{denominator}$ instead of "numerator/denominator"
   - Exponents: Use $x^2$ instead of "x^2" 
   - Square roots: Use $\\sqrt{x}$ instead of "sqrt(x)"
   - Multiplication: Use $\\times$ instead of "*" or "x"
   - Division: Use $\\div$ instead of "/"
   - Examples: $\\frac{32}{8} = 4$, $2^3 = 8$, $\\sqrt{16} = 4$

2. **SOLUTION STRUCTURE**: Create well-spaced, professional solutions:
   - **Solution Approach**: 2-3 clear sentences explaining the strategy
   - **Detailed Solution**: Step-by-step with proper spacing and mathematical formatting

3. **FORMATTING EXCELLENCE**:
   - Use line breaks for readability
   - Number each step clearly
   - Use proper mathematical symbols throughout
   - Make it look like a textbook explanation

4. **NO PLAIN TEXT MATH**: Convert ALL mathematical expressions to proper notation:
   - Instead of "GCD of 32, 216, 136..." → "GCD of $32, 216, 136...$"
   - Instead of "32 = 2^5" → "$32 = 2^5$"
   - Instead of "32/8 = 4" → "$\\frac{32}{8} = 4$"

STRUCTURE:
**Solution Approach:**
[Clear, concise strategy in 2-3 sentences]

**Detailed Solution:**
**Step 1:** [Clear explanation with proper mathematical notation]

**Step 2:** [Continued explanation with LaTeX formatting]

**Step 3:** [Mathematical calculations with proper symbols]

**Conclusion:** [Final answer with verification]"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}

Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Generate a textbook-quality solution with perfect mathematical formatting using LaTeX/MathJax notation for all mathematical expressions.""")
                
                response = await chat.send_message(user_message)
                response_text = response.strip()
                
                # Parse the response
                if "**Detailed Solution:**" in response_text:
                    parts = response_text.split("**Detailed Solution:**", 1)
                    
                    # Extract approach
                    approach_part = parts[0].replace("**Solution Approach:**", "").strip()
                    approach = self.clean_and_format_text(approach_part)
                    
                    # Extract detailed solution
                    detailed = self.clean_and_format_text(parts[1].strip())
                    
                    # Ensure mathematical formatting is preserved
                    approach = self.enhance_mathematical_formatting(approach)
                    detailed = self.enhance_mathematical_formatting(detailed)
                    
                else:
                    # Fallback parsing
                    approach = f"To solve this {subcategory} problem, identify the given information, apply the appropriate mathematical formula, and calculate step by step."
                    detailed = self.enhance_mathematical_formatting(response_text)
                
                logger.info(f"  ✅ Google Gemini generated textbook-quality solutions")
                return approach[:400], detailed[:3000]
                
        except Exception as gemini_error:
            logger.warning(f"  ❌ Google Gemini failed: {gemini_error}")
        
        # Fallback to OpenAI
        try:
            if self.openai_api_key:
                logger.info("  🔄 Trying OpenAI fallback for mathematical solutions...")
                import openai
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """You are an expert CAT mathematics tutor creating textbook-quality solutions.

CRITICAL: Use LaTeX/MathJax notation for ALL mathematical expressions:
- Fractions: $\\frac{a}{b}$ not "a/b"
- Exponents: $x^2$ not "x^2" 
- Square roots: $\\sqrt{x}$ not "sqrt(x)"
- Multiplication: $\\times$ not "*"

Create well-formatted solutions with proper spacing and mathematical notation."""},
                        {"role": "user", "content": f"""
Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Create a textbook-quality solution with:
1. **Solution Approach:** [Brief strategy]
2. **Detailed Solution:** [Step-by-step with LaTeX math formatting]
"""}
                    ],
                    max_tokens=2000
                )
                
                response_text = response.choices[0].message.content.strip()
                response_text = self.enhance_mathematical_formatting(response_text)
                
                # Parse the response
                if "**Detailed Solution:**" in response_text:
                    parts = response_text.split("**Detailed Solution:**")
                    if "**Solution Approach:**" in parts[0]:
                        approach = parts[0].replace("**Solution Approach:**", "").strip()
                        detailed = parts[1].strip()
                    else:
                        approach = f"Apply {subcategory} concepts systematically with proper mathematical notation"
                        detailed = response_text
                else:
                    approach = f"Solve this {subcategory} problem using standard mathematical methods"
                    detailed = response_text
                
                logger.info(f"  ✅ OpenAI generated mathematical solutions")
                return approach[:400], detailed[:3000]
                
        except Exception as openai_error:
            logger.warning(f"  ❌ OpenAI failed: {openai_error}")
        
        # Final fallback to Anthropic
        try:
            if self.anthropic_api_key:
                logger.info("  🔄 Trying Anthropic fallback for mathematical solutions...")
                import anthropic
                
                client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=2000,
                    messages=[
                        {"role": "user", "content": f"""Create a textbook-quality mathematical solution with LaTeX formatting.

Question: {stem}
Answer: {answer}
Category: {category}

Use LaTeX notation: $\\frac{{a}}{{b}}$ for fractions, $x^2$ for exponents, $\\sqrt{{x}}$ for square roots.

Format:
**Solution Approach:** [Brief strategy]
**Detailed Solution:** [Step-by-step with mathematical notation]
"""}
                    ]
                )
                
                response_text = response.content[0].text.strip()
                response_text = self.enhance_mathematical_formatting(response_text)
                
                # Parse similar to OpenAI
                if "**Detailed Solution:**" in response_text:
                    parts = response_text.split("**Detailed Solution:**")
                    if "**Solution Approach:**" in parts[0]:
                        approach = parts[0].replace("**Solution Approach:**", "").strip()
                        detailed = parts[1].strip()
                    else:
                        approach = f"Apply {subcategory} methods with proper mathematical formatting"
                        detailed = response_text
                else:
                    approach = f"Solve using standard {subcategory} techniques"
                    detailed = response_text
                
                logger.info(f"  ✅ Anthropic generated mathematical solutions")
                return approach[:400], detailed[:3000]
                
        except Exception as anthropic_error:
            logger.error(f"  ❌ Anthropic also failed: {anthropic_error}")
        
        # Ultimate fallback with mathematical formatting
        logger.error("  ❌ All LLMs failed - using formatted fallback")
        approach = f"Solve this {subcategory} problem step by step using appropriate mathematical formulas and proper notation."
        detailed = f"""**Step 1:** Identify the given information and what needs to be found.

**Step 2:** Determine the appropriate mathematical formula for this {subcategory} problem.

**Step 3:** Substitute the known values into the formula and calculate systematically.

**Step 4:** Verify that the answer $= {answer}$ is correct and makes sense in context.

**Conclusion:** The final answer is ${answer}$."""
        
        return approach, detailed

    def clean_and_format_text(self, text: str) -> str:
        """Clean and format text for better readability"""
        if not text:
            return text
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        
        # Remove leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned

    def enhance_mathematical_formatting(self, text: str) -> str:
        """Enhance mathematical formatting by converting plain text to LaTeX"""
        if not text:
            return text
        
        # Convert common mathematical expressions to LaTeX
        # Fractions
        text = re.sub(r'(\d+)/(\d+)', r'$\\frac{\1}{\2}$', text)
        
        # Exponents (more careful pattern)
        text = re.sub(r'(\w+)\^(\d+)', r'$\1^{\2}$', text)
        text = re.sub(r'(\d+)\^(\d+)', r'$\1^{\2}$', text)
        
        # Square roots
        text = re.sub(r'sqrt\(([^)]+)\)', r'$\\sqrt{\1}$', text)
        
        # Mathematical operations
        text = text.replace(' × ', r' $\times$ ')
        text = text.replace(' * ', r' $\times$ ')
        text = text.replace(' ÷ ', r' $\div$ ')
        
        # Equal signs in mathematical context
        text = re.sub(r'(\$[^$]*\$)\s*=\s*(\$[^$]*\$)', r'\1 = \2', text)
        
        return text


# Test function
async def test_mathematical_solutions():
    """Test the mathematical solution generation"""
    generator = MathematicalSolutionGenerator()
    
    test_questions = [
        {
            "stem": "Find the HCF of 32, 216, 136, 88, 184, and 120.",
            "answer": "8",
            "category": "Number System",
            "subcategory": "HCF-LCM"
        },
        {
            "stem": "A train travels 240 meters in 20 seconds. What is its speed in km/hr?",
            "answer": "43.2 km/hr",
            "category": "Arithmetic", 
            "subcategory": "Time-Speed-Distance"
        }
    ]
    
    for i, q in enumerate(test_questions):
        logger.info(f"\n🧪 Testing Question {i+1}: {q['stem'][:50]}...")
        
        approach, detailed = await generator.generate_textbook_quality_solutions(
            q['stem'], q['answer'], q['category'], q['subcategory']
        )
        
        logger.info(f"\n✅ **Solution Approach:**")
        logger.info(approach)
        logger.info(f"\n✅ **Detailed Solution:**")
        logger.info(detailed[:500] + "..." if len(detailed) > 500 else detailed)

if __name__ == "__main__":
    asyncio.run(test_mathematical_solutions())