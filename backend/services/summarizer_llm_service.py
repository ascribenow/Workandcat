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
        
        # Initialize API keys using existing pattern
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not self.openai_api_key:
            logger.warning("⚠️ Summarizer LLM: OpenAI API key not found")
        
        # Model configuration (GPT-4o primary + Gemini fallback pattern)
        self.primary_model = "gpt-4o-mini"
        self.fallback_model = "gpt-3.5-turbo"
        self.gemini_model = "gemini-1.5-pro"
        
        # LLM utilities configuration
        self.timeout = 30
        self.max_failures_before_degradation = 3
        self.max_openai_failures_before_gemini = 2
        self.openai_consecutive_failures = 0
        self.primary_model_failures = 0
        
        # Initialize Google AI if key available
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)
            logger.info("✅ Summarizer LLM: Google Gemini configured as fallback")
        else:
            logger.warning("⚠️ Summarizer LLM: Google API key not found - no Gemini fallback")
        
        logger.info("✅ Summarizer LLM: Configured with existing LLM utilities pattern")
    
    async def call_for_concept_analysis(self, system_prompt: str, user_payload: Dict[str, Any]) -> Tuple[str, str]:
        """
        Call LLM for concept analysis with GPT-4o primary, Gemini fallback
        
        Returns:
            (response_text, model_used)
        """
        user_message = json.dumps(user_payload, indent=2)
        
        # Use existing LLM utilities with proper fallback pattern
        try:
            from llm_utils import call_llm_with_fallback
            
            logger.info("🔄 Summarizer LLM: Using existing LLM utilities...")
            
            response_text, model_used = await call_llm_with_fallback(
                service_instance=self,
                system_message=system_prompt,
                user_message=user_message,
                max_tokens=2000,
                temperature=0.1
            )
            
            logger.info(f"✅ Summarizer LLM: Success with {model_used}")
            return response_text, model_used
            
        except Exception as llm_error:
            logger.error(f"❌ Summarizer LLM failed with existing utilities: {str(llm_error)[:100]}...")
            raise Exception(f"Summarizer LLM failed: {str(llm_error)}")
    
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