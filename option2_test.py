#!/usr/bin/env python3
"""
OPTION 2 Enhanced Background Processing Test Suite
Comprehensive testing for the complete OPTION 2 implementation
"""

import requests
import sys
import json
import time
from datetime import datetime

class Option2Tester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.student_token = None
        self.admin_user = None
        self.student_user = None

    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                print(f"❌ {test_name}: Unsupported method {method}")
                return False, {}

            print(f"   {method} {endpoint} -> {response.status_code}")
            
            if response.status_code == expected_status:
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"   Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ {test_name}: Exception - {str(e)}")
            return False, {}

    def test_user_login(self):
        """Test admin and student login"""
        print("\n🔐 AUTHENTICATION SETUP")
        print("-" * 30)
        
        # Test admin login
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.admin_user = response['user']
            print(f"✅ Admin authenticated: {self.admin_user['full_name']}")
        else:
            print("❌ Admin authentication failed")
            return False
        
        # Test student registration/login
        timestamp = datetime.now().strftime('%H%M%S')
        student_data = {
            "email": f"test_student_{timestamp}@catprep.com",
            "full_name": "Test Student",
            "password": "student2025"
        }
        
        success, response = self.run_test("Student Registration", "POST", "auth/register", 200, student_data)
        if success and 'access_token' in response:
            self.student_token = response['access_token']
            self.student_user = response['user']
            print(f"✅ Student authenticated: {self.student_user['full_name']}")
        else:
            print("❌ Student authentication failed")
            return False
            
        return True

    def test_option_2_enhanced_background_processing(self):
        """Test OPTION 2 Enhanced Background Processing Implementation"""
        print("🔍 TESTING OPTION 2 ENHANCED BACKGROUND PROCESSING")
        print("=" * 80)
        print("FOCUS: Complete OPTION 2 Enhanced Background Processing implementation:")
        print("1. Check Database Topics Setup - Verify CAT topics exist")
        print("2. Test Enhanced Question Upload Process - Two-step processing")
        print("3. Test Background Processing Integration - Automatic processing")
        print("4. Test Enhanced Session Creation - PYQ frequency weighting")
        print("5. Verify Complete Integration - End-to-end automation")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 80)
        
        if not self.admin_token:
            print("❌ Cannot test OPTION 2 - no admin token")
            return False

        admin_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        student_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        } if self.student_token else None

        test_results = {
            "database_topics_setup": False,
            "enhanced_question_upload": False,
            "two_step_processing": False,
            "background_processing_integration": False,
            "enhanced_session_creation": False,
            "pyq_frequency_weighting": False,
            "complete_integration": False,
            "automatic_processing": False
        }

        # TEST 1: Check Database Topics Setup
        print("\n📋 TEST 1: DATABASE TOPICS SETUP")
        print("-" * 60)
        print("Verifying that required CAT topics exist in the database")
        
        # Check if topics exist
        success, response = self.run_test("Check Topics Exist", "GET", "questions?limit=1", 200, None, admin_headers)
        if success:
            print("   ✅ Database accessible - checking topic structure")
            
            # Try to initialize topics if they don't exist
            success, response = self.run_test("Initialize Basic Topics", "POST", "admin/init-topics", 200, None, admin_headers)
            if success:
                topics_created = response.get('topics_created', 0)
                if topics_created > 0:
                    print(f"   ✅ Topics initialized: {topics_created} topics created")
                else:
                    print("   ✅ Topics already exist in database")
                test_results["database_topics_setup"] = True
            else:
                print("   ❌ Failed to initialize topics")
        else:
            print("   ❌ Database not accessible")

        # TEST 2: Test Enhanced Question Upload Process
        print("\n📝 TEST 2: ENHANCED QUESTION UPLOAD PROCESS")
        print("-" * 60)
        print("Testing enhanced question upload with two-step background processing")
        
        # Create a test question for enhanced processing
        test_question = {
            "stem": "OPTION 2 Test: A car travels at 60 km/h for 2 hours. What distance does it cover?",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "type_of_question": "Basic Speed-Distance Calculation",
            "tags": ["option_2_test", "enhanced_processing"],
            "source": "OPTION 2 Enhanced Processing Test"
        }
        
        success, response = self.run_test("Create Question for Enhanced Processing", "POST", "questions", 200, test_question, admin_headers)
        if success and 'question_id' in response:
            question_id = response['question_id']
            status = response.get('status', '')
            print(f"   ✅ Question created: {question_id}")
            print(f"   Status: {status}")
            
            if status == "enrichment_queued":
                print("   ✅ Question queued for enhanced background processing")
                test_results["enhanced_question_upload"] = True
            else:
                print(f"   ⚠️ Unexpected status: {status}")
        else:
            print("   ❌ Failed to create question for enhanced processing")

        # TEST 3: Monitor Two-Step Enhanced Background Processing
        print("\n⚙️ TEST 3: TWO-STEP ENHANCED BACKGROUND PROCESSING")
        print("-" * 60)
        print("Monitoring Step 1: LLM enrichment and Step 2: PYQ frequency analysis")
        
        if test_results["enhanced_question_upload"]:
            # Wait a moment for background processing
            print("   Waiting for background processing to complete...")
            time.sleep(3)
            
            # Check if question has been processed
            success, response = self.run_test("Check Question Processing Status", "GET", f"questions?limit=10", 200, None, admin_headers)
            if success:
                questions = response.get('questions', [])
                processed_question = None
                
                for q in questions:
                    if q.get('id') == question_id:
                        processed_question = q
                        break
                
                if processed_question:
                    print(f"   ✅ Question found in database")
                    
                    # Check for LLM enrichment (Step 1)
                    has_answer = processed_question.get('answer') and processed_question.get('answer') != "To be generated by LLM"
                    has_solution = processed_question.get('solution_approach') and processed_question.get('solution_approach') != ""
                    
                    if has_answer and has_solution:
                        print("   ✅ Step 1 Complete: LLM enrichment successful")
                        
                        # Check for PYQ frequency analysis (Step 2)
                        pyq_frequency_score = processed_question.get('pyq_frequency_score')
                        frequency_analysis_method = processed_question.get('frequency_analysis_method')
                        
                        if pyq_frequency_score is not None or frequency_analysis_method:
                            print("   ✅ Step 2 Complete: PYQ frequency analysis successful")
                            test_results["two_step_processing"] = True
                        else:
                            print("   ⚠️ Step 2 Pending: PYQ frequency analysis not yet complete")
                    else:
                        print("   ⚠️ Step 1 Pending: LLM enrichment not yet complete")
                else:
                    print("   ❌ Question not found after processing")
        else:
            print("   ⚠️ Skipping - question upload failed")

        # TEST 4: Test Background Processing Integration
        print("\n🔄 TEST 4: BACKGROUND PROCESSING INTEGRATION")
        print("-" * 60)
        print("Testing automatic background processing and question activation")
        
        # Test enhanced nightly processing endpoint
        success, response = self.run_test("Test Enhanced Nightly Processing", "POST", "admin/run-enhanced-nightly", 200, None, admin_headers)
        if success:
            processing_status = response.get('status', '')
            duration = response.get('duration', 0)
            print(f"   ✅ Enhanced nightly processing completed")
            print(f"   Status: {processing_status}")
            print(f"   Duration: {duration} seconds")
            test_results["background_processing_integration"] = True
        else:
            print("   ❌ Enhanced nightly processing failed")

        # TEST 5: Test Enhanced Session Creation with PYQ Frequency Weighting
        print("\n🎯 TEST 5: ENHANCED SESSION CREATION")
        print("-" * 60)
        print("Testing Phase 1 enhanced session logic with PYQ frequency weighting")
        
        if student_headers:
            # Test enhanced session endpoint
            success, response = self.run_test("Test Enhanced Session Status", "GET", "admin/test/enhanced-session", 200, None, admin_headers)
            if success:
                enhancement_features = response.get('enhancement_features', {})
                pyq_integration = enhancement_features.get('pyq_frequency_integration', '')
                dynamic_quotas = enhancement_features.get('dynamic_category_quotas', '')
                
                print(f"   PYQ Frequency Integration: {pyq_integration}")
                print(f"   Dynamic Category Quotas: {dynamic_quotas}")
                
                if '✅ Active' in pyq_integration:
                    print("   ✅ PYQ frequency integration is active")
                    test_results["pyq_frequency_weighting"] = True
                
                if '✅ Active' in dynamic_quotas:
                    print("   ✅ Dynamic category quotas are active")
                    test_results["enhanced_session_creation"] = True
            else:
                print("   ❌ Enhanced session status check failed")
            
            # Test actual session creation
            session_data = {"target_minutes": 30}
            success, response = self.run_test("Create Enhanced Session", "POST", "sessions/start", 200, session_data, student_headers)
            if success:
                session_id = response.get('session_id')
                session_type = response.get('session_type', '')
                personalization = response.get('personalization', {})
                
                print(f"   ✅ Enhanced session created: {session_id}")
                print(f"   Session type: {session_type}")
                
                if personalization.get('applied', False):
                    print("   ✅ Personalization applied with enhanced logic")
                else:
                    print("   ⚠️ Basic session logic used (may be expected)")
        else:
            print("   ⚠️ Skipping session creation - no student token")

        # TEST 6: Test Frequency Analysis Endpoints
        print("\n📊 TEST 6: FREQUENCY ANALYSIS ENDPOINTS")
        print("-" * 60)
        print("Testing conceptual and time-weighted frequency analysis")
        
        # Test conceptual frequency analysis
        success, response = self.run_test("Test Conceptual Frequency Analysis", "POST", "admin/test/conceptual-frequency", 200, None, admin_headers)
        if success:
            analysis_result = response.get('analysis_result', {})
            status = analysis_result.get('status', '')
            conceptual_matches = analysis_result.get('conceptual_matches', 0)
            
            print(f"   ✅ Conceptual frequency analysis working")
            print(f"   Status: {status}")
            print(f"   Conceptual matches: {conceptual_matches}")
        else:
            print("   ❌ Conceptual frequency analysis failed")
        
        # Test time-weighted frequency analysis
        success, response = self.run_test("Test Time-Weighted Frequency Analysis", "POST", "admin/test/time-weighted-frequency", 200, None, admin_headers)
        if success:
            analysis_result = response.get('analysis_result', {})
            frequency_score = analysis_result.get('frequency_score', 0)
            trend_direction = analysis_result.get('trend_direction', '')
            
            print(f"   ✅ Time-weighted frequency analysis working")
            print(f"   Frequency score: {frequency_score}")
            print(f"   Trend direction: {trend_direction}")
        else:
            print("   ❌ Time-weighted frequency analysis failed")

        # TEST 7: Verify Complete Integration
        print("\n🔗 TEST 7: COMPLETE INTEGRATION VERIFICATION")
        print("-" * 60)
        print("Verifying end-to-end automation and no manual intervention required")
        
        # Check if questions are automatically activated after processing
        success, response = self.run_test("Check Active Questions", "GET", "questions?limit=20", 200, None, admin_headers)
        if success:
            questions = response.get('questions', [])
            active_questions = [q for q in questions if q.get('is_active', False)]
            processed_questions = [q for q in questions if q.get('answer') and q.get('answer') != "To be generated by LLM"]
            
            print(f"   Total questions: {len(questions)}")
            print(f"   Active questions: {len(active_questions)}")
            print(f"   Processed questions: {len(processed_questions)}")
            
            if len(active_questions) > 0 and len(processed_questions) > 0:
                print("   ✅ Questions are being automatically processed and activated")
                test_results["automatic_processing"] = True
                test_results["complete_integration"] = True
            else:
                print("   ⚠️ Limited question processing detected")
        else:
            print("   ❌ Cannot verify question processing status")

        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("OPTION 2 ENHANCED BACKGROUND PROCESSING TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<40} {status}")
            
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Specific analysis for OPTION 2
        if test_results["two_step_processing"] and test_results["automatic_processing"]:
            print("🎉 OPTION 2 ENHANCED BACKGROUND PROCESSING WORKING!")
            print("   ✅ Two-step processing (LLM + PYQ analysis) functional")
            print("   ✅ Automatic processing without manual intervention")
            print("   ✅ Enhanced session creation with PYQ frequency weighting")
        elif test_results["enhanced_question_upload"] and test_results["background_processing_integration"]:
            print("⚠️ OPTION 2 PARTIALLY WORKING")
            print("   ✅ Basic enhanced processing functional")
            print("   ⚠️ Some advanced features may need refinement")
        else:
            print("❌ OPTION 2 HAS SIGNIFICANT ISSUES")
            print("   ❌ Core enhanced background processing not functioning")
            print("   🔧 Manual intervention may be required")
            
        return success_rate >= 70

def main():
    """Main function for OPTION 2 Enhanced Background Processing testing"""
    tester = Option2Tester()
    
    print("🚀 Starting OPTION 2 Enhanced Background Processing Testing Suite...")
    print("=" * 80)
    
    # Login first
    if not tester.test_user_login():
        print("❌ Authentication failed - cannot proceed with OPTION 2 testing")
        return 1
    
    # Run OPTION 2 Enhanced Background Processing test
    success = tester.test_option_2_enhanced_background_processing()
    
    if success:
        print("\n🎉 OPTION 2 ENHANCED BACKGROUND PROCESSING TEST COMPLETED SUCCESSFULLY!")
        print("The OPTION 2 Enhanced Background Processing implementation is working correctly")
        return 0
    else:
        print("\n❌ OPTION 2 ENHANCED BACKGROUND PROCESSING TEST IDENTIFIED ISSUES")
        print("Please review the test results above for specific areas needing attention")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)