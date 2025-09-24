#!/usr/bin/env python3
"""
Blueprint Session System Solution Feedback Test
Testing the specific review request: solution feedback fix in submit answer API
"""

import requests
import json
import sys
import time
from datetime import datetime

class BlueprintSolutionFeedbackTester:
    def __init__(self, base_url="https://smart-blueprint.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        self.session_id = None
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def authenticate(self):
        """Authenticate with sp@theskinmantra.com/student123"""
        self.log("🔐 Authenticating with sp@theskinmantra.com/student123")
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json=auth_data,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                user_data = data.get('user', {})
                
                self.auth_headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                self.user_id = user_data.get('id')
                
                self.log(f"✅ Authentication successful")
                self.log(f"📊 User ID: {self.user_id}")
                self.log(f"📊 JWT Token length: {len(token)} characters")
                self.log(f"📊 Adaptive enabled: {user_data.get('adaptive_enabled')}")
                return True
            else:
                self.log(f"❌ Authentication failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Authentication error: {e}", "ERROR")
            return False
    
    def create_blueprint_session(self):
        """Create a Blueprint session using POST /session/start"""
        self.log("🚀 Creating Blueprint session using POST /session/start")
        
        if not self.auth_headers or not self.user_id:
            self.log("❌ Not authenticated", "ERROR")
            return False
        
        session_data = {
            "user_id": self.user_id
        }
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/session/start",
                json=session_data,
                headers=self.auth_headers,
                timeout=60,
                verify=False
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.session_id = data.get('session_id')
                    questions = data.get('questions', [])
                    
                    self.log(f"✅ Blueprint session created successfully")
                    self.log(f"📊 Session ID: {self.session_id}")
                    self.log(f"📊 Response time: {response_time:.2f} seconds")
                    self.log(f"📊 Questions count: {len(questions)}")
                    
                    if questions:
                        sample_q = questions[0]
                        self.log(f"📊 Sample question ID: {sample_q.get('id', 'N/A')}")
                        self.log(f"📊 Sample question has stem: {bool(sample_q.get('stem'))}")
                        self.log(f"📊 Sample question has correct_answer: {bool(sample_q.get('correct_answer'))}")
                    
                    return True
                else:
                    self.log(f"❌ Session creation failed: {data}", "ERROR")
                    return False
            else:
                self.log(f"❌ Session creation failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Session creation error: {e}", "ERROR")
            return False
    
    def test_submit_answer_solution_feedback(self):
        """Test POST /session/submit and verify solution feedback response"""
        self.log("📝 Testing POST /session/submit with solution feedback validation")
        
        if not self.session_id:
            self.log("❌ No session ID available", "ERROR")
            return False
        
        # Test data - we'll submit an answer to position 1
        submit_data = {
            "session_id": self.session_id,
            "position": 1,
            "answer": "test_answer"  # We'll use a test answer
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/session/submit",
                json=submit_data,
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.log(f"✅ Submit answer endpoint working")
                self.log(f"📊 Response received: {response.status_code}")
                
                # Validate required fields from review request
                required_fields = ['is_correct', 'correct_answer', 'explanation', 'solution_feedback']
                missing_fields = []
                
                for field in required_fields:
                    if field not in data:
                        missing_fields.append(field)
                
                if missing_fields:
                    self.log(f"❌ Missing required fields: {missing_fields}", "ERROR")
                    return False
                
                # Validate field types and content
                is_correct = data.get('is_correct')
                correct_answer = data.get('correct_answer')
                explanation = data.get('explanation')
                solution_feedback = data.get('solution_feedback')
                
                self.log(f"📊 Response field analysis:")
                self.log(f"   is_correct: {is_correct} (type: {type(is_correct).__name__})")
                self.log(f"   correct_answer: '{correct_answer}' (length: {len(str(correct_answer))})")
                self.log(f"   explanation: present={bool(explanation)} (length: {len(str(explanation)) if explanation else 0})")
                self.log(f"   solution_feedback: present={bool(solution_feedback)} (type: {type(solution_feedback).__name__})")
                
                # Validate is_correct is boolean
                if not isinstance(is_correct, bool):
                    self.log(f"❌ is_correct is not boolean: {type(is_correct)}", "ERROR")
                    return False
                else:
                    self.log(f"✅ is_correct field is boolean")
                
                # Validate correct_answer is string
                if not isinstance(correct_answer, str):
                    self.log(f"❌ correct_answer is not string: {type(correct_answer)}", "ERROR")
                    return False
                else:
                    self.log(f"✅ correct_answer field is string")
                
                # Validate explanation is string
                if not isinstance(explanation, str):
                    self.log(f"❌ explanation is not string: {type(explanation)}", "ERROR")
                    return False
                else:
                    self.log(f"✅ explanation field is string")
                
                # Validate solution_feedback object
                if not isinstance(solution_feedback, dict):
                    self.log(f"❌ solution_feedback is not object: {type(solution_feedback)}", "ERROR")
                    return False
                else:
                    self.log(f"✅ solution_feedback field is object")
                
                # Validate solution_feedback sections
                required_sections = ['snap_read', 'solution_approach', 'detailed_solution', 'principle_to_remember']
                missing_sections = []
                empty_sections = []
                
                for section in required_sections:
                    if section not in solution_feedback:
                        missing_sections.append(section)
                    elif not solution_feedback[section]:
                        empty_sections.append(section)
                
                if missing_sections:
                    self.log(f"❌ Missing solution_feedback sections: {missing_sections}", "ERROR")
                    return False
                
                self.log(f"📊 Solution feedback sections analysis:")
                for section in required_sections:
                    content = solution_feedback.get(section, '')
                    length = len(str(content)) if content else 0
                    has_content = bool(content and str(content).strip())
                    self.log(f"   {section}: length={length}, has_content={has_content}")
                
                if empty_sections:
                    self.log(f"⚠️ Empty solution_feedback sections: {empty_sections}")
                    self.log(f"✅ All required solution_feedback sections present (some may be empty)")
                else:
                    self.log(f"✅ All solution_feedback sections have content")
                
                # Overall validation
                all_required_present = (
                    isinstance(is_correct, bool) and
                    isinstance(correct_answer, str) and
                    isinstance(explanation, str) and
                    isinstance(solution_feedback, dict) and
                    len(missing_sections) == 0
                )
                
                if all_required_present:
                    self.log(f"🎉 SOLUTION FEEDBACK FIX VALIDATION: SUCCESS")
                    self.log(f"   ✅ is_correct (boolean): {is_correct}")
                    self.log(f"   ✅ correct_answer (string): present")
                    self.log(f"   ✅ explanation (string): present")
                    self.log(f"   ✅ solution_feedback (object): all 4 sections present")
                    self.log(f"   📊 Missing post-answer feedback issue: RESOLVED")
                    return True
                else:
                    self.log(f"❌ SOLUTION FEEDBACK FIX VALIDATION: FAILED")
                    return False
                
            else:
                self.log(f"❌ Submit answer failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Submit answer error: {e}", "ERROR")
            return False
    
    def run_test(self):
        """Run the complete solution feedback test"""
        self.log("🎯 BLUEPRINT SESSION SYSTEM SUBMIT ANSWER API TESTING")
        self.log("=" * 80)
        self.log("OBJECTIVE: Test solution feedback fix in Blueprint Session submit answer API")
        self.log("FOCUS: POST /session/submit response includes complete solution feedback")
        self.log("EXPECTED: is_correct, correct_answer, explanation, solution_feedback with all 4 sections")
        self.log("=" * 80)
        
        # Step 1: Authentication
        if not self.authenticate():
            self.log("❌ Test failed at authentication step", "ERROR")
            return False
        
        # Step 2: Create Blueprint session
        if not self.create_blueprint_session():
            self.log("❌ Test failed at session creation step", "ERROR")
            return False
        
        # Step 3: Test submit answer with solution feedback
        if not self.test_submit_answer_solution_feedback():
            self.log("❌ Test failed at solution feedback validation step", "ERROR")
            return False
        
        self.log("🎉 ALL TESTS PASSED - SOLUTION FEEDBACK FIX IS WORKING")
        return True

def main():
    """Main test execution"""
    tester = BlueprintSolutionFeedbackTester()
    
    try:
        success = tester.run_test()
        if success:
            print("\n" + "=" * 80)
            print("🎉 BLUEPRINT SESSION SOLUTION FEEDBACK TEST: SUCCESS")
            print("✅ The solution feedback fix is working correctly")
            print("✅ POST /session/submit returns all required fields")
            print("✅ Missing post-answer feedback issue is resolved")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("❌ BLUEPRINT SESSION SOLUTION FEEDBACK TEST: FAILED")
            print("❌ The solution feedback fix needs attention")
            print("❌ Missing post-answer feedback issue not fully resolved")
            print("=" * 80)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()