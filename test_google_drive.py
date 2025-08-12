#!/usr/bin/env python3
"""
Google Drive Image Integration Test Script
"""

import sys
import os
sys.path.append('/app')

from backend_test import CATBackendTester

def main():
    print("🔍 GOOGLE DRIVE IMAGE INTEGRATION TEST")
    print("=" * 80)
    
    tester = CATBackendTester()
    
    # Setup authentication
    print("🔧 Setting up authentication...")
    if not tester.test_user_login():
        print("❌ Failed to authenticate - cannot proceed")
        return False
    
    print("✅ Authentication successful")
    print(f"Admin token: {'✅ Available' if tester.admin_token else '❌ Missing'}")
    print(f"Student token: {'✅ Available' if tester.student_token else '❌ Missing'}")
    
    # Run Google Drive Image Integration test
    print("\n🎯 Running Google Drive Image Integration Test...")
    success = tester.test_google_drive_image_integration()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 GOOGLE DRIVE IMAGE INTEGRATION TEST PASSED!")
    else:
        print("❌ GOOGLE DRIVE IMAGE INTEGRATION TEST FAILED!")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)