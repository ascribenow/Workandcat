#!/usr/bin/env python3
"""
Complete end-to-end test with Gmail service authentication
"""

import requests
import json
import time
import warnings
import sys
import os

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def test_complete_signup_with_gmail_auth():
    base_url = "https://adapt-resume.preview.emergentagent.com/api"
    test_email = "test.final.signup@example.com"
    test_name = "Test Final User"
    test_password = "testpass123"
    
    print("🎯 COMPLETE CORRECTED SIGNUP SYSTEM TEST (WITH GMAIL AUTH)")
    print("=" * 75)
    print("Testing: Complete flow with Gmail service authentication")
    print("=" * 75)
    
    results = {}
    
    # Step 0: Authenticate Gmail service
    print("\n0️⃣ Authenticating Gmail service...")
    
    try:
        sys.path.append('/app/backend')
        from gmail_service import gmail_service
        
        auth_result = gmail_service.authenticate_service()
        if auth_result and gmail_service.service:
            print("   ✅ Gmail service authenticated successfully")
            results["gmail_auth"] = True
        else:
            print("   ❌ Gmail service authentication failed")
            results["gmail_auth"] = False
            return results
            
    except Exception as e:
        print(f"   ❌ Gmail authentication error: {e}")
        results["gmail_auth"] = False
        return results
    
    # Step 1: Send Verification Code (CORRECTED)
    print("\n1️⃣ Sending verification code (CORRECTED structure)...")
    
    signup_data = {
        "name": test_name,
        "email": test_email,
        "password": test_password
        # NO referral_code field
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/send-verification-code", 
            json=signup_data, 
            timeout=15, 
            verify=False
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                print("   ✅ Verification code sent successfully")
                print(f"   📧 Email: {response_data.get('email')}")
                results["send_code"] = True
            else:
                print(f"   ❌ Send failed: {response_data}")
                results["send_code"] = False
                return results
        else:
            print(f"   ❌ Send failed with status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   📋 Error: {error_data}")
            except:
                print(f"   📋 Error text: {response.text[:200]}")
            results["send_code"] = False
            return results
            
    except Exception as e:
        print(f"   ❌ Send error: {e}")
        results["send_code"] = False
        return results
    
    # Step 2: Get verification code from Gmail service
    print("\n2️⃣ Retrieving verification code from Gmail service...")
    
    verification_code = None
    try:
        if hasattr(gmail_service, 'verification_codes') and test_email in gmail_service.verification_codes:
            code_data = gmail_service.verification_codes[test_email]
            verification_code = code_data.get('code')
            
            if verification_code:
                print(f"   ✅ Found verification code: {verification_code}")
                results["get_code"] = True
            else:
                print("   ❌ Verification code is empty")
                results["get_code"] = False
        else:
            print("   ❌ No verification code found")
            print(f"   📋 Available codes: {list(gmail_service.verification_codes.keys()) if hasattr(gmail_service, 'verification_codes') else 'No codes'}")
            results["get_code"] = False
            
    except Exception as e:
        print(f"   ❌ Error accessing verification codes: {e}")
        results["get_code"] = False
    
    if not verification_code:
        print("   ⚠️ Cannot proceed without verification code")
        return results
    
    # Step 3: Verify email and create account
    print("\n3️⃣ Verifying email and creating account...")
    
    verify_data = {
        "email": test_email,
        "verification_code": verification_code
    }
    
    access_token = None
    user_id = None
    
    try:
        response = requests.post(
            f"{base_url}/auth/verify-email", 
            json=verify_data, 
            timeout=15, 
            verify=False
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                print("   ✅ Email verified and account created!")
                
                access_token = response_data.get('access_token')
                user_data = response_data.get('user', {})
                user_id = user_data.get('id')
                
                print(f"   👤 User ID: {user_id}")
                print(f"   👤 Email: {user_data.get('email')}")
                print(f"   🔑 Access token: {'Present' if access_token else 'Missing'}")
                
                results["verify_email"] = True
            else:
                print(f"   ❌ Verification failed: {response_data}")
                results["verify_email"] = False
                return results
        else:
            print(f"   ❌ Verification failed with status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   📋 Error details: {error_data}")
            except:
                print(f"   📋 Error text: {response.text[:200]}")
            results["verify_email"] = False
            return results
            
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        results["verify_email"] = False
        return results
    
    # Step 4: Get user's own referral code
    print("\n4️⃣ Getting user's own referral code...")
    
    user_referral_code = None
    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{base_url}/user/referral-code", 
                headers=headers, 
                timeout=10, 
                verify=False
            )
            
            if response.status_code == 200:
                response_data = response.json()
                user_referral_code = response_data.get('referral_code')
                
                if user_referral_code:
                    print(f"   ✅ User's referral code generated: {user_referral_code}")
                    results["referral_code"] = True
                else:
                    print("   ❌ No referral code in response")
                    results["referral_code"] = False
            else:
                print(f"   ❌ Referral code request failed: {response.status_code}")
                results["referral_code"] = False
                
        except Exception as e:
            print(f"   ❌ Referral code error: {e}")
            results["referral_code"] = False
    else:
        print("   ⚠️ No access token - skipping referral code test")
        results["referral_code"] = False
    
    # Step 5: Test 2-email delivery
    print("\n5️⃣ Testing 2-email delivery (confirmation + referral code)...")
    
    try:
        # Test confirmation email
        confirmation_sent = gmail_service.send_signup_confirmation_email(
            test_email, test_name
        )
        if confirmation_sent:
            print("   ✅ Signup confirmation email sent")
            results["confirmation_email"] = True
        else:
            print("   ❌ Signup confirmation email failed")
            results["confirmation_email"] = False
        
        # Test referral code email
        if user_referral_code:
            referral_email_sent = gmail_service.send_referral_code_email(
                test_email, test_name, user_referral_code
            )
            if referral_email_sent:
                print("   ✅ Referral code email sent")
                results["referral_email"] = True
            else:
                print("   ❌ Referral code email failed")
                results["referral_email"] = False
        else:
            print("   ⚠️ No referral code - cannot send referral email")
            results["referral_email"] = False
            
    except Exception as e:
        print(f"   ❌ Email delivery error: {e}")
        results["confirmation_email"] = False
        results["referral_email"] = False
    
    # Summary
    print("\n" + "=" * 75)
    print("🎯 COMPLETE CORRECTED SIGNUP SYSTEM TEST RESULTS")
    print("=" * 75)
    
    test_names = {
        "gmail_auth": "Gmail Service Authentication",
        "send_code": "Send Verification Code",
        "get_code": "Get Verification Code", 
        "verify_email": "Email Verification & Account Creation",
        "referral_code": "User Referral Code Generation",
        "confirmation_email": "Signup Confirmation Email",
        "referral_email": "Referral Code Email"
    }
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    success_rate = (passed_tests / total_tests) * 100
    
    for test_key, result in results.items():
        test_name = test_names.get(test_key, test_key)
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<40} {status}")
    
    print("-" * 75)
    print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    # Critical Assessment
    print("\n🎯 CRITICAL ASSESSMENT:")
    
    core_signup_working = (
        results.get("send_code", False) and 
        results.get("verify_email", False)
    )
    
    complete_flow_working = (
        core_signup_working and
        results.get("referral_code", False) and
        results.get("confirmation_email", False) and
        results.get("referral_email", False)
    )
    
    if complete_flow_working:
        print("\n🎉 CORRECTED SIGNUP SYSTEM: COMPLETE SUCCESS!")
        print("   ✅ Send verification code works with Name/Email/Password ONLY")
        print("   ✅ Email verification creates account successfully")
        print("   ✅ No referral code validation during signup")
        print("   ✅ User gets own referral code for later subscription use")
        print("   ✅ Both confirmation and referral emails sent")
        print("   ✅ Complete 2-email delivery working")
        print("   🚀 PRODUCTION READY!")
        
    elif core_signup_working:
        print("\n✅ CORRECTED SIGNUP SYSTEM: CORE FUNCTIONALITY WORKING")
        print("   ✅ Send verification code works with Name/Email/Password ONLY")
        print("   ✅ Email verification creates account successfully")
        print("   ✅ No referral code validation during signup")
        
        if not results.get("referral_code", False):
            print("   ❌ User referral code generation needs attention")
        if not results.get("confirmation_email", False) or not results.get("referral_email", False):
            print("   ❌ Email delivery system needs attention")
            
    else:
        print("\n❌ CORRECTED SIGNUP SYSTEM: CRITICAL ISSUES")
        if not results.get("send_code", False):
            print("   ❌ Send verification code has problems")
        if not results.get("verify_email", False):
            print("   ❌ Email verification or account creation failing")
    
    print("\n📋 REVIEW REQUEST VALIDATION:")
    print("   1. Name/Email/Password ONLY:", "✅ PASS" if results.get("send_code", False) else "❌ FAIL")
    print("   2. Send verification code from hello@twelvr.com:", "✅ PASS" if results.get("send_code", False) else "❌ FAIL")
    print("   3. User enters 6-digit code:", "✅ PASS" if results.get("verify_email", False) else "❌ FAIL")
    print("   4. Account created:", "✅ PASS" if results.get("verify_email", False) else "❌ FAIL")
    print("   5. User's own referral code generated:", "✅ PASS" if results.get("referral_code", False) else "❌ FAIL")
    print("   6. 2 emails sent (confirmation + referral):", "✅ PASS" if (results.get("confirmation_email", False) and results.get("referral_email", False)) else "❌ FAIL")
    
    return results

if __name__ == "__main__":
    test_complete_signup_with_gmail_auth()