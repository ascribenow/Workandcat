"""
Anchor Writer V1 Service
Generates and normalizes skill anchors for questions using OpenAI GPT-4o-mini
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()

logger = logging.getLogger(__name__)

ANCHOR_WRITER_SYSTEM_PROMPT = """
You are Anchor Writer v1.
Pick the 1–2 decisive skills (ANCHORS) needed to solve the question.
• 1–2 phrases, lowercase, 1–3 words, no punctuation.
• Prefer precise skills ("relative speed", "ratio scaling", "unit conversion").
• Avoid broad stoplist: arithmetic, algebra, numbers, calculation, proportion, percentage, geometry, mensuration, equation, word problems, time, speed, distance.
• Map patterns: meeting/chasing→"relative speed"; mixture/alligation→"mixture balance"; pipes/cisterns→"flow rate"; divisibility/LCM/GCD→"number properties"; % change/P&L→"percentage change"/"profit and loss"; SI/CI→"interest calculation"; km/h↔m/s→"unit conversion".
• Prefer from: problem_structure → operations_required → core_concepts/concept_keywords; else infer from stem/solution.
Return JSON only:
{"question_id":"<uuid>","anchors":["<a1>","<a2 optional>"]}.
"""

class AnchorWriterV1:
    def __init__(self):
        self.api_key = os.getenv('EMERGENT_LLM_KEY') or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("Neither EMERGENT_LLM_KEY nor OPENAI_API_KEY found in environment variables")
    
    async def generate_anchors(self, question_data: Dict) -> List[str]:
        """
        Generate anchors with belt-and-suspenders normalization
        """
        question_id = question_data.get('id') or question_data.get('question_id', 'unknown')
        
        try:
            # Initialize LLM chat
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"anchor_writer_{question_id}",
                system_message=ANCHOR_WRITER_SYSTEM_PROMPT
            ).with_model("openai", "gpt-4o-mini")
            
            # Create user message with question data
            user_payload = {
                "question_id": question_id,
                "subcategory": question_data.get('subcategory', ''),
                "type_of_question": question_data.get('type_of_question', ''),
                "problem_structure": question_data.get('problem_structure', ''),
                "operations_required": question_data.get('operations_required', []),
                "core_concepts": question_data.get('core_concepts', []),
                "concept_keywords": question_data.get('concept_keywords', []),
                "stem": question_data.get('stem', ''),
                "solution_approach": question_data.get('solution_approach', ''),
                "detailed_solution": question_data.get('detailed_solution', ''),
                "principle_to_remember": question_data.get('principle_to_remember', ''),
                "difficulty_band": question_data.get('difficulty_band', ''),
                "pyq_frequency_score": question_data.get('pyq_frequency_score', 0)
            }
            
            user_message = UserMessage(text=json.dumps(user_payload, indent=2))
            
            # Get response from LLM
            response_text = await chat.send_message(user_message)
            
            # Parse JSON response
            try:
                response_json = json.loads(response_text)
                anchors = response_json.get("anchors", [])
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group(1))
                    anchors = response_json.get("anchors", [])
                else:
                    logger.warning(f"Failed to parse JSON response for question {question_id}")
                    return []
            
            # FIXED: Normalize anchors before save (belt-and-suspenders)
            anchors = [a.strip().lower() for a in anchors if a and isinstance(a, str)]
            anchors = list(dict.fromkeys(anchors))[:2]  # Keep order, dedupe, max 2
            
            logger.info(f"Generated anchors for {question_id}: {anchors}")
            return anchors
            
        except Exception as e:
            logger.error(f"Failed to generate anchors for question {question_id}: {e}")
            return []
    
    async def generate_anchors_batch(self, questions: List[Dict], batch_size: int = 5) -> Dict[str, List[str]]:
        """
        Generate anchors for multiple questions in batches to avoid rate limits
        """
        results = {}
        
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i+batch_size]
            batch_tasks = []
            
            for question in batch:
                question_id = question.get('id') or question.get('question_id', 'unknown')
                task = self.generate_anchors(question)
                batch_tasks.append((question_id, task))
            
            # Execute batch
            for question_id, task in batch_tasks:
                try:
                    anchors = await task
                    results[question_id] = anchors
                except Exception as e:
                    logger.error(f"Failed to generate anchors for {question_id}: {e}")
                    results[question_id] = []
            
            # Small delay between batches to respect rate limits
            if i + batch_size < len(questions):
                await asyncio.sleep(1)
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(questions) + batch_size - 1)//batch_size}")
        
        return results

# Test function for anchor generation
async def test_anchor_generation():
    """Test the anchor writer with a sample question"""
    writer = AnchorWriterV1()
    
    sample_question = {
        "id": "test-123",
        "subcategory": "Time and Speed",
        "type_of_question": "Application Problem",
        "stem": "Two trains are moving in opposite directions at speeds of 60 km/h and 80 km/h. If they meet after 2 hours, what was the initial distance between them?",
        "solution_approach": "Use relative speed concept for trains moving in opposite directions",
        "difficulty_band": "medium",
        "core_concepts": ["relative speed", "distance calculation"],
        "operations_required": ["addition", "multiplication"]
    }
    
    anchors = await writer.generate_anchors(sample_question)
    print(f"Generated anchors: {anchors}")
    return anchors

if __name__ == "__main__":
    asyncio.run(test_anchor_generation())