#!/usr/bin/env python3
"""
Focused test for Enhanced Time-Weighted Conceptual Frequency Analysis System
"""

import requests
import json
from datetime import datetime

class FrequencySystemTester:
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

    def authenticate_admin(self):
        """Authenticate as admin user"""
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin authenticated successfully")
            return True
        return False

    def test_time_weighted_frequency_analysis(self):
        """Test Time-Weighted Frequency Analysis System (20-year data, 10-year relevance)"""
        print("🔍 Testing Time-Weighted Frequency Analysis System...")
        
        if not self.admin_token:
            print("   ❌ Cannot test time-weighted frequency analysis - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        # Test the time-weighted frequency analysis endpoint
        success, response = self.run_test("Time-Weighted Frequency Analysis", "POST", "admin/test/time-weighted-frequency", 200, {}, headers)
        if not success:
            return False
        
        # Verify response structure and key components
        required_fields = ['config', 'sample_data', 'temporal_pattern', 'frequency_metrics', 'insights', 'explanation']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing required fields in response: {missing_fields}")
            return False
        
        print("   ✅ Time-weighted frequency analysis response structure complete")
        
        # Verify configuration
        config = response.get('config', {})
        if config.get('total_data_years') == 20 and config.get('relevance_window_years') == 10:
            print("   ✅ Correct configuration: 20-year data with 10-year relevance window")
        else:
            print(f"   ❌ Incorrect configuration: {config}")
            return False
        
        # Verify temporal pattern analysis
        temporal_pattern = response.get('temporal_pattern', {})
        required_pattern_fields = ['concept_id', 'total_occurrences', 'relevance_window_occurrences', 
                                 'weighted_frequency_score', 'trend_direction', 'trend_strength', 'recency_score']
        missing_pattern_fields = [field for field in required_pattern_fields if field not in temporal_pattern]
        
        if missing_pattern_fields:
            print(f"   ❌ Missing temporal pattern fields: {missing_pattern_fields}")
            return False
        
        print("   ✅ Temporal pattern analysis complete with all required fields")
        print(f"   Concept ID: {temporal_pattern.get('concept_id')}")
        print(f"   Total occurrences: {temporal_pattern.get('total_occurrences')}")
        print(f"   Relevance window occurrences: {temporal_pattern.get('relevance_window_occurrences')}")
        print(f"   Weighted frequency score: {temporal_pattern.get('weighted_frequency_score')}")
        print(f"   Trend direction: {temporal_pattern.get('trend_direction')}")
        print(f"   Trend strength: {temporal_pattern.get('trend_strength')}")
        print(f"   Recency score: {temporal_pattern.get('recency_score')}")
        
        # Verify insights generation
        insights = response.get('insights', {})
        if insights and len(insights) > 0:
            print("   ✅ Frequency insights generated successfully")
            print(f"   Sample insights: {list(insights.keys())[:3]}")
        else:
            print("   ❌ No frequency insights generated")
            return False
        
        # Verify exponential decay calculations
        frequency_metrics = response.get('frequency_metrics', {})
        if 'weighted_score' in frequency_metrics and 'decay_factor' in frequency_metrics:
            print("   ✅ Exponential decay calculations present")
            print(f"   Weighted score: {frequency_metrics.get('weighted_score')}")
            print(f"   Decay factor: {frequency_metrics.get('decay_factor')}")
        else:
            print("   ❌ Exponential decay calculations missing")
            return False
        
        # Verify trend detection
        trend_direction = temporal_pattern.get('trend_direction', '').lower()
        valid_trends = ['increasing', 'decreasing', 'emerging', 'declining', 'stable']
        if trend_direction in valid_trends:
            print(f"   ✅ Trend detection working: {trend_direction}")
        else:
            print(f"   ❌ Invalid trend direction: {trend_direction}")
            return False
        
        return True

    def test_enhanced_nightly_processing(self):
        """Test Enhanced Nightly Processing with Time-Weighted + Conceptual Analysis"""
        print("🔍 Testing Enhanced Nightly Processing...")
        
        if not self.admin_token:
            print("   ❌ Cannot test enhanced nightly processing - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        # Test the enhanced nightly processing endpoint
        success, response = self.run_test("Enhanced Nightly Processing", "POST", "admin/run-enhanced-nightly", 200, {}, headers)
        if not success:
            return False
        
        # Verify response structure
        required_fields = ['message', 'success', 'processing_results']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing required fields in response: {missing_fields}")
            return False
        
        if not response.get('success'):
            print("   ❌ Enhanced nightly processing reported failure")
            return False
        
        print("   ✅ Enhanced nightly processing completed successfully")
        
        # Verify processing results
        processing_results = response.get('processing_results', {})
        if processing_results:
            print("   ✅ Processing results available")
            print(f"   Processing results keys: {list(processing_results.keys())}")
            
            # Check for integration of time-weighted + conceptual analysis
            if 'time_weighted_analysis' in processing_results or 'conceptual_analysis' in processing_results:
                print("   ✅ Time-weighted and conceptual analysis integration confirmed")
            else:
                print("   ⚠️ Time-weighted and conceptual analysis integration not explicitly confirmed")
        else:
            print("   ❌ No processing results returned")
            return False
        
        return True

    def test_conceptual_frequency_analysis(self):
        """Test Conceptual Frequency Analysis System"""
        print("🔍 Testing Conceptual Frequency Analysis System...")
        
        if not self.admin_token:
            print("   ❌ Cannot test conceptual frequency analysis - no admin token")
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        # Test the conceptual frequency analysis endpoint
        success, response = self.run_test("Conceptual Frequency Analysis", "POST", "admin/test/conceptual-frequency", 200, {}, headers)
        if not success:
            return False
        
        # Verify response structure
        required_fields = ['message', 'question_id', 'question_stem', 'analysis_results']
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"   ❌ Missing required fields in response: {missing_fields}")
            return False
        
        print("   ✅ Conceptual frequency analysis response structure complete")
        
        # Verify analysis results
        analysis_results = response.get('analysis_results', {})
        if not analysis_results:
            print("   ❌ No analysis results returned")
            return False
        
        # Check for key analysis components
        expected_components = ['frequency_score', 'conceptual_matches', 'total_pyq_analyzed', 
                             'top_matching_concepts', 'analysis_method', 'pattern_keywords']
        
        present_components = [comp for comp in expected_components if comp in analysis_results]
        print(f"   Analysis components present: {len(present_components)}/{len(expected_components)}")
        print(f"   Components: {present_components}")
        
        if len(present_components) >= 4:  # At least 4 of 6 components should be present
            print("   ✅ Conceptual frequency analysis working with sufficient components")
        else:
            print("   ❌ Insufficient conceptual frequency analysis components")
            return False
        
        # Verify frequency score
        frequency_score = analysis_results.get('frequency_score')
        if frequency_score is not None and isinstance(frequency_score, (int, float)):
            print(f"   ✅ Frequency score calculated: {frequency_score}")
        else:
            print("   ❌ Frequency score missing or invalid")
            return False
        
        # Verify conceptual matches
        conceptual_matches = analysis_results.get('conceptual_matches', [])
        if conceptual_matches and len(conceptual_matches) > 0:
            print(f"   ✅ Conceptual matches found: {len(conceptual_matches)}")
        else:
            print("   ❌ No conceptual matches found")
            return False
        
        return True

    def run_comprehensive_test(self):
        """Run comprehensive test of the Enhanced Time-Weighted Conceptual Frequency Analysis System"""
        print("🚀 Enhanced Time-Weighted Conceptual Frequency Analysis System Test")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate_admin():
            print("❌ Authentication failed - cannot proceed with tests")
            return
        
        test_results = {
            "time_weighted_frequency": False,
            "enhanced_nightly_processing": False,
            "conceptual_frequency": False
        }
        
        # Test 1: Time-Weighted Frequency Analysis
        print("\n📊 TEST 1: Time-Weighted Frequency Analysis")
        test_results["time_weighted_frequency"] = self.test_time_weighted_frequency_analysis()
        
        # Test 2: Enhanced Nightly Processing
        print("\n🌙 TEST 2: Enhanced Nightly Processing")
        test_results["enhanced_nightly_processing"] = self.test_enhanced_nightly_processing()
        
        # Test 3: Conceptual Frequency Analysis
        print("\n🧠 TEST 3: Conceptual Frequency Analysis")
        test_results["conceptual_frequency"] = self.test_conceptual_frequency_analysis()
        
        # Calculate overall success rate
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        print(f"\n📈 ENHANCED TIME-WEIGHTED CONCEPTUAL FREQUENCY SYSTEM RESULTS:")
        print("=" * 80)
        print(f"Time-Weighted Frequency Analysis: {'✅ PASSED' if test_results['time_weighted_frequency'] else '❌ FAILED'}")
        print(f"Enhanced Nightly Processing: {'✅ PASSED' if test_results['enhanced_nightly_processing'] else '❌ FAILED'}")
        print(f"Conceptual Frequency Analysis: {'✅ PASSED' if test_results['conceptual_frequency'] else '❌ FAILED'}")
        print(f"Overall Success Rate: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        print(f"\nTests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Overall Test Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 ENHANCED TIME-WEIGHTED CONCEPTUAL FREQUENCY SYSTEM WORKING!")
        elif success_rate >= 60:
            print("\n⚠️ ENHANCED TIME-WEIGHTED CONCEPTUAL FREQUENCY SYSTEM PARTIALLY WORKING")
        else:
            print("\n❌ ENHANCED TIME-WEIGHTED CONCEPTUAL FREQUENCY SYSTEM FAILED")

if __name__ == "__main__":
    tester = FrequencySystemTester()
    tester.run_comprehensive_test()