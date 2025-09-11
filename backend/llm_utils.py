#!/usr/bin/env python3
"""
LLM Utility Functions
Shared utilities for LLM calls across enrichment services
"""

import os
import logging
import openai
import google.generativeai as genai

logger = logging.getLogger(__name__)

def extract_json_from_response(response_text: str) -> str:
    """Extract JSON from LLM response, handling markdown code blocks"""
    response_text = response_text.strip()
    
    # Handle JSON wrapped in markdown code blocks
    if "```json" in response_text:
        start_idx = response_text.find("```json") + 7
        end_idx = response_text.find("```", start_idx)
        if end_idx > start_idx:
            return response_text[start_idx:end_idx].strip()
    elif "```" in response_text:
        # Handle generic code blocks
        start_idx = response_text.find("```") + 3
        end_idx = response_text.find("```", start_idx)
        if end_idx > start_idx:
            return response_text[start_idx:end_idx].strip()
    
    # Return as-is if no code blocks found
    return response_text

async def calculate_pyq_frequency_score_llm(service_instance, regular_question_data: dict, qualifying_pyq_questions: list) -> float:
    """
    Calculate PYQ frequency score using LLM-based semantic comparison
    
    Args:
        service_instance: Enrichment service instance with LLM configuration
        regular_question_data: Dict with stem, problem_structure, concept_keywords, category, subcategory
        qualifying_pyq_questions: List of PYQ questions filtered by difficulty_score > 1.5 AND category×subcategory match
        
    Returns:
        float: 0.5 (0 matches), 1.0 (1-3 matches), or 1.5 (>3 matches)
    """
    try:
        logger.info(f"🧠 Starting LLM-based PYQ frequency calculation for {len(qualifying_pyq_questions)} category-filtered PYQs")
        logger.info(f"🎯 Category: {regular_question_data.get('category')}, Subcategory: {regular_question_data.get('subcategory')}")
        
        # Handle case where no qualifying PYQ questions found
        if not qualifying_pyq_questions or len(qualifying_pyq_questions) == 0:
            logger.warning("⚠️ No qualifying PYQ questions found for category×subcategory combination")
            return 0.5  # Default to LOW
        
        # Prepare system prompt for LLM
        system_message = """You are a mathematical concept similarity expert. Your task is to compare a regular question against PYQ questions and count semantic matches.

COMPARISON CRITERIA:
- Evaluate >50% semantic similarity of (problem_structure × concept_keywords)
- Focus on mathematical concepts, solution approaches, and problem patterns
- Count only questions that have substantial conceptual overlap
- All PYQ questions are already filtered to same category×subcategory as the regular question

For each PYQ question, respond with "MATCH" or "NO_MATCH" based on whether there is >50% semantic similarity.

Return your analysis in JSON format:
{
  "total_matches": <number>,
  "pyq_analysis": [
    {"pyq_index": 1, "result": "MATCH/NO_MATCH", "reasoning": "brief explanation"},
    {"pyq_index": 2, "result": "MATCH/NO_MATCH", "reasoning": "brief explanation"}
  ]
}"""

        # Prepare user message with question data
        user_message = f"""REGULAR QUESTION TO COMPARE:
Stem: {regular_question_data.get('stem', '')}
Category: {regular_question_data.get('category', '')}
Subcategory: {regular_question_data.get('subcategory', '')}
Problem Structure: {regular_question_data.get('problem_structure', '')}
Concept Keywords: {regular_question_data.get('concept_keywords', '')}

PYQ QUESTIONS TO COMPARE AGAINST (difficulty_score > 1.5, same category×subcategory):
"""

        # Add ALL qualifying PYQ questions to comparison (no limit, no scaling)
        for i, pyq in enumerate(qualifying_pyq_questions, 1):
            user_message += f"""
PYQ {i}:
Stem: {pyq.get('stem', '')}
Problem Structure: {pyq.get('problem_structure', '')}
Concept Keywords: {pyq.get('concept_keywords', '')}
"""

        user_message += f"\nAnalyze semantic similarity between the regular question and each of the {len(qualifying_pyq_questions)} PYQ questions. Count total matches where similarity >50%."

        # Call LLM using existing fallback mechanism
        response_text, model_used = await call_llm_with_fallback(
            service_instance, system_message, user_message, max_tokens=2000, temperature=0.1
        )
        
        if not response_text:
            logger.error("❌ LLM returned empty response for PYQ frequency calculation")
            return 0.5  # Default to LOW
        
        # Parse LLM response
        import json
        clean_json = extract_json_from_response(response_text)
        llm_analysis = json.loads(clean_json)
        
        # Use raw matches (no scaling)
        total_matches = int(llm_analysis.get('total_matches', 0))
        
        # Convert to categorical score
        if total_matches == 0:
            pyq_frequency_score = 0.5  # LOW
        elif total_matches <= 3:
            pyq_frequency_score = 1.0  # MEDIUM
        else:
            pyq_frequency_score = 1.5  # HIGH
        
        logger.info(f"✅ LLM PYQ frequency calculation completed with {model_used}")
        logger.info(f"🎯 Found {total_matches} raw matches (no scaling) → Score: {pyq_frequency_score}")
        logger.info(f"📊 Processed {len(qualifying_pyq_questions)} category-filtered PYQ questions")
        
        return pyq_frequency_score
        
    except Exception as e:
        logger.error(f"❌ LLM PYQ frequency calculation failed: {e}")
        return 0.5  # Default to LOW on error

async def call_llm_with_fallback(service_instance, system_message: str, user_message: str, max_tokens: int = 800, temperature: float = 0.1) -> tuple[str, str]:
    """
    Call LLM with fallback logic: OpenAI → Gemini
    Returns: (response_text, model_used)
    """
    # Try OpenAI first
    try:
        client = openai.OpenAI(api_key=service_instance.openai_api_key)
        
        # Try primary model first
        model_to_use = service_instance.primary_model
        if service_instance.primary_model_failures >= service_instance.max_failures_before_degradation:
            model_to_use = service_instance.fallback_model
            
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=service_instance.timeout
        )
        
        response_text = response.choices[0].message.content.strip()
        if response_text:
            # Reset failure count on success
            service_instance.openai_consecutive_failures = 0
            return response_text, f"openai-{model_to_use}"
        else:
            raise Exception("Empty response from OpenAI")
            
    except Exception as openai_error:
        logger.warning(f"⚠️ OpenAI failed: {str(openai_error)[:100]}...")
        service_instance.openai_consecutive_failures += 1
        
        # If OpenAI fails too many times, try Gemini
        if service_instance.openai_consecutive_failures >= service_instance.max_openai_failures_before_gemini:
            if service_instance.google_api_key:
                try:
                    logger.info("🔄 Falling back to Google Gemini...")
                    
                    # Initialize Gemini model
                    model = genai.GenerativeModel(service_instance.gemini_model)
                    
                    # Combine system and user messages for Gemini
                    combined_prompt = f"{system_message}\n\nUser Request: {user_message}"
                    
                    response = model.generate_content(
                        combined_prompt,
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=max_tokens,
                            temperature=temperature,
                        )
                    )
                    
                    response_text = response.text.strip()
                    if response_text:
                        logger.info("✅ Gemini fallback successful")
                        return response_text, f"gemini-{service_instance.gemini_model}"
                    else:
                        raise Exception("Empty response from Gemini")
                        
                except Exception as gemini_error:
                    logger.error(f"❌ Gemini fallback also failed: {str(gemini_error)[:100]}...")
                    raise Exception(f"Both OpenAI and Gemini failed. OpenAI: {str(openai_error)[:50]}, Gemini: {str(gemini_error)[:50]}")
            else:
                raise Exception(f"OpenAI failed and no Gemini fallback available: {str(openai_error)}")
        else:
            # Re-raise OpenAI error if we haven't hit the fallback threshold
            raise openai_error