import requests
import sys
import json
from datetime import datetime
import time
import os

class AdminEndpointsTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.admin_headers = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, test_name, method, endpoint, expected_status_codes, data=None, headers=None):
        """Run a single test and return success status and response"""
        self.tests_run += 1
        
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Add SSL verification disable and connection settings
            session = requests.Session()
            session.verify = False
            
            if method.upper() == "GET":
                response = session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = session.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = session.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = session.delete(url, headers=headers, timeout=30)
            else:
                print(f"❌ {test_name}: Unsupported method {method}")
                return False, None
            
            # Check if status code is in expected range
            if isinstance(expected_status_codes, list):
                success = response.status_code in expected_status_codes
            else:
                success = response.status_code == expected_status_codes
            
            if success:
                self.tests_passed += 1
                print(f"✅ {test_name}: {response.status_code}")
            else:
                print(f"❌ {test_name}: Expected {expected_status_codes}, got {response.status_code}")
                if response.text:
                    print(f"   Error: {response.text[:200]}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
                response_data['status_code'] = response.status_code
                return success, response_data
            except:
                return success, {
                    'status_code': response.status_code,
                    'text': response.text[:500] if response.text else None
                }
                
        except Exception as e:
            print(f"❌ {test_name}: Exception - {str(e)}")
            return False, {'error': str(e)}

    def authenticate_admin(self):
        """Authenticate as admin and get token"""
        print("🔐 ADMIN AUTHENTICATION")
        print("-" * 50)
        
        admin_login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", [200, 401], admin_login_data)
        
        if success and response.get('access_token'):
            self.admin_token = response['access_token']
            self.admin_headers = {
                'Authorization': f'Bearer {self.admin_token}',
                'Content-Type': 'application/json'
            }
            print(f"   ✅ Admin authentication successful")
            print(f"   📊 JWT Token length: {len(self.admin_token)} characters")
            
            # Verify admin privileges
            success, me_response = self.run_test("Admin Token Validation", "GET", "auth/me", 200, None, self.admin_headers)
            if success and me_response.get('is_admin'):
                print(f"   ✅ Admin privileges confirmed: {me_response.get('email')}")
                return True
            else:
                print(f"   ❌ Admin privileges not confirmed")
                return False
        else:
            print("   ❌ Admin authentication failed")
            return False

    def test_admin_endpoints_404_500_errors(self):
        """
        CRITICAL ADMIN ENDPOINTS TESTING - 404/500 ERROR INVESTIGATION
        
        Test the admin endpoints that are reported to be returning 404/500 errors:
        1. /api/admin/audit-customer-payment (POST)
        2. /api/admin/cleanup-duplicate-subscriptions (POST) 
        3. /api/admin/correct-payment-from-razorpay (POST)
        4. /api/admin/run-payment-reconciliation (POST)
        5. /api/admin/payment-system-health (GET)
        6. /api/admin/payment-analytics (GET)
        7. /api/admin/emergency-activate-subscription (POST)

        AUTHENTICATION:
        Use admin credentials: sumedhprabhu18@gmail.com / admin2025

        EXPECTED BEHAVIOR:
        - All endpoints should return 200 OK with proper data
        - No 404 "Not Found" errors
        - No 500 "Internal Server Error" responses
        - Proper JSON responses with audit/analytics/monitoring data

        FOCUS AREAS:
        - Test if endpoints exist and are accessible 
        - Check for database dependency issues (missing tables/columns)
        - Verify import issues with payment services
        - Test database connection problems
        - Check for proper error handling vs crashes
        """
        print("🚨 CRITICAL ADMIN ENDPOINTS TESTING - 404/500 ERROR INVESTIGATION")
        print("=" * 80)
        print("OBJECTIVE: Test admin endpoints reported to be returning 404/500 errors")
        print("")
        print("CRITICAL ADMIN ENDPOINTS TO TEST:")
        print("1. /api/admin/audit-customer-payment (POST)")
        print("2. /api/admin/cleanup-duplicate-subscriptions (POST)")
        print("3. /api/admin/correct-payment-from-razorpay (POST)")
        print("4. /api/admin/run-payment-reconciliation (POST)")
        print("5. /api/admin/payment-system-health (GET)")
        print("6. /api/admin/payment-analytics (GET)")
        print("7. /api/admin/emergency-activate-subscription (POST)")
        print("")
        print("AUTHENTICATION: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 80)
        
        # First authenticate as admin
        if not self.authenticate_admin():
            print("❌ Cannot proceed without admin authentication")
            return False
        
        admin_endpoints_results = {
            # Endpoint Accessibility
            "audit_customer_payment_accessible": False,
            "cleanup_duplicate_subscriptions_accessible": False,
            "correct_payment_from_razorpay_accessible": False,
            "run_payment_reconciliation_accessible": False,
            "payment_system_health_accessible": False,
            "payment_analytics_accessible": False,
            "emergency_activate_subscription_accessible": False,
            
            # Error Type Detection
            "audit_customer_payment_404_error": False,
            "cleanup_duplicate_subscriptions_404_error": False,
            "correct_payment_from_razorpay_404_error": False,
            "run_payment_reconciliation_404_error": False,
            "payment_system_health_404_error": False,
            "payment_analytics_404_error": False,
            "emergency_activate_subscription_404_error": False,
            
            "audit_customer_payment_500_error": False,
            "cleanup_duplicate_subscriptions_500_error": False,
            "correct_payment_from_razorpay_500_error": False,
            "run_payment_reconciliation_500_error": False,
            "payment_system_health_500_error": False,
            "payment_analytics_500_error": False,
            "emergency_activate_subscription_500_error": False,
            
            # Successful Responses
            "audit_customer_payment_working": False,
            "cleanup_duplicate_subscriptions_working": False,
            "correct_payment_from_razorpay_working": False,
            "run_payment_reconciliation_working": False,
            "payment_system_health_working": False,
            "payment_analytics_working": False,
            "emergency_activate_subscription_working": False,
            
            # Authentication Requirements
            "all_endpoints_require_admin": False,
            "admin_authentication_working": True  # Already confirmed above
        }
        
        # PHASE 1: TEST AUDIT CUSTOMER PAYMENT ENDPOINT
        print("\n💳 PHASE 1: TEST AUDIT CUSTOMER PAYMENT ENDPOINT")
        print("-" * 60)
        print("Testing POST /api/admin/audit-customer-payment")
        
        audit_payload = {
            "user_email": "sp@theskinmantra.com",
            "razorpay_payment_id": "pay_REojjjLlRWUTWb"
        }
        
        success, response = self.run_test(
            "Audit Customer Payment", 
            "POST", 
            "admin/audit-customer-payment", 
            [200, 400, 404, 422, 500], 
            audit_payload, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["audit_customer_payment_accessible"] = True
                admin_endpoints_results["audit_customer_payment_working"] = True
                print(f"   ✅ Audit customer payment endpoint working")
                if response.get('audit_results'):
                    print(f"   📊 Audit results returned: {len(response.get('audit_results', []))} items")
            elif response.get('status_code') == 404:
                admin_endpoints_results["audit_customer_payment_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["audit_customer_payment_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["audit_customer_payment_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Audit customer payment endpoint failed")
        
        # Test without admin authentication
        success_unauth, response_unauth = self.run_test(
            "Audit Customer Payment (No Auth)", 
            "POST", 
            "admin/audit-customer-payment", 
            [401, 403], 
            audit_payload
        )
        
        if success_unauth:
            print(f"   ✅ Endpoint properly requires admin authentication")
        
        # PHASE 2: TEST CLEANUP DUPLICATE SUBSCRIPTIONS ENDPOINT
        print("\n🧹 PHASE 2: TEST CLEANUP DUPLICATE SUBSCRIPTIONS ENDPOINT")
        print("-" * 60)
        print("Testing POST /api/admin/cleanup-duplicate-subscriptions")
        
        cleanup_payload = {}  # Usually no payload needed for cleanup
        
        success, response = self.run_test(
            "Cleanup Duplicate Subscriptions", 
            "POST", 
            "admin/cleanup-duplicate-subscriptions", 
            [200, 400, 404, 422, 500], 
            cleanup_payload, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["cleanup_duplicate_subscriptions_accessible"] = True
                admin_endpoints_results["cleanup_duplicate_subscriptions_working"] = True
                print(f"   ✅ Cleanup duplicate subscriptions endpoint working")
                if response.get('cleanup_results'):
                    print(f"   📊 Cleanup results: {response.get('cleanup_results')}")
            elif response.get('status_code') == 404:
                admin_endpoints_results["cleanup_duplicate_subscriptions_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["cleanup_duplicate_subscriptions_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["cleanup_duplicate_subscriptions_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Cleanup duplicate subscriptions endpoint failed")
        
        # PHASE 3: TEST CORRECT PAYMENT FROM RAZORPAY ENDPOINT
        print("\n🔧 PHASE 3: TEST CORRECT PAYMENT FROM RAZORPAY ENDPOINT")
        print("-" * 60)
        print("Testing POST /api/admin/correct-payment-from-razorpay")
        
        correct_payment_payload = {
            "razorpay_payment_id": "pay_REojjjLlRWUTWb",
            "user_email": "sp@theskinmantra.com"
        }
        
        success, response = self.run_test(
            "Correct Payment From Razorpay", 
            "POST", 
            "admin/correct-payment-from-razorpay", 
            [200, 400, 404, 422, 500], 
            correct_payment_payload, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["correct_payment_from_razorpay_accessible"] = True
                admin_endpoints_results["correct_payment_from_razorpay_working"] = True
                print(f"   ✅ Correct payment from Razorpay endpoint working")
                if response.get('correction_results'):
                    print(f"   📊 Correction results: {response.get('correction_results')}")
            elif response.get('status_code') == 404:
                admin_endpoints_results["correct_payment_from_razorpay_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["correct_payment_from_razorpay_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["correct_payment_from_razorpay_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Correct payment from Razorpay endpoint failed")
        
        # PHASE 4: TEST RUN PAYMENT RECONCILIATION ENDPOINT
        print("\n🔄 PHASE 4: TEST RUN PAYMENT RECONCILIATION ENDPOINT")
        print("-" * 60)
        print("Testing POST /api/admin/run-payment-reconciliation")
        
        reconciliation_payload = {
            "days_back": 7
        }
        
        success, response = self.run_test(
            "Run Payment Reconciliation", 
            "POST", 
            "admin/run-payment-reconciliation", 
            [200, 400, 404, 422, 500], 
            reconciliation_payload, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["run_payment_reconciliation_accessible"] = True
                admin_endpoints_results["run_payment_reconciliation_working"] = True
                print(f"   ✅ Run payment reconciliation endpoint working")
                if response.get('reconciliation_results'):
                    print(f"   📊 Reconciliation results: {response.get('reconciliation_results')}")
            elif response.get('status_code') == 404:
                admin_endpoints_results["run_payment_reconciliation_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["run_payment_reconciliation_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["run_payment_reconciliation_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Run payment reconciliation endpoint failed")
        
        # PHASE 5: TEST PAYMENT SYSTEM HEALTH ENDPOINT
        print("\n🏥 PHASE 5: TEST PAYMENT SYSTEM HEALTH ENDPOINT")
        print("-" * 60)
        print("Testing GET /api/admin/payment-system-health")
        
        success, response = self.run_test(
            "Payment System Health", 
            "GET", 
            "admin/payment-system-health?hours_back=24", 
            [200, 400, 404, 422, 500], 
            None, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["payment_system_health_accessible"] = True
                admin_endpoints_results["payment_system_health_working"] = True
                print(f"   ✅ Payment system health endpoint working")
                if response.get('health_metrics'):
                    print(f"   📊 Health metrics returned: {response.get('health_metrics')}")
            elif response.get('status_code') == 404:
                admin_endpoints_results["payment_system_health_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["payment_system_health_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["payment_system_health_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Payment system health endpoint failed")
        
        # PHASE 6: TEST PAYMENT ANALYTICS ENDPOINT
        print("\n📊 PHASE 6: TEST PAYMENT ANALYTICS ENDPOINT")
        print("-" * 60)
        print("Testing GET /api/admin/payment-analytics")
        
        success, response = self.run_test(
            "Payment Analytics", 
            "GET", 
            "admin/payment-analytics?days_back=30", 
            [200, 400, 404, 422, 500], 
            None, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["payment_analytics_accessible"] = True
                admin_endpoints_results["payment_analytics_working"] = True
                print(f"   ✅ Payment analytics endpoint working")
                if response.get('analytics_data'):
                    print(f"   📊 Analytics data returned: {response.get('analytics_data')}")
            elif response.get('status_code') == 404:
                admin_endpoints_results["payment_analytics_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["payment_analytics_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["payment_analytics_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Payment analytics endpoint failed")
        
        # PHASE 7: TEST EMERGENCY ACTIVATE SUBSCRIPTION ENDPOINT
        print("\n🚨 PHASE 7: TEST EMERGENCY ACTIVATE SUBSCRIPTION ENDPOINT")
        print("-" * 60)
        print("Testing POST /api/admin/emergency-activate-subscription")
        
        emergency_activation_payload = {
            "user_email": "sp@theskinmantra.com",
            "plan_type": "pro_regular",
            "payment_amount": 995,
            "razorpay_payment_id": "pay_test_emergency_activation",
            "reason": "Testing emergency activation endpoint"
        }
        
        success, response = self.run_test(
            "Emergency Activate Subscription", 
            "POST", 
            "admin/emergency-activate-subscription", 
            [200, 400, 404, 422, 500], 
            emergency_activation_payload, 
            self.admin_headers
        )
        
        if success:
            if response.get('status_code') == 200:
                admin_endpoints_results["emergency_activate_subscription_accessible"] = True
                admin_endpoints_results["emergency_activate_subscription_working"] = True
                print(f"   ✅ Emergency activate subscription endpoint working")
                if response.get('message'):
                    print(f"   📊 Response message: {response.get('message')}")
            elif response.get('status_code') == 404:
                admin_endpoints_results["emergency_activate_subscription_404_error"] = True
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
            elif response.get('status_code') == 500:
                admin_endpoints_results["emergency_activate_subscription_500_error"] = True
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                print(f"   🚨 Error details: {response.get('detail', 'No details')}")
            else:
                admin_endpoints_results["emergency_activate_subscription_accessible"] = True
                print(f"   ⚠️ Endpoint accessible but returned {response.get('status_code')}")
        else:
            print(f"   ❌ Emergency activate subscription endpoint failed")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("🚨 CRITICAL ADMIN ENDPOINTS TESTING - COMPREHENSIVE RESULTS")
        print("=" * 80)
        
        passed_tests = sum(admin_endpoints_results.values())
        total_tests = len(admin_endpoints_results)
        success_rate = (passed_tests / total_tests) * 100
        
        # Group results by endpoint
        endpoints = [
            ("audit-customer-payment", "audit_customer_payment"),
            ("cleanup-duplicate-subscriptions", "cleanup_duplicate_subscriptions"),
            ("correct-payment-from-razorpay", "correct_payment_from_razorpay"),
            ("run-payment-reconciliation", "run_payment_reconciliation"),
            ("payment-system-health", "payment_system_health"),
            ("payment-analytics", "payment_analytics"),
            ("emergency-activate-subscription", "emergency_activate_subscription")
        ]
        
        print("\nENDPOINT STATUS SUMMARY:")
        working_endpoints = 0
        error_404_endpoints = 0
        error_500_endpoints = 0
        
        for endpoint_name, endpoint_key in endpoints:
            print(f"\n/api/admin/{endpoint_name}:")
            
            if admin_endpoints_results.get(f"{endpoint_key}_working"):
                print(f"   ✅ WORKING - Returns 200 OK with proper data")
                working_endpoints += 1
            elif admin_endpoints_results.get(f"{endpoint_key}_404_error"):
                print(f"   ❌ 404 NOT FOUND - Endpoint does not exist")
                error_404_endpoints += 1
            elif admin_endpoints_results.get(f"{endpoint_key}_500_error"):
                print(f"   ❌ 500 INTERNAL SERVER ERROR - Backend crash")
                error_500_endpoints += 1
            elif admin_endpoints_results.get(f"{endpoint_key}_accessible"):
                print(f"   ⚠️ ACCESSIBLE - But returns non-200 status")
            else:
                print(f"   ❌ NOT ACCESSIBLE - Connection or other error")
        
        print(f"\nOVERALL ENDPOINT HEALTH:")
        print(f"   ✅ Working Endpoints: {working_endpoints}/7 ({(working_endpoints/7)*100:.1f}%)")
        print(f"   ❌ 404 Not Found Errors: {error_404_endpoints}/7 ({(error_404_endpoints/7)*100:.1f}%)")
        print(f"   ❌ 500 Server Errors: {error_500_endpoints}/7 ({(error_500_endpoints/7)*100:.1f}%)")
        
        # CRITICAL ISSUE ANALYSIS
        print(f"\n🚨 CRITICAL ISSUE ANALYSIS:")
        
        if error_404_endpoints > 0:
            print(f"\n❌ 404 NOT FOUND ERRORS DETECTED ({error_404_endpoints} endpoints)")
            print("   ROOT CAUSE: Endpoints not implemented or routing issues")
            print("   IMPACT: Admin tools completely unavailable")
            print("   URGENCY: HIGH - Admin cannot perform critical operations")
        
        if error_500_endpoints > 0:
            print(f"\n❌ 500 INTERNAL SERVER ERRORS DETECTED ({error_500_endpoints} endpoints)")
            print("   ROOT CAUSE: Backend crashes, database issues, or import errors")
            print("   IMPACT: Admin tools crash when accessed")
            print("   URGENCY: CRITICAL - System instability")
        
        if working_endpoints == 7:
            print(f"\n✅ ALL ADMIN ENDPOINTS WORKING CORRECTLY")
            print("   STATUS: All reported 404/500 errors have been resolved")
            print("   RESULT: Admin tools fully functional")
        elif working_endpoints >= 5:
            print(f"\n⚠️ MOST ADMIN ENDPOINTS WORKING ({working_endpoints}/7)")
            print("   STATUS: Significant progress, minor issues remain")
            print("   RESULT: Core admin functionality available")
        else:
            print(f"\n❌ MAJOR ADMIN ENDPOINT FAILURES ({working_endpoints}/7)")
            print("   STATUS: Critical admin tools not working")
            print("   RESULT: Admin operations severely impacted")
        
        # RECOMMENDATIONS
        print(f"\n🎯 RECOMMENDATIONS:")
        
        if error_404_endpoints > 0:
            print("1. 🔍 CHECK ROUTING: Verify admin endpoint routes are properly defined")
            print("2. 🔍 CHECK IMPORTS: Ensure all admin service modules are imported")
            print("3. 🔍 CHECK DEPLOYMENT: Verify latest code with admin endpoints is deployed")
        
        if error_500_endpoints > 0:
            print("4. 🔍 CHECK LOGS: Review backend logs for specific error messages")
            print("5. 🔍 CHECK DATABASE: Verify required tables/columns exist")
            print("6. 🔍 CHECK DEPENDENCIES: Ensure payment service dependencies are available")
        
        if working_endpoints < 7:
            print("7. 🔧 PRIORITY FIX: Focus on non-working endpoints for immediate resolution")
            print("8. 🧪 COMPREHENSIVE TEST: Re-run tests after fixes to verify resolution")
        
        print("-" * 80)
        print(f"Overall Test Success Rate: {self.tests_passed}/{self.tests_run} ({(self.tests_passed/self.tests_run)*100:.1f}%)")
        print(f"Admin Endpoints Working: {working_endpoints}/7 ({(working_endpoints/7)*100:.1f}%)")
        
        return admin_endpoints_results

def main():
    """Run the admin endpoints testing"""
    print("🚨 STARTING CRITICAL ADMIN ENDPOINTS TESTING")
    print("=" * 80)
    
    tester = AdminEndpointsTester()
    results = tester.test_admin_endpoints_404_500_errors()
    
    print("\n🎯 TESTING COMPLETE")
    print("=" * 80)
    
    return results

if __name__ == "__main__":
    main()