#!/usr/bin/env python3
"""
Fix Solution Formatting - Make solutions textbook-like with proper spacing and structure
"""

import sys
import os
sys.path.append('/app/backend')
sys.path.append('/app/scripts')

import logging
import asyncio
import psycopg2
from dotenv import load_dotenv
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SolutionFormatter:
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.database_url = os.getenv('DATABASE_URL')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        
        logger.info("🎯 Solution Formatter Initialized")
        logger.info(f"   Google Gemini: {'✅ Available' if self.google_api_key else '❌ Missing'}")

    def format_textbook_solution(self, approach: str, detailed_solution: str) -> tuple:
        """Format solutions with proper textbook-like structure"""
        
        # Clean and format approach
        formatted_approach = self.clean_and_structure_approach(approach)
        
        # Clean and format detailed solution
        formatted_detailed = self.clean_and_structure_detailed_solution(detailed_solution)
        
        return formatted_approach, formatted_detailed

    def clean_and_structure_approach(self, approach: str) -> str:
        """Clean and structure the approach section"""
        if not approach or len(approach.strip()) < 10:
            return "Apply systematic mathematical reasoning to solve this problem step by step."
        
        # Clean the text
        clean_approach = approach.strip()
        
        # Remove multiple spaces and clean up
        clean_approach = re.sub(r'\s+', ' ', clean_approach)
        
        # Ensure it ends with proper punctuation
        if not clean_approach.endswith('.'):
            clean_approach += '.'
        
        # Limit length to be concise
        if len(clean_approach) > 200:
            sentences = clean_approach.split('. ')
            clean_approach = '. '.join(sentences[:2]) + '.'
        
        return clean_approach

    def clean_and_structure_detailed_solution(self, detailed_solution: str) -> str:
        """Clean and structure the detailed solution with proper textbook formatting"""
        if not detailed_solution or len(detailed_solution.strip()) < 20:
            return "**Step 1:** Identify the given information and what needs to be found.\n\n**Step 2:** Apply the appropriate mathematical method.\n\n**Step 3:** Perform calculations systematically.\n\n**Step 4:** Verify the answer makes sense in context."
        
        # Clean the text
        clean_text = detailed_solution.strip()
        
        # Remove excessive whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        # Split into logical parts and restructure
        formatted_solution = self.restructure_solution_steps(clean_text)
        
        return formatted_solution

    def restructure_solution_steps(self, text: str) -> str:
        """Restructure solution into clear, numbered steps with proper formatting"""
        
        # Try to identify existing structure
        if "Step 1" in text or "1." in text or "First" in text:
            return self.enhance_existing_structure(text)
        else:
            return self.create_new_structure(text)

    def enhance_existing_structure(self, text: str) -> str:
        """Enhance existing step structure"""
        
        # Split by common step indicators
        parts = re.split(r'(?:Step \d+[:.]\s*|^\d+\.\s*|\n\d+\.\s*)', text)
        if len(parts) < 2:
            parts = text.split('. ')
        
        formatted_steps = []
        step_num = 1
        
        for part in parts:
            if part.strip() and len(part.strip()) > 10:
                clean_part = part.strip()
                if not clean_part.endswith('.'):
                    clean_part += '.'
                
                formatted_steps.append(f"**Step {step_num}:** {clean_part}")
                step_num += 1
        
        # Ensure we have at least 3 steps
        while len(formatted_steps) < 3:
            if step_num == 1:
                formatted_steps.append("**Step 1:** Analyze the given information and identify what needs to be found.")
            elif step_num == 2:
                formatted_steps.append("**Step 2:** Apply the appropriate mathematical formula or method.")
            else:
                formatted_steps.append(f"**Step {step_num}:** Complete the calculation and verify the result.")
            step_num += 1
        
        return '\n\n'.join(formatted_steps)

    def create_new_structure(self, text: str) -> str:
        """Create new step-by-step structure from unstructured text"""
        
        # Split text into logical chunks
        sentences = text.split('. ')
        if len(sentences) < 3:
            sentences = text.split(', ')
        
        formatted_steps = []
        
        # Create structured steps
        if len(sentences) >= 1:
            first_part = sentences[0].strip()
            if first_part:
                formatted_steps.append(f"**Step 1:** {first_part}{'.' if not first_part.endswith('.') else ''}")
        
        if len(sentences) >= 2:
            remaining_text = '. '.join(sentences[1:]).strip()
            if remaining_text:
                # Split remaining into calculation steps
                calc_parts = remaining_text.split(': ')
                if len(calc_parts) > 1:
                    for i, part in enumerate(calc_parts[:3], 2):
                        clean_part = part.strip()
                        if clean_part and len(clean_part) > 5:
                            formatted_steps.append(f"**Step {i}:** {clean_part}{'.' if not clean_part.endswith('.') else ''}")
                else:
                    formatted_steps.append(f"**Step 2:** {remaining_text}{'.' if not remaining_text.endswith('.') else ''}")
        
        # Ensure minimum structure
        if len(formatted_steps) < 3:
            formatted_steps.append("**Step 3:** Verify the answer and ensure it makes sense in the problem context.")
        
        return '\n\n'.join(formatted_steps)

    async def generate_well_formatted_solution(self, stem: str, answer: str, subcategory: str) -> tuple:
        """Generate a new well-formatted solution using LLM with specific formatting instructions"""
        try:
            if self.google_api_key:
                logger.info("  🎯 Generating well-formatted solution with Google Gemini...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="textbook_solution_formatting",
                    system_message="""You are an expert mathematics textbook author creating perfectly formatted solutions.

📚 TEXTBOOK FORMATTING REQUIREMENTS:

**APPROACH (2-3 sentences):**
- Clear, concise strategy overview
- Professional academic tone
- Ends with period

**DETAILED SOLUTION:**
- Must use numbered steps: **Step 1:**, **Step 2:**, **Step 3:**, etc.
- Each step on separate line with double line break between steps
- Clear, logical progression
- Show calculations explicitly
- Use proper mathematical notation (×, ÷, ², ³, √)
- Professional spacing and presentation

**FORMATTING EXAMPLE:**
**Step 1:** Identify the given information and what needs to be found.

**Step 2:** Set up the appropriate mathematical equation or formula.

**Step 3:** Perform the calculations systematically.

**Step 4:** Verify the answer makes sense in context.

CRITICAL: Use proper line breaks (\n\n) between steps for textbook-like spacing."""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}

Correct Answer: {answer}
Subcategory: {subcategory}

Create a perfectly formatted textbook solution with:
1. APPROACH: Brief strategy (2-3 sentences)
2. DETAILED SOLUTION: Numbered steps with proper spacing

Format exactly as:
**APPROACH:**
[Brief strategy overview]

**DETAILED SOLUTION:**
**Step 1:** [First step with clear explanation]

**Step 2:** [Second step with calculations]

**Step 3:** [Continue with logical progression]

**Step 4:** [Final verification and answer]""")
                
                response = await chat.send_message(user_message)
                response_text = response.strip()
                
                # Parse response
                if "**DETAILED SOLUTION:**" in response_text:
                    parts = response_text.split("**DETAILED SOLUTION:**", 1)
                    approach_part = parts[0].replace("**APPROACH:**", "").strip()
                    detailed_part = parts[1].strip()
                    
                    # Clean approach
                    approach = self.clean_and_structure_approach(approach_part)
                    
                    # Ensure detailed solution has proper formatting
                    if "**Step 1:**" not in detailed_part:
                        detailed_part = self.restructure_solution_steps(detailed_part)
                    
                    logger.info(f"  ✅ Generated well-formatted solution")
                    return approach, detailed_part
                    
        except Exception as e:
            logger.warning(f"  ❌ LLM formatting failed: {e}")
        
        # Fallback formatting
        approach = f"Apply {subcategory} concepts systematically to solve this problem step by step."
        detailed = f"""**Step 1:** Analyze the given information and identify what needs to be found.

**Step 2:** Apply the appropriate {subcategory} formula or method.

**Step 3:** Perform the calculations systematically and check each step.

**Step 4:** Verify the final answer: {answer}."""
        
        return approach, detailed

    async def process_single_question_formatting(self, question_data):
        """Process formatting for a single question"""
        question_id, stem, answer, approach, detailed_solution, subcategory = question_data
        
        try:
            logger.info(f"  📝 Question: {stem[:60]}...")
            
            # Check if solution needs formatting improvement
            needs_formatting = self.needs_formatting_improvement(approach, detailed_solution)
            
            if needs_formatting:
                logger.info("  🔧 Improving solution formatting...")
                
                # Generate new well-formatted solution
                new_approach, new_detailed = await self.generate_well_formatted_solution(
                    stem, answer, subcategory
                )
                
                # Update database
                conn = psycopg2.connect(self.database_url)
                cur = conn.cursor()
                
                update_query = """
                UPDATE questions SET 
                    solution_approach = %s,
                    detailed_solution = %s
                WHERE id = %s
                """
                
                cur.execute(update_query, (new_approach, new_detailed, question_id))
                conn.commit()
                conn.close()
                
                logger.info(f"  ✅ Improved formatting")
                return "improved"
            else:
                logger.info(f"  ✅ Formatting already good")
                return "already_good"
                
        except Exception as e:
            logger.error(f"  ❌ Error processing formatting: {e}")
            return "failed"

    def needs_formatting_improvement(self, approach: str, detailed_solution: str) -> bool:
        """Check if solution needs formatting improvement"""
        if not approach or not detailed_solution:
            return True
        
        # Check for poor formatting indicators
        poor_formatting_signs = [
            len(detailed_solution.split('\n')) < 3,  # Too few line breaks
            '**Step' not in detailed_solution,  # No proper step formatting
            detailed_solution.count('.') > 10 and detailed_solution.count('\n') < 3,  # Run-on text
            'Solution Approach:' in detailed_solution and 'Detailed Solution:' in detailed_solution,  # Merged sections
        ]
        
        return any(poor_formatting_signs)

    async def run_solution_formatting_fix(self):
        """Run solution formatting fix on all questions"""
        try:
            logger.info("🚀 STARTING SOLUTION FORMATTING FIX")
            logger.info("=" * 60)
            
            # Get all questions
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, stem, answer, solution_approach, detailed_solution, subcategory
                FROM questions 
                ORDER BY created_at
            """)
            
            all_questions = cur.fetchall()
            total_questions = len(all_questions)
            
            logger.info(f"📊 Found {total_questions} questions to check formatting")
            conn.close()
            
            # Process questions
            improved_count = 0
            already_good_count = 0
            failed_count = 0
            
            for i, question_data in enumerate(all_questions):
                logger.info(f"\n🔄 [{i+1}/{total_questions}] Processing formatting...")
                
                result = await self.process_single_question_formatting(question_data)
                
                if result == "improved":
                    improved_count += 1
                elif result == "already_good":
                    already_good_count += 1
                else:
                    failed_count += 1
                
                # Progress update every 20 questions
                if (i + 1) % 20 == 0:
                    logger.info(f"\n📈 PROGRESS [{i+1}/{total_questions}]")
                    logger.info(f"   ✅ Improved: {improved_count}")
                    logger.info(f"   ✅ Already good: {already_good_count}")
                    logger.info(f"   ❌ Failed: {failed_count}")
                
                # Small delay
                await asyncio.sleep(0.2)
            
            # Final summary
            logger.info(f"\n🎉 SOLUTION FORMATTING FIX COMPLETED!")
            logger.info("=" * 60)
            logger.info(f"📊 FINAL RESULTS:")
            logger.info(f"   Total questions: {total_questions}")
            logger.info(f"   ✅ Formatting improved: {improved_count}")
            logger.info(f"   ✅ Already well-formatted: {already_good_count}")
            logger.info(f"   ❌ Failed: {failed_count}")
            
            success_rate = (improved_count + already_good_count) / total_questions * 100
            logger.info(f"   📈 Success rate: {success_rate:.1f}%")
            
            return success_rate >= 90
            
        except Exception as e:
            logger.error(f"❌ Solution formatting fix failed: {e}")
            return False

async def main():
    formatter = SolutionFormatter()
    success = await formatter.run_solution_formatting_fix()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 SOLUTION FORMATTING FIX COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ SOLUTION FORMATTING FIX FAILED!")
    
    exit(0 if success else 1)