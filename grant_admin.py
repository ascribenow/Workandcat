#!/usr/bin/env python3

import sys
import os
sys.path.append('/app/backend')

from database import SessionLocal, User
from sqlalchemy import text

def grant_admin_permissions(email):
    """Grant admin permissions to a user"""
    db = SessionLocal()
    try:
        # Update user to be admin
        result = db.execute(text("""
            UPDATE users SET is_admin = true WHERE email = :email
        """), {"email": email})
        
        db.commit()
        
        if result.rowcount > 0:
            print(f"✅ Granted admin permissions to {email}")
            return True
        else:
            print(f"❌ User {email} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error granting admin permissions: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def check_admin_status(email):
    """Check if user has admin permissions"""
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT email, is_admin FROM users WHERE email = :email
        """), {"email": email})
        
        user = result.fetchone()
        if user:
            print(f"📊 User {user[0]}: is_admin = {user[1]}")
            return user[1]
        else:
            print(f"❌ User {email} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking admin status: {e}")
        return False
    finally:
        db.close()

def main():
    """Grant admin permissions to test users"""
    print("🔧 GRANTING ADMIN PERMISSIONS FOR TESTING")
    print("=" * 60)
    
    test_users = [
        "sp@theskinmantra.com",
        "twelvrhelp@gmail.com"
    ]
    
    for email in test_users:
        print(f"\n🔍 Processing user: {email}")
        
        # Check current status
        current_admin = check_admin_status(email)
        
        if not current_admin:
            # Grant admin permissions
            success = grant_admin_permissions(email)
            if success:
                # Verify the change
                check_admin_status(email)
        else:
            print(f"✅ User {email} already has admin permissions")
    
    print("\n✅ Admin permission setup complete!")

if __name__ == "__main__":
    main()