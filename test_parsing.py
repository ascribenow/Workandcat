#!/usr/bin/env python3
"""
Test MCQ Options Parsing directly
"""

import os
import sys
sys.path.append('/app/backend')

from services.v2_pack_assembly import V2PackAssemblyService
import json

def test_parsing():
    """Test the new MCQ parsing method directly"""
    
    service = V2PackAssemblyService()
    
    # Test data from our database
    test_cases = [
        ('["20%", "30%", "35.2%", "40%"]', '35.2%'),
        ('["10 hours", "40/3 hours", "15 hours", "8 hours"]', '40/3 hours'),
        ('["24 km/hr", "35 km/hr", "42 km/hr", "48 km/hr"]', '42 km/hr')
    ]
    
    print("🧪 Testing MCQ Options Parsing")
    print("=" * 50)
    
    for i, (json_options, expected_answer) in enumerate(test_cases, 1):
        print(f"\n🔸 Test Case {i}:")
        print(f"   Input: {json_options}")
        print(f"   Expected Answer: {expected_answer}")
        
        try:
            # Test parsing
            result = service._parse_mcq_options(json_options)
            print(f"   ✅ Parsed Result: {result}")
            
            # Check if expected answer is in options
            options_values = list(result.values())
            if expected_answer in options_values:
                answer_index = options_values.index(expected_answer)
                option_letter = ['A', 'B', 'C', 'D'][answer_index]
                print(f"   ✅ Answer '{expected_answer}' found at Option {option_letter}")
            else:
                print(f"   ⚠️  Answer '{expected_answer}' not found in parsed options")
            
        except Exception as e:
            print(f"   ❌ Parsing failed: {e}")
    
    print("\n🎯 Parsing Test Complete")

if __name__ == "__main__":
    test_parsing()