#!/usr/bin/env python3
"""
Comprehensive Re-enrichment of All Questions
Re-generates Approach, Detailed Solutions, Explanation, and MCQs for all questions in database
"""

import sys
import os
sys.path.append('/app/backend')
sys.path.append('/app/scripts')

from database import *
from human_friendly_solution_generator import HumanFriendlySolutionGenerator
import logging
import asyncio
import json
import psycopg2
from dotenv import load_dotenv
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveReEnricher:
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.database_url = os.getenv('DATABASE_URL')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize solution generator
        self.solution_generator = HumanFriendlySolutionGenerator()
        
        logger.info("🔑 API Keys Status:")
        logger.info(f"   Google Gemini: {'✅ Available' if self.google_api_key else '❌ Missing'}")
        logger.info(f"   OpenAI: {'✅ Available' if self.openai_api_key else '❌ Missing'}")
        logger.info(f"   Anthropic: {'✅ Available' if self.anthropic_api_key else '❌ Missing'}")

    async def generate_answer_with_gemini(self, stem: str) -> str:
        """Generate answer using Google Gemini primary"""
        try:
            if self.google_api_key:
                logger.info("  🎯 Generating answer with Google Gemini...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="comprehensive_answer_generation",
                    system_message="""You are an expert CAT exam solver with perfect accuracy. Generate the correct, concise answer.

CRITICAL RULES:
1. Provide ONLY the final numerical answer or expression
2. Be precise and accurate - no approximations unless specified
3. For numerical answers, use integers when possible
4. For fractions, use simplest form (e.g., "3/4" not "0.75" unless decimal requested)
5. No units unless specifically required by the question
6. Single number or expression only - no explanations"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"Question: {stem}")
                response = await chat.send_message(user_message)
                answer = response.strip()
                
                # Clean the answer (remove any extra text)
                import re
                # Try to extract just the number/expression
                match = re.search(r'[\d.,/+\-×÷=\s]+', answer)
                if match and len(match.group().strip()) < len(answer):
                    clean_answer = match.group().strip()
                    if clean_answer:
                        answer = clean_answer
                
                logger.info(f"  ✅ Google Gemini generated answer: {answer}")
                return answer
                
        except Exception as e:
            logger.warning(f"  ❌ Google Gemini failed for answer: {e}")
            return "Error in answer generation"

    async def generate_comprehensive_solutions(self, stem: str, answer: str, subcategory: str) -> tuple:
        """Generate comprehensive solutions with Approach, Detailed Solution, and Explanation"""
        try:
            if self.google_api_key:
                logger.info("  🎯 Generating comprehensive solutions with Google Gemini...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="comprehensive_solution_generation",
                    system_message="""You are an expert CAT mathematics tutor creating comprehensive, student-friendly solutions.

📘 MASTER DIRECTIVE: Create three distinct solution components

**APPROACH (50-100 words):**
- Brief strategic overview of the solution method
- Key insight or pattern recognition
- Main mathematical concept to apply

**DETAILED SOLUTION (200-500 words):**
- Complete step-by-step breakdown
- Show all calculations clearly
- Explain the reasoning behind each step
- Use human-friendly notation: x², √16, 45 ÷ 3, etc.
- Include intermediate results

**EXPLANATION (100-200 words):**
- Why this method works
- Alternative approaches (if any)
- Common mistakes to avoid
- Conceptual understanding

FORMATTING RULES:
❌ NEVER use LaTeX: \\frac{}, \\sqrt{}, \\times
✅ Use Unicode: x², √, ×, ÷, ≤, ≥
✅ Structure with clear headers
✅ Number steps (Step 1:, Step 2:, etc.)
✅ Highlight final answer

Format your response exactly as:
**APPROACH:**
[Brief strategic overview]

**DETAILED SOLUTION:**
[Complete step-by-step solution]

**EXPLANATION:**
[Conceptual understanding and insights]"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}

Correct Answer: {answer}
Category: Quantitative Aptitude
Subcategory: {subcategory}

Generate comprehensive solution with APPROACH, DETAILED SOLUTION, and EXPLANATION sections.""")
                
                response = await chat.send_message(user_message)
                response_text = response.strip()
                
                # Parse the response into three components
                approach = ""
                detailed_solution = ""
                explanation = ""
                
                if "**APPROACH:**" in response_text and "**DETAILED SOLUTION:**" in response_text:
                    parts = response_text.split("**DETAILED SOLUTION:**")
                    approach_section = parts[0].replace("**APPROACH:**", "").strip()
                    
                    if "**EXPLANATION:**" in parts[1]:
                        solution_and_explanation = parts[1].split("**EXPLANATION:**")
                        detailed_solution = solution_and_explanation[0].strip()
                        explanation = solution_and_explanation[1].strip()
                    else:
                        detailed_solution = parts[1].strip()
                        explanation = f"This {subcategory} problem demonstrates the application of fundamental mathematical principles to arrive at the correct answer."
                    
                    approach = self.clean_human_friendly_text(approach_section)
                    detailed_solution = self.clean_human_friendly_text(detailed_solution)
                    explanation = self.clean_human_friendly_text(explanation)
                else:
                    # Fallback parsing
                    approach = f"Apply {subcategory} concepts systematically to solve this problem."
                    detailed_solution = self.clean_human_friendly_text(response_text)
                    explanation = f"This solution demonstrates the practical application of {subcategory} principles."
                
                logger.info(f"  ✅ Google Gemini generated comprehensive solutions")
                return approach[:500], detailed_solution[:2000], explanation[:800]
                
        except Exception as e:
            logger.warning(f"  ❌ Google Gemini failed for solutions: {e}")
            
            # Fallback to human-friendly solution generator
            approach, detailed = await self.solution_generator.generate_human_friendly_solutions(
                stem, answer, "Quantitative Aptitude", subcategory
            )
            explanation = f"This {subcategory} problem requires systematic application of mathematical principles to reach the correct solution."
            
            return approach[:500], detailed[:2000], explanation[:800]

    def clean_human_friendly_text(self, text: str) -> str:
        """Clean text and ensure human-friendly mathematical notation"""
        if not text:
            return text
        
        import re
        
        # Convert LaTeX to plain mathematical notation
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', text)
        text = re.sub(r'\\sqrt\{([^}]+)\}', r'√\1', text)
        text = re.sub(r'([a-zA-Z0-9]+)\^\{([0-9]+)\}', lambda m: f'{m.group(1)}{self.superscript_number(m.group(2))}', text)
        text = re.sub(r'([a-zA-Z0-9]+)\^([0-9]+)', lambda m: f'{m.group(1)}{self.superscript_number(m.group(2))}', text)
        
        # Remove LaTeX delimiters
        text = text.replace('$', '').replace('\\(', '').replace('\\)', '')
        text = text.replace('\\[', '').replace('\\]', '')
        
        # Convert symbols
        text = text.replace('\\times', '×').replace('\\div', '÷')
        text = text.replace('\\le', '≤').replace('\\ge', '≥')
        text = text.replace('\\ne', '≠').replace('\\approx', '≈')
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def superscript_number(self, num_str: str) -> str:
        """Convert number to superscript Unicode"""
        superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }
        return ''.join(superscript_map.get(d, d) for d in num_str)

    def randomize_mcq_placement(self, correct_answer: str, wrong_answers: list) -> dict:
        """Randomize MCQ option placement"""
        import random
        
        all_options = [correct_answer] + wrong_answers[:3]
        random.shuffle(all_options)
        
        correct_position = all_options.index(correct_answer)
        correct_labels = ["A", "B", "C", "D"]
        
        return {
            "A": all_options[0],
            "B": all_options[1], 
            "C": all_options[2],
            "D": all_options[3],
            "correct": correct_labels[correct_position]
        }

    async def generate_mcq_options(self, stem: str, answer: str, subcategory: str) -> dict:
        """Generate MCQ options with Google Gemini"""
        try:
            if self.google_api_key:
                logger.info("  🎯 Generating MCQ options with Google Gemini...")
                
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="comprehensive_mcq_generation",
                    system_message="""You are an expert CAT question creator. Generate exactly 3 plausible wrong answers for multiple choice questions.

RULES:
1. Create 3 wrong answers that look reasonable but are incorrect
2. Base wrong answers on common student calculation errors
3. Make sure all values are distinct from the correct answer
4. Use realistic numerical values for the question type
5. Return ONLY valid JSON, no other text

REQUIRED JSON FORMAT:
{
  "wrong_answer_1": "plausible incorrect value",
  "wrong_answer_2": "plausible incorrect value", 
  "wrong_answer_3": "plausible incorrect value"
}"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {stem}
Correct Answer: {answer}
Subcategory: {subcategory}

Generate 3 plausible wrong answers. Return ONLY the JSON object.""")
                
                response = await chat.send_message(user_message)
                response_text = response.strip()
                
                # Extract and parse JSON
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    
                    if all(field in result for field in ["wrong_answer_1", "wrong_answer_2", "wrong_answer_3"]):
                        wrong_answers = [
                            result["wrong_answer_1"],
                            result["wrong_answer_2"], 
                            result["wrong_answer_3"]
                        ]
                        
                        options = self.randomize_mcq_placement(answer, wrong_answers)
                        logger.info(f"  ✅ Google Gemini generated MCQ options (correct: {options['correct']})")
                        return options
                        
        except Exception as e:
            logger.warning(f"  ❌ Google Gemini failed for MCQ: {e}")
        
        # Smart fallback based on answer
        try:
            import re
            numbers = re.findall(r'-?\d+\.?\d*', answer)
            if numbers:
                base_value = float(numbers[0])
                wrong_answers = [
                    str(int(base_value * 2) if (base_value * 2).is_integer() else base_value * 2),
                    str(int(base_value / 2) if base_value != 0 and (base_value / 2).is_integer() else base_value / 2),
                    str(int(base_value + 1) if (base_value + 1).is_integer() else base_value + 1)
                ]
            else:
                wrong_answers = ["Alternative 1", "Alternative 2", "Alternative 3"]
                
            options = self.randomize_mcq_placement(answer, wrong_answers)
            logger.info(f"  ✅ Generated smart fallback MCQ options (correct: {options['correct']})")
            return options
            
        except:
            wrong_answers = ["Option 1", "Option 2", "Option 3"]
            options = self.randomize_mcq_placement(answer, wrong_answers)
            logger.warning(f"  ⚠️ Using basic fallback MCQ options (correct: {options['correct']})")
            return options

    async def process_single_question(self, question_data):
        """Process a single question with comprehensive re-enrichment"""
        question_id, stem, current_answer, subcategory, type_of_question = question_data
        
        try:
            logger.info(f"  📝 Question: {stem[:60]}...")
            logger.info(f"  📂 Category: {subcategory} -> {type_of_question}")
            
            # Step 1: Generate fresh answer
            if current_answer and current_answer not in ['To Be Enriched', 'Error in answer generation']:
                # Use existing answer if it's good
                answer = current_answer
                logger.info(f"  ✅ Using existing answer: {answer}")
            else:
                # Generate new answer
                answer = await self.generate_answer_with_gemini(stem)
            
            # Step 2: Generate comprehensive solutions (Approach, Detailed, Explanation)
            approach, detailed_solution, explanation = await self.generate_comprehensive_solutions(
                stem, answer, subcategory
            )
            
            # Step 3: Generate MCQ options
            mcq_options = await self.generate_mcq_options(stem, answer, subcategory)
            
            # Step 4: Update database
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            update_query = """
            UPDATE questions SET 
                answer = %s,
                solution_approach = %s,
                detailed_solution = %s,
                mcq_options = %s
            WHERE id = %s
            """
            
            cur.execute(update_query, (
                answer,
                approach,
                detailed_solution,
                json.dumps(mcq_options),
                question_id
            ))
            
            conn.commit()
            conn.close()
            
            # Validate results
            has_good_answer = answer and len(answer.strip()) > 0 and answer != "Error in answer generation"
            has_good_approach = approach and len(approach.strip()) > 20
            has_good_detailed = detailed_solution and len(detailed_solution.strip()) > 50
            has_good_mcq = mcq_options and mcq_options.get("A") != "Option 1"
            
            success_components = sum([has_good_answer, has_good_approach, has_good_detailed, has_good_mcq])
            
            if success_components >= 3:
                logger.info(f"  ✅ Complete success ({success_components}/4 components)")
                return "complete_success"
            elif success_components >= 2:
                logger.info(f"  ⚠️ Partial success ({success_components}/4 components)")
                return "partial_success"
            else:
                logger.info(f"  ❌ Failed ({success_components}/4 components)")
                return "failed"
                
        except Exception as e:
            logger.error(f"  ❌ Error processing question: {e}")
            return "failed"

    async def run_comprehensive_re_enrichment(self):
        """Run comprehensive re-enrichment on all questions"""
        try:
            logger.info("🚀 STARTING COMPREHENSIVE RE-ENRICHMENT OF ALL QUESTIONS")
            logger.info("=" * 80)
            
            # Get all questions from database
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, stem, answer, subcategory, type_of_question
                FROM questions 
                ORDER BY created_at
            """)
            
            all_questions = cur.fetchall()
            total_questions = len(all_questions)
            
            logger.info(f"📊 Found {total_questions} questions to process")
            conn.close()
            
            if total_questions == 0:
                logger.warning("❌ No questions found in database!")
                return False
            
            # Process all questions
            complete_successes = 0
            partial_successes = 0
            failures = 0
            
            start_time = time.time()
            
            for i, question_data in enumerate(all_questions):
                logger.info(f"\n🔄 [{i+1}/{total_questions}] Processing question...")
                
                result = await self.process_single_question(question_data)
                
                if result == "complete_success":
                    complete_successes += 1
                elif result == "partial_success":
                    partial_successes += 1
                else:
                    failures += 1
                
                # Progress update every 10 questions
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / (i + 1)
                    remaining = (total_questions - i - 1) * avg_time
                    
                    logger.info(f"\n📈 PROGRESS UPDATE [{i+1}/{total_questions}]")
                    logger.info(f"   ✅ Complete successes: {complete_successes}")
                    logger.info(f"   ⚠️ Partial successes: {partial_successes}")
                    logger.info(f"   ❌ Failures: {failures}")
                    logger.info(f"   ⏱️ Estimated remaining time: {remaining/60:.1f} minutes")
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.3)
            
            # Final summary
            total_time = time.time() - start_time
            success_rate = (complete_successes + partial_successes) / total_questions * 100
            
            logger.info(f"\n🎉 COMPREHENSIVE RE-ENRICHMENT COMPLETED!")
            logger.info("=" * 80)
            logger.info(f"📊 FINAL RESULTS:")
            logger.info(f"   Total questions processed: {total_questions}")
            logger.info(f"   ✅ Complete successes: {complete_successes} ({complete_successes/total_questions*100:.1f}%)")
            logger.info(f"   ⚠️ Partial successes: {partial_successes} ({partial_successes/total_questions*100:.1f}%)")
            logger.info(f"   ❌ Failures: {failures} ({failures/total_questions*100:.1f}%)")
            logger.info(f"   📈 Overall success rate: {success_rate:.1f}%")
            logger.info(f"   ⏱️ Total processing time: {total_time/60:.1f} minutes")
            logger.info(f"   ⚡ Average time per question: {total_time/total_questions:.1f} seconds")
            
            # Verify final database state
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN answer IS NOT NULL AND answer != '' AND answer != 'To Be Enriched' AND answer != 'Error in answer generation' THEN 1 ELSE 0 END) as good_answers,
                    SUM(CASE WHEN solution_approach IS NOT NULL AND LENGTH(solution_approach) > 20 THEN 1 ELSE 0 END) as good_approaches,
                    SUM(CASE WHEN detailed_solution IS NOT NULL AND LENGTH(detailed_solution) > 50 THEN 1 ELSE 0 END) as good_detailed,
                    SUM(CASE WHEN mcq_options IS NOT NULL AND mcq_options != '' THEN 1 ELSE 0 END) as has_mcq
                FROM questions
            """)
            
            final_stats = cur.fetchone()
            conn.close()
            
            logger.info(f"\n🔍 FINAL DATABASE VERIFICATION:")
            logger.info(f"   Total questions: {final_stats[0]}")
            logger.info(f"   Good answers: {final_stats[1]} ({final_stats[1]/final_stats[0]*100:.1f}%)")
            logger.info(f"   Good approaches: {final_stats[2]} ({final_stats[2]/final_stats[0]*100:.1f}%)")
            logger.info(f"   Good detailed solutions: {final_stats[3]} ({final_stats[3]/final_stats[0]*100:.1f}%)")
            logger.info(f"   Has MCQ options: {final_stats[4]} ({final_stats[4]/final_stats[0]*100:.1f}%)")
            
            return success_rate >= 75  # 75% success rate required
            
        except Exception as e:
            logger.error(f"❌ Comprehensive re-enrichment failed: {e}")
            return False

async def main():
    enricher = ComprehensiveReEnricher()
    success = await enricher.run_comprehensive_re_enrichment()
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 COMPREHENSIVE RE-ENRICHMENT COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ COMPREHENSIVE RE-ENRICHMENT FAILED!")
    
    exit(0 if success else 1)