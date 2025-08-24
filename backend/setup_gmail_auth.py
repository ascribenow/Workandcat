#!/usr/bin/env python3
"""
Gmail OAuth2 Setup Script
This script helps set up Gmail OAuth2 authentication by guiding through the OAuth flow.
"""

import os
import json
from gmail_service import gmail_service

def setup_gmail_auth():
    """Interactive setup for Gmail OAuth2 authentication"""
    print("🔧 Gmail OAuth2 Authentication Setup")
    print("=" * 50)
    
    try:
        # Check if already authenticated
        if gmail_service.authenticate_service():
            print("✅ Gmail service already authenticated!")
            print("🧪 Testing email sending capability...")
            
            # Test email sending
            test_email = "test@example.com"
            code = gmail_service.generate_verification_code(test_email)
            
            print(f"📧 Generated test verification code: {code}")
            print("✅ Gmail service is ready for sending emails!")
            return True
        
        # Get authorization URL
        print("🔑 Getting Gmail authorization URL...")
        auth_url = gmail_service.get_authorization_url()
        
        print("\n📋 Gmail OAuth2 Setup Instructions:")
        print("-" * 40)
        print("1. Open this URL in your browser:")
        print(f"   {auth_url}")
        print("\n2. Login with costodigital@gmail.com")
        print("3. Grant permissions to access Gmail")
        print("4. Copy the authorization code from the redirect URL")
        print("5. Paste the authorization code below")
        
        # Get authorization code from user
        print("\n" + "=" * 50)
        auth_code = input("📝 Enter the authorization code: ").strip()
        
        if not auth_code:
            print("❌ No authorization code provided")
            return False
        
        # Exchange code for tokens
        print("🔄 Exchanging authorization code for tokens...")
        success = gmail_service.exchange_code_for_tokens(auth_code)
        
        if success:
            print("✅ Gmail OAuth2 authentication successful!")
            print("🧪 Testing email sending capability...")
            
            # Test email sending
            test_email = "test@example.com"
            code = gmail_service.generate_verification_code(test_email)
            
            print(f"📧 Generated test verification code: {code}")
            print("✅ Gmail service is ready for sending emails!")
            return True
        else:
            print("❌ Failed to authenticate Gmail service")
            return False
            
    except Exception as e:
        print(f"❌ Error during Gmail setup: {e}")
        return False

if __name__ == "__main__":
    success = setup_gmail_auth()
    if success:
        print("\n🎉 Gmail authentication setup completed successfully!")
        print("🚀 You can now use the email verification system!")
    else:
        print("\n💥 Gmail authentication setup failed!")
        print("🔧 Please check your credentials and try again.")