#!/usr/bin/env python3
"""
Anthropic Semantic Validation Service
Uses Anthropic Claude for semantic quality validation of LLM enrichment
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List
import anthropic

logger = logging.getLogger(__name__)

class AnthropicSemanticValidator:
    """
    Semantic validation service using Anthropic Claude
    Validates mathematical correctness and contextual appropriateness
    """
    
    def __init__(self):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.anthropic_api_key:
            logger.error("❌ Anthropic API key not found")
            raise ValueError("ANTHROPIC_API_KEY environment variable required")
        
        self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        self.max_retries = 3
        self.retry_delays = [2, 5, 10]
        
        logger.info("✅ AnthropicSemanticValidator initialized")
    
    async def validate_semantic_quality(self, question_stem: str, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform semantic validation of enrichment quality
        
        Args:
            question_stem: The original question text
            enrichment_data: Dictionary of enrichment fields to validate
            
        Returns:
            Dict with semantic validation results
        """
        
        validation_results = {
            "semantic_valid": True,
            "issues": [],
            "confidence_score": 0.0,
            "detailed_feedback": {}
        }
        
        try:
            # Fields to validate semantically
            semantic_fields = [
                'core_concepts', 'solution_method', 'concept_difficulty',
                'operations_required', 'problem_structure', 'concept_keywords'
            ]
            
            # Build validation prompt
            fields_to_validate = {}
            for field in semantic_fields:
                if field in enrichment_data and enrichment_data[field]:
                    fields_to_validate[field] = enrichment_data[field]
            
            if not fields_to_validate:
                logger.warning("⚠️ No semantic fields to validate")
                return validation_results
            
            # Create semantic validation prompt
            validation_prompt = self._create_semantic_validation_prompt(
                question_stem, fields_to_validate
            )
            
            # Call Anthropic for semantic validation
            for attempt in range(self.max_retries):
                try:
                    response = self.client.messages.create(
                        model="claude-3-5-sonnet-20241022",
                        max_tokens=1000,
                        temperature=0.1,
                        messages=[
                            {"role": "user", "content": validation_prompt}
                        ]
                    )
                    
                    response_text = response.content[0].text.strip()
                    logger.info(f"🔍 Anthropic semantic validation response: {response_text[:200]}...")
                    
                    # Parse validation response
                    validation_result = self._parse_validation_response(response_text)
                    
                    if validation_result:
                        return validation_result
                    
                except Exception as e:
                        logger.error(f"❌ Anthropic API call failed (attempt {attempt + 1}): {e}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delays[attempt])
                        else:
                            raise e
            
        except Exception as e:
            logger.error(f"❌ Semantic validation failed: {e}")
            validation_results["semantic_valid"] = False
            validation_results["issues"].append(f"Validation service error: {str(e)}")
        
        return validation_results
    
    def _create_semantic_validation_prompt(self, question_stem: str, fields_to_validate: Dict[str, Any]) -> str:
        """Create prompt for semantic validation"""
        
        return f"""You are an expert mathematical content validator with deep understanding of CAT-level quantitative problems.

Your task is to validate whether the enrichment fields are semantically correct and contextually appropriate for the given mathematical question.

QUESTION STEM:
{question_stem}

ENRICHMENT FIELDS TO VALIDATE:
{json.dumps(fields_to_validate, indent=2)}

SEMANTIC VALIDATION CRITERIA:

1. MATHEMATICAL CORRECTNESS:
   - Do the core_concepts actually relate to solving this problem?
   - Is the solution_method appropriate for this question type?
   - Are the operations_required accurate for the mathematical steps needed?

2. CONTEXTUAL APPROPRIATENESS:
   - Do the concept_keywords match the question's mathematical domain?
   - Is the concept_difficulty assessment realistic for this problem?
   - Does the problem_structure accurately describe the question format?

3. EDUCATIONAL VALUE:
   - Would these enrichment fields help a student understand the problem?
   - Are the conceptual elements at the right level of granularity?
   - Do the fields work together cohesively?

4. CONSISTENCY CHECK:
   - Are all fields mutually consistent with each other?
   - Do the solution approach and required operations align?
   - Is there logical coherence across all enrichment aspects?

VALIDATION ASSESSMENT:
Analyze each field for semantic correctness. Identify any mathematical errors, conceptual mismatches, or inappropriate classifications.

Return ONLY this JSON format:
{{
  "semantic_valid": true/false,
  "confidence_score": 0.85,
  "issues": ["list of specific semantic problems found"],
  "detailed_feedback": {{
    "core_concepts": "feedback on mathematical concept relevance",
    "solution_method": "feedback on solution approach appropriateness", 
    "operations_required": "feedback on mathematical operations accuracy",
    "concept_keywords": "feedback on keyword relevance",
    "concept_difficulty": "feedback on difficulty assessment accuracy",
    "problem_structure": "feedback on structural classification accuracy"
  }},
  "overall_assessment": "brief summary of semantic quality"
}}

Be rigorous but fair - flag genuine mathematical inconsistencies while accepting valid alternative approaches."""
        
    def _parse_validation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Anthropic validation response"""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_part = response_text[start_idx:end_idx]
                validation_data = json.loads(json_part)
                
                # Validate required fields
                required_fields = ["semantic_valid", "confidence_score", "issues"]
                if all(field in validation_data for field in required_fields):
                    logger.info(f"✅ Semantic validation parsed successfully")
                    return validation_data
                else:
                    logger.warning(f"⚠️ Missing required fields in validation response")
                    
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse Anthropic validation response: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error parsing validation: {e}")
        
        # Return default failure response
        return {
            "semantic_valid": False,
            "confidence_score": 0.0,
            "issues": ["Failed to parse semantic validation response"],
            "detailed_feedback": {},
            "overall_assessment": "Validation parsing failed"
        }

# Global instance
anthropic_semantic_validator = AnthropicSemanticValidator()