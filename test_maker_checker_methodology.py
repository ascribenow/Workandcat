#!/usr/bin/env python3
"""
Test the new Gemini (Maker) → Anthropic (Checker) methodology
Demonstrate improved approach and explanation quality
"""

import sys
import os
sys.path.append('/app/backend')

import logging
import asyncio
import psycopg2
from dotenv import load_dotenv
from standardized_enrichment_engine import standardized_enricher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MakerCheckerTester:
    """
    Test the Gemini (Maker) → Anthropic (Checker) methodology
    """
    
    def __init__(self):
        load_dotenv('/app/backend/.env')
        self.database_url = os.getenv('DATABASE_URL')
        self.standardized_enricher = standardized_enricher
        
        logger.info("🧪 Gemini (Maker) → Anthropic (Checker) Tester Initialized")

    async def test_methodology_on_sample_questions(self):
        """
        Test the methodology on a few sample questions to show improvement
        """
        try:
            logger.info("🧪 TESTING GEMINI (MAKER) → ANTHROPIC (CHECKER) METHODOLOGY")
            logger.info("=" * 80)
            
            # Get sample questions
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT id, stem, answer, subcategory, type_of_question,
                       solution_approach, detailed_solution
                FROM questions 
                ORDER BY id
                LIMIT 5
            """)
            
            questions = cur.fetchall()
            logger.info(f"📊 Testing methodology on {len(questions)} sample questions")
            
            conn.close()
            
            # Test each question
            results = []
            
            for i, question_data in enumerate(questions):
                question_id, stem, answer, subcategory, question_type, old_approach, old_detailed = question_data
                
                logger.info(f"\n🧪 [{i+1}/{len(questions)}] Testing: {stem[:60]}...")
                logger.info(f"📂 Category: {subcategory} -> {question_type}")
                
                # Show current content
                logger.info(f"\n📋 CURRENT CONTENT:")
                logger.info(f"Current Approach: {old_approach[:100]}..." if old_approach else "No approach")
                
                # Test new methodology
                logger.info(f"\n🔄 TESTING NEW METHODOLOGY...")
                result = await self.standardized_enricher.enrich_question_solution(
                    question_stem=stem,
                    answer=answer or "To be determined", 
                    subcategory=subcategory or "General",
                    question_type=question_type or "Problem Solving"
                )
                
                if result["success"]:
                    logger.info(f"✅ Methodology test successful!")
                    logger.info(f"🎯 Workflow: {result.get('workflow', 'Unknown')}")
                    logger.info(f"📊 Quality Score: {result.get('quality_score', 'N/A')}")
                    
                    # Show new content
                    logger.info(f"\n📋 NEW METHODOLOGY CONTENT:")
                    logger.info(f"New Approach: {result.get('approach', '')[:150]}...")
                    if 'anthropic_validation' in result:
                        anthro_val = result['anthropic_validation']
                        logger.info(f"🔍 Anthropic Assessment:")
                        logger.info(f"   Approach Quality: {anthro_val.get('approach_quality', 'N/A')}")
                        logger.info(f"   Explanation Quality: {anthro_val.get('explanation_quality', 'N/A')}")
                        logger.info(f"   Recommendation: {anthro_val.get('recommendation', 'N/A')}")
                    
                    results.append({
                        "question_id": question_id,
                        "success": True,
                        "quality_score": result.get('quality_score'),
                        "workflow": result.get('workflow'),
                        "anthropic_approved": 'anthropic_validation' in result
                    })
                else:
                    logger.error(f"❌ Methodology test failed: {result.get('error')}")
                    results.append({
                        "question_id": question_id,
                        "success": False,
                        "error": result.get('error')
                    })
                
                # Small delay
                await asyncio.sleep(1)
            
            # Summary
            successful = sum(1 for r in results if r["success"])
            avg_quality = sum(r.get("quality_score", 0) for r in results if r.get("quality_score")) / len([r for r in results if r.get("quality_score")]) if any(r.get("quality_score") for r in results) else 0
            anthropic_validated = sum(1 for r in results if r.get("anthropic_approved"))
            
            logger.info(f"\n🎉 METHODOLOGY TEST COMPLETED!")
            logger.info("=" * 80)
            logger.info(f"📊 Total tests: {len(results)}")
            logger.info(f"✅ Successful: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
            logger.info(f"📈 Average quality score: {avg_quality:.1f}/10")
            logger.info(f"🔍 Anthropic validated: {anthropic_validated}/{len(results)}")
            
            # Show workflow distribution
            workflows = {}
            for r in results:
                if r["success"]:
                    workflow = r.get("workflow", "Unknown")
                    workflows[workflow] = workflows.get(workflow, 0) + 1
            
            logger.info(f"\n🔄 WORKFLOW DISTRIBUTION:")
            for workflow, count in workflows.items():
                logger.info(f"   {workflow}: {count}")
            
            return {
                "success": True,
                "total_tests": len(results),
                "successful": successful,
                "average_quality": avg_quality,
                "anthropic_validated": anthropic_validated,
                "workflows": workflows
            }
            
        except Exception as e:
            logger.error(f"❌ Methodology testing failed: {e}")
            return {"success": False, "error": str(e)}

    async def demonstrate_before_after_comparison(self):
        """
        Show a before/after comparison of approach and explanation quality
        """
        try:
            logger.info("🔍 BEFORE/AFTER COMPARISON DEMONSTRATION")
            logger.info("=" * 80)
            
            # Get one sample question
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT stem, answer, subcategory, type_of_question,
                       solution_approach, detailed_solution
                FROM questions 
                WHERE solution_approach IS NOT NULL 
                AND detailed_solution IS NOT NULL
                ORDER BY id
                LIMIT 1
            """)
            
            question_data = cur.fetchone()
            conn.close()
            
            if not question_data:
                logger.error("No suitable question found for demonstration")
                return
            
            stem, answer, subcategory, question_type, old_approach, old_detailed = question_data
            
            logger.info(f"📝 Demo Question: {stem[:100]}...")
            logger.info(f"📂 Category: {subcategory} -> {question_type}")
            logger.info(f"✅ Answer: {answer}")
            
            # Show BEFORE (current content)
            logger.info(f"\n📋 BEFORE (Current Content):")
            logger.info("=" * 50)
            logger.info(f"APPROACH:\n{old_approach}")
            
            # Extract explanation from detailed solution if present
            old_explanation = "Not clearly separated"
            if "KEY INSIGHT:" in old_detailed:
                old_explanation = old_detailed.split("KEY INSIGHT:")[-1].strip()
            elif "EXPLANATION:" in old_detailed:
                old_explanation = old_detailed.split("EXPLANATION:")[-1].strip()
            
            logger.info(f"\nEXPLANATION:\n{old_explanation}")
            
            # Generate AFTER (new methodology)
            logger.info(f"\n🔄 GENERATING WITH NEW METHODOLOGY...")
            result = await self.standardized_enricher.enrich_question_solution(
                question_stem=stem,
                answer=answer,
                subcategory=subcategory,
                question_type=question_type
            )
            
            if result["success"]:
                # Show AFTER (new methodology content)
                logger.info(f"\n📋 AFTER (New Methodology):")
                logger.info("=" * 50)
                logger.info(f"APPROACH:\n{result.get('approach', 'N/A')}")
                
                # Extract explanation from new detailed solution
                new_detailed = result.get('detailed_solution', '')
                new_explanation = "Not found"
                if "KEY INSIGHT:" in new_detailed:
                    new_explanation = new_detailed.split("KEY INSIGHT:")[-1].strip()
                elif "EXPLANATION:" in new_detailed:
                    new_explanation = new_detailed.split("EXPLANATION:")[-1].strip()
                
                logger.info(f"\nEXPLANATION:\n{new_explanation}")
                
                # Show quality assessment if available
                if 'anthropic_validation' in result:
                    anthro_val = result['anthropic_validation']
                    logger.info(f"\n🔍 ANTHROPIC QUALITY ASSESSMENT:")
                    logger.info("=" * 50)
                    logger.info(f"Approach Quality: {anthro_val.get('approach_quality', 'N/A')}")
                    logger.info(f"Explanation Quality: {anthro_val.get('explanation_quality', 'N/A')}")
                    logger.info(f"Overall Score: {anthro_val.get('overall_score', 'N/A')}/10")
                    logger.info(f"Recommendation: {anthro_val.get('recommendation', 'N/A')}")
                    logger.info(f"Schema Compliance: {anthro_val.get('schema_compliance', 'N/A')}")
                    if anthro_val.get('specific_feedback', 'None') != 'None':
                        logger.info(f"Specific Feedback: {anthro_val.get('specific_feedback')}")
                
                logger.info(f"\n🎯 METHODOLOGY SUCCESS!")
                logger.info(f"Workflow: {result.get('workflow')}")
                logger.info(f"Quality Score: {result.get('quality_score')}/10")
                
            else:
                logger.error(f"❌ New methodology failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Before/after demonstration failed: {e}")

async def main():
    """Main execution function"""
    tester = MakerCheckerTester()
    
    logger.info("🧪 Starting Gemini (Maker) → Anthropic (Checker) methodology testing...")
    
    # Run demonstration
    await tester.demonstrate_before_after_comparison()
    
    # Run sample tests
    results = await tester.test_methodology_on_sample_questions()
    
    if results["success"]:
        logger.info("✅ Methodology testing completed successfully!")
    else:
        logger.error("❌ Methodology testing failed!")
    
    return results["success"]

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)