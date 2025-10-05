#!/usr/bin/env python3
"""
Test the CORRECTED complete signup system
Focus: Name/Email/Password ONLY → Verification → Account + 2 emails
"""

import requests
import json
import time
import sys
import os

class CorrectedSignupTester:
    def __init__(self):
        self.base_url = "https://adapt-resume.preview.emergentagent.com/api"
        self.test_email = "test.new.signup@example.com"
        self.test_name = "Test User New"
        self.test_password = "testpass123"
        self.verification_code = None
        self.access_token = None
        self.user_referral_code = None
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}/{endpoint}"
        
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30, verify=False)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30, verify=False)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except Exception as e:
            self.log(f"Request failed: {e}", "ERROR")
            return None
    
    def test_api_health(self):
        """Test basic API health"""
        self.log("Testing API health...")
        
        response = self.make_request("GET", "health")
        if response and response.status_code == 200:
            self.log("✅ API health check passed", "SUCCESS")
            return True
        else:
            self.log(f"❌ API health check failed: {response.status_code if response else 'No response'}", "ERROR")
            return False
    
    def test_send_verification_code(self):
        """Test sending verification code with CORRECTED data structure"""
        self.log("Testing CORRECTED send-verification-code (Name/Email/Password ONLY)...")
        
        # CORRECTED data structure - NO referral_code field
        signup_data = {
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password
            # NO referral_code field - this is the key correction
        }
        
        response = self.make_request("POST", "auth/send-verification-code", signup_data)
        
        if response is None:
            self.log("❌ No response from send-verification-code", "ERROR")
            return False
        
        self.log(f"Response status: {response.status_code}")
        
        if response.status_code == 404:
            self.log("🎯 REPRODUCED: 'Not Found' error - endpoint missing!", "CRITICAL")
            return False
        elif response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('success'):
                    self.log("✅ CORRECTED send-verification-code working!", "SUCCESS")
                    self.log(f"   Message: {response_data.get('message', 'N/A')}")
                    self.log(f"   Email: {response_data.get('email', 'N/A')}")
                    return True
                else:
                    self.log(f"❌ Send verification failed: {response_data}", "ERROR")
                    return False
            except json.JSONDecodeError:
                self.log(f"❌ Invalid JSON response: {response.text}", "ERROR")
                return False
        else:
            try:
                error_data = response.json()
                self.log(f"❌ Send verification failed ({response.status_code}): {error_data}", "ERROR")
            except:
                self.log(f"❌ Send verification failed ({response.status_code}): {response.text}", "ERROR")
            return False
    
    def test_gmail_service_access(self):
        """Test if we can access Gmail service for verification code"""
        self.log("Attempting to access Gmail service for verification code...")
        
        try:
            # Add backend path
            sys.path.append('/app/backend')
            from gmail_service import gmail_service
            
            if hasattr(gmail_service, 'verification_codes') and self.test_email in gmail_service.verification_codes:
                code_data = gmail_service.verification_codes[self.test_email]
                self.verification_code = code_data.get('code')
                
                if self.verification_code:
                    self.log(f"✅ Found verification code: {self.verification_code}", "SUCCESS")
                    return True
                else:
                    self.log("❌ Verification code is empty", "ERROR")
                    return False
            else:
                self.log("❌ No verification code found in Gmail service", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error accessing Gmail service: {e}", "ERROR")
            return False
    
    def test_email_verification(self):
        """Test email verification and account creation"""
        if not self.verification_code:
            self.log("⚠️ Skipping email verification - no verification code", "WARNING")
            return False
        
        self.log(f"Testing email verification with code: {self.verification_code}")
        
        verify_data = {
            "email": self.test_email,
            "verification_code": self.verification_code
        }
        
        response = self.make_request("POST", "auth/verify-email", verify_data)
        
        if response is None:
            self.log("❌ No response from verify-email", "ERROR")
            return False
        
        self.log(f"Verify response status: {response.status_code}")
        
        if response.status_code == 404:
            self.log("🎯 CRITICAL: verify-email endpoint also missing!", "CRITICAL")
            return False
        elif response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('success'):
                    self.log("✅ Email verification successful - account created!", "SUCCESS")
                    
                    # Store access token
                    self.access_token = response_data.get('access_token')
                    user_data = response_data.get('user', {})
                    
                    self.log(f"   User ID: {user_data.get('id', 'N/A')}")
                    self.log(f"   User Email: {user_data.get('email', 'N/A')}")
                    self.log(f"   Access Token: {'Present' if self.access_token else 'Missing'}")
                    
                    return True
                else:
                    self.log(f"❌ Email verification failed: {response_data}", "ERROR")
                    return False
            except json.JSONDecodeError:
                self.log(f"❌ Invalid JSON response: {response.text}", "ERROR")
                return False
        else:
            try:
                error_data = response.json()
                self.log(f"❌ Email verification failed ({response.status_code}): {error_data}", "ERROR")
            except:
                self.log(f"❌ Email verification failed ({response.status_code}): {response.text}", "ERROR")
            return False
    
    def test_user_referral_code(self):
        """Test that user gets their own referral code"""
        if not self.access_token:
            self.log("⚠️ Skipping referral code test - no access token", "WARNING")
            return False
        
        self.log("Testing user's own referral code generation...")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        response = self.make_request("GET", "user/referral-code", headers=headers)
        
        if response and response.status_code == 200:
            try:
                response_data = response.json()
                self.user_referral_code = response_data.get('referral_code')
                
                if self.user_referral_code:
                    self.log(f"✅ User's own referral code generated: {self.user_referral_code}", "SUCCESS")
                    return True
                else:
                    self.log("❌ No referral code in response", "ERROR")
                    return False
            except json.JSONDecodeError:
                self.log(f"❌ Invalid JSON response: {response.text}", "ERROR")
                return False
        else:
            self.log(f"❌ Referral code request failed: {response.status_code if response else 'No response'}", "ERROR")
            return False
    
    def test_email_delivery(self):
        """Test that 2 emails are sent: confirmation + referral code"""
        self.log("Testing email delivery capability...")
        
        try:
            sys.path.append('/app/backend')
            from gmail_service import gmail_service
            
            if not gmail_service.service:
                self.log("❌ Gmail service not initialized", "ERROR")
                return False
            
            self.log("✅ Gmail service is initialized", "SUCCESS")
            
            # Test sending confirmation email
            try:
                confirmation_sent = gmail_service.send_signup_confirmation_email(
                    self.test_email, self.test_name
                )
                if confirmation_sent:
                    self.log("✅ Signup confirmation email sent successfully", "SUCCESS")
                else:
                    self.log("❌ Signup confirmation email failed", "ERROR")
            except Exception as e:
                self.log(f"❌ Error sending confirmation email: {e}", "ERROR")
                confirmation_sent = False
            
            # Test sending referral code email
            referral_email_sent = False
            if self.user_referral_code:
                try:
                    referral_email_sent = gmail_service.send_referral_code_email(
                        self.test_email, self.test_name, self.user_referral_code
                    )
                    if referral_email_sent:
                        self.log("✅ Referral code email sent successfully", "SUCCESS")
                    else:
                        self.log("❌ Referral code email failed", "ERROR")
                except Exception as e:
                    self.log(f"❌ Error sending referral code email: {e}", "ERROR")
            else:
                self.log("⚠️ No referral code available for email test", "WARNING")
            
            return confirmation_sent and referral_email_sent
            
        except Exception as e:
            self.log(f"❌ Error testing email delivery: {e}", "ERROR")
            return False
    
    def run_complete_test(self):
        """Run the complete corrected signup system test"""
        self.log("🎯 STARTING CORRECTED COMPLETE SIGNUP SYSTEM TEST", "INFO")
        self.log("=" * 80)
        self.log("OBJECTIVE: Test CORRECTED signup (Name/Email/Password ONLY → Verification → Account + 2 emails)")
        self.log("EXPECTED: Complete signup flow without referral validation during registration")
        self.log("=" * 80)
        
        results = {
            "api_health": False,
            "send_verification": False,
            "gmail_access": False,
            "email_verification": False,
            "referral_code_generation": False,
            "email_delivery": False
        }
        
        # Test 1: API Health
        results["api_health"] = self.test_api_health()
        
        # Test 2: Send Verification Code (CORRECTED)
        if results["api_health"]:
            results["send_verification"] = self.test_send_verification_code()
        
        # Test 3: Gmail Service Access
        if results["send_verification"]:
            results["gmail_access"] = self.test_gmail_service_access()
        
        # Test 4: Email Verification
        if results["gmail_access"]:
            results["email_verification"] = self.test_email_verification()
        
        # Test 5: User Referral Code Generation
        if results["email_verification"]:
            results["referral_code_generation"] = self.test_user_referral_code()
        
        # Test 6: Email Delivery
        if results["referral_code_generation"]:
            results["email_delivery"] = self.test_email_delivery()
        
        # Summary
        self.log("=" * 80)
        self.log("🎯 CORRECTED SIGNUP SYSTEM TEST RESULTS")
        self.log("=" * 80)
        
        passed_tests = sum(results.values())
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        self.log("-" * 80)
        self.log(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical Assessment
        if results["send_verification"] and results["email_verification"]:
            self.log("\n🎉 CORRECTED SIGNUP SYSTEM: WORKING")
            self.log("   - Send verification code works with Name/Email/Password ONLY")
            self.log("   - Email verification creates account successfully")
            self.log("   - No referral code validation during signup")
            
            if results["referral_code_generation"] and results["email_delivery"]:
                self.log("   - User gets own referral code for later subscription use")
                self.log("   - Both confirmation and referral emails sent")
                self.log("   - Complete corrected flow operational")
            else:
                self.log("   - Email delivery needs attention")
        else:
            self.log("\n❌ CORRECTED SIGNUP SYSTEM: ISSUES DETECTED")
            if not results["send_verification"]:
                self.log("   - Send verification code endpoint issues")
            if not results["email_verification"]:
                self.log("   - Email verification or account creation issues")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = CorrectedSignupTester()
    success = tester.run_complete_test()
    sys.exit(0 if success else 1)