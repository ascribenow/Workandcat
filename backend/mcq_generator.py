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
    
    def shuffle_options(self, options: Dict[str, str]) -> Dict[str, str]:
        """Shuffle option labels A-D"""
        import random
        
        # Extract options and correct answer
        option_values = [options["A"], options["B"], options["C"], options["D"]]
        correct_value = options[options["correct"]]
        
        # Shuffle
        random.shuffle(option_values)
        
        # Rebuild with shuffled positions
        shuffled = {
            "A": option_values[0],
            "B": option_values[1], 
            "C": option_values[2],
            "D": option_values[3]
        }
        
        # Find new position of correct answer
        for label, value in shuffled.items():
            if value == correct_value:
                shuffled["correct"] = label
                break
        
        return shuffled