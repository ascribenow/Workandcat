#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

# Import the test class
from backend_test import CATBackendTester

def main():
    print("🚀 Starting Comprehensive Adaptive Session Completion Audit")
    print("=" * 100)
    
    tester = CATBackendTester()
    
    # Check if the method exists
    if hasattr(tester, 'test_comprehensive_adaptive_session_completion_audit'):
        print("✅ Method found, running audit...")
        success = tester.test_comprehensive_adaptive_session_completion_audit()
        
        print("\n" + "=" * 100)
        print(f"🎯 AUDIT COMPLETED")
        print(f"📊 Tests Run: {tester.tests_run}")
        print(f"✅ Tests Passed: {tester.tests_passed}")
        print(f"📈 Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
        print(f"🚀 Overall Result: {'✅ SUCCESS' if success else '❌ NEEDS ATTENTION'}")
        print("=" * 100)
    else:
        print("❌ Method not found in CATBackendTester class")
        print("Available methods:")
        methods = [method for method in dir(tester) if method.startswith('test_')]
        for method in methods:
            print(f"  - {method}")

if __name__ == "__main__":
    main()