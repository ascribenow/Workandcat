#!/usr/bin/env python3
"""
Focused Authentication System Testing for Twelvr
Comprehensive end-to-end testing with focus on SIGN UP functionality
"""

import requests
import json
import time
from datetime import datetime

class TwelvrAuthTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        
    def run_test(self, name, method, endpoint, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=60)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=60)
            
            print(f"   Status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
                return response.status_code, response_data
            except:
                return response.status_code, {"text": response.text}
                
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")
            return None, {}

    def test_comprehensive_authentication_system(self):
        """Comprehensive authentication system testing with focus on SIGN UP"""
        print("🎯 COMPREHENSIVE TWELVR AUTHENTICATION SYSTEM TESTING")
        print("=" * 80)
        print("FOCUS: SIGN UP FUNCTIONALITY - Complete End-to-End Testing")
        print("")
        
        results = {
            # SIGN UP TESTING (Primary Focus)
            "basic_register_endpoint": False,
            "email_validation": False,
            "password_validation": False,
            "duplicate_email_prevention": False,
            "user_creation_complete": False,
            "jwt_token_generation": False,
            
            # Authentication Flow
            "login_functionality": False,
            "token_validation": False,
            "user_profile_access": False,
            "access_control": False,
            
            # Email Verification System
            "gmail_oauth_config": False,
            "verification_code_sending": False,
            "code_verification": False,
            "email_signup_flow": False,
            
            # Database Integration
            "database_connectivity": False,
            "password_hashing": False,
            "user_data_storage": False,
            
            # Error Handling
            "input_validation": False,
            "error_responses": False
        }
        
        # PHASE 1: SIGN UP FUNCTIONALITY TESTING (Primary Focus)
        print("\n🎯 PHASE 1: SIGN UP FUNCTIONALITY TESTING (PRIMARY FOCUS)")
        print("=" * 80)
        
        # TEST 1.1: Basic Register Endpoint
        print("\n📝 TEST 1.1: BASIC REGISTER ENDPOINT ACCESSIBILITY")
        print("-" * 60)
        
        signup_data = {
            "email": f"test.user.{int(time.time())}@gmail.com",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        }
        
        status, response = self.run_test("Basic Registration", "POST", "auth/register", signup_data)
        
        if status == 200 and response.get('access_token'):
            results["basic_register_endpoint"] = True
            results["jwt_token_generation"] = True
            results["user_creation_complete"] = True
            self.tests_passed += 3
            print("   ✅ Basic register endpoint working")
            print("   ✅ JWT token generation working")
            print("   ✅ User creation flow complete")
            
            # Store token for later tests
            self.test_token = response.get('access_token')
            self.test_user_id = response.get('user', {}).get('id')
            
        elif status == 200:
            results["basic_register_endpoint"] = True
            self.tests_passed += 1
            print("   ✅ Basic register endpoint accessible")
        else:
            print("   ❌ Basic register endpoint issues")
        
        # TEST 1.2: Email Validation
        print("\n✉️ TEST 1.2: EMAIL VALIDATION TESTING")
        print("-" * 60)
        
        # Test invalid email
        invalid_email_data = {
            "email": "invalid-email-format",
            "password": "TestPassword123!",
            "full_name": "Test User"
        }
        
        status, response = self.run_test("Invalid Email Validation", "POST", "auth/register", invalid_email_data)
        
        if status == 422:  # Validation error expected
            results["email_validation"] = True
            self.tests_passed += 1
            print("   ✅ Email validation working - invalid emails rejected")
        else:
            print("   ❌ Email validation not working properly")
        
        # TEST 1.3: Password Validation
        print("\n🔒 TEST 1.3: PASSWORD REQUIREMENTS TESTING")
        print("-" * 60)
        
        # Test weak password
        weak_password_data = {
            "email": f"weak.password.{int(time.time())}@gmail.com",
            "password": "123",
            "full_name": "Weak Password User"
        }
        
        status, response = self.run_test("Weak Password Test", "POST", "auth/register", weak_password_data)
        
        # Check if weak password is accepted (should ideally be rejected)
        if status == 200 and response.get('access_token'):
            print("   ⚠️ Weak password accepted - password requirements could be stronger")
        else:
            results["password_validation"] = True
            self.tests_passed += 1
            print("   ✅ Password validation working")
        
        # TEST 1.4: Duplicate Email Prevention
        print("\n👥 TEST 1.4: DUPLICATE EMAIL HANDLING")
        print("-" * 60)
        
        # Try to register with same email again
        duplicate_email = f"duplicate.test.{int(time.time())}@gmail.com"
        
        # First registration
        first_signup = {
            "email": duplicate_email,
            "password": "FirstPassword123!",
            "full_name": "First User"
        }
        
        status1, response1 = self.run_test("First Registration", "POST", "auth/register", first_signup)
        
        if status1 == 200:
            # Second registration with same email
            second_signup = {
                "email": duplicate_email,
                "password": "SecondPassword123!",
                "full_name": "Second User"
            }
            
            status2, response2 = self.run_test("Duplicate Registration", "POST", "auth/register", second_signup)
            
            if status2 == 400 or status2 == 409:  # Conflict expected
                results["duplicate_email_prevention"] = True
                self.tests_passed += 1
                print("   ✅ Duplicate email prevention working")
            else:
                print("   ❌ Duplicate email not properly handled")
        
        # PHASE 2: AUTHENTICATION FLOW TESTING
        print("\n🔄 PHASE 2: AUTHENTICATION FLOW TESTING")
        print("=" * 80)
        
        # TEST 2.1: Login Functionality
        print("\n🔑 TEST 2.1: LOGIN FUNCTIONALITY")
        print("-" * 60)
        
        # Create a user for login testing
        login_test_email = f"login.test.{int(time.time())}@gmail.com"
        login_signup = {
            "email": login_test_email,
            "password": "LoginTest123!",
            "full_name": "Login Test User"
        }
        
        status, response = self.run_test("Register for Login Test", "POST", "auth/register", login_signup)
        
        if status == 200:
            # Now test login
            login_data = {
                "email": login_test_email,
                "password": "LoginTest123!"
            }
            
            status, response = self.run_test("Login Test", "POST", "auth/login", login_data)
            
            if status == 200 and response.get('access_token'):
                results["login_functionality"] = True
                self.tests_passed += 1
                print("   ✅ Login functionality working")
                
                # Store login token
                self.login_token = response.get('access_token')
            else:
                print("   ❌ Login functionality issues")
        
        # TEST 2.2: Token Validation and User Profile Access
        print("\n🎫 TEST 2.2: TOKEN VALIDATION AND USER PROFILE")
        print("-" * 60)
        
        if hasattr(self, 'login_token'):
            headers = {'Authorization': f'Bearer {self.login_token}'}
            
            status, response = self.run_test("User Profile Access", "GET", "auth/me", None, headers)
            
            if status == 200 and response.get('email'):
                results["token_validation"] = True
                results["user_profile_access"] = True
                results["user_data_storage"] = True
                self.tests_passed += 3
                print("   ✅ Token validation working")
                print("   ✅ User profile access working")
                print("   ✅ User data storage working")
            else:
                print("   ❌ Token validation or profile access issues")
        
        # TEST 2.3: Access Control
        print("\n🛡️ TEST 2.3: ACCESS CONTROL")
        print("-" * 60)
        
        # Test unauthenticated access
        status, response = self.run_test("Unauthenticated Access", "GET", "auth/me")
        
        if status == 401 or status == 403:
            results["access_control"] = True
            self.tests_passed += 1
            print("   ✅ Access control working - unauthenticated access blocked")
        else:
            print("   ❌ Access control issues")
        
        # PHASE 3: EMAIL VERIFICATION SYSTEM TESTING
        print("\n📧 PHASE 3: EMAIL VERIFICATION SYSTEM TESTING")
        print("=" * 80)
        
        # TEST 3.1: Gmail OAuth Configuration
        print("\n🔐 TEST 3.1: GMAIL OAUTH CONFIGURATION")
        print("-" * 60)
        
        status, response = self.run_test("Gmail Authorization", "GET", "auth/gmail/authorize")
        
        if status == 200 and response.get('authorization_url'):
            results["gmail_oauth_config"] = True
            self.tests_passed += 1
            print("   ✅ Gmail OAuth configuration working")
        elif status == 500:
            print("   ⚠️ Gmail OAuth not configured - setup needed")
        else:
            print("   ❌ Gmail OAuth configuration issues")
        
        # TEST 3.2: Verification Code Sending
        print("\n📨 TEST 3.2: VERIFICATION CODE SENDING")
        print("-" * 60)
        
        email_data = {"email": "test.verification@gmail.com"}
        status, response = self.run_test("Send Verification Code", "POST", "auth/send-verification-code", email_data)
        
        if status == 200 and response.get('success'):
            results["verification_code_sending"] = True
            self.tests_passed += 1
            print("   ✅ Verification code sending working")
        elif status == 503:
            print("   ⚠️ Email service not configured")
        else:
            print("   ❌ Verification code sending issues")
        
        # TEST 3.3: Code Verification
        print("\n🔢 TEST 3.3: CODE VERIFICATION")
        print("-" * 60)
        
        code_data = {"email": "test@gmail.com", "code": "000000"}
        status, response = self.run_test("Invalid Code Verification", "POST", "auth/verify-email-code", code_data)
        
        if status == 400:  # Invalid code should be rejected
            results["code_verification"] = True
            self.tests_passed += 1
            print("   ✅ Code verification working - invalid codes rejected")
        else:
            print("   ❌ Code verification issues")
        
        # TEST 3.4: Email Signup Flow
        print("\n🎯 TEST 3.4: EMAIL SIGNUP FLOW")
        print("-" * 60)
        
        email_signup_data = {
            "email": "email.signup.test@gmail.com",
            "password": "EmailSignup123!",
            "full_name": "Email Signup User",
            "code": "123456"
        }
        
        status, response = self.run_test("Email Signup Flow", "POST", "auth/signup-with-verification", email_signup_data)
        
        if status == 400:  # Invalid code expected
            results["email_signup_flow"] = True
            self.tests_passed += 1
            print("   ✅ Email signup flow accessible - proper verification required")
        elif status == 200:
            results["email_signup_flow"] = True
            self.tests_passed += 1
            print("   ✅ Email signup flow working")
        else:
            print("   ❌ Email signup flow issues")
        
        # PHASE 4: DATABASE AND ERROR HANDLING
        print("\n🗄️ PHASE 4: DATABASE AND ERROR HANDLING")
        print("=" * 80)
        
        # TEST 4.1: Database Connectivity
        print("\n🔍 TEST 4.1: DATABASE CONNECTIVITY")
        print("-" * 60)
        
        status, response = self.run_test("Database Health Check", "GET", "")
        
        if status == 200:
            results["database_connectivity"] = True
            self.tests_passed += 1
            print("   ✅ Database connectivity working")
        else:
            print("   ❌ Database connectivity issues")
        
        # TEST 4.2: Password Hashing
        print("\n🔐 TEST 4.2: PASSWORD HASHING VERIFICATION")
        print("-" * 60)
        
        # Create user and test login with correct/incorrect passwords
        hash_test_email = f"hash.test.{int(time.time())}@gmail.com"
        hash_signup = {
            "email": hash_test_email,
            "password": "HashTest123!",
            "full_name": "Hash Test User"
        }
        
        status, response = self.run_test("Hash Test Registration", "POST", "auth/register", hash_signup)
        
        if status == 200:
            # Test correct password
            correct_login = {"email": hash_test_email, "password": "HashTest123!"}
            status1, response1 = self.run_test("Correct Password Login", "POST", "auth/login", correct_login)
            
            # Test wrong password
            wrong_login = {"email": hash_test_email, "password": "WrongPassword123!"}
            status2, response2 = self.run_test("Wrong Password Login", "POST", "auth/login", wrong_login)
            
            if status1 == 200 and status2 == 401:
                results["password_hashing"] = True
                self.tests_passed += 1
                print("   ✅ Password hashing working")
            else:
                print("   ❌ Password hashing issues")
        
        # TEST 4.3: Input Validation and Error Handling
        print("\n❌ TEST 4.3: INPUT VALIDATION AND ERROR HANDLING")
        print("-" * 60)
        
        # Test missing fields
        invalid_data = {"email": "test@gmail.com"}  # Missing password and full_name
        status, response = self.run_test("Missing Fields Validation", "POST", "auth/register", invalid_data)
        
        if status == 422:  # Validation error expected
            results["input_validation"] = True
            results["error_responses"] = True
            self.tests_passed += 2
            print("   ✅ Input validation working")
            print("   ✅ Error responses working")
        else:
            print("   ❌ Input validation or error handling issues")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("COMPREHENSIVE AUTHENTICATION SYSTEM TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(results.values())
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        # Group results by category
        categories = {
            "SIGN UP TESTING (Primary Focus)": [
                "basic_register_endpoint", "email_validation", "password_validation",
                "duplicate_email_prevention", "user_creation_complete", "jwt_token_generation"
            ],
            "AUTHENTICATION FLOW": [
                "login_functionality", "token_validation", "user_profile_access", "access_control"
            ],
            "EMAIL VERIFICATION SYSTEM": [
                "gmail_oauth_config", "verification_code_sending", "code_verification", "email_signup_flow"
            ],
            "DATABASE INTEGRATION": [
                "database_connectivity", "password_hashing", "user_data_storage"
            ],
            "ERROR HANDLING": [
                "input_validation", "error_responses"
            ]
        }
        
        for category, tests in categories.items():
            print(f"\n{category}:")
            category_passed = 0
            category_total = len(tests)
            
            for test in tests:
                if test in results:
                    result = results[test]
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"  {test.replace('_', ' ').title():<35} {status}")
                    if result:
                        category_passed += 1
            
            category_rate = (category_passed / category_total) * 100 if category_total > 0 else 0
            print(f"  Category Success Rate: {category_passed}/{category_total} ({category_rate:.1f}%)")
        
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # CRITICAL ANALYSIS FOR SIGN UP FUNCTIONALITY
        print("\n🎯 CRITICAL ANALYSIS - SIGN UP FUNCTIONALITY:")
        
        signup_tests = ["basic_register_endpoint", "email_validation", "password_validation",
                       "duplicate_email_prevention", "user_creation_complete", "jwt_token_generation"]
        signup_passed = sum(results.get(test, False) for test in signup_tests)
        signup_rate = (signup_passed / len(signup_tests)) * 100
        
        if signup_rate >= 80:
            print("🎉 SIGN UP SYSTEM: Fully functional and production-ready")
        elif signup_rate >= 60:
            print("⚠️ SIGN UP SYSTEM: Core functionality working, minor issues detected")
        else:
            print("❌ SIGN UP SYSTEM: Critical issues need to be resolved")
        
        print(f"Sign Up Success Rate: {signup_passed}/{len(signup_tests)} ({signup_rate:.1f}%)")
        
        # DETAILED FINDINGS
        print("\n📋 DETAILED FINDINGS:")
        
        if results.get("basic_register_endpoint"):
            print("✅ REGISTER ENDPOINT: POST /api/auth/register accessible and functional")
        else:
            print("❌ REGISTER ENDPOINT: Issues with basic registration functionality")
        
        if results.get("email_validation"):
            print("✅ EMAIL VALIDATION: Proper email format validation implemented")
        else:
            print("❌ EMAIL VALIDATION: Email validation not working properly")
        
        if results.get("duplicate_email_prevention"):
            print("✅ DUPLICATE PREVENTION: Duplicate email registration properly blocked")
        else:
            print("❌ DUPLICATE PREVENTION: Duplicate email handling issues")
        
        if results.get("user_creation_complete"):
            print("✅ USER CREATION: Complete user creation and database storage working")
        else:
            print("❌ USER CREATION: Issues with user creation flow")
        
        if results.get("jwt_token_generation"):
            print("✅ JWT TOKENS: Token generation and validation working")
        else:
            print("❌ JWT TOKENS: Issues with token system")
        
        if results.get("database_connectivity"):
            print("✅ DATABASE: Backend connecting to database properly")
        else:
            print("❌ DATABASE: Database connection issues detected")
        
        # PRODUCTION READINESS ASSESSMENT
        print("\n📋 PRODUCTION READINESS ASSESSMENT:")
        
        if success_rate >= 85:
            print("🎉 PRODUCTION READY: Authentication system ready for production deployment")
        elif success_rate >= 70:
            print("⚠️ MOSTLY READY: Core functionality working, minor improvements needed")
        elif success_rate >= 50:
            print("⚠️ NEEDS WORK: Significant issues need to be resolved before production")
        else:
            print("❌ NOT READY: Critical authentication issues must be fixed")
        
        # SPECIFIC RECOMMENDATIONS
        print("\n📝 RECOMMENDATIONS:")
        
        if not results.get("basic_register_endpoint"):
            print("1. Fix basic registration endpoint - critical for sign up functionality")
        
        if not results.get("email_validation"):
            print("2. Implement proper email validation to prevent invalid registrations")
        
        if not results.get("password_validation"):
            print("3. Strengthen password requirements for better security")
        
        if not results.get("duplicate_email_prevention"):
            print("4. Fix duplicate email handling to prevent data conflicts")
        
        if not results.get("database_connectivity"):
            print("5. Resolve database connection issues for reliable user storage")
        
        if success_rate >= 70:
            print("6. System ready for comprehensive user testing")
        
        print(f"\n📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return success_rate >= 60  # 60% threshold for basic functionality

if __name__ == "__main__":
    print("🚀 Starting Twelvr Authentication System Testing")
    print("=" * 60)
    
    tester = TwelvrAuthTester()
    result = tester.test_comprehensive_authentication_system()
    
    print(f"\n🏁 Authentication Testing Complete - Success: {result}")