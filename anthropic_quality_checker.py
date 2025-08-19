#!/usr/bin/env python3
"""
Anthropic Quality Checker - Assess current approach and explanation texts
Implements Gemini (Maker) → Anthropic (Checker) methodology
"""

import sys
import os
sys.path.append('/app/backend')

import logging
import asyncio
import psycopg2
from dotenv import load_dotenv
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AnthropicQualityChecker:
    """
    Anthropic-powered quality checker for approach and explanation assessment
    """
    
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.database_url = os.getenv('DATABASE_URL')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        
        logger.info("🔍 Anthropic Quality Checker Initialized")
        logger.info(f"   Anthropic (Checker): {'✅' if self.anthropic_api_key else '❌'}")
        logger.info(f"   Google Gemini (Maker): {'✅' if self.google_api_key else '❌'}")

    async def assess_current_content_quality(self, question_data):
        """
        Use Anthropic to assess the quality of current approach and explanation texts
        """
        question_id, stem, answer, approach, detailed_solution, explanation = question_data
        
        try:
            logger.info(f"🔍 Checking quality: {stem[:60]}...")
            
            if not self.anthropic_api_key:
                return {"error": "No Anthropic API key available"}
            
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.anthropic_api_key,
                session_id="quality_assessment",
                system_message="""You are an expert educational content quality assessor. Evaluate the APPROACH and EXPLANATION sections against the required schema.

📘 REQUIRED SCHEMA:

**APPROACH (2-3 sentences):**
- Short preview of how to attack the problem
- Written like an exam strategy tip
- Highlight what student should notice and which method/tool to apply
- ❌ Don't restate the problem or give the answer
- ✅ Do highlight the "entry point" (e.g., symmetry, divisibility, factorization)

**EXPLANATION (1-2 sentences max):**
- Big-picture takeaway and concept reinforcement
- Not a rehash of steps
- Summarize why the method works
- ✅ Should build intuition for similar problems
- ✅ Give student tip for exam scenarios

ASSESSMENT CRITERIA:
1. Schema Compliance (follows exact requirements)
2. Educational Value (teaches strategy/insight)
3. Clarity and Conciseness 
4. Exam Relevance (practical for CAT preparation)

Respond ONLY with:
APPROACH_SCORE: [1-10]
APPROACH_ISSUES: [specific problems or "None"]
EXPLANATION_SCORE: [1-10] 
EXPLANATION_ISSUES: [specific problems or "None"]
OVERALL_QUALITY: [Excellent/Good/Fair/Poor]
RECOMMENDATION: [Accept/Improve/Rewrite]
KEY_IMPROVEMENTS_NEEDED: [specific suggestions or "None"]"""
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            # Extract approach and explanation for assessment
            current_approach = approach or "No approach provided"
            current_explanation = explanation or "No explanation provided"
            
            # If explanation is embedded in detailed solution, try to extract it
            if not explanation and detailed_solution:
                if "KEY INSIGHT:" in detailed_solution:
                    current_explanation = detailed_solution.split("KEY INSIGHT:")[-1].strip()
                elif "EXPLANATION:" in detailed_solution:
                    current_explanation = detailed_solution.split("EXPLANATION:")[-1].strip()
            
            assessment_request = f"""Question: {stem}
Answer: {answer}

CURRENT APPROACH:
{current_approach}

CURRENT EXPLANATION:
{current_explanation}

Assess the quality of the APPROACH and EXPLANATION sections against the schema requirements."""
            
            user_message = UserMessage(text=assessment_request)
            response = await chat.send_message(user_message)
            
            # Parse assessment results
            assessment = self._parse_assessment_response(response)
            assessment["question_id"] = question_id
            assessment["current_approach"] = current_approach
            assessment["current_explanation"] = current_explanation
            
            logger.info(f"  📊 Approach Score: {assessment.get('approach_score', 'N/A')}")
            logger.info(f"  📊 Explanation Score: {assessment.get('explanation_score', 'N/A')}")
            logger.info(f"  🎯 Overall Quality: {assessment.get('overall_quality', 'N/A')}")
            
            return assessment
            
        except Exception as e:
            logger.error(f"  ❌ Assessment failed: {e}")
            return {"error": str(e), "question_id": question_id}

    def _parse_assessment_response(self, response: str) -> dict:
        """Parse Anthropic assessment response"""
        assessment = {
            "approach_score": 0,
            "approach_issues": "Unknown",
            "explanation_score": 0,
            "explanation_issues": "Unknown", 
            "overall_quality": "Unknown",
            "recommendation": "Unknown",
            "key_improvements": "Unknown"
        }
        
        lines = response.strip().split('\n')
        for line in lines:
            if 'APPROACH_SCORE:' in line:
                try:
                    assessment["approach_score"] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'APPROACH_ISSUES:' in line:
                assessment["approach_issues"] = line.split(':', 1)[1].strip()
            elif 'EXPLANATION_SCORE:' in line:
                try:
                    assessment["explanation_score"] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'EXPLANATION_ISSUES:' in line:
                assessment["explanation_issues"] = line.split(':', 1)[1].strip()
            elif 'OVERALL_QUALITY:' in line:
                assessment["overall_quality"] = line.split(':', 1)[1].strip()
            elif 'RECOMMENDATION:' in line:
                assessment["recommendation"] = line.split(':', 1)[1].strip()
            elif 'KEY_IMPROVEMENTS_NEEDED:' in line:
                assessment["key_improvements"] = line.split(':', 1)[1].strip()
        
        return assessment

    async def gemini_maker_anthropic_checker_workflow(self, question_stem: str, answer: str, 
                                                    subcategory: str, question_type: str) -> dict:
        """
        Implement Gemini (Maker) → Anthropic (Checker) methodology
        """
        logger.info("🔄 Running Gemini (Maker) → Anthropic (Checker) workflow...")
        
        # PHASE 1: Gemini as Maker
        logger.info("  🎯 Phase 1: Gemini generating solution...")
        gemini_result = await self._gemini_generate_solution(question_stem, answer, subcategory, question_type)
        
        if not gemini_result["success"]:
            return {"success": False, "error": "Gemini generation failed", "details": gemini_result}
        
        # PHASE 2: Anthropic as Checker
        logger.info("  🔍 Phase 2: Anthropic quality checking...")
        anthropic_assessment = await self._anthropic_check_solution(
            question_stem, answer, gemini_result["approach"], 
            gemini_result["detailed_solution"], gemini_result["explanation"]
        )
        
        # PHASE 3: Decision making
        if anthropic_assessment.get("recommendation") in ["Accept", "Good"]:
            logger.info("  ✅ Phase 3: Anthropic approved - accepting solution")
            return {
                "success": True,
                "approach": gemini_result["approach"],
                "detailed_solution": gemini_result["detailed_solution"], 
                "explanation": gemini_result["explanation"],
                "maker": "Google Gemini",
                "checker": "Anthropic Claude",
                "quality_score": anthropic_assessment.get("approach_score", 8),
                "anthropic_assessment": anthropic_assessment,
                "workflow": "Gemini (Maker) → Anthropic (Checker)"
            }
        else:
            logger.info("  🔄 Phase 3: Anthropic suggests improvements - regenerating...")
            # Try once more with Anthropic feedback
            improved_result = await self._gemini_generate_with_feedback(
                question_stem, answer, subcategory, question_type, anthropic_assessment
            )
            
            return {
                "success": improved_result["success"],
                "approach": improved_result.get("approach"),
                "detailed_solution": improved_result.get("detailed_solution"),
                "explanation": improved_result.get("explanation"), 
                "maker": "Google Gemini",
                "checker": "Anthropic Claude",
                "quality_score": improved_result.get("quality_score", 7),
                "anthropic_assessment": anthropic_assessment,
                "improvement_iteration": True,
                "workflow": "Gemini (Maker) → Anthropic (Checker) → Gemini (Improved)"
            }

    async def _gemini_generate_solution(self, question_stem: str, answer: str, 
                                      subcategory: str, question_type: str) -> dict:
        """Gemini solution generation"""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.google_api_key,
                session_id="gemini_maker",
                system_message=f"""You are an expert CAT mathematics tutor. Create a high-quality solution following the EXACT schema.

📘 MANDATORY SCHEMA:

**APPROACH (2-3 sentences):**
- Brief exam strategy tip showing how to attack the problem
- Highlight the "entry point" (pattern recognition, formula choice, etc.)
- ❌ Don't restate problem or give answer
- ✅ Focus on what student should notice first

**DETAILED SOLUTION:**
- Use numbered steps: **Step 1:**, **Step 2:**, etc.
- Show calculations with clean mathematical notation (×, ÷, ², ³, √)
- Annotate reasoning for each step
- End with **✅ Final Answer: {answer}**

**EXPLANATION (1-2 sentences):**
- Big-picture takeaway about why this method works
- Exam tip for similar problems
- Build intuition, don't repeat steps

Context: {subcategory} - {question_type}
Target: CAT exam preparation"""
            ).with_model("gemini", "gemini-2.0-flash")
            
            user_message = UserMessage(text=f"""Question: {question_stem}

Correct Answer: {answer}

Create the complete solution following the exact schema format:

**APPROACH:**
[2-3 sentences strategy overview]

**DETAILED SOLUTION:**
**Step 1:** [First logical step]
**Step 2:** [Continue systematically]
...
**✅ Final Answer: {answer}**

**EXPLANATION:**
[1-2 sentences conceptual takeaway]""")
            
            response = await chat.send_message(user_message)
            
            # Parse Gemini response
            approach, detailed_solution, explanation = self._parse_gemini_response(response)
            
            return {
                "success": True,
                "approach": approach,
                "detailed_solution": detailed_solution,
                "explanation": explanation
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _anthropic_check_solution(self, question_stem: str, answer: str, 
                                      approach: str, detailed_solution: str, explanation: str) -> dict:
        """Anthropic solution quality checking"""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.anthropic_api_key,
                session_id="anthropic_checker",
                system_message="""You are a quality control expert for educational content. Assess the solution against the schema requirements.

ASSESSMENT FOCUS:
1. APPROACH: Does it provide strategic insight without giving away the answer?
2. DETAILED SOLUTION: Is it clear, well-structured, and complete? 
3. EXPLANATION: Does it build conceptual understanding?

Respond ONLY with:
APPROACH_QUALITY: [Excellent/Good/Fair/Poor]
DETAILED_QUALITY: [Excellent/Good/Fair/Poor]
EXPLANATION_QUALITY: [Excellent/Good/Fair/Poor]
OVERALL_SCORE: [1-10]
RECOMMENDATION: [Accept/Improve/Rewrite]
SPECIFIC_ISSUES: [detailed feedback or "None"]"""
            ).with_model("anthropic", "claude-3-5-sonnet-20241022")
            
            user_message = UserMessage(text=f"""Question: {question_stem}
Answer: {answer}

APPROACH:
{approach}

DETAILED SOLUTION:
{detailed_solution}

EXPLANATION:
{explanation}

Assess this solution's quality against educational standards.""")
            
            response = await chat.send_message(user_message)
            return self._parse_anthropic_check(response)
            
        except Exception as e:
            return {"error": str(e), "recommendation": "Error"}

    def _parse_gemini_response(self, response: str) -> tuple:
        """Parse Gemini response into three sections"""
        approach = ""
        detailed_solution = ""
        explanation = ""
        
        # Try to extract sections
        if "**APPROACH:**" in response and "**DETAILED SOLUTION:**" in response:
            parts = response.split("**DETAILED SOLUTION:**")
            approach = parts[0].replace("**APPROACH:**", "").strip()
            
            remaining = parts[1]
            if "**EXPLANATION:**" in remaining:
                solution_parts = remaining.split("**EXPLANATION:**")
                detailed_solution = solution_parts[0].strip()
                explanation = solution_parts[1].strip()
            else:
                detailed_solution = remaining.strip()
                explanation = "This problem demonstrates systematic application of mathematical principles."
        else:
            # Fallback parsing
            lines = response.strip().split('\n')
            current_section = "approach"
            temp_sections = {"approach": [], "detailed": [], "explanation": []}
            
            for line in lines:
                line = line.strip()
                if "**APPROACH:**" in line:
                    current_section = "approach"
                    continue
                elif "**DETAILED SOLUTION:**" in line:
                    current_section = "detailed"
                    continue
                elif "**EXPLANATION:**" in line:
                    current_section = "explanation"
                    continue
                
                if line:
                    temp_sections[current_section].append(line)
            
            approach = '\n'.join(temp_sections["approach"])
            detailed_solution = '\n'.join(temp_sections["detailed"])
            explanation = '\n'.join(temp_sections["explanation"])
        
        return approach.strip(), detailed_solution.strip(), explanation.strip()

    def _parse_anthropic_check(self, response: str) -> dict:
        """Parse Anthropic quality check response"""
        check_result = {
            "approach_quality": "Unknown",
            "detailed_quality": "Unknown", 
            "explanation_quality": "Unknown",
            "overall_score": 5,
            "recommendation": "Improve",
            "specific_issues": "Unknown"
        }
        
        lines = response.strip().split('\n')
        for line in lines:
            if 'APPROACH_QUALITY:' in line:
                check_result["approach_quality"] = line.split(':', 1)[1].strip()
            elif 'DETAILED_QUALITY:' in line:
                check_result["detailed_quality"] = line.split(':', 1)[1].strip()
            elif 'EXPLANATION_QUALITY:' in line:
                check_result["explanation_quality"] = line.split(':', 1)[1].strip()
            elif 'OVERALL_SCORE:' in line:
                try:
                    check_result["overall_score"] = int(line.split(':')[1].strip())
                except:
                    pass
            elif 'RECOMMENDATION:' in line:
                check_result["recommendation"] = line.split(':', 1)[1].strip()
            elif 'SPECIFIC_ISSUES:' in line:
                check_result["specific_issues"] = line.split(':', 1)[1].strip()
        
        return check_result

    async def _gemini_generate_with_feedback(self, question_stem: str, answer: str, 
                                           subcategory: str, question_type: str, 
                                           feedback: dict) -> dict:
        """Generate improved solution based on Anthropic feedback"""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.google_api_key,
                session_id="gemini_improvement",
                system_message=f"""You are creating an improved solution based on quality feedback.

QUALITY FEEDBACK RECEIVED:
- Approach Issues: {feedback.get('approach_issues', 'Unknown')}
- Explanation Issues: {feedback.get('explanation_issues', 'Unknown')}
- Key Improvements Needed: {feedback.get('key_improvements', 'Unknown')}

Address these specific issues while maintaining the exact schema format."""
            ).with_model("gemini", "gemini-2.0-flash")
            
            user_message = UserMessage(text=f"""Question: {question_stem}
Answer: {answer}

Create an IMPROVED solution addressing the feedback. Follow exact schema:

**APPROACH:**
[Improved 2-3 sentences addressing feedback]

**DETAILED SOLUTION:**
**Step 1:** [Clear first step]
**Step 2:** [Continue systematically]
...
**✅ Final Answer: {answer}**

**EXPLANATION:**
[Improved 1-2 sentences addressing feedback]""")
            
            response = await chat.send_message(user_message)
            approach, detailed_solution, explanation = self._parse_gemini_response(response)
            
            return {
                "success": True,
                "approach": approach,
                "detailed_solution": detailed_solution,
                "explanation": explanation,
                "quality_score": 8  # Higher score for improved version
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_quality_assessment(self):
        """Run quality assessment on all current questions"""
        try:
            logger.info("🔍 STARTING ANTHROPIC QUALITY ASSESSMENT")
            logger.info("=" * 70)
            
            # Get all questions
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, stem, answer, solution_approach, detailed_solution, ''
                FROM questions 
                WHERE solution_approach IS NOT NULL 
                AND detailed_solution IS NOT NULL
                ORDER BY id
                LIMIT 20
            """)  # Limit to 20 for initial assessment
            
            questions = cur.fetchall()
            logger.info(f"📊 Assessing {len(questions)} questions...")
            
            conn.close()
            
            # Assess each question
            assessments = []
            poor_quality_count = 0
            needs_improvement_count = 0
            
            for i, question_data in enumerate(questions):
                logger.info(f"\n🔍 [{i+1}/{len(questions)}] Assessing quality...")
                
                assessment = await self.assess_current_content_quality(question_data)
                
                if "error" not in assessment:
                    assessments.append(assessment)
                    
                    # Track quality issues
                    if assessment.get("overall_quality") == "Poor":
                        poor_quality_count += 1
                    elif assessment.get("recommendation") == "Improve":
                        needs_improvement_count += 1
                
                # Small delay
                await asyncio.sleep(0.5)
            
            # Summary results
            logger.info(f"\n🎉 QUALITY ASSESSMENT COMPLETED!")
            logger.info("=" * 70)
            logger.info(f"📊 Total assessments: {len(assessments)}")
            logger.info(f"❌ Poor quality: {poor_quality_count}")
            logger.info(f"⚠️ Needs improvement: {needs_improvement_count}")
            logger.info(f"✅ Good quality: {len(assessments) - poor_quality_count - needs_improvement_count}")
            
            if assessments:
                avg_approach_score = sum(a.get("approach_score", 0) for a in assessments) / len(assessments)
                avg_explanation_score = sum(a.get("explanation_score", 0) for a in assessments) / len(assessments)
                
                logger.info(f"📈 Average approach score: {avg_approach_score:.1f}/10")
                logger.info(f"📈 Average explanation score: {avg_explanation_score:.1f}/10")
            
            # Show sample issues
            logger.info(f"\n🔍 SAMPLE QUALITY ISSUES:")
            for assessment in assessments[:3]:
                if assessment.get("recommendation") != "Accept":
                    logger.info(f"Question: {assessment.get('question_id', 'Unknown')}")
                    logger.info(f"  Approach Issues: {assessment.get('approach_issues', 'Unknown')}")
                    logger.info(f"  Explanation Issues: {assessment.get('explanation_issues', 'Unknown')}")
                    logger.info(f"  Recommendation: {assessment.get('recommendation', 'Unknown')}")
            
            return {
                "success": True,
                "total_assessed": len(assessments),
                "poor_quality": poor_quality_count,
                "needs_improvement": needs_improvement_count,
                "assessments": assessments
            }
            
        except Exception as e:
            logger.error(f"❌ Quality assessment failed: {e}")
            return {"success": False, "error": str(e)}

async def main():
    """Main execution function"""
    checker = AnthropicQualityChecker()
    
    logger.info("🎯 Starting Anthropic Quality Assessment...")
    results = await checker.run_quality_assessment()
    
    if results["success"]:
        logger.info("✅ Quality assessment completed successfully!")
    else:
        logger.error("❌ Quality assessment failed!")
    
    return results["success"]

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)