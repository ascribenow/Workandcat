#!/usr/bin/env python3
"""
Gmail OAuth2 Re-Authentication Script
This script helps re-authenticate Gmail service when tokens have expired.
"""

import os
import json
from gmail_service import gmail_service

def main():
    print("🔧 Gmail OAuth2 Re-Authentication")
    print("=" * 50)
    
    # Check current credential status
    print("\n1. Checking current Gmail credentials...")
    
    if os.path.exists('/app/backend/gmail_credentials.json'):
        print("✅ Gmail credentials file exists")
        
        if os.path.exists('/app/backend/gmail_token.json'):
            print("⚠️  Gmail token file exists but may be expired")
        else:
            print("❌ Gmail token file missing")
    else:
        print("❌ Gmail credentials file missing")
        return
    
    # Test current authentication
    print("\n2. Testing current authentication...")
    if gmail_service.authenticate_service():
        print("✅ Gmail service is working! No re-authentication needed.")
        # Test sending an email
        test_result = gmail_service.send_verification_email("test@example.com", "123456")
        print(f"📧 Test email result: {'✅ Success' if test_result else '❌ Failed'}")
        
        if test_result:
            print("🎉 Gmail service is fully functional!")
            return
    else:
        print("❌ Gmail service authentication failed - re-authentication needed")
    
    # Generate new authorization URL
    print("\n3. Generating new authorization URL...")
    try:
        auth_url = gmail_service.get_authorization_url()
        print("\n🔗 Please visit this URL to re-authorize Gmail access:")
        print(f"\n{auth_url}")
        print("\nInstructions:")
        print("1. Copy the URL above and paste it in your browser")
        print("2. Log in with the Gmail account: costodigital@gmail.com") 
        print("3. Grant the requested permissions")
        print("4. After authorization, you'll be redirected to https://www.twelvr.com")
        print("5. Copy the 'code' parameter from the redirect URL")
        print("6. Run this script again with the authorization code")
        
        # Check if user wants to enter code now
        print("\n" + "=" * 50)
        code = input("Enter the authorization code (or press Enter to exit): ").strip()
        
        if code:
            print(f"\n4. Exchanging authorization code...")
            success = gmail_service.exchange_code_for_tokens(code)
            
            if success:
                print("✅ Gmail re-authentication successful!")
                
                # Test the new authentication
                print("\n5. Testing new authentication...")
                if gmail_service.authenticate_service():
                    print("✅ Gmail service re-authenticated successfully")
                    test_result = gmail_service.send_verification_email("test@example.com", "123456")
                    print(f"📧 Test email result: {'✅ Success' if test_result else '❌ Failed'}")
                    
                    if test_result:
                        print("🎉 Gmail service is now fully functional!")
                        print("✅ Email verification system is ready for production use!")
                    else:
                        print("⚠️  Authentication successful but email sending failed")
                else:
                    print("❌ Re-authentication verification failed")
            else:
                print("❌ Authorization code exchange failed")
                print("Please check the code and try again")
        else:
            print("👋 Exiting. Run this script again when you have the authorization code.")
            
    except Exception as e:
        print(f"❌ Error generating authorization URL: {e}")

if __name__ == "__main__":
    main()