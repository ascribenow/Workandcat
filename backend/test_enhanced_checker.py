#!/usr/bin/env python3
"""
Test Enhanced Enrichment Checker
Test the updated checker logic with placeholder detection
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_checker():
    """Test the enhanced enrichment checker"""
    try:
        database_url = os.getenv('DATABASE_URL')
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        from enhanced_enrichment_checker_service import EnhancedEnrichmentCheckerService
        
        checker = EnhancedEnrichmentCheckerService()
        
        with SessionLocal() as db:
            print("🔍 Testing Enhanced Enrichment Checker with updated validation...")
            
            # Test PYQ questions check
            result = await checker.check_and_enrich_pyq_questions(db, limit=5)
            
            if result.get("success"):
                check_results = result.get("check_results", {})
                
                print("\n" + "="*60)
                print("ENHANCED CHECKER TEST RESULTS")
                print("="*60)
                print(f"Questions Checked: {check_results.get('total_questions_checked', 0)}")
                print(f"Poor Enrichment Identified: {check_results.get('poor_enrichment_identified', 0)}")
                print(f"Re-enrichment Attempted: {check_results.get('re_enrichment_attempted', 0)}")
                print(f"Re-enrichment Successful: {check_results.get('re_enrichment_successful', 0)}")
                print(f"Perfect Quality Count: {check_results.get('perfect_quality_count', 0)}")
                print(f"Perfect Quality Percentage: {check_results.get('perfect_quality_percentage', 0):.1f}%")
                print("="*60)
                
                # Show detailed results for failed questions
                detailed_results = check_results.get('detailed_results', [])
                if detailed_results:
                    print("\nDETAILED VALIDATION FAILURES:")
                    for i, result in enumerate(detailed_results[:3], 1):
                        print(f"\n{i}. Question ID: {result['question_id']}")
                        print(f"   Stem: {result['stem']}")
                        print(f"   Failed Criteria: {result['failed_criteria']}")
                        print(f"   Quality Issues: {result['quality_issues'][:2]}")  # Show first 2 issues
                        if len(result['quality_issues']) > 2:
                            print(f"   ... and {len(result['quality_issues']) - 2} more issues")
                
            else:
                print(f"❌ Enhanced checker test failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_checker())