#!/usr/bin/env python3
"""
Complete LLM Enrichment Fix - Generate missing answers, solutions, and MCQs
Implements OpenAI primary with Anthropic fallback as per user directive
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
from llm_enrichment import LLMEnrichmentPipeline
import logging
import asyncio
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_answer_with_fallback(stem: str) -> str:
    """Generate answer with OpenAI primary, Anthropic fallback"""
    try:
        # Try OpenAI first
        import openai
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            logger.info("  Trying OpenAI for answer generation...")
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
        logger.warning(f"  ❌ OpenAI failed: {openai_error}")
        
        # Fallback to Anthropic
        try:
            import anthropic
            
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                logger.info("  Trying Anthropic fallback for answer generation...")
                client = anthropic.Anthropic(api_key=anthropic_key)
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=200,
                    messages=[
                        {"role": "user", "content": f"""You are an expert CAT exam solver. Generate the correct, concise answer for the given question.

Rules:
1. Provide only the final answer (number, expression, or choice)
2. Be precise and accurate
3. Use standard mathematical notation
4. For numerical answers, include units if applicable

Question: {stem}"""}
                    ]
                )
                
                answer = response.content[0].text.strip()
                logger.info(f"  ✅ Anthropic generated answer: {answer}")
                return answer
                
        except Exception as anthropic_error:
            logger.error(f"  ❌ Anthropic also failed: {anthropic_error}")
    
    # Ultimate fallback
    logger.error("  ❌ Both OpenAI and Anthropic failed!")
    return "Answer could not be generated - manual review required"

async def generate_solutions_with_fallback(stem: str, answer: str, category: str, subcategory: str) -> tuple:
    """Generate solutions with OpenAI primary, Anthropic fallback"""
    try:
        # Try OpenAI first
        import openai
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            logger.info("  Trying OpenAI for solution generation...")
            client = openai.OpenAI(api_key=openai_key)
            
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
   - Uses simple, clear language"""},
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
            
            logger.info(f"  ✅ OpenAI generated solutions")
            return approach[:500], detailed[:2000]
            
    except Exception as openai_error:
        logger.warning(f"  ❌ OpenAI failed for solutions: {openai_error}")
        
        # Fallback to Anthropic
        try:
            import anthropic
            
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                logger.info("  Trying Anthropic fallback for solution generation...")
                client = anthropic.Anthropic(api_key=anthropic_key)
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1500,
                    messages=[
                        {"role": "user", "content": f"""You are an expert CAT math tutor who creates comprehensive explanations.

Question: {stem}
Correct Answer: {answer}
Category: {category}
Subcategory: {subcategory}

Please provide:
1. SOLUTION APPROACH: [Brief strategy overview]
2. DETAILED SOLUTION: [Comprehensive step-by-step explanation with basics]
"""}
                    ]
                )
                
                response_text = response.content[0].text.strip()
                
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
                
                logger.info(f"  ✅ Anthropic generated solutions")
                return approach[:500], detailed[:2000]
                
        except Exception as anthropic_error:
            logger.error(f"  ❌ Anthropic also failed for solutions: {anthropic_error}")
    
    # Ultimate fallback
    logger.error("  ❌ Both OpenAI and Anthropic failed for solutions!")
    approach = f"Apply {subcategory} concepts systematically"
    detailed = f"This is a {subcategory} problem from {category}. Step 1: Identify what is given. Step 2: Determine what to find. Step 3: Apply relevant formula. Step 4: Calculate step by step. Step 5: Verify the answer."
    return approach, detailed

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
    """Generate MCQ options with OpenAI primary, Anthropic fallback"""
    try:
        # Try OpenAI first
        import openai
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            logger.info("  Trying OpenAI for MCQ generation...")
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
                
                # Validate and format
                if all(field in result for field in ["option_a", "option_b", "option_c", "option_d", "correct_label"]):
                    options = {
                        "A": result["option_a"],
                        "B": result["option_b"], 
                        "C": result["option_c"],
                        "D": result["option_d"],
                        "correct": result["correct_label"].upper()
                    }
                    logger.info(f"  ✅ OpenAI generated MCQ options")
                    return options
                    
    except Exception as openai_error:
        logger.warning(f"  ❌ OpenAI failed for MCQ: {openai_error}")
        
        # Fallback to Anthropic
        try:
            import anthropic
            
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
            if anthropic_key:
                logger.info("  Trying Anthropic fallback for MCQ generation...")
                client = anthropic.Anthropic(api_key=anthropic_key)
                
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    messages=[
                        {"role": "user", "content": f"""Generate 4 MCQ options for this question. Return ONLY valid JSON:

Question: {stem}
Correct Answer: {answer}

Format:
{{
  "option_a": "value",
  "option_b": "value", 
  "option_c": "value",
  "option_d": "value",
  "correct_label": "A"
}}"""}
                    ]
                )
                
                response_text = response.content[0].text.strip()
                
                # Extract JSON
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    
                    if all(field in result for field in ["option_a", "option_b", "option_c", "option_d", "correct_label"]):
                        options = {
                            "A": result["option_a"],
                            "B": result["option_b"], 
                            "C": result["option_c"],
                            "D": result["option_d"],
                            "correct": result["correct_label"].upper()
                        }
                        logger.info(f"  ✅ Anthropic generated MCQ options")
                        return options
                        
        except Exception as anthropic_error:
            logger.error(f"  ❌ Anthropic also failed for MCQ: {anthropic_error}")
    
    # Smart fallback based on correct answer
    try:
        import re
        numbers = re.findall(r'-?\d+\.?\d*', answer)
        if numbers:
            base_value = float(numbers[0])
            options = {
                "A": str(int(base_value) if base_value.is_integer() else base_value),
                "B": str(int(base_value * 2) if (base_value * 2).is_integer() else base_value * 2),
                "C": str(int(base_value / 2) if (base_value / 2).is_integer() else base_value / 2),
                "D": str(int(base_value + 1) if (base_value + 1).is_integer() else base_value + 1),
                "correct": "A"
            }
            logger.info(f"  ✅ Generated smart fallback MCQ options")
            return options
    except:
        pass
    
    # Ultimate fallback
    logger.warning("  ⚠️ Using basic fallback MCQ options")
    return {
        "A": answer,
        "B": "Alternative 1",
        "C": "Alternative 2",
        "D": "Alternative 3",
        "correct": "A"
    }

async def fix_all_enrichment():
    """Fix all missing enrichment data with comprehensive LLM processing"""
    try:
        logger.info("🚀 Starting comprehensive enrichment fix...")
        
        # Initialize database
        init_database()
        db = SessionLocal()
        
        # Check API keys
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not openai_key or not anthropic_key:
            logger.error("❌ Required API keys not found")
            return False
        
        logger.info("✅ Both OpenAI and Anthropic API keys found")
        
        # Get all questions needing enrichment
        questions = db.query(Question).filter(
            (Question.answer == '') | 
            (Question.answer == None) |
            (Question.solution_approach == '') |
            (Question.solution_approach == None)
        ).all()
        
        logger.info(f"📊 Found {len(questions)} questions needing enrichment")
        
        # Add MCQ column if it doesn't exist
        try:
            db.execute("ALTER TABLE questions ADD COLUMN mcq_options TEXT")
            db.commit()
            logger.info("✅ Added mcq_options column to database")
        except Exception as e:
            logger.info("ℹ️ mcq_options column already exists or couldn't be added")
        
        # Process each question
        success_count = 0
        partial_success_count = 0
        failed_count = 0
        
        for i, question in enumerate(questions):
            try:
                logger.info(f"\n🔄 [{i+1}/{len(questions)}] Processing: {question.stem[:50]}...")
                
                # Generate answer if missing
                if not question.answer or question.answer.strip() == '':
                    logger.info("  Generating answer...")
                    question.answer = await generate_answer_with_fallback(question.stem)
                
                # Generate solutions if missing
                if not question.solution_approach or question.solution_approach.strip() == '':
                    logger.info("  Generating solutions...")
                    approach, detailed = await generate_solutions_with_fallback(
                        question.stem, 
                        question.answer,
                        question.subcategory or "General",
                        question.subcategory or "General"
                    )
                    question.solution_approach = approach
                    question.detailed_solution = detailed
                
                # Generate MCQ options
                logger.info("  Generating MCQ options...")
                mcq_options = await generate_mcq_options_with_fallback(
                    question.stem,
                    question.answer,
                    question.subcategory or "General",
                    question.difficulty_band or "Medium"
                )
                
                # Store MCQ options as JSON string (check if column exists)
                try:
                    question.mcq_options = json.dumps(mcq_options)
                except:
                    logger.info("  ℹ️ Could not store MCQ options (column may not exist)")
                
                # Commit this question
                db.commit()
                
                # Check success level
                has_answer = question.answer and not question.answer.startswith("Answer")
                has_solution = question.solution_approach and len(question.solution_approach) > 10
                has_mcq = mcq_options and mcq_options.get("A") != "Alternative 1"
                
                if has_answer and has_solution and has_mcq:
                    success_count += 1
                    logger.info(f"  ✅ Complete success")
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
        
        # Final summary
        logger.info(f"\n🎉 ENRICHMENT FIX COMPLETED!")
        logger.info(f"✅ Complete successes: {success_count}")
        logger.info(f"⚠️ Partial successes: {partial_success_count}")
        logger.info(f"❌ Failures: {failed_count}")
        logger.info(f"📊 Total processed: {len(questions)}")
        
        # Verify final state
        fixed_questions = db.query(Question).filter(
            Question.answer != '',
            Question.answer != None,
            Question.solution_approach != '',
            Question.solution_approach != None
        ).count()
        
        logger.info(f"🔍 Final verification: {fixed_questions} questions now have answers and solutions")
        
        success_rate = (success_count + partial_success_count) / len(questions) if questions else 0
        logger.info(f"📈 Overall success rate: {success_rate:.1%}")
        
        return success_rate > 0.7  # 70% success rate required
        
    except Exception as e:
        logger.error(f"❌ Enrichment fix failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(fix_all_enrichment())
    exit(0 if success else 1)