#!/usr/bin/env python3
"""
Test script for verification codes cleanup functionality
"""

import sys
import os
sys.path.append('/app/backend')

from database import SessionLocal, init_database
from gmail_service import gmail_service
from sqlalchemy import text
from datetime import datetime, timedelta

def test_cleanup():
    """Test the cleanup functionality"""
    
    print("🧹 Testing verification codes cleanup functionality...")
    
    # Initialize database
    init_database()
    
    test_email = "cleanup_test@example.com"
    
    try:
        # Create an expired verification code directly in database
        print(f"\n📧 Creating expired verification code for {test_email}")
        
        db = SessionLocal()
        try:
            # Insert expired code (expired 1 hour ago)
            expired_time = datetime.utcnow() - timedelta(hours=1)
            
            db.execute(text("""
                INSERT INTO verification_codes (id, email, code, expires_at, verified, attempts, created_at)
                VALUES (:id, :email, :code, :expires_at, false, 0, :created_at)
            """), {
                "id": "test-expired-id",
                "email": test_email,
                "code": "123456", 
                "expires_at": expired_time,
                "created_at": datetime.utcnow()
            })
            db.commit()
            print(f"✅ Expired code created")
            
            # Verify it exists
            result = db.execute(text("""
                SELECT COUNT(*) FROM verification_codes WHERE email = :email
            """), {"email": test_email}).scalar()
            print(f"✅ Codes in database before cleanup: {result}")
            
        finally:
            db.close()
        
        # Run cleanup
        print(f"\n🧹 Running cleanup...")
        gmail_service.cleanup_expired_codes()
        print(f"✅ Cleanup completed")
        
        # Check if expired code was removed
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT COUNT(*) FROM verification_codes WHERE email = :email
            """), {"email": test_email}).scalar()
            print(f"✅ Codes in database after cleanup: {result}")
            
            if result == 0:
                print(f"✅ Expired code was successfully cleaned up!")
                return True
            else:
                print(f"❌ Expired code was not cleaned up")
                return False
                
        finally:
            db.close()
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cleanup()
    if success:
        print("\n✅ Cleanup functionality is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Cleanup functionality has issues!")
        sys.exit(1)