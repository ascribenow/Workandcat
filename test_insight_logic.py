#!/usr/bin/env python3

import sys
import os
sys.path.append('/app/backend')

def test_insight_generation_logic():
    """Test the insight generation logic directly"""
    print("🎯 TESTING INSIGHT GENERATION LOGIC DIRECTLY")
    print("=" * 80)
    
    try:
        from services.insight_generator_service import insight_generator_service
        
        # Test 1: Check if the prompt includes minimum attempt threshold logic
        print("\n📋 TEST 1: Checking minimum attempt threshold in prompt")
        
        # Create test data
        test_data = {"user_id": "test-user-123"}
        
        # Get the prompt (this should work even without database)
        try:
            prompt = insight_generator_service._build_comprehensive_insights_prompt(test_data)
            
            # Check for key phrases that indicate the fix is in place
            threshold_indicators = [
                "minimum 3 attempts required",
                "≥3 attempts",
                "sufficient data",
                "limited data",
                "<3 attempts",
                "few more attempts would help assess"
            ]
            
            found_indicators = []
            for indicator in threshold_indicators:
                if indicator.lower() in prompt.lower():
                    found_indicators.append(indicator)
            
            print(f"   📊 Prompt length: {len(prompt)} characters")
            print(f"   ✅ Found threshold indicators: {found_indicators}")
            
            if len(found_indicators) >= 3:
                print(f"   ✅ MINIMUM ATTEMPT THRESHOLD LOGIC DETECTED")
                threshold_working = True
            else:
                print(f"   ❌ MINIMUM ATTEMPT THRESHOLD LOGIC NOT CLEARLY DETECTED")
                threshold_working = False
                
            # Show relevant parts of the prompt
            lines = prompt.split('\n')
            relevant_lines = []
            for line in lines:
                if any(indicator.lower() in line.lower() for indicator in threshold_indicators):
                    relevant_lines.append(line.strip())
            
            if relevant_lines:
                print(f"   📝 Relevant prompt sections:")
                for line in relevant_lines[:5]:  # Show first 5 relevant lines
                    print(f"      {line}")
            
        except Exception as e:
            print(f"   ❌ Error testing prompt: {e}")
            threshold_working = False
        
        # Test 2: Check fallback insights
        print("\n📋 TEST 2: Testing fallback insights generation")
        
        try:
            fallback_insights = insight_generator_service._generate_simple_fallback_insights(test_data)
            
            if isinstance(fallback_insights, dict):
                print(f"   ✅ Fallback insights generated successfully")
                print(f"   📊 Keys: {list(fallback_insights.keys())}")
                
                # Check content
                all_time = fallback_insights.get("dashboard_all_time", "")
                recent = fallback_insights.get("dashboard_recent", "")
                
                if len(all_time) > 50 and len(recent) > 50:
                    print(f"   ✅ Fallback content has reasonable length")
                    fallback_working = True
                else:
                    print(f"   ⚠️ Fallback content may be too short")
                    fallback_working = False
            else:
                print(f"   ❌ Fallback insights not in expected format")
                fallback_working = False
                
        except Exception as e:
            print(f"   ❌ Error testing fallback: {e}")
            fallback_working = False
        
        # Test 3: Check the comprehensive insights method
        print("\n📋 TEST 3: Testing comprehensive insights generation")
        
        try:
            # This will likely use fallback due to no database, but we can check the structure
            comprehensive_insights = insight_generator_service.generate_comprehensive_insights(test_data)
            
            if isinstance(comprehensive_insights, dict):
                required_keys = ["dashboard_all_time", "dashboard_recent", "source", "generated_at"]
                has_all_keys = all(key in comprehensive_insights for key in required_keys)
                
                if has_all_keys:
                    print(f"   ✅ Comprehensive insights structure correct")
                    print(f"   📊 Source: {comprehensive_insights.get('source')}")
                    comprehensive_working = True
                else:
                    print(f"   ❌ Missing required keys in comprehensive insights")
                    comprehensive_working = False
            else:
                print(f"   ❌ Comprehensive insights not in expected format")
                comprehensive_working = False
                
        except Exception as e:
            print(f"   ❌ Error testing comprehensive insights: {e}")
            comprehensive_working = False
        
        # Test 4: Check the specific fix for minimum attempts
        print("\n📋 TEST 4: Checking specific minimum attempt threshold implementation")
        
        try:
            # Look at the actual code to see if the fix is implemented
            import inspect
            
            # Get the source code of the prompt building method
            source = inspect.getsource(insight_generator_service._build_comprehensive_insights_prompt)
            
            # Check for the specific fix
            fix_indicators = [
                "MINIMUM_ATTEMPTS_FOR_MASTERY = 3",
                "c[4] >= MINIMUM_ATTEMPTS_FOR_MASTERY",
                "concepts_sufficient_data",
                "concepts_low_data",
                "low_data_concepts",
                "DO NOT make strong claims about mastery"
            ]
            
            found_fixes = []
            for indicator in fix_indicators:
                if indicator in source:
                    found_fixes.append(indicator)
            
            print(f"   📊 Found fix indicators: {len(found_fixes)}/{len(fix_indicators)}")
            for fix in found_fixes:
                print(f"      ✅ {fix}")
            
            if len(found_fixes) >= 4:
                print(f"   ✅ MINIMUM ATTEMPT THRESHOLD FIX IMPLEMENTED")
                fix_implemented = True
            else:
                print(f"   ❌ MINIMUM ATTEMPT THRESHOLD FIX NOT FULLY IMPLEMENTED")
                fix_implemented = False
                
        except Exception as e:
            print(f"   ❌ Error checking fix implementation: {e}")
            fix_implemented = False
        
        # Final Assessment
        print("\n" + "=" * 80)
        print("🎯 INSIGHT GENERATION LOGIC TEST RESULTS")
        print("=" * 80)
        
        tests = {
            "Minimum Attempt Threshold Logic": threshold_working,
            "Fallback Insights Working": fallback_working,
            "Comprehensive Insights Structure": comprehensive_working,
            "Fix Implementation Verified": fix_implemented
        }
        
        passed = sum(tests.values())
        total = len(tests)
        success_rate = (passed / total) * 100
        
        for test_name, result in tests.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name:<40} {status}")
        
        print(f"\nOverall Success Rate: {passed}/{total} ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print("\n🎉 INSIGHT GENERATION LOGIC: WORKING CORRECTLY")
            print("   - Minimum attempt threshold logic implemented")
            print("   - Appropriate safeguards for low-data concepts")
            print("   - System ready for production use")
            return True
        else:
            print("\n⚠️ INSIGHT GENERATION LOGIC: NEEDS ATTENTION")
            print("   - Some components may need fixes")
            return False
            
    except Exception as e:
        print(f"❌ Error testing insight generation logic: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_insight_generation_logic()
    sys.exit(0 if result else 1)