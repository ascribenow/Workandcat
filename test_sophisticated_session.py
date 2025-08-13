#!/usr/bin/env python3
"""
Test runner specifically for the FIXED Sophisticated 12-Question Session Logic
Focus on AsyncSession compatibility and personalization features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend_test import CATBackendTester

def main():
    """Main function for testing FIXED sophisticated session logic"""
    tester = CATBackendTester()
    
    print("🚀 TESTING FIXED SOPHISTICATED 12-QUESTION SESSION LOGIC")
    print("=" * 80)
    print("CRITICAL FOCUS - FIXED INTEGRATION TESTING:")
    print("1. Sophisticated Logic Invocation - Verify adaptive session logic is properly called")
    print("2. Learning Profile Analysis - Test user profile analysis with AsyncSession compatibility")
    print("3. Personalization Metadata - Verify session responses include personalization details")
    print("4. 12-Question Selection - Confirm sessions contain 12 questions instead of 1")
    print("5. Category & Difficulty Intelligence - Test proper distribution and reasoning")
    print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
    print("=" * 80)
    
    # Test user authentication first
    print("\n🔐 STEP 1: AUTHENTICATION")
    if not tester.test_user_login():
        print("❌ Authentication failed - cannot proceed with sophisticated session testing")
        return 1
    
    print("✅ Authentication successful - proceeding with sophisticated session testing")
    
    # Test the FIXED sophisticated session logic
    print("\n🎯 STEP 2: COMPREHENSIVE SOPHISTICATED SESSION TESTING")
    success = tester.test_fixed_sophisticated_session_comprehensive()
    
    print("\n" + "=" * 80)
    print("FINAL RECOMMENDATIONS FOR MAIN AGENT")
    print("=" * 80)
    
    if success:
        print("🎉 SOPHISTICATED SESSION LOGIC FIX SUCCESSFUL!")
        print("✅ AsyncSession compatibility confirmed")
        print("✅ Adaptive session logic is properly invoked")
        print("✅ Personalization metadata is populated")
        print("✅ 12-question selection working correctly")
        print("✅ Category & difficulty intelligence operational")
        print("")
        print("📋 RECOMMENDATION: The sophisticated 12-question session system is now")
        print("   working correctly after the AsyncSession compatibility fixes.")
        print("   The system is ready for production use.")
        return 0
    else:
        print("❌ SOPHISTICATED SESSION LOGIC STILL HAS CRITICAL ISSUES!")
        print("❌ AsyncSession compatibility may not be fully resolved")
        print("❌ Adaptive session logic may not be properly invoked")
        print("❌ Personalization features may not be working")
        print("")
        print("🔧 URGENT RECOMMENDATIONS:")
        print("   1. Verify AsyncSession compatibility in adaptive_session_logic.py")
        print("   2. Check if sophisticated logic is being called vs fallback")
        print("   3. Ensure personalization metadata is properly generated")
        print("   4. Validate 12-question selection instead of 1-question fallback")
        print("   5. Test learning stage detection (should not be 'unknown')")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)