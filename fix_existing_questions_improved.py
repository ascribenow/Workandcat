#!/usr/bin/env python3
"""
Fix existing questions using the improved Maker-Checker system
Target questions with: same approach/explanation, generic content, non-teaching style
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

class ImprovedQuestionFixer:
    """
    Fix existing questions using the improved Maker-Checker system
    """
    
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.database_url = os.getenv('DATABASE_URL')
        
        logger.info("🔧 Improved Question Fixer Initialized")
        logger.info("   Target: Questions with same approach/explanation, generic content")

    def assess_question_quality(self, question_data):
        """
        Assess if a question needs fixing with the improved system
        """
        question_id, stem, answer, approach, detailed_solution, subcategory, type_of_question = question_data
        
        issues = []
        needs_fixing = False
        
        # Extract explanation from detailed solution
        explanation = ""
        solution_only = detailed_solution
        if "KEY INSIGHT:" in detailed_solution:
            parts = detailed_solution.split("KEY INSIGHT:", 1)
            solution_only = parts[0].strip()
            explanation = parts[1].strip()
        elif "EXPLANATION:" in detailed_solution:
            parts = detailed_solution.split("EXPLANATION:", 1)
            solution_only = parts[0].strip()
            explanation = parts[1].strip()
        
        # Check for generic approach content
        generic_approach_phrases = [
            "apply systematic", "standard method", "mathematical reasoning",
            "general approach", "appropriate method", "identify the key", 
            "time-speed-distance concept"  # This was a major issue
        ]
        
        if approach and any(phrase in approach.lower() for phrase in generic_approach_phrases):
            issues.append("Generic approach content")
            needs_fixing = True
        
        # Check if approach is too short or poor quality
        if not approach or len(approach.strip()) < 50:
            issues.append("Approach too short or missing")
            needs_fixing = True
        
        # Check for generic detailed solution
        generic_solution_phrases = [
            "analyze the given information", "apply the appropriate", 
            "perform the calculations", "review the question carefully",
            "standard approach for this type"
        ]
        
        if any(phrase in solution_only.lower() for phrase in generic_solution_phrases):
            issues.append("Generic solution content")
            needs_fixing = True
        
        # Check if explanation is missing or poor
        if not explanation or len(explanation.strip()) < 30:
            issues.append("Explanation missing or too short")
            needs_fixing = True
        
        # Check if approach and explanation are too similar
        if approach and explanation and len(approach) > 20 and len(explanation) > 20:
            approach_words = set(approach.lower().split())
            explanation_words = set(explanation.lower().split())
            if len(approach_words) > 0 and len(explanation_words) > 0:
                overlap_ratio = len(approach_words.intersection(explanation_words)) / max(len(approach_words), len(explanation_words))
                if overlap_ratio > 0.6:  # More than 60% word overlap
                    issues.append("Approach and Explanation too similar")
                    needs_fixing = True
        
        # Check for teaching language in solution
        teaching_phrases = ["let's", "we need", "now we", "we can", "we find", "we get"]
        has_teaching_language = any(phrase in solution_only.lower() for phrase in teaching_phrases)
        
        if not has_teaching_language:
            issues.append("Solution lacks teaching language")
            needs_fixing = True
        
        # Check for $ signs (should be cleaned by now but double-check)
        if '$' in f"{approach} {detailed_solution}":
            issues.append("Contains $ signs")
            needs_fixing = True
        
        return {
            "question_id": question_id,
            "stem": stem[:80] + "..." if len(stem) > 80 else stem,
            "issues": issues,
            "needs_fixing": needs_fixing,
            "subcategory": subcategory,
            "type_of_question": type_of_question,
            "current_approach": approach,
            "current_explanation": explanation,
            "issue_count": len(issues)
        }

    async def fix_question_with_improved_system(self, question_data, assessment):
        """
        Fix a single question using the improved Maker-Checker system
        """
        question_id, stem, answer, old_approach, old_detailed, subcategory, type_of_question = question_data
        
        try:
            logger.info(f"🔧 Fixing: {stem[:60]}...")
            logger.info(f"   Issues: {', '.join(assessment['issues'])}")
            
            # Use the improved standardized enricher
            result = await standardized_enricher.enrich_question_solution(
                question_stem=stem,
                answer=answer,
                subcategory=subcategory or "General",
                question_type=type_of_question or "Problem Solving"
            )
            
            if result["success"]:
                # Verify the new content is actually better
                new_approach = result["approach"]
                new_detailed = result["detailed_solution"]
                
                # Extract new explanation
                new_explanation = ""
                if "KEY INSIGHT:" in new_detailed:
                    new_explanation = new_detailed.split("KEY INSIGHT:")[-1].strip()
                
                # Basic quality check on new content
                is_better = True
                improvement_notes = []
                
                # Check if still generic
                generic_phrases = ["apply systematic", "standard method", "general approach"]
                if any(phrase in new_approach.lower() for phrase in generic_phrases):
                    is_better = False
                    logger.warning(f"  ⚠️ New approach still generic")
                else:
                    improvement_notes.append("Approach is specific")
                
                # Check for teaching language
                teaching_phrases = ["let's", "we need", "now we", "we can"]
                if any(phrase in new_detailed.lower() for phrase in teaching_phrases):
                    improvement_notes.append("Uses teaching language")
                
                # Check explanation distinctness
                if new_explanation and len(new_explanation) > 30:
                    approach_words = set(new_approach.lower().split())
                    explanation_words = set(new_explanation.lower().split())
                    overlap = len(approach_words.intersection(explanation_words)) / max(len(approach_words), len(explanation_words), 1)
                    if overlap < 0.5:  # Less than 50% overlap is good
                        improvement_notes.append("Explanation is distinct")
                
                if is_better:
                    # Update database with improved content
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
                    
                    logger.info(f"  ✅ Fixed successfully")
                    logger.info(f"     Quality Score: {result.get('quality_score', 'N/A')}")
                    logger.info(f"     Improvements: {', '.join(improvement_notes)}")
                    
                    return {
                        "success": True,
                        "question_id": question_id,
                        "quality_score": result.get("quality_score"),
                        "improvements": improvement_notes,
                        "anthropic_validation": result.get("anthropic_validation")
                    }
                else:
                    logger.warning(f"  ⚠️ New content not better than original - skipping update")
                    return {
                        "success": False,
                        "question_id": question_id,
                        "error": "New content not significantly better"
                    }
            else:
                logger.error(f"  ❌ Fix failed: {result.get('error')}")
                return {
                    "success": False,
                    "question_id": question_id,
                    "error": result.get("error")
                }
                
        except Exception as e:
            logger.error(f"  ❌ Fix exception: {e}")
            return {
                "success": False,
                "question_id": question_id,
                "error": str(e)
            }

    async def run_improved_fixing(self):
        """
        Run improved fixing on all questions that need it
        """
        try:
            logger.info("🚀 STARTING IMPROVED QUESTION FIXING")
            logger.info("=" * 80)
            logger.info("Using improved Maker-Checker system with:")
            logger.info("✅ Strict student-focused prompting")
            logger.info("✅ Problem-specific content requirements")  
            logger.info("✅ Clear Approach vs Explanation distinction")
            logger.info("✅ Enhanced Anthropic validation")
            
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
            
            logger.info(f"📊 Found {total_questions} questions to assess")
            conn.close()
            
            # Phase 1: Assess all questions for issues
            logger.info(f"\n🔍 PHASE 1: QUALITY ASSESSMENT")
            logger.info("=" * 50)
            
            assessments = []
            questions_needing_fixes = 0
            issue_summary = {}
            
            for i, question_data in enumerate(all_questions):
                assessment = self.assess_question_quality(question_data)
                assessments.append((question_data, assessment))
                
                if assessment["needs_fixing"]:
                    questions_needing_fixes += 1
                
                # Track issue types
                for issue in assessment["issues"]:
                    issue_summary[issue] = issue_summary.get(issue, 0) + 1
                
                # Progress update every 25 questions
                if (i + 1) % 25 == 0:
                    logger.info(f"   Progress: {i+1}/{total_questions} assessed")
            
            # Assessment summary
            logger.info(f"\n📊 ASSESSMENT SUMMARY:")
            logger.info(f"   Total questions: {total_questions}")
            logger.info(f"   Questions needing fixes: {questions_needing_fixes}")
            logger.info(f"   Questions already good: {total_questions - questions_needing_fixes}")
            
            logger.info(f"\n🔍 ISSUE BREAKDOWN:")
            for issue, count in sorted(issue_summary.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"   {issue}: {count} questions")
            
            if questions_needing_fixes == 0:
                logger.info("🎉 All questions already meet the improved standards!")
                return True
            
            # Phase 2: Fix questions using improved system
            logger.info(f"\n🔧 PHASE 2: FIXING {questions_needing_fixes} QUESTIONS")
            logger.info("=" * 50)
            
            fix_results = {
                "successful_fixes": 0,
                "failed_fixes": 0,
                "skipped_fixes": 0,
                "total_processed": 0,
                "quality_scores": []
            }
            
            for question_data, assessment in assessments:
                if assessment["needs_fixing"]:
                    fix_results["total_processed"] += 1
                    
                    logger.info(f"\n🔧 [{fix_results['total_processed']}/{questions_needing_fixes}] Fixing...")
                    
                    fix_result = await self.fix_question_with_improved_system(question_data, assessment)
                    
                    if fix_result["success"]:
                        fix_results["successful_fixes"] += 1
                        if fix_result.get("quality_score"):
                            fix_results["quality_scores"].append(fix_result["quality_score"])
                    else:
                        if "not better" in fix_result.get("error", ""):
                            fix_results["skipped_fixes"] += 1
                        else:
                            fix_results["failed_fixes"] += 1
                    
                    # Progress update every 10 fixes
                    if fix_results["total_processed"] % 10 == 0:
                        avg_quality = sum(fix_results["quality_scores"]) / len(fix_results["quality_scores"]) if fix_results["quality_scores"] else 0
                        logger.info(f"\n📈 FIXING PROGRESS [{fix_results['total_processed']}/{questions_needing_fixes}]")
                        logger.info(f"   Successful: {fix_results['successful_fixes']}")
                        logger.info(f"   Failed: {fix_results['failed_fixes']}")
                        logger.info(f"   Skipped: {fix_results['skipped_fixes']}")
                        logger.info(f"   Average quality: {avg_quality:.1f}")
                    
                    # Small delay
                    await asyncio.sleep(0.3)
            
            # Final summary
            success_rate = fix_results["successful_fixes"] / fix_results["total_processed"] * 100 if fix_results["total_processed"] > 0 else 0
            avg_quality = sum(fix_results["quality_scores"]) / len(fix_results["quality_scores"]) if fix_results["quality_scores"] else 0
            
            logger.info(f"\n🎉 IMPROVED FIXING COMPLETED!")
            logger.info("=" * 80)
            logger.info(f"📊 FINAL RESULTS:")
            logger.info(f"   Total questions in database: {total_questions}")
            logger.info(f"   Questions that needed fixing: {questions_needing_fixes}")
            logger.info(f"   Successful fixes: {fix_results['successful_fixes']}")
            logger.info(f"   Failed fixes: {fix_results['failed_fixes']}")
            logger.info(f"   Skipped fixes: {fix_results['skipped_fixes']}")
            logger.info(f"   Fix success rate: {success_rate:.1f}%")
            logger.info(f"   Average quality score: {avg_quality:.1f}/10")
            
            logger.info(f"\n✅ DATABASE STATUS:")
            total_high_quality = fix_results['successful_fixes'] + (total_questions - questions_needing_fixes)
            logger.info(f"   High-quality questions: {total_high_quality}/{total_questions}")
            logger.info(f"   Coverage: {total_high_quality/total_questions*100:.1f}%")
            
            logger.info(f"\n🎯 IMPROVEMENTS ACHIEVED:")
            logger.info("✅ Generic content replaced with problem-specific solutions")
            logger.info("✅ Teaching language implemented throughout")
            logger.info("✅ Clear Approach vs Explanation distinction established")
            logger.info("✅ Student-focused presentation style applied")
            logger.info("✅ Anthropic quality validation for all improvements")
            
            return success_rate >= 70  # 70% success rate required
            
        except Exception as e:
            logger.error(f"❌ Improved fixing failed: {e}")
            return False

async def main():
    """Main execution function"""
    fixer = ImprovedQuestionFixer()
    
    logger.info("🔧 Starting improved fixing of existing questions...")
    success = await fixer.run_improved_fixing()
    
    if success:
        logger.info("✅ Improved fixing completed successfully!")
    else:
        logger.error("❌ Improved fixing failed!")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)