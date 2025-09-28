#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    print("🎯 ADAPTIVE INSIGHTS BACKEND TESTING")
    print("=" * 60)
    
    tester = CATBackendTester()
    
    try:
        success = tester.test_adaptive_insights_backend_implementation()
        
        if success:
            print("\n🎉 ADAPTIVE INSIGHTS TESTING COMPLETED SUCCESSFULLY!")
            sys.exit(0)
        else:
            print("\n❌ ADAPTIVE INSIGHTS TESTING FAILED!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 TESTING ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()