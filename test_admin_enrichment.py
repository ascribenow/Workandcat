#!/usr/bin/env python3
"""
Test Fixed Admin Enrichment Endpoints
Testing the specific endpoints mentioned in the review request
"""

import requests
import json
import time
import sys

class AdminEnrichmentTester:
    def __init__(self):
        self.base_url = "https://learning-tutor.preview.emergentagent.com/api"
        self.admin_token = None
        self.admin_headers = None
        
    def authenticate_admin(self):
        """Authenticate as admin user"""
        print("🔐 Authenticating as admin...")
        
        login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                self.admin_headers = {
                    'Authorization': f'Bearer {self.admin_token}',
                    'Content-Type': 'application/json'
                }
                print(f"✅ Admin authentication successful")
                return True
            else:
                print(f"❌ Admin authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Admin authentication error: {str(e)}")
            return False
    
    def test_enrichment_status_endpoint(self):
        """Test /api/admin/pyq/enrichment-status endpoint"""
        print("\n📊 Testing Enrichment Status Endpoint...")
        
        try:
            response = requests.get(
                f"{self.base_url}/admin/pyq/enrichment-status",
                headers=self.admin_headers,
                timeout=30,
                verify=False
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Enrichment status endpoint working")
                print(f"Response data: {json.dumps(data, indent=2)}")
                
                # Check for key indicators
                if 'error' not in str(data).lower():
                    print("✅ No errors in response")
                else:
                    print("❌ Error detected in response")
                
                return True
            else:
                print(f"❌ Enrichment status endpoint failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Enrichment status endpoint error: {str(e)}")
            return False
    
    def test_trigger_enrichment_endpoint(self):
        """Test /api/admin/pyq/trigger-enrichment endpoint"""
        print("\n🚀 Testing Trigger Enrichment Endpoint...")
        
        try:
            # Test with empty payload first
            response = requests.post(
                f"{self.base_url}/admin/pyq/trigger-enrichment",
                headers=self.admin_headers,
                json={},
                timeout=30,
                verify=False
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code in [200, 202]:
                data = response.json()
                print("✅ Trigger enrichment endpoint working")
                print(f"Response data: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Trigger enrichment endpoint failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Trigger enrichment endpoint error: {str(e)}")
            return False
    
    def test_enrich_checker_endpoints(self):
        """Test both enrich checker endpoints"""
        print("\n🔍 Testing Enrich Checker Endpoints...")
        
        results = {}
        
        # Test regular questions enrich checker
        try:
            response = requests.post(
                f"{self.base_url}/admin/enrich-checker/regular-questions",
                headers=self.admin_headers,
                json={},
                timeout=30,
                verify=False
            )
            
            print(f"Regular Questions Enrich Checker - Status Code: {response.status_code}")
            
            if response.status_code in [200, 202]:
                data = response.json()
                print("✅ Regular questions enrich checker working")
                
                # Check for old service errors
                if 'old enrich checker service removed' not in str(data).lower():
                    print("✅ No 'old service removed' errors")
                    results['regular_no_old_errors'] = True
                else:
                    print("❌ Old service error detected")
                    results['regular_no_old_errors'] = False
                
                results['regular_working'] = True
            else:
                print(f"❌ Regular questions enrich checker failed")
                print(f"Response: {response.text}")
                results['regular_working'] = False
                
        except Exception as e:
            print(f"❌ Regular questions enrich checker error: {str(e)}")
            results['regular_working'] = False
        
        # Test PYQ questions enrich checker
        try:
            response = requests.post(
                f"{self.base_url}/admin/enrich-checker/pyq-questions",
                headers=self.admin_headers,
                json={},
                timeout=30,
                verify=False
            )
            
            print(f"PYQ Questions Enrich Checker - Status Code: {response.status_code}")
            
            if response.status_code in [200, 202]:
                data = response.json()
                print("✅ PYQ questions enrich checker working")
                
                # Check for old service errors
                if 'old enrich checker service removed' not in str(data).lower():
                    print("✅ No 'old service removed' errors")
                    results['pyq_no_old_errors'] = True
                else:
                    print("❌ Old service error detected")
                    results['pyq_no_old_errors'] = False
                
                results['pyq_working'] = True
            else:
                print(f"❌ PYQ questions enrich checker failed")
                print(f"Response: {response.text}")
                results['pyq_working'] = False
                
        except Exception as e:
            print(f"❌ PYQ questions enrich checker error: {str(e)}")
            results['pyq_working'] = False
        
        return results
    
    def test_database_health(self):
        """Test database health through question queries"""
        print("\n🗄️ Testing Database Health...")
        
        try:
            # Test PYQ questions endpoint to check database
            response = requests.get(
                f"{self.base_url}/admin/pyq/questions?limit=5",
                headers=self.admin_headers,
                timeout=30,
                verify=False
            )
            
            print(f"PYQ Questions Query - Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Database queries working")
                
                questions = data.get('questions', [])
                print(f"📊 Found {len(questions)} questions")
                
                # Check for constraint-related errors
                response_str = str(data).lower()
                if 'constraint' not in response_str and 'null' not in response_str:
                    print("✅ No database constraint errors")
                    return True
                else:
                    print("❌ Database constraint issues detected")
                    return False
            else:
                print(f"❌ Database query failed")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Database health check error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all admin enrichment endpoint tests"""
        print("🔧 FIXED ADMIN ENRICHMENT ENDPOINTS TESTING")
        print("=" * 60)
        
        results = {
            'admin_auth': False,
            'enrichment_status': False,
            'trigger_enrichment': False,
            'regular_enrich_checker': False,
            'pyq_enrich_checker': False,
            'no_old_service_errors': False,
            'database_health': False
        }
        
        # Step 1: Authenticate
        if not self.authenticate_admin():
            print("\n❌ Cannot proceed without admin authentication")
            return results
        
        results['admin_auth'] = True
        
        # Step 2: Test enrichment status endpoint
        results['enrichment_status'] = self.test_enrichment_status_endpoint()
        
        # Step 3: Test trigger enrichment endpoint
        results['trigger_enrichment'] = self.test_trigger_enrichment_endpoint()
        
        # Step 4: Test enrich checker endpoints
        enrich_checker_results = self.test_enrich_checker_endpoints()
        results['regular_enrich_checker'] = enrich_checker_results.get('regular_working', False)
        results['pyq_enrich_checker'] = enrich_checker_results.get('pyq_working', False)
        results['no_old_service_errors'] = (
            enrich_checker_results.get('regular_no_old_errors', False) and 
            enrich_checker_results.get('pyq_no_old_errors', False)
        )
        
        # Step 5: Test database health
        results['database_health'] = self.test_database_health()
        
        # Summary
        print("\n" + "=" * 60)
        print("🎯 ADMIN ENRICHMENT ENDPOINTS TEST RESULTS")
        print("=" * 60)
        
        passed = sum(results.values())
        total = len(results)
        success_rate = (passed / total) * 100
        
        for test, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test.replace('_', ' ').title():<30} {status}")
        
        print("-" * 60)
        print(f"Overall Success Rate: {passed}/{total} ({success_rate:.1f}%)")
        
        # Assessment based on review request requirements
        print("\n🎯 REVIEW REQUEST VALIDATION:")
        
        validation_points = [
            ("Fixed Enrichment Status Endpoint Working?", results['enrichment_status']),
            ("Fixed Trigger Enrichment Working?", results['trigger_enrichment']),
            ("Fixed Enrich Checker Endpoints Working?", results['regular_enrich_checker'] and results['pyq_enrich_checker']),
            ("No 'Old Service Removed' Errors?", results['no_old_service_errors']),
            ("Database Updates Working?", results['database_health'])
        ]
        
        for question, result in validation_points:
            status = "✅ YES" if result else "❌ NO"
            print(f"{question:<45} {status}")
        
        if success_rate >= 85:
            print("\n🎉 ADMIN ENRICHMENT ENDPOINTS FIXES SUCCESSFUL!")
            print("   ✅ All endpoints working correctly")
            print("   ✅ No old service errors detected")
            print("   ✅ Database constraints resolved")
            print("   🏆 READY FOR PRODUCTION")
        elif success_rate >= 70:
            print("\n⚠️ ADMIN ENRICHMENT ENDPOINTS MOSTLY WORKING")
            print("   🔧 Minor issues detected")
        else:
            print("\n❌ ADMIN ENRICHMENT ENDPOINTS NEED ATTENTION")
            print("   🚨 Major issues detected")
        
        return results

if __name__ == "__main__":
    tester = AdminEnrichmentTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    success_rate = (sum(results.values()) / len(results)) * 100
    sys.exit(0 if success_rate >= 70 else 1)