#!/usr/bin/env python3
"""
Upgrade all existing questions to new enrichment standards:
1. Run Anthropic checker on all existing solutions
2. Fix $ signs in existing content 
3. Ensure proper Approach vs Explanation distinction
4. Apply new Gemini (Maker) → Anthropic (Checker) methodology
"""

import sys
import os
sys.path.append('/app/backend')

import logging
import asyncio
import psycopg2
from dotenv import load_dotenv
from standardized_enrichment_engine import standardized_enricher
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExistingQuestionUpgrader:
    """
    Upgrade existing questions to new enrichment standards
    """
    
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.database_url = os.getenv('DATABASE_URL')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        logger.info("🔄 Existing Question Upgrader Initialized")
        logger.info(f"   Anthropic Checker: {'✅' if self.anthropic_api_key else '❌'}")

    async def assess_existing_question_quality(self, question_data):
        """
        Use Anthropic to assess quality of existing questions
        """
        question_id, stem, answer, approach, detailed_solution, subcategory, type_of_question = question_data
        
        try:
            logger.info(f"🔍 Assessing: {stem[:60]}...")
            
            # Extract explanation from detailed solution if present
            explanation = ""
            if "KEY INSIGHT:" in detailed_solution:
                parts = detailed_solution.split("KEY INSIGHT:", 1)
                detailed_clean = parts[0].strip()
                explanation = parts[1].strip()
            elif "EXPLANATION:" in detailed_solution:
                parts = detailed_solution.split("EXPLANATION:", 1)
                detailed_clean = parts[0].strip()
                explanation = parts[1].strip()
            else:
                detailed_clean = detailed_solution
                explanation = "No explanation found"
            
            # Check for $ signs
            has_dollar_signs = '$' in f"{approach} {detailed_solution}"
            
            # Quick quality assessment
            approach_length = len(approach) if approach else 0
            explanation_length = len(explanation) if explanation else 0
            
            # Basic quality issues
            issues = []
            needs_upgrade = False
            
            if has_dollar_signs:
                issues.append("Contains $ signs")
                needs_upgrade = True
                
            if approach_length < 50:
                issues.append("Approach too short")
                needs_upgrade = True
                
            if explanation_length < 30:
                issues.append("Explanation missing or too short")
                needs_upgrade = True
                
            # Check if approach and explanation are too similar
            if approach and explanation:
                approach_words = set(approach.lower().split())
                explanation_words = set(explanation.lower().split())
                if len(approach_words) > 0 and len(explanation_words) > 0:
                    overlap_ratio = len(approach_words.intersection(explanation_words)) / max(len(approach_words), len(explanation_words))
                    if overlap_ratio > 0.7:
                        issues.append("Approach and Explanation too similar")
                        needs_upgrade = True
            
            # Use Anthropic for detailed assessment if available
            anthropic_assessment = None
            if self.anthropic_api_key and needs_upgrade:
                anthropic_assessment = await self._anthropic_assess_quality(
                    stem, answer, approach, detailed_clean, explanation
                )
                
                if anthropic_assessment and anthropic_assessment.get("recommendation") not in ["Accept", "Excellent", "Good"]:
                    needs_upgrade = True
            
            assessment_result = {
                "question_id": question_id,
                "stem": stem[:100] + "..." if len(stem) > 100 else stem,
                "has_dollar_signs": has_dollar_signs,
                "approach_length": approach_length,
                "explanation_length": explanation_length,
                "issues": issues,
                "needs_upgrade": needs_upgrade,
                "anthropic_assessment": anthropic_assessment,
                "subcategory": subcategory,
                "type_of_question": type_of_question,
                "current_approach": approach,
                "current_explanation": explanation
            }
            
            if needs_upgrade:
                logger.info(f"  ❌ Needs upgrade: {', '.join(issues)}")
            else:
                logger.info(f"  ✅ Quality acceptable")
                
            return assessment_result
            
        except Exception as e:
            logger.error(f"  ❌ Assessment failed: {e}")
            return {
                "question_id": question_id,
                "error": str(e),
                "needs_upgrade": True  # Assume needs upgrade if assessment fails
            }

    async def _anthropic_assess_quality(self, stem, answer, approach, detailed_solution, explanation):
        """
        Use Anthropic to assess quality of existing question
        """
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.anthropic_api_key,
                session_id="existing_quality_assessment",
                system_message="""You are assessing existing educational content quality against new standards.

ASSESSMENT CRITERIA:
- APPROACH should show HOW to solve (strategic method) in 2-3 sentences
- EXPLANATION should show WHY it works (conceptual principle) in 1-2 sentences  
- No $ signs or LaTeX artifacts should be present
- Both sections should be distinct and serve different purposes

Respond ONLY with:
APPROACH_QUALITY: [Excellent/Good/Fair/Poor]
EXPLANATION_QUALITY: [Excellent/Good/Fair/Poor]
DOLLAR_SIGNS_PRESENT: [Yes/No]
APPROACH_EXPLANATION_DISTINCT: [Yes/No]
RECOMMENDATION: [Accept/Improve/Rewrite]
ISSUES: [specific problems or "None"]"""
            ).with_model("anthropic", "claude-3-haiku-20240307")
            
            assessment_request = f"""Existing Content Assessment:

Question: {stem}
Answer: {answer}

CURRENT APPROACH:
{approach}

CURRENT DETAILED SOLUTION:
{detailed_solution}

CURRENT EXPLANATION:  
{explanation}

Assess this existing content against new quality standards."""
            
            user_message = UserMessage(text=assessment_request)
            response = await chat.send_message(user_message)
            
            # Parse response
            assessment = {}
            lines = response.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace('_', '').replace(' ', '')
                    assessment[key] = value.strip()
            
            return assessment
            
        except Exception as e:
            logger.warning(f"  ⚠️ Anthropic assessment failed: {e}")
            return None

    async def upgrade_question_to_new_standards(self, question_data, assessment):
        """
        Upgrade a single question using the new methodology
        """
        question_id, stem, answer, old_approach, old_detailed, subcategory, type_of_question = question_data
        
        try:
            logger.info(f"🔄 Upgrading: {stem[:60]}...")
            logger.info(f"   Issues: {', '.join(assessment.get('issues', []))}")
            
            # Use the new standardized enricher to generate improved content
            result = await standardized_enricher.enrich_question_solution(
                question_stem=stem,
                answer=answer,
                subcategory=subcategory or "General",
                question_type=type_of_question or "Problem Solving"
            )
            
            if result["success"]:
                # Update database with new enriched content
                conn = psycopg2.connect(self.database_url)
                cur = conn.cursor()
                
                update_query = """
                UPDATE questions SET 
                    solution_approach = %s,
                    detailed_solution = %s
                WHERE id = %s
                """
                
                cur.execute(update_query, (
                    result["approach"],
                    result["detailed_solution"],
                    question_id
                ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"  ✅ Upgraded successfully")
                logger.info(f"     Quality Score: {result.get('quality_score', 'N/A')}")
                logger.info(f"     Workflow: {result.get('workflow', 'N/A')}")
                
                return {
                    "success": True,
                    "question_id": question_id,
                    "quality_score": result.get("quality_score"),
                    "workflow": result.get("workflow"),
                    "anthropic_validation": result.get("anthropic_validation")
                }
            else:
                logger.error(f"  ❌ Upgrade failed: {result.get('error')}")
                return {
                    "success": False,
                    "question_id": question_id,
                    "error": result.get("error")
                }
                
        except Exception as e:
            logger.error(f"  ❌ Upgrade exception: {e}")
            return {
                "success": False,
                "question_id": question_id,
                "error": str(e)
            }

    async def run_comprehensive_upgrade(self):
        """
        Run comprehensive upgrade on all existing questions
        """
        try:
            logger.info("🚀 STARTING COMPREHENSIVE UPGRADE OF EXISTING QUESTIONS")
            logger.info("=" * 80)
            logger.info("Objectives:")
            logger.info("1. Remove $ signs from existing solutions")
            logger.info("2. Ensure proper Approach vs Explanation distinction")  
            logger.info("3. Apply new Gemini (Maker) → Anthropic (Checker) methodology")
            logger.info("4. Upgrade all questions to new quality standards")
            
            # Get all existing questions
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, stem, answer, solution_approach, detailed_solution, subcategory, type_of_question
                FROM questions 
                WHERE solution_approach IS NOT NULL 
                AND detailed_solution IS NOT NULL
                ORDER BY created_at
            """)
            
            all_questions = cur.fetchall()
            total_questions = len(all_questions)
            
            logger.info(f"📊 Found {total_questions} existing questions to assess")
            conn.close()
            
            if total_questions == 0:
                logger.warning("❌ No existing questions found!")
                return False
            
            # Phase 1: Assess all questions
            logger.info(f"\n🔍 PHASE 1: QUALITY ASSESSMENT")
            logger.info("=" * 50)
            
            assessments = []
            questions_needing_upgrade = 0
            
            for i, question_data in enumerate(all_questions):
                logger.info(f"\n[{i+1}/{total_questions}] Assessing quality...")
                
                assessment = await self.assess_existing_question_quality(question_data)
                assessments.append((question_data, assessment))
                
                if assessment.get("needs_upgrade"):
                    questions_needing_upgrade += 1
                
                # Progress update every 20 questions
                if (i + 1) % 20 == 0:
                    logger.info(f"\n📈 ASSESSMENT PROGRESS [{i+1}/{total_questions}]")
                    logger.info(f"   Questions needing upgrade: {questions_needing_upgrade}")
                
                # Small delay
                await asyncio.sleep(0.2)
            
            # Assessment summary
            logger.info(f"\n📊 ASSESSMENT SUMMARY:")
            logger.info(f"   Total questions assessed: {total_questions}")
            logger.info(f"   Questions needing upgrade: {questions_needing_upgrade}")
            logger.info(f"   Questions already good: {total_questions - questions_needing_upgrade}")
            
            # Show sample issues
            dollar_sign_issues = sum(1 for _, a in assessments if a.get("has_dollar_signs"))
            short_approach_issues = sum(1 for _, a in assessments if "Approach too short" in a.get("issues", []))
            missing_explanation_issues = sum(1 for _, a in assessments if "Explanation missing" in a.get("issues", []))
            similarity_issues = sum(1 for _, a in assessments if "too similar" in ' '.join(a.get("issues", [])))
            
            logger.info(f"\n🔍 ISSUE BREAKDOWN:")
            logger.info(f"   Questions with $ signs: {dollar_sign_issues}")
            logger.info(f"   Questions with short approaches: {short_approach_issues}")
            logger.info(f"   Questions with missing explanations: {missing_explanation_issues}")
            logger.info(f"   Questions with similar approach/explanation: {similarity_issues}")
            
            if questions_needing_upgrade == 0:
                logger.info("🎉 All questions already meet new standards!")
                return True
            
            # Phase 2: Upgrade questions that need it
            logger.info(f"\n🔄 PHASE 2: UPGRADING {questions_needing_upgrade} QUESTIONS")
            logger.info("=" * 50)
            
            upgrade_results = {
                "successful_upgrades": 0,
                "failed_upgrades": 0,
                "total_processed": 0,
                "quality_scores": []
            }
            
            for i, (question_data, assessment) in enumerate(assessments):
                if assessment.get("needs_upgrade"):
                    upgrade_results["total_processed"] += 1
                    
                    logger.info(f"\n🔄 [{upgrade_results['total_processed']}/{questions_needing_upgrade}] Upgrading...")
                    
                    upgrade_result = await self.upgrade_question_to_new_standards(question_data, assessment)
                    
                    if upgrade_result["success"]:
                        upgrade_results["successful_upgrades"] += 1
                        if upgrade_result.get("quality_score"):
                            upgrade_results["quality_scores"].append(upgrade_result["quality_score"])
                    else:
                        upgrade_results["failed_upgrades"] += 1
                    
                    # Progress update every 10 upgrades
                    if upgrade_results["total_processed"] % 10 == 0:
                        avg_quality = sum(upgrade_results["quality_scores"]) / len(upgrade_results["quality_scores"]) if upgrade_results["quality_scores"] else 0
                        logger.info(f"\n📈 UPGRADE PROGRESS [{upgrade_results['total_processed']}/{questions_needing_upgrade}]")
                        logger.info(f"   Successful: {upgrade_results['successful_upgrades']}")
                        logger.info(f"   Failed: {upgrade_results['failed_upgrades']}")
                        logger.info(f"   Average quality: {avg_quality:.1f}")
                    
                    # Small delay to be nice to APIs
                    await asyncio.sleep(0.5)
            
            # Final summary
            success_rate = upgrade_results["successful_upgrades"] / upgrade_results["total_processed"] * 100 if upgrade_results["total_processed"] > 0 else 0
            avg_quality = sum(upgrade_results["quality_scores"]) / len(upgrade_results["quality_scores"]) if upgrade_results["quality_scores"] else 0
            
            logger.info(f"\n🎉 COMPREHENSIVE UPGRADE COMPLETED!")
            logger.info("=" * 80)
            logger.info(f"📊 FINAL RESULTS:")
            logger.info(f"   Total questions in database: {total_questions}")
            logger.info(f"   Questions that needed upgrade: {questions_needing_upgrade}")
            logger.info(f"   Successful upgrades: {upgrade_results['successful_upgrades']}")
            logger.info(f"   Failed upgrades: {upgrade_results['failed_upgrades']}")
            logger.info(f"   Upgrade success rate: {success_rate:.1f}%")
            logger.info(f"   Average quality score: {avg_quality:.1f}/10")
            
            logger.info(f"\n✅ DATABASE STATUS:")
            logger.info(f"   Questions with new enrichment standards: {upgrade_results['successful_upgrades']}")
            logger.info(f"   Questions already meeting standards: {total_questions - questions_needing_upgrade}")
            logger.info(f"   Total high-quality questions: {upgrade_results['successful_upgrades'] + (total_questions - questions_needing_upgrade)}")
            
            return success_rate >= 80  # 80% success rate required
            
        except Exception as e:
            logger.error(f"❌ Comprehensive upgrade failed: {e}")
            return False

async def main():
    """Main execution function"""
    upgrader = ExistingQuestionUpgrader()
    
    logger.info("🔄 Starting comprehensive upgrade of existing questions...")
    success = await upgrader.run_comprehensive_upgrade()
    
    if success:
        logger.info("✅ Comprehensive upgrade completed successfully!")
    else:
        logger.error("❌ Comprehensive upgrade failed!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)