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
            
            system_message = f"""You are an expert CAT question option generator. Generate 4 multiple choice options for the given question with exactly 1 correct answer and 3 carefully crafted distractors.

DISTRACTOR STRATEGY:
Use these common misconceptions for {subcategory}:
{json.dumps(misconceptions, indent=2)}

RULES:
1. Generate exactly 4 options
2. Make distractors plausible but incorrect
3. Base distractors on common student errors and misconceptions
4. Ensure one option is clearly correct
5. Avoid obviously wrong or silly options
6. Match the difficulty level: {difficulty_band}

RETURN FORMAT:
{{
  "option_a": "first option",
  "option_b": "second option", 
  "option_c": "third option",
  "option_d": "fourth option",
  "correct_label": "A|B|C|D"
}}"""

            chat = LlmChat(
                api_key=self.llm_api_key,
                session_id=f"mcq_gen_{uuid.uuid4()}",
                system_message=system_message
            ).with_model("openai", "gpt-4o-mini")

            prompt = f"""Question: {question_stem}
Sub-category: {subcategory}
Difficulty: {difficulty_band}

Generate 4 MCQ options with misconception-based distractors."""

            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse response
            result = json.loads(response)
            
            # Format for return
            options = {
                "A": result.get("option_a", "Option A"),
                "B": result.get("option_b", "Option B"), 
                "C": result.get("option_c", "Option C"),
                "D": result.get("option_d", "Option D"),
                "correct": result.get("correct_label", "A")
            }
            
            return options
            
        except Exception as e:
            logger.error(f"Error generating MCQ options: {e}")
            # Return fallback options
            return {
                "A": "Option A",
                "B": "Option B",
                "C": "Option C", 
                "D": "Option D",
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