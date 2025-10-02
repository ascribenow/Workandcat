#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    """Run the insight generation minimum attempt threshold test"""
    print("🎯 RUNNING INSIGHT GENERATION MINIMUM ATTEMPT THRESHOLD TEST")
    print("=" * 80)
    
    tester = CATBackendTester()
    
    try:
        result = tester.test_insight_generation_minimum_attempt_threshold()
        
        if result:
            print("\n🎉 TEST PASSED: Insight generation system is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ TEST FAILED: Issues detected in insight generation system")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()