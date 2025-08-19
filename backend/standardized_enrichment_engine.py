#!/usr/bin/env python3
"""
Standardized Enrichment Engine - Automatic, consistent LLM enrichment using the schema directive
NO MORE MANUAL SCRIPTS - This handles all enrichment automatically with quality control
"""

import os
import json
import logging
import asyncio
from typing import Tuple, Dict, Any, Optional
from dotenv import load_dotenv
from enrichment_schema_manager import enrichment_schema, quality_controller

logger = logging.getLogger(__name__)

class StandardizedEnrichmentEngine:
    """
    Automatic enrichment engine that enforces the schema directive
    Handles all LLM interactions with built-in quality control
    """
    
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY') 
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize quality controller
        quality_controller.anthropic_api_key = self.anthropic_api_key
        
        logger.info("🎯 Standardized Enrichment Engine Initialized")
        logger.info(f"   Google Gemini: {'✅' if self.google_api_key else '❌'}")
        logger.info(f"   OpenAI: {'✅' if self.openai_api_key else '❌'}")
        logger.info(f"   Anthropic (QC): {'✅' if self.anthropic_api_key else '❌'}")

    async def enrich_question_solution(self, question_stem: str, answer: str, 
                                     subcategory: str, question_type: str = "") -> Dict[str, Any]:
        """
        Main enrichment method - automatically follows schema directive
        Returns high-quality, consistent solutions with built-in quality control
        """
        logger.info(f"🔄 Enriching: {question_stem[:60]}...")
        logger.info(f"📂 Category: {subcategory} -> {question_type}")
        
        # Try primary LLMs with schema enforcement
        enrichment_result = await self._enrich_with_schema_compliance(
            question_stem, answer, subcategory, question_type
        )
        
        if enrichment_result["success"]:
            logger.info(f"✅ Enrichment successful with quality score: {enrichment_result.get('quality_score', 'N/A')}")
            return enrichment_result
        else:
            logger.error(f"❌ Enrichment failed: {enrichment_result.get('error', 'Unknown error')}")
            return self._generate_fallback_solution(question_stem, answer, subcategory)

    async def _enrich_with_schema_compliance(self, question_stem: str, answer: str, 
                                           subcategory: str, question_type: str) -> Dict[str, Any]:
        """
        Enrich with automatic schema compliance and quality validation
        """
        
        # Primary: Google Gemini with schema directive
        if self.google_api_key:
            try:
                logger.info("  🎯 Trying Google Gemini with schema directive...")
                result = await self._enrich_with_gemini_schema(question_stem, answer, subcategory, question_type)
                if result["success"]:
                    return result
            except Exception as e:
                logger.warning(f"  ❌ Google Gemini failed: {e}")
        
        # Fallback: OpenAI with schema directive
        if self.openai_api_key:
            try:
                logger.info("  🎯 Trying OpenAI with schema directive...")
                result = await self._enrich_with_openai_schema(question_stem, answer, subcategory, question_type)
                if result["success"]:
                    return result
            except Exception as e:
                logger.warning(f"  ❌ OpenAI failed: {e}")
        
        return {"success": False, "error": "All LLM enrichment methods failed"}

    async def _enrich_with_gemini_schema(self, question_stem: str, answer: str, 
                                       subcategory: str, question_type: str) -> Dict[str, Any]:
        """
        Enrich using Google Gemini with embedded schema directive
        """
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Get schema-compliant system prompt
        system_prompt = enrichment_schema.get_enrichment_system_prompt(subcategory, question_type)
        
        chat = LlmChat(
            api_key=self.google_api_key,
            session_id="standardized_enrichment",
            system_message=system_prompt
        ).with_model("gemini", "gemini-2.0-flash")
        
        user_prompt = f"""Question: {question_stem}

Correct Answer: {answer}

Create a complete solution following the EXACT three-section schema:

**APPROACH:**
[2-3 sentences: exam strategy tip, highlight entry point, no answer reveal]

**DETAILED SOLUTION:**
**Step 1:** [First step with clear reasoning]
**Step 2:** [Continue with logical progression]
**Step 3:** [Show calculations systematically]
**Step N:** [Final verification]
**✅ Final Answer: {answer}**

**EXPLANATION:**
[1-2 sentences: big-picture takeaway, exam tip for similar problems]

CRITICAL: Follow the schema EXACTLY. All three sections are mandatory."""
        
        user_message = UserMessage(text=user_prompt)
        response = await chat.send_message(user_message)
        
        # Validate response against schema
        validation = enrichment_schema.validate_enrichment_output(response)
        
        if validation["is_valid"]:
            # Optional: Anthropic quality control validation
            anthropic_validation = await quality_controller.validate_with_anthropic(
                question_stem, answer, 
                validation["approach"], 
                validation["detailed_solution"], 
                validation["explanation"]
            )
            
            # Format final solution
            final_approach, final_detailed = enrichment_schema.format_final_solution(
                validation["approach"], validation["detailed_solution"], validation["explanation"]
            )
            
            return {
                "success": True,
                "approach": final_approach,
                "detailed_solution": final_detailed,
                "validation": validation,
                "anthropic_validation": anthropic_validation,
                "quality_score": anthropic_validation.get("quality_score", 8),
                "llm_used": "Google Gemini"
            }
        else:
            logger.warning(f"  ⚠️ Gemini output failed schema validation: {validation['issues']}")
            return {"success": False, "error": "Schema validation failed", "issues": validation["issues"]}

    async def _enrich_with_openai_schema(self, question_stem: str, answer: str, 
                                       subcategory: str, question_type: str) -> Dict[str, Any]:
        """
        Enrich using OpenAI with embedded schema directive
        """
        import openai
        
        client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Get schema-compliant system prompt
        system_prompt = enrichment_schema.get_enrichment_system_prompt(subcategory, question_type)
        
        user_prompt = f"""Question: {question_stem}

Correct Answer: {answer}

Create a complete solution following the EXACT three-section schema:

**APPROACH:**
[2-3 sentences: exam strategy tip, highlight entry point, no answer reveal]

**DETAILED SOLUTION:**
**Step 1:** [First step with clear reasoning]
**Step 2:** [Continue with logical progression] 
**Step 3:** [Show calculations systematically]
**Step N:** [Final verification]
**✅ Final Answer: {answer}**

**EXPLANATION:**
[1-2 sentences: big-picture takeaway, exam tip for similar problems]

CRITICAL: Follow the schema EXACTLY. All three sections are mandatory."""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Validate response against schema
        validation = enrichment_schema.validate_enrichment_output(response_text)
        
        if validation["is_valid"]:
            # Optional: Anthropic quality control validation
            anthropic_validation = await quality_controller.validate_with_anthropic(
                question_stem, answer,
                validation["approach"],
                validation["detailed_solution"], 
                validation["explanation"]
            )
            
            # Format final solution
            final_approach, final_detailed = enrichment_schema.format_final_solution(
                validation["approach"], validation["detailed_solution"], validation["explanation"]
            )
            
            return {
                "success": True,
                "approach": final_approach,
                "detailed_solution": final_detailed,
                "validation": validation,
                "anthropic_validation": anthropic_validation,
                "quality_score": anthropic_validation.get("quality_score", 8),
                "llm_used": "OpenAI GPT-4o"
            }
        else:
            logger.warning(f"  ⚠️ OpenAI output failed schema validation: {validation['issues']}")
            return {"success": False, "error": "Schema validation failed", "issues": validation["issues"]}

    def _generate_fallback_solution(self, question_stem: str, answer: str, subcategory: str) -> Dict[str, Any]:
        """
        Generate fallback solution that still follows the schema
        """
        logger.info("  🔄 Generating schema-compliant fallback solution...")
        
        # Create schema-compliant fallback
        approach = f"Identify the key {subcategory} concept in this problem and apply the standard solution method systematically. Look for the mathematical pattern or formula that directly addresses what the question is asking."
        
        detailed_solution = f"""**Step 1:** Analyze the given information and identify what needs to be found.
Review the question carefully to understand the mathematical relationship involved.

**Step 2:** Apply the appropriate {subcategory} method or formula.
Use the standard approach for this type of problem to set up the solution.

**Step 3:** Perform the calculations systematically.
Work through each calculation step-by-step to ensure accuracy.

**Step 4:** Verify the result makes sense in the problem context.
**✅ Final Answer: {answer}**

**KEY INSIGHT:**
This {subcategory} problem demonstrates the importance of systematic application of mathematical principles to reach the correct solution efficiently."""
        
        return {
            "success": True,
            "approach": approach,
            "detailed_solution": detailed_solution,
            "validation": {"is_valid": True, "fallback_used": True},
            "quality_score": 6,  # Lower score for fallback
            "llm_used": "Schema-compliant fallback"
        }

    async def generate_mcq_options_with_schema(self, question_stem: str, answer: str, 
                                             subcategory: str) -> Dict[str, Any]:
        """
        Generate MCQ options following quality standards
        """
        logger.info("  🎯 Generating MCQ options with quality control...")
        
        if self.google_api_key:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                
                chat = LlmChat(
                    api_key=self.google_api_key,
                    session_id="mcq_generation",
                    system_message=f"""You are an expert CAT question creator. Generate exactly 3 plausible wrong answers.

QUALITY STANDARDS:
- Create wrong answers that look reasonable but are incorrect
- Base on common student calculation errors for {subcategory} problems
- Make sure all values are distinct from the correct answer
- Use realistic numerical values that could arise from the problem

Return ONLY valid JSON:
{{
  "wrong_answer_1": "plausible incorrect value",
  "wrong_answer_2": "plausible incorrect value", 
  "wrong_answer_3": "plausible incorrect value"
}}"""
                ).with_model("gemini", "gemini-2.0-flash")
                
                user_message = UserMessage(text=f"""Question: {question_stem}
Correct Answer: {answer}
Subcategory: {subcategory}

Generate 3 plausible wrong answers. Return ONLY the JSON object.""")
                
                response = await chat.send_message(user_message)
                
                # Extract and validate JSON
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    result = json.loads(json_str)
                    
                    if all(field in result for field in ["wrong_answer_1", "wrong_answer_2", "wrong_answer_3"]):
                        wrong_answers = [
                            result["wrong_answer_1"],
                            result["wrong_answer_2"], 
                            result["wrong_answer_3"]
                        ]
                        
                        # Randomize placement
                        mcq_options = self._randomize_mcq_placement(answer, wrong_answers)
                        logger.info(f"  ✅ Generated MCQ options (correct: {mcq_options['correct']})")
                        return mcq_options
                        
            except Exception as e:
                logger.warning(f"  ❌ MCQ generation failed: {e}")
        
        # Smart fallback
        return self._generate_smart_mcq_fallback(answer)

    def _randomize_mcq_placement(self, correct_answer: str, wrong_answers: list) -> Dict[str, str]:
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

    def _generate_smart_mcq_fallback(self, answer: str) -> Dict[str, str]:
        """Generate smart fallback MCQ options"""
        import re
        
        try:
            # Extract numbers from answer
            numbers = re.findall(r'-?\d+\.?\d*', answer)
            if numbers:
                base_value = float(numbers[0])
                wrong_answers = [
                    str(int(base_value * 2) if (base_value * 2).is_integer() else base_value * 2),
                    str(int(base_value / 2) if base_value != 0 and (base_value / 2).is_integer() else base_value / 2 if base_value != 0 else base_value + 1),
                    str(int(base_value + 1) if (base_value + 1).is_integer() else base_value + 1)
                ]
            else:
                wrong_answers = ["Alternative Option 1", "Alternative Option 2", "Alternative Option 3"]
                
            return self._randomize_mcq_placement(answer, wrong_answers)
            
        except:
            wrong_answers = ["Option 1", "Option 2", "Option 3"]
            return self._randomize_mcq_placement(answer, wrong_answers)

# Singleton instance for global use
standardized_enricher = StandardizedEnrichmentEngine()