#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

if __name__ == "__main__":
    print("🎯 DOUBTS/CHAT API INVESTIGATION")
    print("=" * 80)
    
    tester = CATBackendTester()
    
    try:
        # Run the doubts chat API investigation
        success = tester.test_doubts_chat_api_investigation()
        
        print("\n" + "=" * 80)
        print("🏁 DOUBTS TESTING COMPLETE")
        print("=" * 80)
        print(f"Total Tests Run: {tester.tests_run}")
        print(f"Total Tests Passed: {tester.tests_passed}")
        
        if tester.tests_run > 0:
            success_rate = (tester.tests_passed / tester.tests_run) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        if success:
            print("✅ DOUBTS SYSTEM: WORKING")
        else:
            print("❌ DOUBTS SYSTEM: ISSUES DETECTED")
            
    except Exception as e:
        print(f"❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()