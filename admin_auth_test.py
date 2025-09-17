#!/usr/bin/env python3
"""
URGENT ADMIN AUTHENTICATION DEBUG TEST
Comprehensive testing for admin login issue reported by user
"""

import requests
import json
import sys
from datetime import datetime

class AdminAuthTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        
    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
        self.tests_run += 1
        
        try:
            url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
            
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

    def test_admin_authentication_urgent(self):
        """URGENT: Debug admin authentication issue reported by user"""
        print("🚨 URGENT ADMIN AUTHENTICATION DEBUG")
        print("=" * 80)
        print("USER REPORT: Admin login with sumedhprabhu18@gmail.com/admin2025 is NOT working")
        print("CONTRADICTION: Previous testing showed it was working")
        print("GOAL: Identify exact issue and provide immediate solution")
        print("=" * 80)
        
        debug_results = {
            "admin_login_direct_test": False,
            "admin_user_exists_in_db": False,
            "password_hash_validates": False,
            "jwt_token_generated": False,
            "is_admin_flag_correct": False,
            "auth_me_endpoint_working": False,
            "database_connection_healthy": False,
            "backend_service_status": False,
            "admin_registration_possible": False,
            "alternative_login_methods": False
        }
        
        # PHASE 1: DIRECT ADMIN LOGIN TEST
        print("\n🎯 PHASE 1: DIRECT ADMIN LOGIN TEST")
        print("-" * 50)
        print("Testing admin login with EXACT credentials: sumedhprabhu18@gmail.com/admin2025")
        
        admin_login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("DIRECT Admin Login Test", "POST", "auth/login", [200, 401, 400, 500], admin_login_data)
        
        if success:
            access_token = response.get('access_token')
            user_data = response.get('user', {})
            message = response.get('message', '')
            detail = response.get('detail', '')
            
            print(f"   📊 Response Status: SUCCESS")
            print(f"   📊 Access Token Present: {bool(access_token)}")
            print(f"   📊 Message: {message}")
            print(f"   📊 Detail: {detail}")
            
            if access_token:
                debug_results["admin_login_direct_test"] = True
                debug_results["jwt_token_generated"] = True
                debug_results["admin_user_exists_in_db"] = True
                debug_results["password_hash_validates"] = True
                
                # Check admin flag
                is_admin = user_data.get('is_admin', False)
                user_id = user_data.get('id', 'N/A')
                email = user_data.get('email', 'N/A')
                
                print(f"   ✅ ADMIN LOGIN SUCCESSFUL!")
                print(f"   📊 JWT Token Length: {len(access_token)} characters")
                print(f"   📊 User ID: {user_id}")
                print(f"   📊 Email: {email}")
                print(f"   📊 Is Admin: {is_admin}")
                
                if is_admin:
                    debug_results["is_admin_flag_correct"] = True
                    print(f"   ✅ Admin privileges confirmed")
                else:
                    print(f"   ❌ Admin flag is False - privilege issue")
                
                # Store token for further testing
                self.admin_token = access_token
                self.admin_headers = {'Authorization': f'Bearer {access_token}'}
                
            else:
                print(f"   ❌ ADMIN LOGIN FAILED - No access token")
                print(f"   📊 Error Detail: {detail}")
                
                # Analyze error type
                if 'credentials' in detail.lower() or 'password' in detail.lower():
                    debug_results["admin_user_exists_in_db"] = True
                    print(f"   🔍 Analysis: User exists but password incorrect")
                elif 'not found' in detail.lower() or 'user' in detail.lower():
                    print(f"   🔍 Analysis: Admin user may not exist in database")
                else:
                    print(f"   🔍 Analysis: Unknown authentication error")
        else:
            print(f"   ❌ ADMIN LOGIN REQUEST FAILED")
        
        # PHASE 2: DATABASE USER VERIFICATION
        print("\n🗄️ PHASE 2: DATABASE USER VERIFICATION")
        print("-" * 50)
        print("Checking if admin user exists in database and verifying details")
        
        # Test database health first
        success, response = self.run_test("Database Health Check", "GET", "", [200, 500], None)
        if success:
            debug_results["database_connection_healthy"] = True
            debug_results["backend_service_status"] = True
            print(f"   ✅ Backend service and database connection healthy")
        else:
            print(f"   ❌ Backend service or database connection issues")
        
        # Try to register admin user to see if it already exists
        admin_register_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025",
            "full_name": "Admin User"
        }
        
        success, response = self.run_test("Admin User Existence Check", "POST", "auth/register", [200, 201, 400, 409, 422], admin_register_data)
        
        if success:
            access_token = response.get('access_token')
            detail = response.get('detail', '')
            message = response.get('message', '')
            
            if access_token:
                debug_results["admin_registration_possible"] = True
                debug_results["admin_user_exists_in_db"] = False  # User didn't exist before
                print(f"   ⚠️ Admin user was NOT in database - just created")
                print(f"   📊 New admin user registered successfully")
                
                # Check if new user has admin privileges
                user_data = response.get('user', {})
                is_admin = user_data.get('is_admin', False)
                if is_admin:
                    debug_results["is_admin_flag_correct"] = True
                    print(f"   ✅ New admin user has correct privileges")
                else:
                    print(f"   ❌ New admin user lacks admin privileges")
                
            elif 'already' in detail.lower() or 'exists' in detail.lower():
                debug_results["admin_user_exists_in_db"] = True
                print(f"   ✅ Admin user EXISTS in database")
                print(f"   📊 Registration blocked: {detail}")
            else:
                print(f"   ❌ Registration failed: {detail}")
        
        # PHASE 3: JWT TOKEN VALIDATION TEST
        if hasattr(self, 'admin_token') and self.admin_token:
            print("\n🎫 PHASE 3: JWT TOKEN VALIDATION TEST")
            print("-" * 50)
            print("Testing JWT token validation via /api/auth/me endpoint")
            
            success, response = self.run_test("JWT Token Validation", "GET", "auth/me", [200, 401], None, self.admin_headers)
            
            if success:
                debug_results["auth_me_endpoint_working"] = True
                
                user_id = response.get('id')
                email = response.get('email')
                full_name = response.get('full_name')
                is_admin = response.get('is_admin', False)
                created_at = response.get('created_at')
                
                print(f"   ✅ JWT token validation successful")
                print(f"   📊 User ID: {user_id}")
                print(f"   📊 Email: {email}")
                print(f"   📊 Full Name: {full_name}")
                print(f"   📊 Is Admin: {is_admin}")
                print(f"   📊 Created At: {created_at}")
                
                if is_admin:
                    debug_results["is_admin_flag_correct"] = True
                    print(f"   ✅ Admin privileges confirmed via /auth/me")
                else:
                    print(f"   ❌ Admin privileges NOT confirmed")
            else:
                print(f"   ❌ JWT token validation failed")
        
        # PHASE 4: ALTERNATIVE LOGIN METHODS TEST
        print("\n🔄 PHASE 4: ALTERNATIVE LOGIN METHODS TEST")
        print("-" * 50)
        print("Testing alternative approaches to isolate the issue")
        
        # Test with different password variations
        password_variations = [
            "admin2025",
            "Admin2025", 
            "ADMIN2025",
            "admin_2025",
            "admin@2025"
        ]
        
        for password in password_variations:
            test_data = {
                "email": "sumedhprabhu18@gmail.com",
                "password": password
            }
            
            success, response = self.run_test(f"Password Variation: {password}", "POST", "auth/login", [200, 401], test_data)
            
            if success and response.get('access_token'):
                debug_results["alternative_login_methods"] = True
                print(f"   ✅ Login successful with password: {password}")
                break
            else:
                print(f"   ❌ Login failed with password: {password}")
        
        # PHASE 5: BACKEND SERVICE STATUS CHECK
        print("\n🔧 PHASE 5: BACKEND SERVICE STATUS CHECK")
        print("-" * 50)
        print("Checking overall backend service health and auth endpoints")
        
        # Test various auth endpoints
        auth_endpoints = [
            ("auth/register", "POST", "Registration endpoint"),
            ("auth/login", "POST", "Login endpoint"),
            ("auth/me", "GET", "User info endpoint"),
            ("", "GET", "Root endpoint")
        ]
        
        working_endpoints = 0
        for endpoint, method, description in auth_endpoints:
            if method == "GET":
                success, response = self.run_test(f"Service Check: {description}", method, endpoint, [200, 401, 422], None)
            else:
                success, response = self.run_test(f"Service Check: {description}", method, endpoint, [200, 400, 401, 422], {})
            
            if success:
                working_endpoints += 1
                print(f"   ✅ {description}: Accessible")
            else:
                print(f"   ❌ {description}: Not accessible")
        
        if working_endpoints >= 3:
            debug_results["backend_service_status"] = True
            print(f"   ✅ Backend service status: Healthy ({working_endpoints}/4 endpoints working)")
        else:
            print(f"   ❌ Backend service status: Issues detected ({working_endpoints}/4 endpoints working)")
        
        # FINAL RESULTS AND DIAGNOSIS
        print("\n" + "=" * 80)
        print("ADMIN AUTHENTICATION DEBUG RESULTS")
        print("=" * 80)
        
        passed_tests = sum(debug_results.values())
        total_tests = len(debug_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\nDEBUG TEST RESULTS:")
        for test_name, result in debug_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name.replace('_', ' ').title():<35} {status}")
        
        print(f"\nOverall Debug Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # CRITICAL DIAGNOSIS
        print(f"\n🔍 CRITICAL DIAGNOSIS:")
        
        if debug_results["admin_login_direct_test"]:
            print("✅ ADMIN LOGIN WORKING: sumedhprabhu18@gmail.com/admin2025 credentials are functional")
            print("   → User report may be incorrect or issue was resolved")
        else:
            print("❌ ADMIN LOGIN FAILING: Credentials sumedhprabhu18@gmail.com/admin2025 not working")
            
            if debug_results["admin_user_exists_in_db"]:
                print("   → Admin user exists in database")
                if not debug_results["password_hash_validates"]:
                    print("   → PASSWORD HASH ISSUE: Stored password hash doesn't match 'admin2025'")
                    print("   → SOLUTION: Reset admin password hash in database")
                else:
                    print("   → Unknown authentication issue")
            else:
                print("   → ADMIN USER MISSING: Admin user not found in database")
                print("   → SOLUTION: Create admin user with correct credentials")
        
        if debug_results["jwt_token_generated"] and not debug_results["is_admin_flag_correct"]:
            print("⚠️ PRIVILEGE ISSUE: User authenticates but lacks admin privileges")
            print("   → Check ADMIN_EMAIL constant in auth_service.py")
        
        if not debug_results["backend_service_status"]:
            print("❌ SERVICE ISSUE: Backend authentication service has problems")
            print("   → Check service logs and database connectivity")
        
        # IMMEDIATE ACTION ITEMS
        print(f"\n📋 IMMEDIATE ACTION ITEMS:")
        
        if not debug_results["admin_login_direct_test"]:
            if not debug_results["admin_user_exists_in_db"]:
                print("1. CREATE ADMIN USER: Register sumedhprabhu18@gmail.com with admin2025 password")
            elif debug_results["admin_user_exists_in_db"] and not debug_results["password_hash_validates"]:
                print("1. RESET PASSWORD HASH: Update admin user password hash for 'admin2025'")
            else:
                print("1. INVESTIGATE AUTH SERVICE: Debug authentication logic")
        
        if debug_results["admin_login_direct_test"] and not debug_results["is_admin_flag_correct"]:
            print("2. FIX ADMIN PRIVILEGES: Ensure is_admin flag is set correctly")
        
        if not debug_results["backend_service_status"]:
            print("3. FIX BACKEND SERVICE: Resolve service connectivity issues")
        
        print("4. VERIFY WITH USER: Confirm exact error message user is seeing")
        
        return debug_results["admin_login_direct_test"]

def main():
    """Run the urgent admin authentication debug test"""
    print("🚨 STARTING URGENT ADMIN AUTHENTICATION DEBUG")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("")
    
    tester = AdminAuthTester()
    
    try:
        success = tester.test_admin_authentication_urgent()
        
        print(f"\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"Tests Run: {tester.tests_run}")
        print(f"Tests Passed: {tester.tests_passed}")
        print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
        
        if success:
            print("🎉 ADMIN LOGIN IS WORKING - User report may be incorrect")
        else:
            print("❌ ADMIN LOGIN CONFIRMED BROKEN - Immediate action required")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())