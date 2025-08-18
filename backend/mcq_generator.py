"""
Real-time MCQ Option Generator for CAT Preparation Platform
Generates misconception-based distractors as per specification
"""

import json
import uuid
from typing import Dict, List
from emergentintegrations.llm.chat import LlmChat, UserMessage
import logging

logger = logging.getLogger(__name__)

class MCQGenerator:
    def __init__(self, llm_api_key: str):
        self.llm_api_key = llm_api_key
        
        # Common misconceptions by subcategory
        self.misconception_patterns = {
            "Time–Speed–Distance (TSD)": [
                "Unit confusion (km/h vs m/s)",
                "Direction confusion in relative speed",
                "Adding instead of subtracting speeds",
                "Forgetting to convert units"
            ],
            "Percentages": [
                "Percentage of percentage errors",
                "Base value confusion",
                "Successive percentage miscalculation",
                "Direct addition instead of compounding"
            ],
            "Linear Equations": [
                "Sign errors in equation manipulation",
                "Coefficient confusion",
                "Substitution errors",
                "Cross-multiplication mistakes"
            ],
            "Profit–Loss–Discount (PLD)": [
                "Cost price vs selling price confusion",
                "Successive discount calculation errors", 
                "Markup vs margin confusion",
                "Percentage calculation base errors"
            ],
            "Time & Work": [
                "Rate vs work confusion",
                "Combined work calculation errors",
                "Pipe and cistern direction confusion",
                "Efficiency ratio miscalculation"
            ]
        }
    
    async def generate_options(self, question_stem: str, subcategory: str, difficulty_band: str, correct_answer: str = None) -> Dict[str, str]:
        """
        Generate 4 MCQ options with misconception-based distractors
        Returns: {"A": "option1", "B": "option2", "C": "option3", "D": "option4", "correct": "B"}
        """
        try:
            # Get relevant misconceptions for this subcategory
            misconceptions = self.misconception_patterns.get(
                subcategory, 
                ["Calculation errors", "Unit mistakes", "Sign errors", "Formula confusion"]
            )
            
            system_message = f"""You are an expert CAT math tutor creating multiple choice questions. Generate 4 realistic mathematical options for the given question with exactly 1 correct answer and 3 carefully crafted wrong answers.

DISTRACTOR STRATEGY for {subcategory}:
Use these common misconceptions:
{json.dumps(misconceptions, indent=2)}

RULES:
1. Generate exactly 4 numerical/mathematical options
2. Make wrong answers plausible but incorrect based on common student errors
3. Ensure options are distinct values  
4. Match the difficulty level: {difficulty_band}
5. Return ONLY valid JSON, no other text

REQUIRED JSON FORMAT:
{{
  "option_a": "actual mathematical answer/value",
  "option_b": "actual mathematical answer/value", 
  "option_c": "actual mathematical answer/value",
  "option_d": "actual mathematical answer/value",
  "correct_label": "A"
}}"""

            chat = LlmChat(
                api_key=self.llm_api_key,
                session_id=f"mcq_gen_{uuid.uuid4()}",
                system_message=system_message
            ).with_model("openai", "gpt-4o-mini")

            prompt = f"""Question: {question_stem.strip()}
Correct Answer: {correct_answer}
Sub-category: {subcategory}
Difficulty: {difficulty_band}

Generate 4 MCQ options where one matches the correct answer and three are plausible wrong answers based on common mistakes. Return ONLY the JSON object."""

            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            logger.info(f"MCQ LLM raw response: {response}")
            
            # Clean the response - remove any extra text before/after JSON
            response_clean = response.strip()
            
            # Find JSON object in response
            start_idx = response_clean.find('{')
            end_idx = response_clean.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_clean[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Validate required fields
                required_fields = ["option_a", "option_b", "option_c", "option_d", "correct_label"]
                if all(field in result for field in required_fields):
                    # Format for return
                    options = {
                        "A": result["option_a"],
                        "B": result["option_b"], 
                        "C": result["option_c"],
                        "D": result["option_d"],
                        "correct": result["correct_label"].upper()
                    }
                    
                    logger.info(f"MCQ options generated successfully: {options}")
                    return options
                else:
                    logger.warning(f"MCQ response missing required fields: {result}")
                    raise ValueError("Missing required fields in LLM response")
            else:
                logger.warning(f"No valid JSON found in MCQ response: {response}")
                raise ValueError("No valid JSON in LLM response")
            
        except Exception as e:
            logger.error(f"Error generating MCQ options: {e}")
            logger.error(f"LLM response was: {response if 'response' in locals() else 'No response'}")
            
            # Generate better fallback options based on the correct answer
            if correct_answer:
                try:
                    # Try to generate numerical variations of the correct answer
                    fallback_options = self.generate_fallback_options(correct_answer, subcategory)
                    logger.info(f"Using fallback options: {fallback_options}")
                    return fallback_options
                except:
                    pass
            
            # Raise exception to let server's enhanced fallback handle it
            raise Exception("MCQ generation failed, using server fallback")
    
    def generate_fallback_options(self, correct_answer: str, subcategory: str) -> Dict[str, str]:
        """Generate mathematical fallback options based on correct answer"""
        try:
            # Try to extract numerical value from correct answer
            import re
            numbers = re.findall(r'-?\d+\.?\d*', correct_answer)
            
            if numbers:
                base_value = float(numbers[0])
                
                # Generate plausible wrong answers
                variations = [
                    base_value,  # correct
                    base_value * 2,  # common doubling error
                    base_value / 2,  # common halving error
                    base_value + 1   # off-by-one error
                ]
                
                # Shuffle and format
                import random
                random.shuffle(variations)
                
                options = {
                    "A": str(int(variations[0]) if variations[0].is_integer() else variations[0]),
                    "B": str(int(variations[1]) if variations[1].is_integer() else variations[1]),
                    "C": str(int(variations[2]) if variations[2].is_integer() else variations[2]),
                    "D": str(int(variations[3]) if variations[3].is_integer() else variations[3])
                }
                
                # Find which option matches the correct answer
                correct_key = "A"
                for key, value in options.items():
                    if value == str(int(base_value) if base_value.is_integer() else base_value):
                        correct_key = key
                        break
                
                options["correct"] = correct_key
                return options
            
        except Exception as e:
            logger.error(f"Error generating fallback options: {e}")
        
        return {
            "A": correct_answer,
            "B": "Alternative answer 1",
            "C": "Alternative answer 2", 
            "D": "Alternative answer 3",
            "correct": "A"
        }
    
    async def generate_shuffled_options(self, question_stem: str, correct_answer: str, 
                                      subcategory: str = "General") -> Dict[str, str]:
        """
        Generate MCQ options with v1.3 shuffling requirements
        Always shuffle non-correct options; correct answer position randomized
        """
        try:
            # Generate basic options first
            basic_options = await self.generate_options(question_stem, correct_answer, subcategory)
            
            # Apply v1.3 shuffling logic
            shuffled_options = self.shuffle_options_v13(basic_options)
            
            return shuffled_options
            
        except Exception as e:
            logger.error(f"Error generating shuffled options: {e}")
            return self.get_fallback_shuffled_options(correct_answer)
    
    def shuffle_options_v13(self, options: Dict[str, str]) -> Dict[str, str]:
        """
        Apply v1.3 shuffling rules:
        - Always shuffle non-correct options
        - Randomize correct answer position
        """
        import random
        
        try:
            # Extract the correct answer value
            correct_label = options["correct"]
            correct_value = options[correct_label]
            
            # Get all option values
            all_values = [options["A"], options["B"], options["C"], options["D"]]
            
            # Remove correct answer from list for shuffling
            incorrect_values = [v for v in all_values if v != correct_value]
            
            # Shuffle the incorrect options
            random.shuffle(incorrect_values)
            
            # Randomly choose position for correct answer (0-3)
            correct_position = random.randint(0, 3)
            
            # Build new option list with correct answer in random position
            final_values = []
            incorrect_index = 0
            
            for i in range(4):
                if i == correct_position:
                    final_values.append(correct_value)
                else:
                    final_values.append(incorrect_values[incorrect_index])
                    incorrect_index += 1
            
            # Create final options dict
            labels = ["A", "B", "C", "D"]
            shuffled_options = {}
            
            for i, label in enumerate(labels):
                shuffled_options[label] = final_values[i]
            
            # Set correct label
            shuffled_options["correct"] = labels[correct_position]
            
            logger.info(f"Shuffled options - correct answer now at position {labels[correct_position]}")
            return shuffled_options
            
        except Exception as e:
            logger.error(f"Error in v1.3 shuffling: {e}")
            return options  # Return original if shuffling fails
    
    def get_fallback_shuffled_options(self, correct_answer: str) -> Dict[str, str]:
        """
        Provide fallback shuffled options when generation fails
        """
        import random
        
        # Generate plausible incorrect options
        fallback_options = [
            f"Incorrect option 1",
            f"Incorrect option 2", 
            f"Incorrect option 3"
        ]
        
        # Insert correct answer at random position
        correct_position = random.randint(0, 3)
        all_options = fallback_options.copy()
        all_options.insert(correct_position, correct_answer)
        
        # Build options dict
        labels = ["A", "B", "C", "D"]
        options = {}
        
        for i, label in enumerate(labels):
            options[label] = all_options[i]
        
        options["correct"] = labels[correct_position]
        
        return options