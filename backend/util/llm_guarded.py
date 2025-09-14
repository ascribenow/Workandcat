"""
Guarded LLM wrapper with JSON schema validation and auto-retry logic
Wraps LLM calls with automatic JSON parsing, validation, and repair attempts.
"""

import json
import os
import openai
from typing import Dict, Any
from .json_guard import parse_and_validate, build_repair_message

def call_llm_with_fallback(system_prompt: str, user_json: Dict[str, Any], 
                          model_primary: str, model_fallback: str, 
                          response_format: str = "json") -> str:
    """
    Simple synchronous LLM call with fallback for the guarded wrapper
    """
    # Set up OpenAI client
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Convert user_json to string for the prompt
    user_content = json.dumps(user_json, indent=2)
    
    try:
        # Try primary model with JSON mode and hardening
        response = client.chat.completions.create(
            model=model_primary,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0,  # Set to 0 for deterministic JSON output
            max_tokens=2000,
            response_format={"type": "json_object"} if response_format == "json" else None
        )
        raw_content = response.choices[0].message.content
        
        # JSON hardening: Clean up common issues
        if response_format == "json":
            # Trim to first complete JSON object
            if '{' in raw_content:
                start_idx = raw_content.find('{')
                # Find matching closing brace
                brace_count = 0
                end_idx = -1
                for i, char in enumerate(raw_content[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                
                if end_idx > start_idx:
                    raw_content = raw_content[start_idx:end_idx]
            
            # Remove trailing commas
            raw_content = raw_content.replace(',}', '}').replace(',]', ']')
        
        return raw_content
    except Exception as e:
        # Try fallback model (simplified - just return a basic response)
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e2:
            raise Exception(f"Both primary ({model_primary}) and fallback models failed: {e}, {e2}")

def call_llm_json_with_retry(system_prompt: str, user_payload: Dict[str, Any],
                             schema: Dict[str, Any], model_primary: str, model_fallback: str,
                             max_retries: int = 1,
                             timeout_ms: int = 15000) -> Dict[str, Any]:
    """
    Call LLM with JSON schema validation and automatic retry on invalid output
    
    Args:
        system_prompt: System prompt for the LLM
        user_payload: User data to send to LLM
        schema: JSON schema to validate against
        model_primary: Primary LLM model to use
        model_fallback: Fallback model if primary fails
        max_retries: Maximum number of retry attempts
        
    Returns:
        Validated JSON data from LLM
        
    Raises:
        ValueError: If LLM returns invalid JSON after all retries
    """
    # Initial LLM call
    resp = call_llm_with_fallback(
        system_prompt=system_prompt, 
        user_json=user_payload,
        model_primary=model_primary, 
        model_fallback=model_fallback,
        response_format="json"
    )
    
    # Convert response to text for validation
    raw_text = resp if isinstance(resp, str) else json.dumps(resp) if isinstance(resp, dict) else str(resp)
    
    # Parse and validate initial response
    ok, data, errors = parse_and_validate(raw_text, schema)
    if ok:
        return data
    
    # Retry with repair messages
    for retry_count in range(max_retries):
        repair_msg = build_repair_message(errors)
        
        repaired = call_llm_with_fallback(
            system_prompt=system_prompt, 
            user_json={
                "original_payload": user_payload,
                "error_feedback": repair_msg,
                "instruction": "Return ONLY valid JSON matching the schema; no prose."
            }, 
            model_primary=model_primary, 
            model_fallback=model_fallback, 
            response_format="json"
        )
        
        # Convert repaired response to text
        raw_text = repaired if isinstance(repaired, str) else json.dumps(repaired) if isinstance(repaired, dict) else str(repaired)
        
        # Parse and validate repaired response
        ok, data, errors = parse_and_validate(raw_text, schema)
        if ok:
            # Mark that retry was used
            if isinstance(data, dict):
                data.setdefault("constraint_report", {}).setdefault("meta", {})["retry_used"] = True
            return data
    
    # All retries failed
    raise ValueError(f"LLM returned invalid JSON after {max_retries} retries. Reasons: {'; '.join(errors)}")