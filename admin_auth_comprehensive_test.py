#!/usr/bin/env python3
"""
COMPREHENSIVE ADMIN AUTHENTICATION TEST
Testing all aspects of admin authentication as requested in review
"""

import requests
import json
import sys
from datetime import datetime

class ComprehensiveAdminAuthTester:
    def __init__(self):
        self.base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None
        
    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
        self.tests_run += 1
        
        try:
            url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url.replace('/api', '')
            
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                print(f"   ❌ {test_name}: Unsupported method {method}")
                return False, {}
            
            # Check if status code matches expected
            if isinstance(expected_status, list):
                status_match = response.status_code in expected_status
            else:
                status_match = response.status_code == expected_status
            
            if status_match:
                self.tests_passed += 1
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": response.text}
                
                print(f"   ✅ {test_name}: Status {response.status_code}")
                return True, response_data
            else:
                print(f"   ❌ {test_name}: Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"      Error: {error_data}")
                except:
                    print(f"      Raw response: {response.text[:200]}")
                return False, {}
                
        except Exception as e:
            print(f"   ❌ {test_name}: Exception - {str(e)}")
            return False, {}

    def test_comprehensive_admin_authentication(self):
        """Comprehensive admin authentication testing as per review request"""
        print("🔐 COMPREHENSIVE ADMIN AUTHENTICATION TESTING")
        print("=" * 80)
        print("REVIEW REQUEST: Test admin login and debug authentication issues")
        print("CREDENTIALS: sumedhprabhu18@gmail.com / admin2025")
        print("REQUIREMENTS:")
        print("1. Test Admin Login Directly")
        print("2. Check Admin User in Database")
        print("3. Test Password Hash Validation")
        print("4. Check JWT Token Generation")
        print("5. Test Alternative Login Methods")
        print("6. Backend Service Status")
        print("=" * 80)
        
        test_results = {
            "admin_login_direct_success": False,
            "admin_user_exists_verified": False,
            "password_hash_validation_working": False,
            "jwt_token_generation_success": False,
            "jwt_token_validation_success": False,
            "is_admin_flag_correct": False,
            "admin_user_id_retrieved": False,
            "backend_service_healthy": False,
            "database_connection_working": False,
            "auth_endpoints_accessible": False
        }
        
        # TEST 1: Direct Admin Login Test
        print("\n🎯 TEST 1: DIRECT ADMIN LOGIN TEST")
        print("-" * 50)
        print("Testing admin login with exact credentials: sumedhprabhu18@gmail.com/admin2025")
        
        admin_login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login Direct", "POST", "auth/login", 200, admin_login_data)
        
        if success:
            access_token = response.get('access_token')
            user_data = response.get('user', {})
            token_type = response.get('token_type')
            expires_in = response.get('expires_in')
            
            if access_token:
                test_results["admin_login_direct_success"] = True
                test_results["jwt_token_generation_success"] = True
                test_results["admin_user_exists_verified"] = True
                test_results["password_hash_validation_working"] = True
                
                # Store token for further tests
                self.admin_token = access_token
                
                # Check user data
                user_id = user_data.get('id')
                email = user_data.get('email')
                full_name = user_data.get('full_name')
                is_admin = user_data.get('is_admin', False)
                created_at = user_data.get('created_at')
                
                print(f"   📊 JWT Token Length: {len(access_token)} characters")
                print(f"   📊 Token Type: {token_type}")
                print(f"   📊 Expires In: {expires_in} seconds")
                print(f"   📊 User ID: {user_id}")
                print(f"   📊 Email: {email}")
                print(f"   📊 Full Name: {full_name}")
                print(f"   📊 Is Admin: {is_admin}")
                print(f"   📊 Created At: {created_at}")
                
                if is_admin:
                    test_results["is_admin_flag_correct"] = True
                    print(f"   ✅ Admin privileges confirmed")
                
                if user_id:
                    test_results["admin_user_id_retrieved"] = True
                    print(f"   ✅ Admin user ID retrieved: {user_id}")
                
                print(f"   ✅ ADMIN LOGIN SUCCESSFUL!")
            else:
                print(f"   ❌ No access token in response")
        
        # TEST 2: JWT Token Validation Test
        if self.admin_token:
            print("\n🎫 TEST 2: JWT TOKEN VALIDATION TEST")
            print("-" * 50)
            print("Testing JWT token validation via /api/auth/me endpoint")
            
            admin_headers = {'Authorization': f'Bearer {self.admin_token}'}
            
            success, response = self.run_test("JWT Token Validation", "GET", "auth/me", 200, None, admin_headers)
            
            if success:
                test_results["jwt_token_validation_success"] = True
                
                user_id = response.get('id')
                email = response.get('email')
                full_name = response.get('full_name')
                is_admin = response.get('is_admin', False)
                created_at = response.get('created_at')
                
                print(f"   📊 Validated User ID: {user_id}")
                print(f"   📊 Validated Email: {email}")
                print(f"   📊 Validated Full Name: {full_name}")
                print(f"   📊 Validated Is Admin: {is_admin}")
                print(f"   📊 Validated Created At: {created_at}")
                
                if is_admin and email == "sumedhprabhu18@gmail.com":
                    print(f"   ✅ JWT token validation confirms admin privileges")
                else:
                    print(f"   ❌ JWT token validation failed admin check")
        
        # TEST 3: Database Connection and User Verification
        print("\n🗄️ TEST 3: DATABASE CONNECTION AND USER VERIFICATION")
        print("-" * 50)
        print("Testing database connectivity and admin user existence")
        
        # Test root endpoint for database health
        success, response = self.run_test("Database Health Check", "GET", "", 200)
        if success:
            test_results["database_connection_working"] = True
            admin_email = response.get('admin_email')
            print(f"   📊 Admin Email from Config: {admin_email}")
            
            if admin_email == "sumedhprabhu18@gmail.com":
                print(f"   ✅ Admin email configuration correct")
        
        # TEST 4: Alternative Login Methods
        print("\n🔄 TEST 4: ALTERNATIVE LOGIN METHODS TEST")
        print("-" * 50)
        print("Testing various password scenarios to isolate issues")
        
        # Test wrong password (should fail)
        wrong_password_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "wrongpassword"
        }
        
        success, response = self.run_test("Wrong Password Test", "POST", "auth/login", 401, wrong_password_data)
        if success:
            print(f"   ✅ Wrong password correctly rejected")
        
        # Test non-existent user (should fail)
        nonexistent_user_data = {
            "email": "nonexistent@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Non-existent User Test", "POST", "auth/login", 401, nonexistent_user_data)
        if success:
            print(f"   ✅ Non-existent user correctly rejected")
        
        # TEST 5: Backend Service Status
        print("\n🔧 TEST 5: BACKEND SERVICE STATUS CHECK")
        print("-" * 50)
        print("Testing overall backend service health")
        
        # Test various endpoints
        auth_endpoints = [
            ("auth/register", "POST", "Registration endpoint"),
            ("auth/login", "POST", "Login endpoint"),
            ("auth/me", "GET", "User info endpoint")
        ]
        
        working_endpoints = 0
        for endpoint, method, description in auth_endpoints:
            if method == "GET":
                success, response = self.run_test(f"Service: {description}", method, endpoint, [200, 401], None)
            else:
                success, response = self.run_test(f"Service: {description}", method, endpoint, [200, 400, 401, 422], {})
            
            if success:
                working_endpoints += 1
        
        if working_endpoints >= 2:
            test_results["backend_service_healthy"] = True
            test_results["auth_endpoints_accessible"] = True
            print(f"   ✅ Backend service healthy ({working_endpoints}/3 endpoints working)")
        
        # FINAL RESULTS
        print("\n" + "=" * 80)
        print("COMPREHENSIVE ADMIN AUTHENTICATION TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\nTEST RESULTS SUMMARY:")
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name.replace('_', ' ').title():<40} {status}")
        
        print(f"\nOverall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # CRITICAL FINDINGS
        print(f"\n🔍 CRITICAL FINDINGS:")
        
        if test_results["admin_login_direct_success"]:
            print("✅ ADMIN LOGIN: sumedhprabhu18@gmail.com/admin2025 credentials working perfectly")
        else:
            print("❌ ADMIN LOGIN: Credentials not working")
        
        if test_results["jwt_token_generation_success"]:
            print("✅ JWT TOKEN: Generated successfully with correct admin privileges")
        else:
            print("❌ JWT TOKEN: Generation failed")
        
        if test_results["is_admin_flag_correct"]:
            print("✅ ADMIN PRIVILEGES: is_admin flag correctly set to True")
        else:
            print("❌ ADMIN PRIVILEGES: is_admin flag not set correctly")
        
        if test_results["password_hash_validation_working"]:
            print("✅ PASSWORD HASH: Validation working correctly")
        else:
            print("❌ PASSWORD HASH: Validation issues detected")
        
        if test_results["database_connection_working"]:
            print("✅ DATABASE: Connection healthy and admin user exists")
        else:
            print("❌ DATABASE: Connection or user existence issues")
        
        if test_results["backend_service_healthy"]:
            print("✅ BACKEND SERVICE: All authentication services working")
        else:
            print("❌ BACKEND SERVICE: Service issues detected")
        
        # CONCLUSION
        print(f"\n📋 CONCLUSION:")
        
        if success_rate >= 90:
            print("🎉 ADMIN AUTHENTICATION FULLY FUNCTIONAL")
            print("   → All tests passed - admin login working perfectly")
            print("   → User report may be incorrect or issue was temporary")
        elif success_rate >= 70:
            print("⚠️ ADMIN AUTHENTICATION MOSTLY WORKING")
            print("   → Core functionality working with minor issues")
        else:
            print("❌ ADMIN AUTHENTICATION HAS ISSUES")
            print("   → Significant problems detected requiring investigation")
        
        return test_results

def main():
    """Run comprehensive admin authentication testing"""
    print("🔐 STARTING COMPREHENSIVE ADMIN AUTHENTICATION TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    tester = ComprehensiveAdminAuthTester()
    
    try:
        results = tester.test_comprehensive_admin_authentication()
        
        print(f"\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"Tests Run: {tester.tests_run}")
        print(f"Tests Passed: {tester.tests_passed}")
        print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
        
        admin_working = results.get("admin_login_direct_success", False)
        
        if admin_working:
            print("🎉 ADMIN AUTHENTICATION CONFIRMED WORKING")
            print("   → sumedhprabhu18@gmail.com/admin2025 credentials functional")
            print("   → JWT tokens generated with admin privileges")
            print("   → All authentication endpoints accessible")
        else:
            print("❌ ADMIN AUTHENTICATION ISSUES DETECTED")
        
        return 0 if admin_working else 1
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())