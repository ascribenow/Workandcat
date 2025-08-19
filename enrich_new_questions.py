#!/usr/bin/env python3
"""
Enrich newly added questions from CSV with LLM-generated content
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_answer_with_fallback(stem: str) -> str:
    """Generate answer with Google Gemini primary, OpenAI/Anthropic fallback"""
    try:
        # Try Google Gemini first
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if google_api_key:
            logger.info("  Trying Google Gemini for answer generation...")
            
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=google_api_key,
                session_id="answer_generation",
                system_message="""You are an expert CAT exam solver. Generate the correct, concise answer for the given question.

Rules:
1. Provide only the final answer (number, expression, or choice)
2. Be precise and accurate
3. Use standard mathematical notation
4. For numerical answers, include units if applicable"""
            ).with_model("gemini", "gemini-2.0-flash")
            
            user_message = UserMessage(text=f"Question: {stem}")
            response = await chat.send_message(user_message)
            answer = response.strip()
            
            logger.info(f"  ✅ Google Gemini generated answer: {answer}")
            return answer
            
    except Exception as gemini_error:
        logger.warning(f"  ❌ Google Gemini failed: {gemini_error}")
        
        # Fallback to OpenAI
        try:
            import openai
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                logger.info("  Trying OpenAI fallback for answer generation...")
                client = openai.OpenAI(api_key=openai_key)
                
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
            logger.warning(f"  ❌ OpenAI also failed: {openai_error}")
    
    # Ultimate fallback
    logger.error("  ❌ All LLMs failed for answer generation!")
    return "Answer could not be generated - manual review required"

def randomize_mcq_placement(correct_answer: str, wrong_answers: list) -> dict:
    """Randomize the placement of correct answer among MCQ options"""
    import random
    
    # Create list of all options with correct answer
    all_options = [correct_answer] + wrong_answers[:3]  # Ensure only 3 wrong answers
    
    # Shuffle the options
    random.shuffle(all_options)
    
    # Find which position the correct answer ended up in
    correct_position = all_options.index(correct_answer)
    correct_labels = ["A", "B", "C", "D"]
    
    # Create the final MCQ dictionary
    mcq_options = {
        "A": all_options[0],
        "B": all_options[1], 
        "C": all_options[2],
        "D": all_options[3],
        "correct": correct_labels[correct_position]
    }
    
    return mcq_options

async def generate_mcq_options_with_fallback(stem: str, answer: str, subcategory: str, difficulty: str = "Medium") -> dict:
    """Generate MCQ options with Google Gemini primary, OpenAI/Anthropic fallback"""
    try:
        # Try Google Gemini first
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if google_api_key:
            logger.info("  Trying Google Gemini for MCQ generation...")
            
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=google_api_key,
                session_id="mcq_generation",
                system_message=f"""You are an expert CAT math tutor creating multiple choice questions. Generate exactly 3 plausible wrong answers for the given question. The correct answer is already provided.

RULES:
1. Generate exactly 3 wrong answers that are plausible but incorrect
2. Base wrong answers on common student errors for this type of problem
3. Make sure all values are distinct from the correct answer
4. Match the difficulty level: {difficulty}
5. Return ONLY valid JSON, no other text

REQUIRED JSON FORMAT:
{{
  "wrong_answer_1": "plausible incorrect value",
  "wrong_answer_2": "plausible incorrect value", 
  "wrong_answer_3": "plausible incorrect value"
}}"""
            ).with_model("gemini", "gemini-2.0-flash")
            
            user_message = UserMessage(text=f"""Question: {stem}
Correct Answer: {answer}
Sub-category: {subcategory}
Difficulty: {difficulty}

Generate 3 plausible wrong answers for this question. The correct answer is already "{answer}". Return ONLY the JSON object with 3 wrong answers.""")
            
            response = await chat.send_message(user_message)
            response_text = response.strip()
            
            # Extract JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate new format with wrong answers
                if all(field in result for field in ["wrong_answer_1", "wrong_answer_2", "wrong_answer_3"]):
                    wrong_answers = [
                        result["wrong_answer_1"],
                        result["wrong_answer_2"], 
                        result["wrong_answer_3"]
                    ]
                    
                    # Randomize placement of correct answer
                    options = randomize_mcq_placement(answer, wrong_answers)
                    logger.info(f"  ✅ Google Gemini generated MCQ options with randomized placement (correct: {options['correct']})")
                    return options
                    
    except Exception as gemini_error:
        logger.warning(f"  ❌ Google Gemini failed for MCQ: {gemini_error}")
        
        # Fallback to OpenAI
        try:
            import openai
            
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                logger.info("  Trying OpenAI fallback for MCQ generation...")
                client = openai.OpenAI(api_key=openai_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"""You are an expert CAT math tutor creating multiple choice questions. Generate exactly 3 plausible wrong answers for the given question. The correct answer is already provided.

RULES:
1. Generate exactly 3 wrong answers that are plausible but incorrect
2. Base wrong answers on common student errors for this type of problem
3. Make sure all values are distinct from the correct answer
4. Match the difficulty level: {difficulty}
5. Return ONLY valid JSON, no other text

REQUIRED JSON FORMAT:
{{
  "wrong_answer_1": "plausible incorrect value",
  "wrong_answer_2": "plausible incorrect value", 
  "wrong_answer_3": "plausible incorrect value"
}}"""},
                        {"role": "user", "content": f"""Question: {stem}
Correct Answer: {answer}
Sub-category: {subcategory}
Difficulty: {difficulty}

Generate 3 plausible wrong answers for this question. The correct answer is already "{answer}". Return ONLY the JSON object with 3 wrong answers."""}
                    ],
                    max_tokens=300
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # Extract JSON
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    
                    # Validate new format with wrong answers
                    if all(field in result for field in ["wrong_answer_1", "wrong_answer_2", "wrong_answer_3"]):
                        wrong_answers = [
                            result["wrong_answer_1"],
                            result["wrong_answer_2"], 
                            result["wrong_answer_3"]
                        ]
                        
                        # Randomize placement of correct answer
                        options = randomize_mcq_placement(answer, wrong_answers)
                        logger.info(f"  ✅ OpenAI generated MCQ options with randomized placement (correct: {options['correct']})")
                        return options
                        
        except Exception as openai_error:
            logger.error(f"  ❌ OpenAI also failed for MCQ: {openai_error}")
    
    # Smart fallback based on correct answer
    try:
        import re
        numbers = re.findall(r'-?\d+\.?\d*', answer)
        if numbers:
            base_value = float(numbers[0])
            wrong_answers = [
                str(int(base_value * 2) if (base_value * 2).is_integer() else base_value * 2),
                str(int(base_value / 2) if (base_value / 2).is_integer() else base_value / 2),
                str(int(base_value + 1) if (base_value + 1).is_integer() else base_value + 1)
            ]
            
            # Randomize placement  
            options = randomize_mcq_placement(answer, wrong_answers)
            logger.info(f"  ✅ Generated smart fallback MCQ options with randomized placement (correct: {options['correct']})")
            return options
    except:
        pass
    
    # Ultimate fallback - also randomize
    wrong_answers = ["Alternative 1", "Alternative 2", "Alternative 3"]
    options = randomize_mcq_placement(answer, wrong_answers)
    logger.warning(f"  ⚠️ Using basic fallback MCQ options with randomized placement (correct: {options['correct']})")
    return options

async def classify_question_with_llm(stem: str) -> tuple:
    """Classify question into subcategory and type using LLM"""
    try:
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if google_api_key:
            logger.info("  Classifying question with Google Gemini...")
            
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=google_api_key,
                session_id="question_classification",
                system_message="""You are an expert at classifying CAT Quantitative Aptitude questions. Classify the given question into appropriate subcategory and type.

Available subcategories: HCF-LCM, Divisibility, Remainders, Factorials, Digit Properties, Number Properties, Averages, Ratios, Percentages, Time-Speed-Distance, Geometry, Arithmetic Progressions, Algebra, Other

Available types: Basics, Applications, Factorisation of Integers, Chinese Remainder Theorem, Perfect Squares, Properties of Factorials, Sum of Digits, Ratio Proportions, Basic Calculations, Advanced Applications

Return ONLY a JSON object:
{
  "subcategory": "appropriate subcategory",
  "type_of_question": "appropriate type"
}"""
            ).with_model("gemini", "gemini-2.0-flash")
            
            user_message = UserMessage(text=f"Question: {stem}")
            response = await chat.send_message(user_message)
            
            # Extract JSON
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                if "subcategory" in result and "type_of_question" in result:
                    logger.info(f"  ✅ Classified: {result['subcategory']} -> {result['type_of_question']}")
                    return result["subcategory"], result["type_of_question"]
                    
    except Exception as e:
        logger.warning(f"  ❌ Classification failed: {e}")
    
    # Fallback classification
    return "General", "Basics"

async def enrich_new_questions():
    """Enrich newly added questions with answers, solutions, MCQs, and classifications"""
    try:
        logger.info("🚀 Starting enrichment of newly added questions...")
        
        # Load environment
        load_dotenv('/app/backend/.env')
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        # Check API keys
        google_key = os.getenv('GOOGLE_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if not google_key and not openai_key:
            logger.error("❌ No API keys found")
            return False
        
        logger.info("✅ API keys found - ready for enrichment")
        
        # Find questions that need enrichment (recently added ones with 'To Be Enriched')
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, stem, answer, solution_approach, detailed_solution, subcategory, type_of_question, source
            FROM questions 
            WHERE answer = 'To Be Enriched' OR solution_approach = 'To Be Enriched'
            ORDER BY created_at DESC
        """)
        
        questions = cur.fetchall()
        logger.info(f"📊 Found {len(questions)} questions needing enrichment")
        
        if not questions:
            logger.info("✅ No questions need enrichment")
            return True
        
        # Initialize human-friendly solution generator
        solution_generator = HumanFriendlySolutionGenerator()
        
        # Process each question
        success_count = 0
        partial_success_count = 0
        failed_count = 0
        
        for i, question_data in enumerate(questions):
            try:
                question_id, stem, answer, solution_approach, detailed_solution, subcategory, type_of_question, source = question_data
                
                logger.info(f"\n🔄 [{i+1}/{len(questions)}] Processing: {stem[:50]}...")
                
                # Step 1: Classify question if needed
                if subcategory == 'To Be Classified' or type_of_question == 'To Be Classified':
                    logger.info("  Classifying question...")
                    new_subcategory, new_type = await classify_question_with_llm(stem)
                    subcategory = new_subcategory
                    type_of_question = new_type
                
                # Step 2: Generate answer if needed
                if answer == 'To Be Enriched' or not answer or answer.strip() == '':
                    logger.info("  Generating answer...")
                    answer = await generate_answer_with_fallback(stem)
                
                # Step 3: Generate solutions if needed
                if solution_approach == 'To Be Enriched' or not solution_approach or solution_approach.strip() == '':
                    logger.info("  Generating human-friendly solutions...")
                    solution_approach, detailed_solution = await solution_generator.generate_human_friendly_solutions(
                        stem, answer, "Quantitative Aptitude", subcategory
                    )
                
                # Step 4: Generate MCQ options
                logger.info("  Generating MCQ options...")
                mcq_options = await generate_mcq_options_with_fallback(
                    stem, answer, subcategory, "Medium"
                )
                
                # Convert Unicode mathematical notation (similar to question_mathematical_enhancement.py)
                stem_enhanced = enhance_mathematical_notation(stem)
                
                # Step 5: Update database
                update_query = """
                UPDATE questions SET 
                    stem = %s,
                    subcategory = %s,
                    type_of_question = %s,
                    answer = %s,
                    solution_approach = %s,
                    detailed_solution = %s,
                    mcq_options = %s
                WHERE id = %s
                """
                
                cur.execute(update_query, (
                    stem_enhanced,
                    subcategory,
                    type_of_question,
                    answer,
                    solution_approach,
                    detailed_solution,
                    json.dumps(mcq_options),
                    question_id
                ))
                
                conn.commit()
                
                # Check success level
                has_answer = answer and not answer.startswith("Answer could not")
                has_solution = solution_approach and len(solution_approach) > 10
                has_mcq = mcq_options and mcq_options.get("A") != "Alternative 1"
                
                if has_answer and has_solution and has_mcq:
                    success_count += 1
                    logger.info(f"  ✅ Complete success - {subcategory} -> {type_of_question}")
                elif has_answer or has_solution:
                    partial_success_count += 1
                    logger.info(f"  ⚠️ Partial success")
                else:
                    failed_count += 1
                    logger.info(f"  ❌ Failed")
                
                # Small delay to be nice to APIs
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process question {i+1}: {e}")
                failed_count += 1
                continue
        
        conn.close()
        
        # Final summary
        logger.info(f"\n🎉 ENRICHMENT COMPLETED!")
        logger.info(f"✅ Complete successes: {success_count}")
        logger.info(f"⚠️ Partial successes: {partial_success_count}")
        logger.info(f"❌ Failures: {failed_count}")
        logger.info(f"📊 Total processed: {len(questions)}")
        
        success_rate = (success_count + partial_success_count) / len(questions) if questions else 0
        logger.info(f"📈 Overall success rate: {success_rate:.1%}")
        
        return success_rate > 0.7  # 70% success rate required
        
    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}")
        return False

def enhance_mathematical_notation(text: str) -> str:
    """Convert mathematical expressions to Unicode notation"""
    if not text:
        return text
    
    import re
    
    # Convert exponents
    exponent_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
    }
    
    def replace_exponent(match):
        base = match.group(1)
        exp = match.group(2)
        if exp in exponent_map:
            return f"{base}{exponent_map[exp]}"
        elif len(exp) <= 3 and exp.isdigit():
            return f"{base}{''.join(exponent_map.get(d, d) for d in exp)}"
        else:
            return match.group(0)  # Keep original if too complex
    
    # Replace ^ exponents (like 2^3 → 2³)
    text = re.sub(r'(\w+)\^(\d+)', replace_exponent, text)
    
    # Replace * with × for multiplication
    text = text.replace('*', '×')
    
    # Replace / with ÷ for simple divisions
    text = re.sub(r'(\d+)\s*/\s*(\d+)', r'\1 ÷ \2', text)
    
    return text

if __name__ == "__main__":
    success = asyncio.run(enrich_new_questions())
    exit(0 if success else 1)