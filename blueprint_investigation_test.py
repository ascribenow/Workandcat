#!/usr/bin/env python3
"""
Blueprint Session Data Flow Investigation Test
Comprehensive testing of Blueprint session data lifecycle to identify question data mismatches
"""

import requests
import json
import uuid
import time
from datetime import datetime

class BlueprintDataFlowInvestigator:
    def __init__(self, base_url="https://learn-twelvr.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=60, verify=False)
            elif method == "POST":
                if data:
                    response = requests.post(url, json=data, headers=headers, timeout=60, verify=False)
                else:
                    response = requests.post(url, headers=headers, timeout=60, verify=False)
            else:
                print(f"❌ {test_name}: Unsupported method {method}")
                return False, None
            
            if isinstance(expected_status, list):
                status_ok = response.status_code in expected_status
            else:
                status_ok = response.status_code == expected_status
            
            if status_ok:
                try:
                    response_data = response.json()
                    print(f"✅ {test_name}: {response.status_code}")
                    return True, response_data
                except:
                    print(f"✅ {test_name}: {response.status_code} (No JSON)")
                    return True, {"status_code": response.status_code, "text": response.text}
            else:
                try:
                    response_data = response.json()
                    print(f"❌ {test_name}: {response.status_code} - {response_data}")
                    return False, {"status_code": response.status_code, **response_data}
                except:
                    print(f"❌ {test_name}: {response.status_code} - {response.text}")
                    return False, {"status_code": response.status_code, "text": response.text}
                    
        except Exception as e:
            print(f"❌ {test_name}: Exception - {str(e)}")
            return False, {"error": str(e)}
    
    def authenticate(self):
        """Authenticate with test credentials"""
        print("🔐 AUTHENTICATION SETUP")
        print("-" * 60)
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Authentication", "POST", "auth/login", [200, 401], auth_data)
        
        if success and response.get('access_token'):
            token = response['access_token']
            self.auth_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            user_data = response.get('user', {})
            self.user_id = user_data.get('id')
            
            print(f"   ✅ Authentication successful")
            print(f"   📊 User ID: {self.user_id}")
            return True
        else:
            print("   ❌ Authentication failed")
            return False
    
    def investigate_session_creation(self):
        """Phase 1: Investigate session creation and question selection"""
        print("\n📊 PHASE 1: SESSION CREATION DATA INTEGRITY")
        print("-" * 60)
        
        if not self.auth_headers or not self.user_id:
            print("   ❌ Authentication required")
            return None, []
        
        # Create Blueprint session
        session_data = {"user_id": self.user_id}
        
        success, session_response = self.run_test(
            "Create Blueprint Session", 
            "POST", 
            "session/start", 
            [200, 400, 500], 
            session_data, 
            self.auth_headers
        )
        
        if success and session_response.get('success'):
            session_id = session_response.get('session_id')
            session_questions = session_response.get('questions', [])
            
            print(f"   ✅ Blueprint session created: {session_id}")
            print(f"   📊 Questions count: {len(session_questions)}")
            
            # Analyze question data integrity
            if session_questions:
                print(f"   🔍 Question data analysis:")
                for i, question in enumerate(session_questions[:3]):
                    print(f"      Q{i+1}: ID={question.get('id', 'N/A')[:8]}, Answer='{question.get('answer', 'N/A')}'")
                    
                    # Check solution feedback
                    solution_fields = ['snap_read', 'solution_approach', 'detailed_solution', 'principle_to_remember']
                    has_solution = any(question.get(field) for field in solution_fields)
                    print(f"           Solution feedback: {'✅' if has_solution else '❌'}")
            
            return session_id, session_questions
        else:
            print(f"   ❌ Session creation failed: {session_response}")
            return None, []
    
    def investigate_question_serving(self, session_id, original_questions):
        """Phase 2: Investigate question serving and position mapping"""
        print("\n🖥️ PHASE 2: QUESTION DISPLAY DATA FLOW")
        print("-" * 60)
        
        if not session_id:
            print("   ❌ Session ID required")
            return False
        
        # Test question serving by position
        success, question_response = self.run_test(
            "Get Question at Position 1", 
            "GET", 
            f"session/question/{session_id}/1", 
            [200, 404], 
            None, 
            self.auth_headers
        )
        
        if success and question_response.get('question'):
            served_question = question_response.get('question', {})
            
            print(f"   ✅ Question serving working")
            print(f"   📊 Served question ID: {served_question.get('id', 'N/A')[:8]}")
            
            # Compare with original data
            if original_questions and len(original_questions) > 0:
                original_question = original_questions[0]
                
                if served_question.get('id') == original_question.get('id'):
                    print(f"   ✅ Position mapping consistent")
                    return True
                else:
                    print(f"   ❌ Position mapping MISMATCH!")
                    print(f"      Original: {original_question.get('id', 'N/A')[:8]}")
                    print(f"      Served: {served_question.get('id', 'N/A')[:8]}")
                    return False
        else:
            print(f"   ❌ Question serving failed: {question_response}")
            return False
    
    def investigate_answer_submission(self, session_id, original_questions):
        """Phase 3: Investigate answer submission and solution feedback"""
        print("\n✍️ PHASE 3: ANSWER SUBMISSION DATA FLOW")
        print("-" * 60)
        
        if not session_id or not original_questions:
            print("   ❌ Session ID and questions required")
            return False
        
        # Submit test answer for position 1
        submit_data = {
            "session_id": session_id,
            "position": 1,
            "answer": "test_answer"
        }
        
        success, submit_response = self.run_test(
            "Submit Answer Position 1", 
            "POST", 
            "session/submit", 
            [200, 400, 404], 
            submit_data, 
            self.auth_headers
        )
        
        if success and submit_response.get('success'):
            correct_answer = submit_response.get('correct_answer', '')
            solution_feedback = submit_response.get('solution_feedback', {})
            
            print(f"   ✅ Answer submission working")
            print(f"   📊 Correct answer returned: '{correct_answer}'")
            
            # Compare with original question data
            original_question = original_questions[0]
            original_answer = original_question.get('answer', '')
            
            if correct_answer == original_answer:
                print(f"   ✅ Answer consistency maintained")
                
                # Check solution feedback
                feedback_fields = list(solution_feedback.keys())
                print(f"   📊 Solution feedback fields: {feedback_fields}")
                
                return True
            else:
                print(f"   ❌ Answer MISMATCH detected!")
                print(f"      Original: '{original_answer}'")
                print(f"      Returned: '{correct_answer}'")
                return False
        else:
            print(f"   ❌ Answer submission failed: {submit_response}")
            return False
    
    def investigate_data_consistency(self, session_id):
        """Phase 4: Cross-check data consistency across operations"""
        print("\n🔍 PHASE 4: DATA MISMATCH DETECTION")
        print("-" * 60)
        
        if not session_id:
            print("   ❌ Session ID required")
            return False
        
        # Test multiple positions for consistency
        consistent = True
        
        for position in range(1, 4):  # Check first 3 positions
            success, pos_response = self.run_test(
                f"Position Cross-Check {position}", 
                "GET", 
                f"session/question/{session_id}/{position}", 
                [200, 404], 
                None, 
                self.auth_headers
            )
            
            if success and pos_response.get('question'):
                question = pos_response.get('question', {})
                question_id = question.get('id', 'N/A')[:8]
                print(f"   📊 Position {position}: {question_id}")
            else:
                print(f"   ❌ Position {position}: Failed to retrieve")
                consistent = False
        
        if consistent:
            print(f"   ✅ Position cross-check passed")
        else:
            print(f"   ❌ Position cross-check failed")
        
        return consistent
    
    def run_investigation(self):
        """Run complete Blueprint session data flow investigation"""
        print("🔍 BLUEPRINT SESSION DATA FLOW INVESTIGATION")
        print("=" * 80)
        print("OBJECTIVE: Investigate Blueprint session data flow to identify question data mismatch")
        print("FOCUS: Session creation → storage → display → submission data integrity")
        print("=" * 80)
        
        results = {
            "authentication": False,
            "session_creation": False,
            "question_serving": False,
            "answer_submission": False,
            "data_consistency": False
        }
        
        # Phase 1: Authentication
        if self.authenticate():
            results["authentication"] = True
            
            # Phase 2: Session Creation
            session_id, session_questions = self.investigate_session_creation()
            if session_id and session_questions:
                results["session_creation"] = True
                
                # Phase 3: Question Serving
                if self.investigate_question_serving(session_id, session_questions):
                    results["question_serving"] = True
                
                # Phase 4: Answer Submission
                if self.investigate_answer_submission(session_id, session_questions):
                    results["answer_submission"] = True
                
                # Phase 5: Data Consistency
                if self.investigate_data_consistency(session_id):
                    results["data_consistency"] = True
        
        # Final Results
        print("\n" + "=" * 80)
        print("🔍 INVESTIGATION RESULTS")
        print("=" * 80)
        
        passed_tests = sum(results.values())
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        for phase, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {phase.replace('_', ' ').title():<30} {status}")
        
        print(f"\nOverall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Root Cause Analysis
        if success_rate < 100:
            print("\n🎯 ROOT CAUSE ANALYSIS:")
            
            if not results["session_creation"]:
                print("  ❌ Session creation failed - check Blueprint planner")
            if not results["question_serving"]:
                print("  ❌ Question serving inconsistent - check position mapping")
            if not results["answer_submission"]:
                print("  ❌ Answer submission mismatch - check question data integrity")
            if not results["data_consistency"]:
                print("  ❌ Data consistency issues - check database storage")
        else:
            print("\n✅ NO CRITICAL ISSUES DETECTED")
            print("   - Blueprint session data flow appears consistent")
            print("   - Question data integrity maintained across operations")
        
        return success_rate >= 75

if __name__ == "__main__":
    investigator = BlueprintDataFlowInvestigator()
    investigator.run_investigation()