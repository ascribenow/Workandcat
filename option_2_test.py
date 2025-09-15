import requests
import sys
import json
from datetime import datetime
import time
import os

class OPTION2Tester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
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
        """Authenticate as admin and student"""
        # Admin login
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   ✅ Admin authenticated")
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
            print(f"   ✅ Student authenticated")
            return True
        else:
            print("   ❌ Student authentication failed")
            return False

    def test_option_2_enhanced_background_processing_after_transaction_fix(self):
        """Test OPTION 2 Enhanced Background Processing after Critical Database Transaction Fix"""
        print("🔍 OPTION 2 ENHANCED BACKGROUND PROCESSING - POST TRANSACTION FIX")
        print("=" * 80)
        print("TESTING AFTER CRITICAL DATABASE TRANSACTION FIX:")
        print("Context: Fixed critical database persistence issue in enrich_question_background")
        print("Fix: Combined LLM enrichment (Step 1) and PYQ frequency analysis (Step 2) into single atomic transaction")
        print("Expected: Answer field should now persist correctly, questions should be activated")
        print("=" * 80)
        print("SPECIFIC TESTS:")
        print("1. Enhanced Question Upload with Complete Processing")
        print("2. Database Transaction Fix Verification") 
        print("3. Complete End-to-End OPTION 2 Flow")
        print("4. Enhanced Session Creation with PYQ Weighting")
        print("=" * 80)
        
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

        test_results = {
            "topics_initialization": False,
            "enhanced_question_upload": False,
            "background_processing_completion": False,
            "database_transaction_fix": False,
            "pyq_frequency_population": False,
            "enhanced_session_creation": False,
            "end_to_end_flow": False
        }

        # TEST 1: Initialize CAT Topics for OPTION 2
        print("\n🏗️ TEST 1: INITIALIZE CAT TOPICS FOR OPTION 2")
        print("-" * 60)
        print("Initializing canonical taxonomy topics required for OPTION 2 system")
        
        success, response = self.run_test("Initialize CAT Topics", "POST", "admin/init-topics", 200, None, admin_headers)
        if success:
            print("   ✅ CAT topics initialization successful")
            print(f"   Topics created/verified: {response.get('topics_created', 'existing')}")
            test_results["topics_initialization"] = True
        else:
            print("   ❌ CAT topics initialization failed")
            return False

        # TEST 2: Enhanced Question Upload with Complete Processing
        print("\n📝 TEST 2: ENHANCED QUESTION UPLOAD WITH COMPLETE PROCESSING")
        print("-" * 60)
        print("Testing question upload with automatic two-step background processing")
        
        # Create test question for OPTION 2 processing
        test_question = {
            "stem": "OPTION 2 Test: A train travels at 60 km/h for 2 hours, then at 80 km/h for 3 hours. What is the average speed for the entire journey?",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "type_of_question": "Average Speed Calculation",
            "tags": ["option_2_test", "transaction_fix_test"],
            "source": "OPTION 2 Transaction Fix Test"
        }
        
        success, response = self.run_test("Upload Question for OPTION 2 Processing", "POST", "questions", 200, test_question, admin_headers)
        if success and 'question_id' in response:
            test_question_id = response['question_id']
            status = response.get('status')
            print(f"   ✅ Question uploaded successfully: {test_question_id}")
            print(f"   Status: {status}")
            
            if status == "enrichment_queued":
                print("   ✅ Question queued for background processing")
                test_results["enhanced_question_upload"] = True
            else:
                print(f"   ⚠️ Unexpected status: {status}")
        else:
            print("   ❌ Question upload failed")
            return False

        # TEST 3: Wait for Background Processing Completion
        print("\n⏳ TEST 3: BACKGROUND PROCESSING COMPLETION VERIFICATION")
        print("-" * 60)
        print("Waiting for two-step background processing to complete...")
        print("Step 1: LLM enrichment (answer, solution_approach, detailed_solution)")
        print("Step 2: PYQ frequency analysis (pyq_frequency_score, learning_impact)")
        
        # Wait for background processing (should be faster after transaction fix)
        max_wait_time = 30  # seconds
        check_interval = 3  # seconds
        waited_time = 0
        processing_complete = False
        
        while waited_time < max_wait_time:
            print(f"   Checking processing status... ({waited_time}s elapsed)")
            
            # Check question status by retrieving it
            success, response = self.run_test("Check Question Processing Status", "GET", f"questions?limit=50", 200, None, admin_headers)
            if success:
                questions = response.get('questions', [])
                test_question_found = None
                
                for q in questions:
                    if q.get('id') == test_question_id:
                        test_question_found = q
                        break
                
                if test_question_found:
                    answer = test_question_found.get('answer')
                    pyq_frequency_score = test_question_found.get('pyq_frequency_score')
                    learning_impact = test_question_found.get('learning_impact')
                    
                    print(f"   Question found - Answer: {answer}")
                    print(f"   PYQ frequency score: {pyq_frequency_score}")
                    print(f"   Learning impact: {learning_impact}")
                    
                    # Check if processing is complete (answer field populated and not default)
                    if answer and answer != "To be generated by LLM" and answer != "None":
                        print("   ✅ Step 1 (LLM enrichment) completed - answer field populated")
                        
                        if pyq_frequency_score and pyq_frequency_score > 0:
                            print("   ✅ Step 2 (PYQ frequency analysis) completed")
                            processing_complete = True
                            break
                        else:
                            print("   ⏳ Step 2 (PYQ frequency analysis) still pending")
                    else:
                        print("   ⏳ Step 1 (LLM enrichment) still pending")
                else:
                    print("   ⚠️ Test question not found in results")
            
            time.sleep(check_interval)
            waited_time += check_interval
        
        if processing_complete:
            print(f"   ✅ Background processing completed in {waited_time}s")
            test_results["background_processing_completion"] = True
        else:
            print(f"   ❌ Background processing did not complete within {max_wait_time}s")
            print("   This may indicate the transaction fix did not resolve the persistence issue")

        # TEST 4: Database Transaction Fix Verification
        print("\n🔍 TEST 4: DATABASE TRANSACTION FIX VERIFICATION")
        print("-" * 60)
        print("Verifying that the atomic transaction fix resolved database persistence issues")
        
        # Get the processed question details
        success, response = self.run_test("Get Processed Question Details", "GET", f"questions?limit=50", 200, None, admin_headers)
        if success:
            questions = response.get('questions', [])
            processed_question = None
            
            for q in questions:
                if q.get('id') == test_question_id:
                    processed_question = q
                    break
            
            if processed_question:
                answer = processed_question.get('answer')
                solution_approach = processed_question.get('solution_approach')
                detailed_solution = processed_question.get('detailed_solution')
                subcategory = processed_question.get('subcategory')
                pyq_frequency_score = processed_question.get('pyq_frequency_score')
                learning_impact = processed_question.get('learning_impact')
                importance_index = processed_question.get('importance_index')
                is_active = processed_question.get('is_active')
                
                print(f"   Answer field: {answer}")
                print(f"   Solution approach: {solution_approach}")
                print(f"   Detailed solution: {detailed_solution}")
                print(f"   Subcategory: {subcategory}")
                print(f"   PYQ frequency score: {pyq_frequency_score}")
                print(f"   Learning impact: {learning_impact}")
                print(f"   Importance index: {importance_index}")
                print(f"   Is active: {is_active}")
                
                # Verify transaction fix - all fields should be populated
                fields_populated = 0
                total_fields = 7
                
                if answer and answer not in ["To be generated by LLM", "None", None]:
                    fields_populated += 1
                    print("   ✅ Answer field properly populated")
                else:
                    print("   ❌ Answer field not populated - transaction fix may have failed")
                
                if solution_approach and solution_approach not in ["To be generated by LLM", "None", None]:
                    fields_populated += 1
                    print("   ✅ Solution approach populated")
                
                if detailed_solution and detailed_solution not in ["To be generated by LLM", "None", None]:
                    fields_populated += 1
                    print("   ✅ Detailed solution populated")
                
                if subcategory and subcategory not in ["To be classified by LLM", "None", None]:
                    fields_populated += 1
                    print("   ✅ Subcategory populated")
                
                if pyq_frequency_score and pyq_frequency_score > 0:
                    fields_populated += 1
                    print("   ✅ PYQ frequency score populated")
                    test_results["pyq_frequency_population"] = True
                
                if learning_impact and learning_impact > 0:
                    fields_populated += 1
                    print("   ✅ Learning impact populated")
                
                if is_active:
                    fields_populated += 1
                    print("   ✅ Question activated (is_active=true)")
                else:
                    print("   ❌ Question not activated - may indicate processing incomplete")
                
                completion_rate = (fields_populated / total_fields) * 100
                print(f"   Field completion rate: {fields_populated}/{total_fields} ({completion_rate:.1f}%)")
                
                if completion_rate >= 85:
                    print("   ✅ DATABASE TRANSACTION FIX SUCCESSFUL")
                    test_results["database_transaction_fix"] = True
                else:
                    print("   ❌ DATABASE TRANSACTION FIX INCOMPLETE")
                    print("   Some fields still not persisting correctly")
            else:
                print("   ❌ Processed question not found")

        # TEST 5: Enhanced Session Creation with PYQ Weighting
        print("\n🎯 TEST 5: ENHANCED SESSION CREATION WITH PYQ WEIGHTING")
        print("-" * 60)
        print("Testing that sessions now use intelligent question selection with PYQ frequency weighting")
        
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create Enhanced Session", "POST", "sessions/start", 200, session_data, student_headers)
        
        if success:
            session_id = response.get('session_id')
            session_type = response.get('session_type')
            personalization = response.get('personalization', {})
            
            print(f"   Session ID: {session_id}")
            print(f"   Session type: {session_type}")
            print(f"   Personalization applied: {personalization.get('applied', False)}")
            
            if session_type == "intelligent_12_question_set":
                print("   ✅ Enhanced session using intelligent question selection")
                test_results["enhanced_session_creation"] = True
            elif session_type == "fallback_12_question_set":
                print("   ❌ Session falling back to simple selection - PYQ weighting not working")
            else:
                print(f"   ⚠️ Unknown session type: {session_type}")
            
            # Check if session intelligence mentions PYQ-based selection
            success, response = self.run_test("Get Enhanced Question", "GET", f"sessions/{session_id}/next-question", 200, None, student_headers)
            if success and response.get('session_intelligence'):
                intelligence = response['session_intelligence']
                selection_reason = intelligence.get('question_selected_for', '')
                
                print(f"   Selection rationale: {selection_reason}")
                
                if 'frequency' in selection_reason.lower() or 'pyq' in selection_reason.lower():
                    print("   ✅ Session intelligence mentions frequency/PYQ-based selection")
                else:
                    print("   ⚠️ Session intelligence doesn't mention PYQ frequency weighting")
        else:
            print("   ❌ Enhanced session creation failed")

        # TEST 6: Complete End-to-End OPTION 2 Flow
        print("\n🔄 TEST 6: COMPLETE END-TO-END OPTION 2 FLOW")
        print("-" * 60)
        print("Testing complete automation pipeline: Upload → Processing → Session Creation")
        
        # Upload another test question
        test_question_2 = {
            "stem": "OPTION 2 End-to-End Test: If 20% of a number is 45, what is 75% of that number?",
            "hint_category": "Arithmetic", 
            "hint_subcategory": "Percentages",
            "type_of_question": "Percentage Calculation",
            "tags": ["option_2_e2e_test"],
            "source": "OPTION 2 End-to-End Test"
        }
        
        success, response = self.run_test("Upload Second Test Question", "POST", "questions", 200, test_question_2, admin_headers)
        if success and 'question_id' in response:
            test_question_2_id = response['question_id']
            print(f"   ✅ Second question uploaded: {test_question_2_id}")
            
            # Wait briefly for processing
            time.sleep(10)
            
            # Check if both questions are now available for sessions
            success, response = self.run_test("Check Available Questions", "GET", "questions?limit=50", 200, None, admin_headers)
            if success:
                questions = response.get('questions', [])
                active_questions = [q for q in questions if q.get('is_active')]
                option_2_questions = [q for q in active_questions if 'option_2' in str(q.get('tags', [])).lower()]
                
                print(f"   Total active questions: {len(active_questions)}")
                print(f"   OPTION 2 test questions active: {len(option_2_questions)}")
                
                if len(option_2_questions) >= 1:
                    print("   ✅ OPTION 2 questions processed and available for sessions")
                    test_results["end_to_end_flow"] = True
                else:
                    print("   ❌ OPTION 2 questions not processed or not active")
        else:
            print("   ❌ Second question upload failed")

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
        
        # Specific analysis for transaction fix
        if test_results["database_transaction_fix"] and test_results["background_processing_completion"]:
            print("🎉 DATABASE TRANSACTION FIX SUCCESSFUL!")
            print("   ✅ Atomic transaction handling resolved persistence issues")
            print("   ✅ Answer field now persists correctly after LLM enrichment")
            print("   ✅ Two-step processing (LLM + PYQ analysis) working")
        else:
            print("❌ DATABASE TRANSACTION FIX ISSUES DETECTED!")
            print("   ❌ Persistence issues may still exist")
            print("   ❌ Background processing may not be completing properly")
            
        if test_results["enhanced_session_creation"]:
            print("✅ ENHANCED SESSION CREATION WORKING!")
            print("   ✅ Sessions using intelligent_12_question_set")
            print("   ✅ PYQ frequency weighting operational")
        else:
            print("❌ ENHANCED SESSION CREATION ISSUES!")
            print("   ❌ Sessions falling back to simple selection")
            
        return success_rate >= 70

if __name__ == "__main__":
    tester = OPTION2Tester()
    success = tester.test_option_2_enhanced_background_processing_after_transaction_fix()
    
    if success:
        print("\n🎉 OPTION 2 TESTING COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ OPTION 2 TESTING FAILED!")
        
    sys.exit(0 if success else 1)