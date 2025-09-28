#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    print("🎯 SUBSCRIPTION ACCESS SERVICE TESTING")
    print("=" * 80)
    
    tester = CATBackendTester()
    
    try:
        # Run the subscription access service test
        success = tester.test_subscription_access_service_unified_features()
        
        print("\n" + "=" * 80)
        print("🎯 SUBSCRIPTION ACCESS SERVICE TESTING COMPLETE")
        print("=" * 80)
        
        if success:
            print("✅ OVERALL RESULT: SUCCESS")
            print("   - Subscription access service working correctly")
            print("   - All tiers have Ask Twelvr access")
            print("   - Plan availability logic working")
            print("   - Session limits properly enforced")
            return 0
        else:
            print("❌ OVERALL RESULT: ISSUES DETECTED")
            print("   - Some subscription features need attention")
            return 1
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)