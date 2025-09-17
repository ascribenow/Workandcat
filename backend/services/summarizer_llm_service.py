"""
Summarizer LLM Service - Dedicated service for post-session analytics
Uses GPT-4o as primary and Gemini as fallback for concept analysis
"""

import os
import json
import logging
import openai
import google.generativeai as genai
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

class SummarizerLLMService:
    """Dedicated LLM service for post-session summarization and analytics"""
    
    def __init__(self):
        # Load environment variables (same pattern as working services)
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize API keys
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not self.openai_api_key:
            logger.error("❌ Summarizer LLM: OpenAI API key not found")
            raise ValueError("OPENAI_API_KEY environment variable required for summarizer")
        
        # Model configuration (GPT-4o primary + Gemini fallback pattern)
        self.primary_model = "gpt-4o-mini"
        self.fallback_model = "gemini-1.5-pro"
        
        # Initialize Google AI if key available
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)
            logger.info("✅ Summarizer LLM: Google Gemini configured as fallback")
        else:
            logger.warning("⚠️ Summarizer LLM: Google API key not found - no Gemini fallback")
        
        if self.openai_api_key:
            logger.info("✅ Summarizer LLM: OpenAI configured as primary")
        else:
            logger.warning("⚠️ Summarizer LLM: OpenAI API key not found")
    
    async def call_for_concept_analysis(self, system_prompt: str, user_payload: Dict[str, Any]) -> Tuple[str, str]:
        """
        Call LLM for concept analysis with GPT-4o primary, Gemini fallback
        
        Returns:
            (response_text, model_used)
        """
        user_message = json.dumps(user_payload, indent=2)
        
        # Try OpenAI first (GPT-4o)
        if self.openai_api_key:
            try:
                logger.info("🔄 Summarizer LLM: Trying OpenAI GPT-4o...")
                
                client = openai.OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model=self.primary_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.1,
                    max_tokens=2000,
                    timeout=30
                )
                
                response_text = response.choices[0].message.content
                logger.info("✅ Summarizer LLM: OpenAI GPT-4o successful")
                return response_text, f"openai-{self.primary_model}"
                
            except Exception as openai_error:
                logger.warning(f"⚠️ Summarizer LLM: OpenAI failed: {str(openai_error)[:100]}...")
                
                # Try Gemini fallback
                if self.google_api_key:
                    try:
                        logger.info("🔄 Summarizer LLM: Falling back to Google Gemini...")
                        
                        model = genai.GenerativeModel(self.fallback_model)
                        combined_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_message}"
                        
                        response = model.generate_content(
                            combined_prompt,
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.1,
                                max_output_tokens=2000
                            )
                        )
                        
                        response_text = response.text
                        logger.info("✅ Summarizer LLM: Gemini fallback successful")
                        return response_text, f"gemini-{self.fallback_model}"
                        
                    except Exception as gemini_error:
                        logger.error(f"❌ Summarizer LLM: Both OpenAI and Gemini failed")
                        raise Exception(f"Summarizer LLM failed: OpenAI: {str(openai_error)[:50]}, Gemini: {str(gemini_error)[:50]}")
                else:
                    raise Exception(f"Summarizer LLM failed: OpenAI: {str(openai_error)[:100]}, No Gemini fallback")
        else:
            raise Exception("Summarizer LLM: No OpenAI API key configured")
    
    def validate_json_response(self, response_text: str, schema: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], List[str]]:
        """Validate LLM JSON response against schema"""
        try:
            # Extract JSON from response if wrapped in markdown
            json_text = response_text.strip()
            if "```json" in json_text:
                start_idx = json_text.find("```json") + 7
                end_idx = json_text.find("```", start_idx)
                if end_idx > start_idx:
                    json_text = json_text[start_idx:end_idx].strip()
            elif "```" in json_text:
                start_idx = json_text.find("```") + 3
                end_idx = json_text.find("```", start_idx)
                if end_idx > start_idx:
                    json_text = json_text[start_idx:end_idx].strip()
            
            # Parse JSON
            data = json.loads(json_text)
            
            # Basic schema validation (simplified)
            required_fields = schema.get("required", [])
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return False, {}, [f"Missing required field: {field}" for field in missing_fields]
            
            return True, data, []
            
        except json.JSONDecodeError as e:
            return False, {}, [f"Invalid JSON: {str(e)}"]
        except Exception as e:
            return False, {}, [f"Validation error: {str(e)}"]

# Global instance for summarizer LLM operations
summarizer_llm_service = SummarizerLLMService()