#!/usr/bin/env python3
"""
Debug Taxonomy Path Validation Issue
"""

import asyncio
from canonical_taxonomy_service import canonical_taxonomy_service
from canonical_taxonomy_data import CANONICAL_TAXONOMY

def debug_taxonomy_validation():
    """Debug taxonomy path validation"""
    
    print("🐛 DEBUGGING TAXONOMY PATH VALIDATION")
    print("=" * 50)
    
    # Test case from our debug
    test_category = "ARITHMETIC"
    test_subcategory = "Time-Speed-Distance"
    test_type = "Basics"
    
    print(f"Testing taxonomy path:")
    print(f"  Category: '{test_category}'")
    print(f"  Subcategory: '{test_subcategory}'")
    print(f"  Type: '{test_type}'")
    
    # Check what's actually in the canonical taxonomy
    print(f"\n📋 Available categories in canonical taxonomy:")
    for category in CANONICAL_TAXONOMY.keys():
        print(f"  - '{category}'")
    
    # Check if category matches
    category_match = test_category in CANONICAL_TAXONOMY
    print(f"\n🔍 Category match: '{test_category}' in taxonomy = {category_match}")
    
    if not category_match:
        # Check case variations
        for canon_category in CANONICAL_TAXONOMY.keys():
            if canon_category.lower() == test_category.lower():
                print(f"   ⚠️ Case mismatch! Found '{canon_category}' (canonical) vs '{test_category}' (test)")
                test_category = canon_category
                category_match = True
                break
    
    if category_match:
        print(f"\n📋 Available subcategories in '{test_category}':")
        subcategories = list(CANONICAL_TAXONOMY[test_category].keys())
        for subcategory in subcategories:
            print(f"  - '{subcategory}'")
        
        # Check subcategory match
        subcategory_match = test_subcategory in CANONICAL_TAXONOMY[test_category]
        print(f"\n🔍 Subcategory match: '{test_subcategory}' in '{test_category}' = {subcategory_match}")
        
        if subcategory_match:
            print(f"\n📋 Available question types in '{test_category}' → '{test_subcategory}':")
            question_types = list(CANONICAL_TAXONOMY[test_category][test_subcategory]['types'].keys())
            for q_type in question_types:
                print(f"  - '{q_type}'")
            
            # Check type match
            type_match = test_type in CANONICAL_TAXONOMY[test_category][test_subcategory]['types']
            print(f"\n🔍 Type match: '{test_type}' in '{test_category}' → '{test_subcategory}' = {type_match}")
            
            # Final validation
            is_valid = canonical_taxonomy_service.validate_taxonomy_path(
                test_category, test_subcategory, test_type
            )
            print(f"\n📊 Final validation result: {is_valid}")
            
        else:
            print(f"❌ Subcategory '{test_subcategory}' not found in '{test_category}'")
    else:
        print(f"❌ Category '{test_category}' not found in canonical taxonomy")
    
    print("\n🎉 Taxonomy Validation Debug Complete!")

if __name__ == "__main__":
    debug_taxonomy_validation()