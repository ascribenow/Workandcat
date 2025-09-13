#!/usr/bin/env python3
"""
Test script to verify PYQ Frequency Fix - Phase 2 is working correctly
"""

import asyncio
from regular_enrichment_service import regular_questions_enrichment_service

async def test_pyq_frequency_fix():
    print("🧪 TESTING PYQ FREQUENCY FIX - PHASE 2")
    print("=" * 45)
    
    # Test case 1: Easy question (difficulty <= 1.5) - should return 0.5 immediately
    print("\n📝 Test Case 1: Easy Question (difficulty ≤ 1.5)")
    print("-" * 50)
    
    easy_enrichment_data = {
        'category': 'Arithmetic',
        'subcategory': 'Basic Math',
        'difficulty_score': 1.2  # Below threshold
    }
    
    result1 = await regular_questions_enrichment_service._calculate_pyq_frequency_score_llm(
        "Simple addition: 2 + 2 = ?", 
        easy_enrichment_data
    )
    
    print(f"✅ Easy question result: {result1}")
    print(f"✅ Expected: 0.5 (LOW) - {'PASS' if result1 == 0.5 else 'FAIL'}")
    
    # Test case 2: Hard question (difficulty > 1.5) - should proceed with PYQ comparison
    print("\n📝 Test Case 2: Hard Question (difficulty > 1.5)")
    print("-" * 50)
    
    hard_enrichment_data = {
        'category': 'Arithmetic',
        'subcategory': 'Time-Speed-Distance',
        'difficulty_score': 3.5  # Above threshold
    }
    
    result2 = await regular_questions_enrichment_service._calculate_pyq_frequency_score_llm(
        "Complex train problem with multiple variables", 
        hard_enrichment_data
    )
    
    print(f"✅ Hard question result: {result2}")
    print(f"✅ Expected: 0.5, 1.0, or 1.5 based on PYQ matches - {'PASS' if result2 in [0.5, 1.0, 1.5] else 'FAIL'}")
    
    print("\n🎉 PYQ FREQUENCY FIX VERIFICATION COMPLETE")
    print("=" * 45)
    
    return result1 == 0.5 and result2 in [0.5, 1.0, 1.5]

if __name__ == "__main__":
    success = asyncio.run(test_pyq_frequency_fix())
    print(f"\n🎯 Overall Test Result: {'✅ PASS' if success else '❌ FAIL'}")