#!/usr/bin/env python3

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    """Run the Admin Dashboard Fix & Regenerate Pack Transaction Error Fix test"""
    print("🚀 STARTING ADMIN DASHBOARD TRANSACTION ERROR FIX TEST")
    print("=" * 80)
    
    # Initialize tester
    tester = CATBackendTester()
    
    # Run the specific test
    try:
        success = tester.test_admin_dashboard_fix_regenerate_pack_transaction_error_fix()
        
        print("\n" + "=" * 80)
        print("🎯 ADMIN DASHBOARD TRANSACTION ERROR FIX TEST SUMMARY")
        print("=" * 80)
        
        if success:
            print("✅ ADMIN DASHBOARD TRANSACTION ERROR FIX TEST PASSED!")
            print("✅ Transaction management working correctly")
            print("✅ Pack regeneration functional")
            print("✅ No SQLAlchemy transaction conflicts")
            print("✅ Ready for production use")
            return 0
        else:
            print("❌ ADMIN DASHBOARD TRANSACTION ERROR FIX TEST FAILED!")
            print("❌ Transaction management issues detected")
            print("❌ Additional fixes required")
            return 1
            
    except Exception as e:
        print(f"❌ TEST EXECUTION ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)