#!/usr/bin/env python3
"""
Test Enhanced Semantic Matching Implementation
"""

import asyncio
import os
from canonical_taxonomy_service import canonical_taxonomy_service

async def test_enhanced_semantic_matching():
    """Test the NEW enhanced semantic matching implementation with NEW FLOW"""
    
    print("🧪 Testing NEW Enhanced Semantic Matching Implementation")
    print("🔄 NEW FLOW: Subcategory → Type → Category (lookup)")
    print("=" * 70)
    
    # Test NEW FLOW: Global subcategory matching
    print("\n📋 Testing NEW: Enhanced Global Subcategory Matching:")
    subcategory_tests = [
        "Speed Problems",       # Should match to Time-Speed-Distance
        "Interest Calculations", # Should match to Simple and Compound Interest  
        "Circle Properties",    # Should match to Circles
        "Area Problems",        # Should match to Areas and Volumes
    ]
    
    for test_subcategory in subcategory_tests:
        print(f"\n🔍 Testing global subcategory: '{test_subcategory}'")
        try:
            result = await canonical_taxonomy_service.match_subcategory_without_category(test_subcategory)
            print(f"✅ Result: '{test_subcategory}' → '{result}'")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test question type matching within subcategory
    print("\n📝 Testing NEW: Question Type Matching Within Subcategory:")
    print(f"\n🔍 Testing question type: 'Basic Speed Problem' within 'Time-Speed-Distance'")
    try:
        result = await canonical_taxonomy_service.match_question_type_within_subcategory(
            "Basic Speed Problem", "Time-Speed-Distance"
        )
        print(f"✅ Result: 'Basic Speed Problem' → '{result}'")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test code-based category lookup
    print("\n💻 Testing NEW: Code-based Category Lookup:")
    lookup_tests = [
        ("Time-Speed-Distance", "Basics"),
        ("Simple and Compound Interest", "Basics"),
        ("Circles", "Basics"),
    ]
    
    for subcategory, question_type in lookup_tests:
        print(f"\n🔍 Testing lookup: '{subcategory}' + '{question_type}'")
        try:
            result = canonical_taxonomy_service.lookup_category_by_combination(subcategory, question_type)
            print(f"✅ Result: LOOKUP('{subcategory}' + '{question_type}') → '{result}'")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test complete NEW FLOW taxonomy path
    print("\n🎯 Testing Complete NEW FLOW Taxonomy Path:")
    test_cases = [
        ("Math", "Speed", "Basic Problem"),
        ("Unknown", "Interest Rate", "Simple Calculation"),  
        ("Generic", "Circle Area", "Basic Formula"),
    ]
    
    for llm_category, llm_subcategory, llm_type in test_cases:
        print(f"\n🔍 Testing NEW FLOW: '{llm_category}' → '{llm_subcategory}' → '{llm_type}'")
        try:
            category, subcategory, question_type = await canonical_taxonomy_service.get_canonical_taxonomy_path(
                llm_category, llm_subcategory, llm_type
            )
            print(f"✅ NEW FLOW Complete mapping:")
            print(f"   Input: ('{llm_category}', '{llm_subcategory}', '{llm_type}')")
            print(f"   Step 1 - Subcategory: '{llm_subcategory}' → '{subcategory}'")
            print(f"   Step 2 - Type: '{llm_type}' → '{question_type}'")
            print(f"   Step 3 - Category: LOOKUP('{subcategory}' + '{question_type}') → '{category}'")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎉 NEW Enhanced Semantic Matching Flow Test Complete!")

if __name__ == "__main__":
    # Set OpenAI API key for testing
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️ OPENAI_API_KEY not set - tests may fail")
    
    asyncio.run(test_enhanced_semantic_matching())