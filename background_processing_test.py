#!/usr/bin/env python3
"""
Background Processing and LLM Enrichment Testing Script
Tests the background processing functionality after PostgreSQL migration
"""

import requests
import json
import time
from datetime import datetime

class BackgroundProcessingTester:
    def __init__(self):
        self.base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def test_api_call(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Make API call and return success status and response"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"API call failed: {method} {endpoint} - Status {response.status_code}", "ERROR")
                try:
                    error_data = response.json()
                    self.log(f"Error details: {error_data}", "ERROR")
                except:
                    self.log(f"Error text: {response.text[:200]}", "ERROR")
                return False, {}

        except Exception as e:
            self.log(f"API call exception: {method} {endpoint} - {str(e)}", "ERROR")
            return False, {}

    def authenticate_admin(self):
        """Authenticate as admin"""
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.test_api_call("POST", "auth/login", admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.log("✅ Admin authentication successful")
            return True
        else:
            self.log("❌ Admin authentication failed", "ERROR")
            return False

    def test_background_processing(self):
        """Test background processing and LLM enrichment"""
        self.log("Testing Background Processing and LLM Enrichment")
        
        if not self.admin_token:
            self.log("❌ No admin token", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Create a question that should trigger background processing
        question_data = {
            "stem": "Background Processing Test: A train travels 300 km in 4 hours. What is its average speed in km/h?",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "source": "Background Processing Test"
        }
        
        self.log("Creating question for background processing...")
        success, response = self.test_api_call("POST", "questions", question_data, headers)
        if not success or 'question_id' not in response:
            self.log("❌ Failed to create question for background processing", "ERROR")
            return False
        
        question_id = response['question_id']
        status = response.get('status', 'unknown')
        self.log(f"✅ Question created: {question_id}")
        self.log(f"   Initial status: {status}")
        
        # Wait for background processing
        self.log("Waiting for background processing to complete...")
        time.sleep(10)  # Wait 10 seconds for processing
        
        # Check if processing completed
        success, response = self.test_api_call("GET", f"questions?limit=50", headers=headers)
        if not success:
            self.log("❌ Failed to retrieve questions for processing check", "ERROR")
            return False
        
        questions = response.get('questions', [])
        test_question = None
        
        for q in questions:
            if q.get('id') == question_id:
                test_question = q
                break
        
        if not test_question:
            self.log("❌ Test question not found after creation", "ERROR")
            return False
        
        # Check processing results
        answer = test_question.get('answer')
        solution_approach = test_question.get('solution_approach')
        detailed_solution = test_question.get('detailed_solution')
        learning_impact = test_question.get('learning_impact')
        importance_index = test_question.get('importance_index')
        is_active = test_question.get('is_active')
        
        self.log("Background processing results:")
        self.log(f"   Answer: {answer}")
        self.log(f"   Solution approach: {solution_approach}")
        self.log(f"   Learning impact: {learning_impact}")
        self.log(f"   Importance index: {importance_index}")
        self.log(f"   Is active: {is_active}")
        
        # Evaluate processing success
        processing_success = True
        
        if answer and answer != "To be generated by LLM":
            self.log("✅ LLM enrichment completed - answer generated")
        else:
            self.log("❌ LLM enrichment failed - no answer generated")
            processing_success = False
        
        if learning_impact and learning_impact > 0:
            self.log("✅ PYQ frequency analysis completed")
        else:
            self.log("⚠️ PYQ frequency analysis may not have completed")
        
        if is_active:
            self.log("✅ Question activated after processing")
        else:
            self.log("⚠️ Question not activated (may still be processing)")
        
        return processing_success

    def test_admin_processing_endpoints(self):
        """Test admin processing endpoints"""
        self.log("Testing Admin Processing Endpoints")
        
        if not self.admin_token:
            self.log("❌ No admin token", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Test manual nightly processing
        success, response = self.test_api_call("POST", "admin/run-enhanced-nightly", {}, headers)
        if success:
            self.log("✅ Enhanced nightly processing endpoint working")
            self.log(f"   Status: {response.get('status', 'unknown')}")
            self.log(f"   Duration: {response.get('duration', 'unknown')}")
        else:
            self.log("❌ Enhanced nightly processing failed", "ERROR")
            return False

        return True

    def test_frequency_analysis_endpoints(self):
        """Test frequency analysis endpoints"""
        self.log("Testing Frequency Analysis Endpoints")
        
        if not self.admin_token:
            self.log("❌ No admin token", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Test conceptual frequency analysis
        test_question = {
            "stem": "A car travels 150 km in 2.5 hours. What is its speed?",
            "subcategory": "Time–Speed–Distance (TSD)"
        }
        
        success, response = self.test_api_call("POST", "admin/test/conceptual-frequency", test_question, headers)
        if success:
            self.log("✅ Conceptual frequency analysis endpoint working")
            analysis = response.get('analysis', {})
            self.log(f"   Status: {analysis.get('status', 'unknown')}")
            self.log(f"   Conceptual score: {analysis.get('conceptual_score', 'unknown')}")
        else:
            self.log("❌ Conceptual frequency analysis failed", "ERROR")
            return False

        # Test time-weighted frequency analysis
        success, response = self.test_api_call("POST", "admin/test/time-weighted-frequency", test_question, headers)
        if success:
            self.log("✅ Time-weighted frequency analysis endpoint working")
            analysis = response.get('analysis', {})
            self.log(f"   Status: {analysis.get('status', 'unknown')}")
            self.log(f"   Frequency score: {analysis.get('frequency_score', 'unknown')}")
        else:
            self.log("❌ Time-weighted frequency analysis failed", "ERROR")
            return False

        return True

    def run_comprehensive_test(self):
        """Run comprehensive background processing test"""
        self.log("🔍 COMPREHENSIVE BACKGROUND PROCESSING TESTING")
        self.log("=" * 60)
        self.log("Testing LLM enrichment and frequency analysis systems")
        self.log("Database: PostgreSQL (Supabase)")
        self.log("=" * 60)

        # Authenticate
        if not self.authenticate_admin():
            return False

        # Run test suite
        test_results = {}
        
        test_results['background_processing'] = self.test_background_processing()
        test_results['admin_processing_endpoints'] = self.test_admin_processing_endpoints()
        test_results['frequency_analysis_endpoints'] = self.test_frequency_analysis_endpoints()

        # Summary
        self.log("=" * 60)
        self.log("BACKGROUND PROCESSING TEST RESULTS")
        self.log("=" * 60)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        self.log("-" * 60)
        self.log(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        self.log(f"API Calls: {self.tests_passed}/{self.tests_run} successful")
        
        if success_rate >= 80:
            self.log("🎉 BACKGROUND PROCESSING SUCCESSFUL!")
            self.log("LLM enrichment and frequency analysis systems working")
        elif success_rate >= 60:
            self.log("⚠️ Background processing mostly working with minor issues")
        else:
            self.log("❌ Background processing has significant issues")
        
        return success_rate >= 60

if __name__ == "__main__":
    tester = BackgroundProcessingTester()
    success = tester.run_comprehensive_test()
    exit(0 if success else 1)