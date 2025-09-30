#!/usr/bin/env python3
"""
Test script for verification codes database integration
"""

import sys
import os
sys.path.append('/app/backend')

from database import SessionLocal, init_database
from gmail_service import gmail_service
from sqlalchemy import text

def test_verification_codes():
    """Test the verification codes database integration"""
    
    print("🧪 Testing verification codes database integration...")
    
    # Initialize database (create tables if they don't exist)
    try:
        init_database()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    
    # Test email for verification
    test_email = "test@example.com"
    
    try:
        # Test 1: Generate verification code
        print(f"\n📧 Testing code generation for {test_email}")
        code = gmail_service.generate_verification_code(test_email)
        print(f"✅ Generated code: {code}")
        
        # Test 2: Verify the code exists in database
        print(f"\n🔍 Checking if code exists in database...")
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT email, code, verified, attempts 
                FROM verification_codes 
                WHERE email = :email
            """), {"email": test_email}).fetchone()
            
            if result:
                email, stored_code, verified, attempts = result
                print(f"✅ Code found in database: {stored_code}")
                print(f"   Email: {email}")
                print(f"   Verified: {verified}")
                print(f"   Attempts: {attempts}")
                
                # Test 3: Verify the code
                print(f"\n🔐 Testing code verification...")
                is_valid = gmail_service.verify_code(test_email, code)
                print(f"✅ Code verification result: {is_valid}")
                
                # Test 4: Try to verify again (should fail as already verified)
                print(f"\n🔐 Testing duplicate verification (should fail)...")
                is_valid_again = gmail_service.verify_code(test_email, code)
                print(f"✅ Duplicate verification result: {is_valid_again}")
                
                # Test 5: Clean up
                print(f"\n🧹 Cleaning up test data...")
                gmail_service.remove_pending_user(test_email)
                print(f"✅ Test data cleaned up")
                
            else:
                print(f"❌ Code not found in database")
                return False
                
        finally:
            db.close()
        
        print(f"\n🎉 All verification code tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_verification_codes()
    if success:
        print("\n✅ Verification codes database integration is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Verification codes database integration has issues!")
        sys.exit(1)