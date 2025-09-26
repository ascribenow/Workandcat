#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    """Run only the session discrepancy analysis test"""
    tester = CATBackendTester()
    
    print("🚀 Starting Session Sequence Discrepancy Analysis")
    print("=" * 80)
    
    try:
        # Run the session discrepancy analysis test
        result = tester.test_session_sequence_discrepancy_analysis()
        
        print("\n" + "=" * 80)
        print("🏁 SESSION DISCREPANCY ANALYSIS COMPLETE")
        print("=" * 80)
        
        if result:
            print("✅ Analysis completed successfully")
            sys.exit(0)
        else:
            print("⚠️ Analysis completed with issues - review results")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()