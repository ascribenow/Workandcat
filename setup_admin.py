#!/usr/bin/env python3

import requests
import json

BACKEND_URL = "http://localhost:8001/api"

# Create admin user with your Gmail
def create_admin_user():
    admin_data = {
        "email": "sumedhprabhu18@gmail.com",
        "name": "Sumedh Prabhu",
        "password": "admin2025"
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/auth/register", json=admin_data)
        if response.status_code == 200:
            print("✅ Created admin user: sumedhprabhu18@gmail.com")
            print("🔑 Password: admin2025")
            print("🛡️ Admin privileges: Automatically granted")
            
            # Show login details
            login_response = response.json()
            print(f"🎯 User ID: {login_response['user']['id']}")
            print(f"📧 Email verified: {login_response['user']['email_verified']}")
            print(f"🔐 Token: {login_response['access_token'][:50]}...")
            
            return login_response
        else:
            print(f"❌ Failed to create admin user: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return None

# Test admin access
def test_admin_access(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Test admin stats endpoint
        response = requests.get(f"{BACKEND_URL}/admin/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print("✅ Admin access verified!")
            print(f"📊 System Stats:")
            print(f"   - Total Users: {stats['total_users']}")
            print(f"   - Total Questions: {stats['total_questions']}")
            print(f"   - Total Attempts: {stats['total_attempts']}")
            return True
        else:
            print(f"❌ Admin access failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error testing admin access: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up Admin User for CAT Preparation App")
    print("=" * 60)
    
    admin_response = create_admin_user()
    
    if admin_response:
        token = admin_response["access_token"]
        print("\n" + "=" * 60)
        print("🧪 Testing Admin Access...")
        
        if test_admin_access(token):
            print("\n🎉 Setup Complete!")
            print("\n📋 Admin Login Credentials:")
            print("   Email: sumedhprabhu18@gmail.com")
            print("   Password: admin2025")
            print("\n🌐 Access the app at:")
            print("   https://mcq-platform-1.preview.emergentagent.com")
        else:
            print("\n❌ Admin access test failed")
    else:
        print("\n❌ Failed to create admin user")