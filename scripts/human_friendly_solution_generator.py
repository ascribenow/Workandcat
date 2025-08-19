#!/usr/bin/env python3
"""
Human-Friendly Solution Generator
Creates solutions with plain mathematical notation optimized for human readability
Based on the Master Directive: Human-Friendly Solution Presentation
"""

import sys
import os
sys.path.append('/app/backend')

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HumanFriendlySolutionGenerator:
    """Generate human-friendly solutions with plain mathematical notation"""
    
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        logger.info("🔑 API Keys Status:")
        logger.info(f"   Google Gemini: {'✅ Available' if self.google_api_key else '❌ Missing'}")

    async def generate_human_friendly_solutions(self, stem: str, answer: str, category: str = "Quantitative Aptitude", subcategory: str = "General") -> tuple:
        """Generate human-friendly solutions with plain mathematical notation"""
        
        # Try Google Gemini with human-friendly formatting directive
        try:
            if self.google_api_key:
                logger.info("  🎯 Generating human-friendly solutions with Google Gemini...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="human_friendly_solution",
                    system_message="""You are an expert CAT mathematics tutor who creates HUMAN-FRIENDLY solutions optimized for readability.

📘 MASTER DIRECTIVE: Human-Friendly Solution Presentation

CRITICAL FORMATTING RULES:

1. **Equations & Algebraic Steps**
   - ❌ NEVER use LaTeX: \\times, \\frac, \\sqrt, ^, \\begin{align}
   - ✅ Use plain math notation: x² + 3x + 2 = 0, sqrt(16) = 4, 45 ÷ 9 = 5
   - Show steps as numbered steps with word explanations
   - Example: "Step 1: 6 + a + 2 = 15 → Solving gives a = 7"

2. **Grids, Matrices, Tables**
   - ❌ NEVER use \\begin{matrix} or LaTeX arrays
   - ✅ Use simple ASCII-style layout:
     6  a  2
     b  c  d  
     e  f  g
   - Or use markdown tables when appropriate

3. **Fractions, Roots, Exponents**
   - ❌ NEVER use \\frac{45}{3}, \\sqrt{16}
   - ✅ Use simple formats: 45/3, √16 = 4, x², 2³

4. **Structure Requirements**
   - **Solution Approach**: 2-3 clear sentences explaining strategy
   - **Detailed Solution**: Step-by-step with:
     1. Setup/Problem restatement
     2. Step-by-step reasoning (equations + words)
     3. Updated state after each step
     4. Final verification
     5. Highlighted final answer

5. **Final Answer Formatting**
   - Always highlight with ✅ or bold formatting
   - Example: ✅ Therefore, the answer is **12**

✅ GOLDEN RULE: Explain like a teacher on a whiteboard. Use equations + words + simple layouts. NEVER code, NEVER raw syntax, NEVER LaTeX."""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}

Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Generate a human-friendly solution following the Master Directive. Use PLAIN mathematical notation (no LaTeX), clear step-by-step explanations, and highlight the final answer.""")
                
                response = await chat.send_message(user_message)
                response_text = response.strip()
                
                # Parse the response
                if "**Detailed Solution:**" in response_text:
                    parts = response_text.split("**Detailed Solution:**", 1)
                    
                    # Extract approach
                    approach_part = parts[0].replace("**Solution Approach:**", "").strip()
                    approach = self.clean_human_friendly_text(approach_part)
                    
                    # Extract detailed solution
                    detailed = self.clean_human_friendly_text(parts[1].strip())
                    
                else:
                    # Fallback parsing
                    approach = f"Solve this {subcategory} problem step by step using clear mathematical reasoning."
                    detailed = self.clean_human_friendly_text(response_text)
                
                logger.info(f"  ✅ Google Gemini generated human-friendly solutions")
                return approach[:400], detailed[:3000]
                
        except Exception as gemini_error:
            logger.warning(f"  ❌ Google Gemini failed: {gemini_error}")
        
        # Fallback to OpenAI with human-friendly directive
        try:
            if self.openai_api_key:
                logger.info("  🔄 Trying OpenAI fallback for human-friendly solutions...")
                import openai
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": """You are an expert CAT mathematics tutor creating human-friendly solutions.

CRITICAL: Use PLAIN mathematical notation optimized for human readability:
- Use x², 2³, √16 (NOT LaTeX like x^2, \\sqrt{16})
- Use 45/3, not \\frac{45}{3}
- Use simple ASCII layouts for grids/matrices
- Show step-by-step with clear explanations
- Highlight final answer with ✅

Structure: **Solution Approach** (brief), **Detailed Solution** (step-by-step)"""},
                        {"role": "user", "content": f"""
Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Create a human-friendly solution with PLAIN mathematical notation (no LaTeX)."""}
                    ],
                    max_tokens=2000
                )
                
                response_text = response.choices[0].message.content.strip()
                response_text = self.clean_human_friendly_text(response_text)
                
                # Parse the response
                if "**Detailed Solution:**" in response_text:
                    parts = response_text.split("**Detailed Solution:**")
                    if "**Solution Approach:**" in parts[0]:
                        approach = parts[0].replace("**Solution Approach:**", "").strip()
                        detailed = parts[1].strip()
                    else:
                        approach = f"Apply {subcategory} concepts systematically"
                        detailed = response_text
                else:
                    approach = f"Solve this {subcategory} problem step by step"
                    detailed = response_text
                
                logger.info(f"  ✅ OpenAI generated human-friendly solutions")
                return approach[:400], detailed[:3000]
                
        except Exception as openai_error:
            logger.warning(f"  ❌ OpenAI failed: {openai_error}")
        
        # Ultimate fallback with human-friendly format
        logger.error("  ❌ All LLMs failed - using human-friendly fallback")
        approach = f"Solve this {subcategory} problem step by step using clear mathematical reasoning."
        detailed = f"""**Step 1:** Identify what is given in the problem and what needs to be found.

**Step 2:** Determine the appropriate mathematical approach for this {subcategory} problem.

**Step 3:** Set up the equations and perform calculations systematically.

**Step 4:** Verify the solution makes sense in the context of the problem.

✅ **Final Answer:** {answer}"""
        
        return approach, detailed

    def clean_human_friendly_text(self, text: str) -> str:
        """Clean text and convert to human-friendly mathematical notation"""
        if not text:
            return text
        
        # Convert LaTeX to plain mathematical notation
        import re
        
        # Convert fractions: \frac{a}{b} → a/b
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', text)
        
        # Convert square roots: \sqrt{x} → √x
        text = re.sub(r'\\sqrt\{([^}]+)\}', r'√\1', text)
        
        # Convert exponents: x^{2} → x², x^2 → x²
        text = re.sub(r'([a-zA-Z0-9]+)\^\{([0-9]+)\}', lambda m: f'{m.group(1)}{self.superscript_number(m.group(2))}', text)
        text = re.sub(r'([a-zA-Z0-9]+)\^([0-9]+)', lambda m: f'{m.group(1)}{self.superscript_number(m.group(2))}', text)
        
        # Remove LaTeX math delimiters
        text = text.replace('$', '')
        text = text.replace('\\(', '').replace('\\)', '')
        text = text.replace('\\[', '').replace('\\]', '')
        
        # Convert LaTeX symbols to Unicode
        text = text.replace('\\times', '×')
        text = text.replace('\\div', '÷')
        text = text.replace('\\le', '≤')
        text = text.replace('\\ge', '≥')
        text = text.replace('\\ne', '≠')
        text = text.replace('\\approx', '≈')
        text = text.replace('\\pm', '±')
        
        # Remove LaTeX commands
        text = re.sub(r'\\begin\{[^}]+\}', '', text)
        text = re.sub(r'\\end\{[^}]+\}', '', text)
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        # Clean up excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text

    def superscript_number(self, num_str: str) -> str:
        """Convert number to superscript Unicode"""
        superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }
        return ''.join(superscript_map.get(d, d) for d in num_str)


# Test function
async def test_human_friendly_solutions():
    """Test the human-friendly solution generation"""
    generator = HumanFriendlySolutionGenerator()
    
    test_questions = [
        {
            "stem": "The numbers 1, 2, ..., 9 are arranged in a 3×3 square grid. If the top left is 6 and top right is 2, and each row, column, and diagonal sum is the same, find the value at the bottom middle position.",
            "answer": "3",
            "category": "Number System",
            "subcategory": "Magic Squares"
        }
    ]
    
    for i, q in enumerate(test_questions):
        logger.info(f"\n🧪 Testing Question {i+1}: {q['stem'][:60]}...")
        
        approach, detailed = await generator.generate_human_friendly_solutions(
            q['stem'], q['answer'], q['category'], q['subcategory']
        )
        
        logger.info(f"\n✅ **Solution Approach:**")
        logger.info(approach)
        logger.info(f"\n✅ **Detailed Solution:**")
        logger.info(detailed[:800] + "..." if len(detailed) > 800 else detailed)

if __name__ == "__main__":
    asyncio.run(test_human_friendly_solutions())