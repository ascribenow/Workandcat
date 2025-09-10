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