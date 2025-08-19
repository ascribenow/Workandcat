#!/usr/bin/env python3
"""
Enrichment Schema Manager - Ensures ALL LLM enrichment follows the standardized directive
Provides automatic consistency and quality control for question enrichment
"""

import json
import logging
from typing import Tuple, Dict, Any
import re

logger = logging.getLogger(__name__)

class EnrichmentSchemaManager:
    """
    Central manager for enforcing enrichment schema consistency across all LLM interactions
    """
    
    # 📘 MASTER ENRICHMENT DIRECTIVE
    ENRICHMENT_DIRECTIVE = """
📘 ENRICHMENT SCHEMA FOR QUESTION SOLUTIONS

You MUST enrich every solution into exactly THREE sections following this schema:

**1. APPROACH** (2-3 sentences)
Purpose: Short preview of how to attack the problem
- Written like an exam strategy tip
- Highlight what student should notice and which method/tool to apply
- ❌ Don't restate the problem or give the answer
- ✅ Do highlight the "entry point" (e.g., symmetry, divisibility, factorization, standard formula)

**2. DETAILED SOLUTION** (Step-by-step)
Purpose: Clear, visual step-by-step logical reasoning
- Break into numbered steps: **Step 1:**, **Step 2:**, etc.
- Use clean formatting instead of raw LaTeX code
- ✅ Always annotate each step with reasoning ("Why we do this")
- ✅ Show work clearly with proper mathematical notation (×, ÷, ², ³, √)
- ✅ Highlight final answer with **✅ Final Answer: [answer]**

**3. EXPLANATION** (1-2 sentences max)
Purpose: Big-picture takeaway and concept reinforcement
- Not a rehash of steps
- Summarize why the method works
- ✅ Should build intuition for similar problems
- ✅ Give student tip for exam scenarios

🎯 QUALITY STANDARDS:
- Output must feel like a teacher explaining to a student, not computer logs
- Visually clean, professional, and exam-ready
- Use Markdown formatting, Unicode math symbols
- No LaTeX unless explicitly requested
- Teaching aid quality, not repetition

CRITICAL: Follow this schema EXACTLY. All three sections are mandatory.
"""

    @staticmethod
    def get_enrichment_system_prompt(subcategory: str = "", question_type: str = "") -> str:
        """
        Get the complete system prompt that includes the enrichment directive
        """
        base_prompt = f"""You are an expert CAT mathematics tutor creating high-quality educational content.

{EnrichmentSchemaManager.ENRICHMENT_DIRECTIVE}

CONTEXT:
- Subcategory: {subcategory or 'General Mathematics'}
- Question Type: {question_type or 'Problem Solving'}
- Target: CAT exam preparation
- Audience: Serious exam candidates

Remember: Every response must follow the three-section schema EXACTLY."""
        
        return base_prompt

    @staticmethod
    def validate_enrichment_output(response_text: str) -> Dict[str, Any]:
        """
        Validate that LLM output follows the enrichment schema
        Returns validation results and extracted sections
        """
        validation = {
            "is_valid": False,
            "has_approach": False,
            "has_detailed_solution": False,
            "has_explanation": False,
            "has_proper_steps": False,
            "has_final_answer": False,
            "approach": "",
            "detailed_solution": "",
            "explanation": "",
            "issues": []
        }
        
        # Extract sections
        approach, detailed_solution, explanation = EnrichmentSchemaManager.extract_sections(response_text)
        
        validation["approach"] = approach
        validation["detailed_solution"] = detailed_solution  
        validation["explanation"] = explanation
        
        # Validate Approach
        if approach and len(approach.strip()) >= 50:
            validation["has_approach"] = True
        else:
            validation["issues"].append("Approach missing or too short (need 2-3 sentences)")
        
        # Validate Detailed Solution
        if detailed_solution and len(detailed_solution.strip()) >= 100:
            validation["has_detailed_solution"] = True
            
            # Check for proper step structure
            if "**Step 1:**" in detailed_solution and "**Step 2:**" in detailed_solution:
                validation["has_proper_steps"] = True
            else:
                validation["issues"].append("Detailed solution missing proper **Step 1:**, **Step 2:** structure")
            
            # Check for final answer
            if "final answer" in detailed_solution.lower() or "✅" in detailed_solution:
                validation["has_final_answer"] = True
            else:
                validation["issues"].append("Missing highlighted final answer")
        else:
            validation["issues"].append("Detailed solution missing or too short")
        
        # Validate Explanation
        if explanation and len(explanation.strip()) >= 30:
            validation["has_explanation"] = True
        else:
            validation["issues"].append("Explanation missing or too short (need 1-2 sentences)")
        
        # Overall validation
        validation["is_valid"] = (
            validation["has_approach"] and 
            validation["has_detailed_solution"] and 
            validation["has_explanation"] and
            validation["has_proper_steps"] and
            validation["has_final_answer"]
        )
        
        return validation

    @staticmethod
    def extract_sections(response_text: str) -> Tuple[str, str, str]:
        """
        Extract the three sections from LLM response
        """
        approach = ""
        detailed_solution = ""
        explanation = ""
        
        # Try different section headers
        patterns = [
            (r'\*\*APPROACH\*\*:?\s*(.*?)(?=\*\*DETAILED SOLUTION\*\*|\*\*EXPLANATION\*\*|$)', "approach"),
            (r'\*\*DETAILED SOLUTION\*\*:?\s*(.*?)(?=\*\*EXPLANATION\*\*|$)', "detailed"),
            (r'\*\*EXPLANATION\*\*:?\s*(.*?)$', "explanation"),
        ]
        
        for pattern, section_type in patterns:
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if section_type == "approach":
                    approach = content
                elif section_type == "detailed":
                    detailed_solution = content
                elif section_type == "explanation":
                    explanation = content
        
        # Fallback parsing if headers not found
        if not approach or not detailed_solution:
            lines = response_text.strip().split('\n')
            current_section = None
            temp_approach = []
            temp_detailed = []
            temp_explanation = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if 'approach' in line.lower() and ('**' in line or ':' in line):
                    current_section = 'approach'
                    continue
                elif 'detailed' in line.lower() and 'solution' in line.lower():
                    current_section = 'detailed'
                    continue
                elif 'explanation' in line.lower() and ('**' in line or ':' in line):
                    current_section = 'explanation'
                    continue
                
                if current_section == 'approach':
                    temp_approach.append(line)
                elif current_section == 'detailed':
                    temp_detailed.append(line)
                elif current_section == 'explanation':
                    temp_explanation.append(line)
            
            if not approach:
                approach = '\n'.join(temp_approach)
            if not detailed_solution:
                detailed_solution = '\n'.join(temp_detailed)
            if not explanation:
                explanation = '\n'.join(temp_explanation)
        
        return approach.strip(), detailed_solution.strip(), explanation.strip()

    @staticmethod
    def format_final_solution(approach: str, detailed_solution: str, explanation: str) -> Tuple[str, str]:
        """
        Format the validated sections into final approach and detailed_solution for database
        """
        # Clean approach
        clean_approach = approach.strip()
        if len(clean_approach) > 300:
            sentences = clean_approach.split('. ')
            clean_approach = '. '.join(sentences[:3]) + ('.' if not sentences[2].endswith('.') else '')
        
        # Format detailed solution with explanation
        formatted_detailed = detailed_solution.strip()
        
        # Add explanation as final section if not already included
        if explanation and explanation.lower() not in formatted_detailed.lower():
            formatted_detailed += f"\n\n**KEY INSIGHT:**\n{explanation}"
        
        return clean_approach, formatted_detailed

class QualityController:
    """
    Quality control system using Anthropic as checker LLM
    """
    
    def __init__(self, anthropic_api_key: str = None):
        self.anthropic_api_key = anthropic_api_key
    
    async def validate_with_anthropic(self, question_stem: str, answer: str, 
                                    approach: str, detailed_solution: str, 
                                    explanation: str) -> Dict[str, Any]:
        """
        Use Anthropic as quality checker for enrichment validation
        """
        if not self.anthropic_api_key:
            return {"validation_skipped": True, "reason": "No Anthropic API key"}
        
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.anthropic_api_key,
                session_id="quality_control_validation",
                system_message="""You are a quality control expert validating educational content.

VALIDATION CRITERIA:
1. ✅ APPROACH: 2-3 sentences, exam strategy focus, highlights entry point
2. ✅ DETAILED SOLUTION: Numbered steps, clear reasoning, proper math notation, highlighted final answer
3. ✅ EXPLANATION: 1-2 sentences, builds intuition, exam tip

Respond with ONLY:
QUALITY_SCORE: [1-10]
ISSUES: [list any problems, or "None"]
RECOMMENDATION: [Accept/Revise/Reject]"""
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            validation_request = f"""Question: {question_stem}
Answer: {answer}

APPROACH:
{approach}

DETAILED SOLUTION:
{detailed_solution}

EXPLANATION:  
{explanation}

Validate this enrichment against the schema requirements."""
            
            user_message = UserMessage(text=validation_request)
            response = await chat.send_message(user_message)
            
            # Parse response
            quality_score = 0
            issues = "Unknown"
            recommendation = "Revise"
            
            lines = response.strip().split('\n')
            for line in lines:
                if 'QUALITY_SCORE:' in line:
                    try:
                        quality_score = int(re.search(r'(\d+)', line).group(1))
                    except:
                        pass
                elif 'ISSUES:' in line:
                    issues = line.split('ISSUES:', 1)[1].strip()
                elif 'RECOMMENDATION:' in line:
                    recommendation = line.split('RECOMMENDATION:', 1)[1].strip()
            
            return {
                "quality_score": quality_score,
                "issues": issues,
                "recommendation": recommendation,
                "anthropic_validated": True
            }
            
        except Exception as e:
            logger.error(f"Anthropic validation failed: {e}")
            return {"validation_failed": True, "error": str(e)}

# Singleton instance for global use
enrichment_schema = EnrichmentSchemaManager()
quality_controller = QualityController()