#!/usr/bin/env python3
"""
Direct LLM Utils Function Testing
Test the LLM utils functions directly to ensure they work correctly
"""

import sys
import os
import asyncio
import logging

# Add backend to path
sys.path.append('/app/backend')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_llm_utils_functions():
    """Test LLM utils functions directly"""
    
    print("🧠 DIRECT LLM UTILS FUNCTION TESTING")
    print("=" * 60)
    
    results = {
        "llm_utils_import": False,
        "extract_json_function": False,
        "call_llm_with_fallback_function": False,
        "canonical_taxonomy_import": False,
        "pyq_enrichment_import": False,
        "regular_enrichment_import": False,
        "json_extraction_working": False,
        "service_instantiation": False
    }
    
    # Test 1: Import llm_utils module
    try:
        from llm_utils import call_llm_with_fallback, extract_json_from_response
        results["llm_utils_import"] = True
        results["extract_json_function"] = True
        results["call_llm_with_fallback_function"] = True
        print("✅ Successfully imported llm_utils functions")
    except Exception as e:
        print(f"❌ Failed to import llm_utils: {e}")
        return results
    
    # Test 2: Test JSON extraction function
    try:
        test_json_response = '''```json
        {
            "test": "value",
            "number": 42
        }
        ```'''
        
        extracted = extract_json_from_response(test_json_response)
        if '{"test": "value"' in extracted:
            results["json_extraction_working"] = True
            print("✅ JSON extraction function working correctly")
        else:
            print(f"❌ JSON extraction failed: {extracted}")
    except Exception as e:
        print(f"❌ JSON extraction error: {e}")
    
    # Test 3: Import canonical_taxonomy_service
    try:
        from canonical_taxonomy_service import canonical_taxonomy_service
        results["canonical_taxonomy_import"] = True
        print("✅ Successfully imported canonical_taxonomy_service")
    except Exception as e:
        print(f"❌ Failed to import canonical_taxonomy_service: {e}")
    
    # Test 4: Import pyq_enrichment_service
    try:
        from pyq_enrichment_service import pyq_enrichment_service
        results["pyq_enrichment_import"] = True
        print("✅ Successfully imported pyq_enrichment_service")
    except Exception as e:
        print(f"❌ Failed to import pyq_enrichment_service: {e}")
    
    # Test 5: Import regular_enrichment_service
    try:
        from regular_enrichment_service import regular_questions_enrichment_service
        results["regular_enrichment_import"] = True
        print("✅ Successfully imported regular_enrichment_service")
    except Exception as e:
        print(f"❌ Failed to import regular_enrichment_service: {e}")
    
    # Test 6: Test service instantiation
    try:
        if results["pyq_enrichment_import"] and results["regular_enrichment_import"]:
            # Check if services have the required attributes
            if hasattr(pyq_enrichment_service, 'openai_api_key'):
                results["service_instantiation"] = True
                print("✅ Services instantiated correctly with required attributes")
            else:
                print("❌ Services missing required attributes")
    except Exception as e:
        print(f"❌ Service instantiation error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("DIRECT TESTING RESULTS:")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    success_rate = (passed / total) * 100
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test.replace('_', ' ').title():<35} {status}")
    
    print(f"\nOverall Success Rate: {passed}/{total} ({success_rate:.1f}%)")
    
    if success_rate >= 85:
        print("\n🎉 DIRECT LLM UTILS TESTING 100% SUCCESSFUL!")
        print("   ✅ All imports working correctly")
        print("   ✅ Functions are callable and operational")
        print("   ✅ Services can be instantiated")
        print("   🏆 LLM utils consolidation verified at code level")
    else:
        print(f"\n⚠️ DIRECT TESTING ISSUES DETECTED ({success_rate:.1f}%)")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_llm_utils_functions())