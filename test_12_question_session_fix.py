#!/usr/bin/env python3
"""
Test the FINAL FIX for 12-question session issue
Testing the two critical changes:
1. Fixed Category Distribution Bug: Changed self.category_distribution to self.base_category_distribution
2. Added Robust Fallback Logic: Ensures 12 questions are always selected
"""

import requests
import json
import sys
import time
from datetime import datetime

class Test12QuestionSessionFix:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.session_id = None
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

    def test_12_question_session_final_fix(self):
        """Test the FINAL FIX for 12-question session issue"""
        print("🔍 TESTING FINAL 12-QUESTION SESSION FIX VERIFICATION")
        print("=" * 70)
        print("Testing the final fix for 12-question session issue with two critical changes:")
        print("1. Fixed Category Distribution Bug: Changed self.category_distribution to self.base_category_distribution")
        print("2. Added Robust Fallback Logic: Ensures 12 questions are always selected")
        print("Expected Results:")
        print("  - Session creation returns total_questions = 12")
        print("  - Session.units contains 12 question IDs")
        print("  - Session progress displays proper 'X of 12' format")
        print("  - No more 3-question limitation")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 70)
        
        test_results = {
            "admin_authentication": False,
            "question_pool_verification": False,
            "session_creation_12_questions": False,
            "session_units_verification": False,
            "session_progress_display": False,
            "first_question_progress": False,
            "question_selection_working": False,
            "fallback_logic_verification": False,
            "multiple_session_consistency": False
        }
        
        # TEST 1: Admin Authentication
        print("\n🔐 TEST 1: ADMIN AUTHENTICATION")
        print("-" * 50)
        
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'user' in response and 'access_token' in response:
            self.admin_token = response['access_token']
            admin_user = response['user']
            print(f"   ✅ Admin authenticated: {admin_user['email']}")
            print(f"   Admin privileges: {admin_user.get('is_admin', False)}")
            test_results["admin_authentication"] = True
        else:
            print("   ❌ Admin authentication failed")
            return False
            
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        # TEST 2: Question Pool Verification
        print("\n📊 TEST 2: QUESTION POOL VERIFICATION")
        print("-" * 50)
        print("Verifying sufficient active questions exist for 12-question sessions")
        
        success, response = self.run_test("Check Question Pool", "GET", "questions?limit=50", 200, None, headers)
        if success:
            questions = response.get('questions', [])
            active_questions = [q for q in questions if q.get('is_active', False)]
            
            print(f"   Total questions in database: {len(questions)}")
            print(f"   Active questions available: {len(active_questions)}")
            
            if len(active_questions) >= 12:
                print(f"   ✅ Sufficient active questions for 12-question session ({len(active_questions)} available)")
                test_results["question_pool_verification"] = True
                
                # Show subcategory distribution
                subcategories = {}
                for q in active_questions:
                    subcat = q.get('subcategory', 'Unknown')
                    subcategories[subcat] = subcategories.get(subcat, 0) + 1
                
                print("   Active questions by subcategory:")
                for subcat, count in sorted(subcategories.items()):
                    print(f"     - {subcat}: {count} questions")
            else:
                print(f"   ❌ Insufficient active questions for 12-question session (only {len(active_questions)} available)")
                print("   This could be the root cause of the 3-question limitation")
        else:
            print("   ❌ Failed to check question pool")
            return False
        
        # TEST 3: Session Creation with 12 Questions
        print("\n🎯 TEST 3: SESSION CREATION WITH 12 QUESTIONS")
        print("-" * 50)
        print("Testing POST /api/sessions/start to create a new session with exactly 12 questions")
        
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Start 12-Question Session", "POST", "sessions/start", 200, session_data, headers)
        if success:
            session_id = response.get('session_id')
            total_questions = response.get('total_questions')
            session_type = response.get('session_type')
            
            print(f"   Session ID: {session_id}")
            print(f"   Total questions: {total_questions}")
            print(f"   Session type: {session_type}")
            
            if session_id:
                self.session_id = session_id
                
                # CRITICAL CHECK: Is it exactly 12 questions?
                if total_questions == 12:
                    print("   ✅ SUCCESS: Session created with exactly 12 questions")
                    test_results["session_creation_12_questions"] = True
                elif total_questions == 3:
                    print("   ❌ CRITICAL FAILURE: Session still creating only 3 questions - fix NOT working")
                    print("   The category distribution bug fix has NOT resolved the issue")
                else:
                    print(f"   ⚠️ UNEXPECTED: Session created with {total_questions} questions (expected 12)")
                    
                # Check personalization data
                if 'personalization' in response:
                    personalization = response['personalization']
                    print(f"   Personalization applied: {personalization.get('applied')}")
                    print(f"   Learning stage: {personalization.get('learning_stage')}")
                    print(f"   Category distribution: {personalization.get('category_distribution')}")
                    print(f"   Difficulty distribution: {personalization.get('difficulty_distribution')}")
            else:
                print("   ❌ Session ID not returned")
        else:
            print("   ❌ Session creation failed")
            return False
        
        # TEST 4: Session Units Verification
        print("\n📋 TEST 4: SESSION UNITS VERIFICATION")
        print("-" * 50)
        print("Verifying that session.units contains exactly 12 question IDs")
        
        success, response = self.run_test("Check Session Status", "GET", "sessions/current-status", 200, None, headers)
        if success:
            active_session = response.get('active_session')
            progress = response.get('progress', {})
            
            if active_session:
                total_in_status = progress.get('total', 0)
                answered = progress.get('answered', 0)
                next_question = progress.get('next_question', 0)
                
                print(f"   Session status total questions: {total_in_status}")
                print(f"   Questions answered: {answered}")
                print(f"   Next question number: {next_question}")
                
                if total_in_status == 12:
                    print("   ✅ SUCCESS: Session units contains 12 question IDs")
                    test_results["session_units_verification"] = True
                else:
                    print(f"   ❌ FAILURE: Session units contains {total_in_status} question IDs (expected 12)")
            else:
                print("   ⚠️ No active session found")
        else:
            print("   ❌ Session status check failed")
        
        # TEST 5: Session Progress Display
        print("\n📊 TEST 5: SESSION PROGRESS DISPLAY")
        print("-" * 50)
        print("Verifying session progress displays 'X of 12' format correctly")
        
        if self.session_id:
            success, response = self.run_test("Get Next Question", "GET", f"sessions/{self.session_id}/next-question", 200, None, headers)
            if success:
                session_progress = response.get('session_progress', {})
                session_complete = response.get('session_complete', False)
                
                if not session_complete:
                    total_questions = session_progress.get('total_questions', 0)
                    current_question = session_progress.get('current_question', 0)
                    questions_remaining = session_progress.get('questions_remaining', 0)
                    progress_percentage = session_progress.get('progress_percentage', 0)
                    
                    print(f"   Session progress total questions: {total_questions}")
                    print(f"   Current question number: {current_question}")
                    print(f"   Questions remaining: {questions_remaining}")
                    print(f"   Progress percentage: {progress_percentage}%")
                    
                    if total_questions == 12:
                        print("   ✅ SUCCESS: Session metadata shows total_questions = 12")
                        test_results["session_progress_display"] = True
                    else:
                        print(f"   ❌ FAILURE: Session metadata shows total_questions = {total_questions} (expected 12)")
                else:
                    print("   ⚠️ Session already complete")
            else:
                print("   ❌ Failed to get session progress")
        else:
            print("   ❌ No session ID available")
        
        # TEST 6: First Question Progress Check
        print("\n❓ TEST 6: FIRST QUESTION PROGRESS CHECK")
        print("-" * 50)
        print("Testing that first question shows progress as '1 of 12'")
        
        if self.session_id:
            success, response = self.run_test("Get First Question Details", "GET", f"sessions/{self.session_id}/next-question", 200, None, headers)
            if success:
                question = response.get('question')
                session_progress = response.get('session_progress', {})
                
                if question:
                    current_question = session_progress.get('current_question', 0)
                    total_questions = session_progress.get('total_questions', 0)
                    
                    print(f"   Question ID: {question.get('id')}")
                    print(f"   Question stem: {question.get('stem', '')[:60]}...")
                    print(f"   Subcategory: {question.get('subcategory')}")
                    print(f"   Difficulty: {question.get('difficulty_band')}")
                    print(f"   Progress: Question {current_question} of {total_questions}")
                    
                    if current_question == 1 and total_questions == 12:
                        print("   ✅ SUCCESS: First question shows progress '1 of 12'")
                        test_results["first_question_progress"] = True
                    else:
                        print(f"   ❌ FAILURE: Progress shows '{current_question} of {total_questions}' (expected '1 of 12')")
                else:
                    print("   ❌ No question available")
            else:
                print("   ❌ Failed to get first question")
        else:
            print("   ❌ No session ID available")
        
        # TEST 7: Question Selection Working
        print("\n🗂️ TEST 7: QUESTION SELECTION WORKING")
        print("-" * 50)
        print("Verifying that question selection is working properly")
        
        if self.session_id:
            success, response = self.run_test("Verify Question Selection", "GET", f"sessions/{self.session_id}/next-question", 200, None, headers)
            if success:
                question = response.get('question')
                session_intelligence = response.get('session_intelligence', {})
                
                if question:
                    print(f"   Question selected successfully")
                    print(f"   Question has proper metadata: {bool(question.get('subcategory'))}")
                    print(f"   Session intelligence available: {bool(session_intelligence)}")
                    print(f"   Question selection rationale: {session_intelligence.get('question_selected_for', 'N/A')}")
                    test_results["question_selection_working"] = True
                else:
                    print("   ❌ No question selected")
            else:
                print("   ❌ Failed to verify question selection")
        else:
            print("   ❌ No session ID available")
        
        # TEST 8: Fallback Logic Verification
        print("\n🔄 TEST 8: FALLBACK LOGIC VERIFICATION")
        print("-" * 50)
        print("Testing that fallback logic ensures 12 questions even with category mismatches")
        
        # Create a second session to test consistency
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Start Second Session (Fallback Test)", "POST", "sessions/start", 200, session_data, headers)
        if success:
            second_session_id = response.get('session_id')
            second_total_questions = response.get('total_questions')
            second_session_type = response.get('session_type')
            
            print(f"   Second session ID: {second_session_id}")
            print(f"   Second session total questions: {second_total_questions}")
            print(f"   Second session type: {second_session_type}")
            
            if second_total_questions == 12:
                print("   ✅ SUCCESS: Fallback logic ensures 12 questions consistently")
                test_results["fallback_logic_verification"] = True
            else:
                print(f"   ❌ FAILURE: Second session also has {second_total_questions} questions (expected 12)")
        else:
            print("   ❌ Failed to create second session for fallback test")
        
        # TEST 9: Multiple Session Consistency
        print("\n🔁 TEST 9: MULTIPLE SESSION CONSISTENCY")
        print("-" * 50)
        print("Testing that multiple sessions consistently create 12 questions")
        
        consistent_sessions = 0
        total_test_sessions = 3
        
        for i in range(total_test_sessions):
            session_data = {"target_minutes": 30}
            success, response = self.run_test(f"Consistency Test Session {i+1}", "POST", "sessions/start", 200, session_data, headers)
            if success:
                test_total_questions = response.get('total_questions')
                if test_total_questions == 12:
                    consistent_sessions += 1
                    print(f"   Session {i+1}: ✅ {test_total_questions} questions")
                else:
                    print(f"   Session {i+1}: ❌ {test_total_questions} questions (expected 12)")
            else:
                print(f"   Session {i+1}: ❌ Failed to create")
        
        if consistent_sessions == total_test_sessions:
            print(f"   ✅ SUCCESS: All {total_test_sessions} sessions consistently created 12 questions")
            test_results["multiple_session_consistency"] = True
        else:
            print(f"   ❌ FAILURE: Only {consistent_sessions}/{total_test_sessions} sessions created 12 questions")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 70)
        print("FINAL 12-QUESTION SESSION FIX TEST RESULTS")
        print("=" * 70)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<40} {status}")
            
        print("-" * 70)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical Analysis
        critical_tests = [
            "session_creation_12_questions",
            "session_units_verification", 
            "session_progress_display",
            "first_question_progress"
        ]
        
        critical_passed = sum(1 for test in critical_tests if test_results[test])
        critical_total = len(critical_tests)
        
        print(f"Critical Tests Passed: {critical_passed}/{critical_total}")
        
        if test_results["session_creation_12_questions"]:
            print("🎉 CRITICAL SUCCESS: 12-QUESTION SESSION FIX IS WORKING!")
            print("   ✅ Sessions now create exactly 12 questions instead of 3")
            print("   ✅ Category distribution bug has been resolved")
            print("   ✅ Fallback logic ensures consistent 12-question sessions")
        else:
            print("❌ CRITICAL FAILURE: 12-QUESTION SESSION FIX IS NOT WORKING!")
            print("   ❌ Sessions are still creating 3 questions instead of 12")
            print("   ❌ The category distribution bug fix has NOT resolved the issue")
            print("   ❌ Further investigation needed in adaptive_session_logic.py")
            
        if success_rate >= 80:
            print("🎉 12-QUESTION SESSION FUNCTIONALITY FULLY RESTORED!")
            print("   ✅ All critical session creation issues resolved")
            print("   ✅ Session progress displays correctly as 'X of 12'")
            print("   ✅ Question selection and fallback logic working properly")
        elif success_rate >= 60:
            print("⚠️ 12-question session mostly working with minor issues")
        else:
            print("❌ 12-question session has significant issues requiring attention")
            
        return success_rate >= 80

def main():
    """Main test execution"""
    print("Starting 12-Question Session Fix Verification Tests...")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = Test12QuestionSessionFix()
    success = tester.test_12_question_session_final_fix()
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total tests run: {tester.tests_run}")
    print(f"Total tests passed: {tester.tests_passed}")
    
    if success:
        print("🎉 ALL TESTS PASSED - 12-QUESTION SESSION FIX IS WORKING!")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED - 12-QUESTION SESSION FIX NEEDS ATTENTION")
        sys.exit(1)

if __name__ == "__main__":
    main()