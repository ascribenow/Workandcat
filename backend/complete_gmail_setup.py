#!/usr/bin/env python3
"""
Gmail OAuth2 Setup Completion Script
This script helps complete the Gmail OAuth2 setup by providing the authorization URL and accepting the callback code.
"""

import requests
import json
from urllib.parse import urlparse, parse_qs

def get_auth_url():
    """Get the Gmail authorization URL"""
    try:
        response = requests.get("http://localhost:8001/api/auth/gmail/authorize")
        if response.status_code == 200:
            data = response.json()
            return data.get('authorization_url')
        else:
            print(f"Error getting auth URL: {response.text}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def complete_oauth_setup(auth_code):
    """Complete OAuth setup with authorization code"""
    try:
        response = requests.post(
            "http://localhost:8001/api/auth/gmail/callback",
            json={"authorization_code": auth_code}
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get('message', 'Success')
        else:
            error_data = response.json()
            return False, error_data.get('detail', 'Unknown error')
    except Exception as e:
        return False, str(e)

def test_email_sending():
    """Test email sending after OAuth setup"""
    try:
        response = requests.post(
            "http://localhost:8001/api/auth/send-verification-code",
            json={"email": "test@example.com"}
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get('message', 'Success')
        else:
            error_data = response.json()
            return False, error_data.get('detail', 'Unknown error')
    except Exception as e:
        return False, str(e)

def main():
    print("🔧 Gmail OAuth2 Setup Completion Tool")
    print("=" * 60)
    
    # Step 1: Get authorization URL
    print("\n📋 STEP 1: Get Gmail Authorization URL")
    print("-" * 40)
    auth_url = get_auth_url()
    
    if not auth_url:
        print("❌ Failed to get authorization URL")
        return
    
    print("✅ Gmail Authorization URL generated!")
    print("\n📋 INSTRUCTIONS:")
    print("1. Copy and open this URL in your browser:")
    print(f"\n{auth_url}\n")
    print("2. Login with costodigital@gmail.com")
    print("3. Grant permissions to access Gmail")
    print("4. You'll be redirected to https://www.twelvr.com/?code=AUTHORIZATION_CODE")
    print("5. Copy the 'code' parameter from the URL")
    print("6. Run this script again with the code as argument:")
    print("   python complete_gmail_setup.py YOUR_AUTHORIZATION_CODE")
    print("\nExample URL after authorization:")
    print("https://www.twelvr.com/?code=4/0AanRRvsxyz123...")
    print("Copy the code part: 4/0AanRRvsxyz123...")
    
    # Check if authorization code was provided as argument
    import sys
    if len(sys.argv) > 1:
        auth_code = sys.argv[1]
        print(f"\n📝 STEP 2: Processing authorization code: {auth_code[:20]}...")
        print("-" * 40)
        
        success, message = complete_oauth_setup(auth_code)
        
        if success:
            print("✅ Gmail OAuth2 setup completed successfully!")
            print(f"📧 Message: {message}")
            
            # Test email sending
            print("\n🧪 STEP 3: Testing email sending capability...")
            print("-" * 40)
            
            test_success, test_message = test_email_sending()
            if test_success:
                print("✅ Email sending test successful!")
                print(f"📧 Message: {test_message}")
                print("\n🎉 Gmail email verification system is now fully functional!")
            else:
                print("⚠️ Email sending test failed:")
                print(f"❌ Error: {test_message}")
        else:
            print("❌ Gmail OAuth2 setup failed:")
            print(f"❌ Error: {message}")
    
    print("\n" + "=" * 60)
    print("📧 Once setup is complete, the email verification system will be ready!")

if __name__ == "__main__":
    main()