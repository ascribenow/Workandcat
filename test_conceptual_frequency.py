#!/usr/bin/env python3
"""
Test Enhanced Conceptual Frequency Analysis System
Focus on testing the newly implemented conceptual frequency analysis endpoints
"""

import requests
import json
import sys

class ConceptualFrequencyTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:300]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def login_admin(self):
        """Login as admin user"""
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin logged in successfully")
            return True
        else:
            print(f"   ❌ Admin login failed")
            return False

    def test_conceptual_frequency_analysis_endpoint(self):
        """Test POST /api/admin/test/conceptual-frequency"""
        if not self.admin_token:
            print("❌ Cannot test conceptual frequency - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        print("\n🧪 Testing Conceptual Frequency Analysis Endpoint...")
        success, response = self.run_test(
            "Conceptual Frequency Analysis", 
            "POST", 
            "admin/test/conceptual-frequency", 
            200, 
            {}, 
            headers
        )
        
        if success:
            print("   ✅ Conceptual frequency analysis endpoint working")
            analysis_results = response.get('analysis_results', {})
            if analysis_results:
                print(f"   Analysis results found: {type(analysis_results)}")
                if isinstance(analysis_results, dict):
                    print(f"   Result keys: {list(analysis_results.keys())}")
            return True
        else:
            print("   ❌ Conceptual frequency analysis endpoint failed")
            print("   This indicates missing ConceptualFrequencyAnalyzer module")
            return False

    def test_enhanced_nightly_processing_endpoint(self):
        """Test POST /api/admin/run-enhanced-nightly"""
        if not self.admin_token:
            print("❌ Cannot test enhanced nightly - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        print("\n🌙 Testing Enhanced Nightly Processing Endpoint...")
        success, response = self.run_test(
            "Enhanced Nightly Processing", 
            "POST", 
            "admin/run-enhanced-nightly", 
            200, 
            {}, 
            headers
        )
        
        if success:
            print("   ✅ Enhanced nightly processing endpoint working")
            processing_results = response.get('processing_results', {})
            if processing_results:
                print(f"   Processing results found: {type(processing_results)}")
                if isinstance(processing_results, dict):
                    print(f"   Result keys: {list(processing_results.keys())}")
            return True
        else:
            print("   ❌ Enhanced nightly processing endpoint failed")
            print("   This indicates missing EnhancedNightlyEngine module")
            return False

    def test_database_schema_conceptual_fields(self):
        """Test database schema for new conceptual frequency fields"""
        if not self.admin_token:
            print("❌ Cannot test database schema - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        print("\n🗄️ Testing Database Schema for Conceptual Frequency Fields...")
        success, response = self.run_test(
            "Check Questions Schema", 
            "GET", 
            "questions?limit=5", 
            200, 
            None, 
            headers
        )
        
        if success:
            questions = response.get('questions', [])
            if questions:
                first_question = questions[0]
                print(f"   Sample question ID: {first_question.get('id')}")
                
                # Check for new conceptual frequency fields mentioned in review request
                conceptual_fields = [
                    'pyq_conceptual_matches', 
                    'total_pyq_analyzed', 
                    'top_matching_concepts',
                    'conceptual_frequency_score'
                ]
                
                found_fields = [field for field in conceptual_fields if field in first_question]
                print(f"   Conceptual frequency fields found: {found_fields}")
                print(f"   Expected fields: {conceptual_fields}")
                
                if len(found_fields) >= 2:
                    print("   ✅ Database schema includes conceptual frequency fields")
                    return True
                else:
                    print("   ❌ Database schema missing conceptual frequency fields")
                    print("   This indicates the database schema hasn't been updated yet")
                    return False
            else:
                print("   ⚠️ No questions found to check schema")
                return False
        else:
            print("   ❌ Failed to check database schema")
            return False

    def test_llm_pattern_analysis(self):
        """Test if LLM pattern analysis is working"""
        if not self.admin_token:
            print("❌ Cannot test LLM pattern analysis - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        print("\n🤖 Testing LLM Pattern Analysis Integration...")
        
        # Check if questions have been analyzed with LLM patterns
        success, response = self.run_test(
            "Check LLM Analysis in Questions", 
            "GET", 
            "questions?limit=10", 
            200, 
            None, 
            headers
        )
        
        if success:
            questions = response.get('questions', [])
            llm_analyzed_count = 0
            
            for question in questions:
                # Look for signs of LLM analysis
                if (question.get('subcategory') and 
                    question.get('type_of_question') and
                    question.get('difficulty_score') is not None):
                    llm_analyzed_count += 1
            
            analysis_rate = (llm_analyzed_count / len(questions)) * 100 if questions else 0
            print(f"   Questions with LLM analysis: {llm_analyzed_count}/{len(questions)}")
            print(f"   LLM analysis rate: {analysis_rate:.1f}%")
            
            if analysis_rate >= 50:
                print("   ✅ LLM pattern analysis appears to be working")
                return True
            else:
                print("   ❌ Insufficient LLM pattern analysis")
                return False
        
        return False

    def run_all_tests(self):
        """Run all conceptual frequency analysis tests"""
        print("🚀 Enhanced Conceptual Frequency Analysis System Testing")
        print("=" * 70)
        
        # Login as admin
        if not self.login_admin():
            print("❌ Cannot proceed without admin access")
            return
        
        # Test 1: Conceptual frequency analysis endpoint
        test1_result = self.test_conceptual_frequency_analysis_endpoint()
        
        # Test 2: Enhanced nightly processing endpoint
        test2_result = self.test_enhanced_nightly_processing_endpoint()
        
        # Test 3: Database schema for conceptual frequency fields
        test3_result = self.test_database_schema_conceptual_fields()
        
        # Test 4: LLM pattern analysis integration
        test4_result = self.test_llm_pattern_analysis()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 ENHANCED CONCEPTUAL FREQUENCY ANALYSIS RESULTS")
        print("=" * 70)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print(f"\n🧪 Individual Test Results:")
        print(f"   Conceptual Frequency Endpoint: {'✅ PASSED' if test1_result else '❌ FAILED'}")
        print(f"   Enhanced Nightly Endpoint: {'✅ PASSED' if test2_result else '❌ FAILED'}")
        print(f"   Database Schema Check: {'✅ PASSED' if test3_result else '❌ FAILED'}")
        print(f"   LLM Pattern Analysis: {'✅ PASSED' if test4_result else '❌ FAILED'}")
        
        passed_tests = sum([test1_result, test2_result, test3_result, test4_result])
        
        if passed_tests >= 3:
            print("\n🎉 ENHANCED CONCEPTUAL FREQUENCY ANALYSIS SYSTEM FUNCTIONAL!")
            print("   The system appears to be properly implemented.")
        elif passed_tests >= 2:
            print("\n⚠️ ENHANCED CONCEPTUAL FREQUENCY ANALYSIS PARTIALLY WORKING")
            print("   Some components are missing or not fully implemented.")
        else:
            print("\n❌ ENHANCED CONCEPTUAL FREQUENCY ANALYSIS SYSTEM NOT IMPLEMENTED")
            print("   Major components are missing:")
            if not test1_result:
                print("   - ConceptualFrequencyAnalyzer module missing")
            if not test2_result:
                print("   - EnhancedNightlyEngine module missing")
            if not test3_result:
                print("   - Database schema not updated with conceptual frequency fields")
            if not test4_result:
                print("   - LLM pattern analysis not working properly")

if __name__ == "__main__":
    tester = ConceptualFrequencyTester()
    tester.run_all_tests()