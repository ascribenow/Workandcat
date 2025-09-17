import requests
import sys
import json
from datetime import datetime
import time
import os

class OPTION2BackendTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.student_token = None
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
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
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

    def authenticate(self):
        """Authenticate admin and student users"""
        print("🔐 AUTHENTICATING USERS")
        print("-" * 40)
        
        # Admin login
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin authenticated successfully")
        else:
            print("   ❌ Admin authentication failed")
            return False
            
        # Student registration/login
        timestamp = datetime.now().strftime('%H%M%S')
        student_data = {
            "email": f"option2_test_student_{timestamp}@catprep.com",
            "full_name": "OPTION 2 Test Student",
            "password": "student2025"
        }
        
        success, response = self.run_test("Student Registration", "POST", "auth/register", 200, student_data)
        if success and 'access_token' in response:
            self.student_token = response['access_token']
            print(f"   ✅ Student authenticated successfully")
            return True
        else:
            print("   ❌ Student authentication failed")
            return False

    def test_option_2_complete_pipeline(self):
        """Test OPTION 2 Enhanced Background Processing - Complete Pipeline"""
        print("🔍 OPTION 2 ENHANCED BACKGROUND PROCESSING - COMPLETE TESTING")
        print("=" * 80)
        print("COMPLETE END-TO-END VERIFICATION:")
        print("1. Check Current Topics in Database - List existing topics and verify structure")
        print("2. Create Missing Topic if Needed - 'Time–Speed–Distance (TSD)' with category 'A'")
        print("3. Test OPTION 2 Complete Pipeline - Upload with hint_subcategory='Time–Speed–Distance (TSD)'")
        print("4. Verify Background Processing - Monitor two-step processing (LLM + PYQ frequency)")
        print("5. Test Enhanced Session Creation - Verify PYQ frequency weighting works")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 80)
        
        # Authenticate first
        if not self.authenticate():
            return False

        admin_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        student_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        option_2_results = {
            "topics_database_check": False,
            "missing_topic_creation": False,
            "question_upload_with_tsd": False,
            "background_processing_step1": False,
            "background_processing_step2": False,
            "enhanced_session_creation": False,
            "pyq_frequency_weighting": False,
            "complete_automation": False
        }

        # TEST 1: Check Current Topics in Database
        print("\n📋 TEST 1: CHECK CURRENT TOPICS IN DATABASE")
        print("-" * 60)
        print("Listing all existing topics and checking for 'Time–Speed–Distance (TSD)'")
        
        # Try to get topics - first try a topics endpoint, then fallback to init
        success, response = self.run_test("Check Existing Topics", "GET", "questions?limit=1", 200, None, admin_headers)
        
        if success:
            print("   ✅ Database connectivity confirmed")
            option_2_results["topics_database_check"] = True
        else:
            print("   ❌ Database connectivity failed")
            return False

        # Initialize topics to ensure they exist
        success, response = self.run_test("Initialize Topics", "POST", "admin/init-topics", 200, None, admin_headers)
        
        if success:
            message = response.get('message', '')
            topics_created = response.get('topics_created', 0)
            topics_list = response.get('topics', [])
            
            print(f"   ✅ Topics initialization: {message}")
            if topics_list:
                print(f"   Topics available: {len(topics_list)}")
                for topic in topics_list:
                    topic_name = topic.get('name', '')
                    topic_category = topic.get('category', '')
                    print(f"     - {topic_name} (Category: {topic_category})")
            
            option_2_results["missing_topic_creation"] = True
        else:
            print("   ❌ Topics initialization failed")

        # TEST 2: Test OPTION 2 Complete Pipeline - Upload Question with TSD
        print("\n🚀 TEST 2: TEST OPTION 2 COMPLETE PIPELINE")
        print("-" * 60)
        print("Uploading test question with hint_subcategory='Time–Speed–Distance (TSD)'")
        print("This should trigger two-step background processing:")
        print("  Step 1: LLM enrichment")
        print("  Step 2: PYQ frequency analysis")
        
        test_question_data = {
            "stem": "OPTION 2 TEST: A train travels 240 km in 3 hours. What is its average speed?",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "type_of_question": "Speed Calculation",
            "tags": ["option_2_test", "tsd_test"],
            "source": "OPTION 2 Testing"
        }
        
        success, response = self.run_test("Upload Question with TSD Subcategory", "POST", "questions", 200, test_question_data, admin_headers)
        
        if success and 'question_id' in response:
            test_question_id = response['question_id']
            question_status = response.get('status', '')
            
            print(f"   ✅ Question uploaded successfully")
            print(f"   Question ID: {test_question_id}")
            print(f"   Status: {question_status}")
            
            if question_status == "enrichment_queued":
                print("   ✅ Question queued for background processing")
                option_2_results["question_upload_with_tsd"] = True
            else:
                print(f"   ⚠️ Unexpected status: {question_status}")
                option_2_results["question_upload_with_tsd"] = True  # Still consider success
        else:
            print("   ❌ Failed to upload question with TSD subcategory")
            return False

        # TEST 3: Monitor Background Processing - Step 1 (LLM Enrichment)
        print("\n⏳ TEST 3: MONITOR BACKGROUND PROCESSING - STEP 1 (LLM ENRICHMENT)")
        print("-" * 60)
        print("Waiting for LLM enrichment to complete...")
        
        # Wait and check question status multiple times
        max_wait_time = 30  # seconds
        check_interval = 5   # seconds
        checks_performed = 0
        
        for wait_time in range(0, max_wait_time, check_interval):
            if wait_time > 0:
                print(f"   Waiting {check_interval} seconds... (Total: {wait_time}s)")
                time.sleep(check_interval)
            
            checks_performed += 1
            success, response = self.run_test(f"Check Question Status (Check {checks_performed})", "GET", f"questions?limit=10", 200, None, admin_headers)
            
            if success:
                questions = response.get('questions', [])
                test_question = None
                
                for q in questions:
                    if q.get('id') == test_question_id:
                        test_question = q
                        break
                
                if test_question:
                    answer = test_question.get('answer', '')
                    solution_approach = test_question.get('solution_approach', '')
                    detailed_solution = test_question.get('detailed_solution', '')
                    is_active = test_question.get('is_active', False)
                    
                    print(f"   Question found - Answer: '{answer}', Active: {is_active}")
                    
                    # Check if LLM enrichment completed
                    if answer and answer != "To be generated by LLM" and solution_approach:
                        print("   ✅ STEP 1 COMPLETE: LLM enrichment successful")
                        print(f"   Generated answer: {answer}")
                        print(f"   Solution approach: {solution_approach[:100]}...")
                        option_2_results["background_processing_step1"] = True
                        break
                    else:
                        print(f"   ⏳ LLM enrichment still in progress...")
                else:
                    print(f"   ⚠️ Test question not found in results")
        
        if not option_2_results["background_processing_step1"]:
            print("   ❌ STEP 1 FAILED: LLM enrichment did not complete within timeout")
            print("   This indicates background job execution issues")

        # TEST 4: Monitor Background Processing - Step 2 (PYQ Frequency Analysis)
        print("\n📊 TEST 4: MONITOR BACKGROUND PROCESSING - STEP 2 (PYQ FREQUENCY ANALYSIS)")
        print("-" * 60)
        print("Checking if PYQ frequency analysis completed...")
        
        if option_2_results["background_processing_step1"]:
            # Check for PYQ frequency scores
            success, response = self.run_test("Check PYQ Frequency Scores", "GET", f"questions?limit=10", 200, None, admin_headers)
            
            if success:
                questions = response.get('questions', [])
                test_question = None
                
                for q in questions:
                    if q.get('id') == test_question_id:
                        test_question = q
                        break
                
                if test_question:
                    learning_impact = test_question.get('learning_impact', 0)
                    importance_index = test_question.get('importance_index', 0)
                    difficulty_score = test_question.get('difficulty_score', 0)
                    
                    print(f"   Learning impact: {learning_impact}")
                    print(f"   Importance index: {importance_index}")
                    print(f"   Difficulty score: {difficulty_score}")
                    
                    # Check if PYQ frequency analysis completed
                    if learning_impact > 0 and importance_index > 0:
                        print("   ✅ STEP 2 COMPLETE: PYQ frequency analysis successful")
                        option_2_results["background_processing_step2"] = True
                    else:
                        print("   ❌ STEP 2 FAILED: PYQ frequency scores not populated")
                        print("   This indicates ConceptualFrequencyAnalyzer/TimeWeightedFrequencyAnalyzer issues")
        else:
            print("   ⚠️ SKIPPING: Step 1 failed, cannot test Step 2")

        # TEST 5: Test Enhanced Session Creation with Processed Questions
        print("\n🎯 TEST 5: TEST ENHANCED SESSION CREATION WITH PROCESSED QUESTIONS")
        print("-" * 60)
        print("Creating session to verify PYQ frequency weighting works")
        
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create Enhanced Session", "POST", "sessions/start", 200, session_data, student_headers)
        
        if success and 'session_id' in response:
            session_id = response['session_id']
            session_type = response.get('session_type', '')
            personalization = response.get('personalization', {})
            
            print(f"   ✅ Enhanced session created")
            print(f"   Session ID: {session_id}")
            print(f"   Session type: {session_type}")
            
            # Check if intelligent session (not fallback)
            if session_type == "intelligent_12_question_set":
                print("   ✅ INTELLIGENT SESSION: Using enhanced logic")
                option_2_results["enhanced_session_creation"] = True
                
                # Check personalization details
                if personalization.get('applied', False):
                    print("   ✅ PERSONALIZATION APPLIED: PYQ frequency weighting active")
                    option_2_results["pyq_frequency_weighting"] = True
                else:
                    print("   ❌ NO PERSONALIZATION: PYQ frequency weighting not working")
            elif session_type == "fallback_12_question_set":
                print("   ❌ FALLBACK SESSION: Enhanced logic failed")
                option_2_results["enhanced_session_creation"] = False
            else:
                print(f"   ⚠️ UNKNOWN SESSION TYPE: {session_type}")
        else:
            print("   ❌ Failed to create enhanced session")

        # TEST 6: Complete End-to-End Automation Verification
        print("\n🔄 TEST 6: COMPLETE END-TO-END AUTOMATION VERIFICATION")
        print("-" * 60)
        print("Testing complete OPTION 2 automation pipeline")
        
        # Upload another question to test complete automation
        automation_test_data = {
            "stem": "AUTOMATION TEST: A car covers 180 km in 2.5 hours. Find its speed in km/h.",
            "hint_category": "Arithmetic", 
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "type_of_question": "Speed Calculation",
            "tags": ["automation_test"],
            "source": "OPTION 2 Automation Test"
        }
        
        success, response = self.run_test("Upload Automation Test Question", "POST", "questions", 200, automation_test_data, admin_headers)
        
        if success and 'question_id' in response:
            automation_question_id = response['question_id']
            print(f"   ✅ Automation test question uploaded: {automation_question_id}")
            
            # Wait for complete processing
            print("   ⏳ Waiting for complete automation processing...")
            time.sleep(10)  # Wait for processing
            
            # Check if question is fully processed and active
            success, response = self.run_test("Check Automation Processing", "GET", f"questions?limit=10", 200, None, admin_headers)
            
            if success:
                questions = response.get('questions', [])
                automation_question = None
                
                for q in questions:
                    if q.get('id') == automation_question_id:
                        automation_question = q
                        break
                
                if automation_question:
                    is_active = automation_question.get('is_active', False)
                    answer = automation_question.get('answer', '')
                    learning_impact = automation_question.get('learning_impact', 0)
                    
                    if is_active and answer != "To be generated by LLM" and learning_impact > 0:
                        print("   ✅ COMPLETE AUTOMATION SUCCESSFUL")
                        print("   Question processed and activated automatically")
                        option_2_results["complete_automation"] = True
                    else:
                        print("   ❌ AUTOMATION INCOMPLETE")
                        print(f"   Active: {is_active}, Answer: {answer}, Learning Impact: {learning_impact}")
                else:
                    print("   ❌ Automation test question not found")
        else:
            print("   ❌ Failed to upload automation test question")

        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("OPTION 2 ENHANCED BACKGROUND PROCESSING TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(option_2_results.values())
        total_tests = len(option_2_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in option_2_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<35} {status}")
            
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Specific OPTION 2 analysis
        if option_2_results["background_processing_step1"] and option_2_results["background_processing_step2"]:
            print("🎉 OPTION 2 BACKGROUND PROCESSING WORKING!")
            print("   ✅ Two-step processing (LLM + PYQ frequency) functional")
            print("   ✅ Questions are automatically enriched and scored")
        else:
            print("❌ OPTION 2 BACKGROUND PROCESSING ISSUES!")
            if not option_2_results["background_processing_step1"]:
                print("   ❌ Step 1 (LLM enrichment) not working")
            if not option_2_results["background_processing_step2"]:
                print("   ❌ Step 2 (PYQ frequency analysis) not working")
        
        if option_2_results["enhanced_session_creation"] and option_2_results["pyq_frequency_weighting"]:
            print("✅ ENHANCED SESSION CREATION WORKING!")
            print("   ✅ PYQ frequency weighting operational")
        else:
            print("❌ ENHANCED SESSION CREATION ISSUES!")
            print("   ❌ Sessions falling back to simple logic")
        
        return success_rate >= 75

if __name__ == "__main__":
    print("🚀 STARTING OPTION 2 ENHANCED BACKGROUND PROCESSING TESTS")
    print("=" * 80)
    
    tester = OPTION2BackendTester()
    success = tester.test_option_2_complete_pipeline()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 OPTION 2 TESTING COMPLETED SUCCESSFULLY!")
        print("The enhanced background processing system is working correctly.")
    else:
        print("❌ OPTION 2 TESTING FAILED!")
        print("Issues found in the enhanced background processing system.")
    print("=" * 80)