#!/usr/bin/env python3
"""
Test Enhanced Semantic Matching Implementation
"""

import asyncio
import os
from canonical_taxonomy_service import canonical_taxonomy_service

async def test_enhanced_semantic_matching():
    """Test the enhanced semantic matching implementation"""
    
    print("🧪 Testing Enhanced Semantic Matching Implementation")
    print("=" * 60)
    
    # Test enhanced category matching
    print("\n📂 Testing Enhanced Category Matching:")
    category_tests = [
        "Basic Math",          # Should match to some category
        "Calculation Problems", # Should match to Arithmetic
        "Shape Analysis",      # Should match to Geometry and Mensuration
    ]
    
    for test_category in category_tests:
        print(f"\n🔍 Testing category: '{test_category}'")
        try:
            result = await canonical_taxonomy_service.match_category(test_category)
            print(f"✅ Result: '{test_category}' → '{result}'")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test enhanced subcategory matching  
    print("\n📋 Testing Enhanced Subcategory Matching:")
    print(f"\n🔍 Testing subcategory: 'Speed Problems' in 'Arithmetic'")
    try:
        result = await canonical_taxonomy_service.match_subcategory("Speed Problems", "Arithmetic")
        print(f"✅ Result: 'Speed Problems' → '{result}'")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test enhanced question type matching
    print("\n📝 Testing Enhanced Question Type Matching:")
    print(f"\n🔍 Testing question type: 'Basic Speed Problem' in 'Arithmetic' → 'Time-Speed-Distance'")
    try:
        result = await canonical_taxonomy_service.match_question_type(
            "Basic Speed Problem", "Arithmetic", "Time-Speed-Distance"
        )
        print(f"✅ Result: 'Basic Speed Problem' → '{result}'")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test complete taxonomy path
    print("\n🎯 Testing Complete Enhanced Taxonomy Path:")
    print(f"\n🔍 Testing complete path: 'Math' → 'Speed' → 'Basic Problem'")
    try:
        category, subcategory, question_type = await canonical_taxonomy_service.get_canonical_taxonomy_path(
            "Math", "Speed", "Basic Problem"
        )
        print(f"✅ Complete mapping:")
        print(f"   Category: 'Math' → '{category}'")
        print(f"   Subcategory: 'Speed' → '{subcategory}'")
        print(f"   Type: 'Basic Problem' → '{question_type}'")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Enhanced Semantic Matching Test Complete!")

if __name__ == "__main__":
    # Set OpenAI API key for testing
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️ OPENAI_API_KEY not set - tests may fail")
    
    asyncio.run(test_enhanced_semantic_matching())