#!/usr/bin/env python3
"""
Quick test of the CORRECTED complete signup system
"""

import requests
import json
import time
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def test_corrected_signup():
    base_url = "https://twelvr-adaptive-2.preview.emergentagent.com/api"
    
    print("🎯 CORRECTED COMPLETE SIGNUP SYSTEM TEST")
    print("=" * 60)
    print("Testing: Name/Email/Password ONLY → Verification → Account + 2 emails")
    print("=" * 60)
    
    results = {}
    
    # Test 1: API Health
    print("\n1️⃣ Testing API Health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10, verify=False)
        if response.status_code == 200:
            print("   ✅ API health check passed")
            results["api_health"] = True
        else:
            print(f"   ❌ API health failed: {response.status_code}")
            results["api_health"] = False
    except Exception as e:
        print(f"   ❌ API health error: {e}")
        results["api_health"] = False
    
    if not results["api_health"]:
        print("\n❌ Cannot proceed - API not accessible")
        return
    
    # Test 2: Send Verification Code (CORRECTED - NO referral_code)
    print("\n2️⃣ Testing CORRECTED Send Verification Code...")
    
    # CORRECTED data structure - Name/Email/Password ONLY
    signup_data = {
        "name": "Test User New",
        "email": "test.new.signup@example.com", 
        "password": "testpass123"
        # NO referral_code field - this is the key correction
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/send-verification-code", 
            json=signup_data, 
            timeout=15, 
            verify=False
        )
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 404:
            print("   🎯 REPRODUCED: 'Not Found' error - endpoint missing!")
            results["send_verification"] = False
        elif response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('success'):
                    print("   ✅ CORRECTED send-verification-code working!")
                    print(f"   📧 Message: {response_data.get('message', 'N/A')}")
                    print(f"   📧 Email: {response_data.get('email', 'N/A')}")
                    results["send_verification"] = True
                else:
                    print(f"   ❌ Send verification failed: {response_data}")
                    results["send_verification"] = False
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON response")
                results["send_verification"] = False
        else:
            try:
                error_data = response.json()
                print(f"   ❌ Send verification failed ({response.status_code}): {error_data}")
            except:
                print(f"   ❌ Send verification failed ({response.status_code}): {response.text[:200]}")
            results["send_verification"] = False
            
    except Exception as e:
        print(f"   ❌ Send verification error: {e}")
        results["send_verification"] = False
    
    # Test 3: Check if referral_code field is ignored (should still work)
    print("\n3️⃣ Testing that referral_code field is ignored during signup...")
    
    signup_data_with_referral = {
        "name": "Test User With Referral Field",
        "email": "test.referral.field@example.com",
        "password": "testpass123",
        "referral_code": "SHOULDBEIGNORED"  # This should be ignored
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/send-verification-code", 
            json=signup_data_with_referral, 
            timeout=15, 
            verify=False
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                print("   ✅ Referral code field ignored during signup (correct behavior)")
                results["referral_ignored"] = True
            else:
                print(f"   ❌ Signup failed with referral field: {response_data}")
                results["referral_ignored"] = False
        else:
            print(f"   ❌ Signup with referral field failed: {response.status_code}")
            results["referral_ignored"] = False
            
    except Exception as e:
        print(f"   ❌ Referral field test error: {e}")
        results["referral_ignored"] = False
    
    # Test 4: Check verify-email endpoint exists
    print("\n4️⃣ Testing verify-email endpoint availability...")
    
    # Test with empty data to see if endpoint exists
    try:
        response = requests.post(
            f"{base_url}/auth/verify-email", 
            json={}, 
            timeout=10, 
            verify=False
        )
        
        if response.status_code == 404:
            print("   🎯 CRITICAL: verify-email endpoint missing!")
            results["verify_endpoint"] = False
        elif response.status_code in [400, 422]:  # Validation error is expected
            print("   ✅ verify-email endpoint exists (validation error expected)")
            results["verify_endpoint"] = True
        else:
            print(f"   ✅ verify-email endpoint accessible (status: {response.status_code})")
            results["verify_endpoint"] = True
            
    except Exception as e:
        print(f"   ❌ verify-email endpoint test error: {e}")
        results["verify_endpoint"] = False
    
    # Test 5: Check Gmail service status
    print("\n5️⃣ Testing Gmail service status...")
    
    try:
        import sys
        sys.path.append('/app/backend')
        from gmail_service import gmail_service
        
        if gmail_service.service:
            print("   ✅ Gmail service is initialized and ready")
            results["gmail_service"] = True
        else:
            print("   ❌ Gmail service not initialized")
            results["gmail_service"] = False
            
    except Exception as e:
        print(f"   ❌ Gmail service check error: {e}")
        results["gmail_service"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 CORRECTED SIGNUP SYSTEM TEST RESULTS")
    print("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    success_rate = (passed_tests / total_tests) * 100
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():<25} {status}")
    
    print("-" * 60)
    print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    # Critical Assessment
    print("\n🎯 CRITICAL ASSESSMENT:")
    
    if results.get("send_verification", False):
        print("\n✅ CORRECTED SIGNUP SYSTEM: WORKING")
        print("   - Send verification code works with Name/Email/Password ONLY")
        print("   - No referral code validation during signup")
        print("   - Endpoints are accessible and functional")
        
        if results.get("verify_endpoint", False):
            print("   - Email verification endpoint exists")
        else:
            print("   - Email verification endpoint missing")
            
        if results.get("gmail_service", False):
            print("   - Gmail service ready for email delivery")
        else:
            print("   - Gmail service needs attention")
            
    else:
        print("\n❌ CORRECTED SIGNUP SYSTEM: ISSUES DETECTED")
        print("   - Send verification code endpoint has problems")
        print("   - May still have referral code validation during signup")
    
    print("\n📋 NEXT STEPS:")
    if results.get("send_verification", False) and results.get("verify_endpoint", False):
        print("   - Complete end-to-end flow testing with actual verification codes")
        print("   - Test 2-email delivery (confirmation + referral code)")
        print("   - Verify user account creation and referral code generation")
    else:
        print("   - Fix endpoint availability issues")
        print("   - Ensure Gmail service is properly configured")
    
    return success_rate >= 80

if __name__ == "__main__":
    test_corrected_signup()