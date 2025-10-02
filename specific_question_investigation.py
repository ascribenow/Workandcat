#!/usr/bin/env python3
"""
Specific Question Investigation - b7005cd9-12a0-4a4c-a6d9-beb7020f1389
Investigate the specific question mentioned in the review request
"""

import requests
import json
import uuid

class SpecificQuestionInvestigator:
    def __init__(self, base_url="https://adaptive-engine-fix.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        self.target_question_id = "b7005cd9-12a0-4a4c-a6d9-beb7020f1389"
        
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
            return True
        return False
    
    def search_in_questions_table(self):
        """Search for the target question in questions table"""
        print("🔍 SEARCHING IN QUESTIONS TABLE")
        print("-" * 60)
        
        success, response = self.run_test(
            "Get Questions from Database", 
            "GET", 
            "questions?limit=100", 
            [200, 500], 
            None, 
            self.auth_headers
        )
        
        if success and response:
            questions = response if isinstance(response, list) else []
            
            print(f"   📊 Retrieved {len(questions)} questions from database")
            
            # Search for target question
            target_found = False
            for question in questions:
                if question.get('id') == self.target_question_id:
                    target_found = True
                    print(f"   ✅ Target question found in questions table!")
                    print(f"      ID: {question.get('id')}")
                    print(f"      Answer: '{question.get('right_answer', 'N/A')}'")
                    print(f"      Stem preview: {question.get('stem', '')[:100]}...")
                    break
            
            if not target_found:
                print(f"   ❌ Target question {self.target_question_id} NOT found in questions table")
                
                # Search for questions with "6 hours" answer
                six_hours_questions = []
                for question in questions:
                    answer = question.get('right_answer', '')
                    if '6 hours' in str(answer).lower():
                        six_hours_questions.append(question)
                
                if six_hours_questions:
                    print(f"   📊 Found {len(six_hours_questions)} questions with '6 hours' answer:")
                    for q in six_hours_questions[:3]:
                        print(f"      ID: {q.get('id')}, Answer: '{q.get('right_answer', 'N/A')}'")
                
                # Search for questions with "127.27%" answer
                percent_questions = []
                for question in questions:
                    answer = question.get('right_answer', '')
                    if '127.27%' in str(answer):
                        percent_questions.append(question)
                
                if percent_questions:
                    print(f"   📊 Found {len(percent_questions)} questions with '127.27%' answer:")
                    for q in percent_questions[:3]:
                        print(f"      ID: {q.get('id')}, Answer: '{q.get('right_answer', 'N/A')}'")
            
            return target_found
        else:
            print(f"   ❌ Failed to retrieve questions: {response}")
            return False
    
    def test_adaptive_session_for_target(self):
        """Test adaptive session to see if target question appears"""
        print("\n🎯 TESTING ADAPTIVE SESSION FOR TARGET QUESTION")
        print("-" * 60)
        
        # Create multiple adaptive sessions to find the target question
        for attempt in range(3):
            print(f"   🚀 Attempt {attempt + 1}: Creating adaptive session...")
            
            session_id = f"target_search_{attempt}_{uuid.uuid4()}"
            plan_data = {
                "user_id": self.user_id,
                "last_session_id": "S0",
                "next_session_id": session_id
            }
            
            headers_with_idem = self.auth_headers.copy()
            headers_with_idem['Idempotency-Key'] = f"{self.user_id}:S0:{session_id}"
            
            success, plan_response = self.run_test(
                f"Create Adaptive Session {attempt + 1}", 
                "POST", 
                "adapt/plan-next", 
                [200, 400, 500, 502], 
                plan_data, 
                headers_with_idem
            )
            
            if success and plan_response.get('status') == 'planned':
                # Get pack data
                success, pack_response = self.run_test(
                    f"Get Pack {attempt + 1}", 
                    "GET", 
                    f"adapt/pack?user_id={self.user_id}&session_id={session_id}", 
                    [200], 
                    None, 
                    self.auth_headers
                )
                
                if success and pack_response.get('pack'):
                    pack_data = pack_response.get('pack', [])
                    
                    # Search for target question in pack
                    target_found = False
                    for i, question in enumerate(pack_data):
                        if question.get('id') == self.target_question_id:
                            target_found = True
                            print(f"      ✅ Target question found at position {i+1}!")
                            print(f"         Answer: '{question.get('answer', 'N/A')}'")
                            print(f"         Right Answer: '{question.get('right_answer', 'N/A')}'")
                            
                            # Test question action logging
                            self.test_question_action_logging(session_id, question)
                            return True
                    
                    if not target_found:
                        print(f"      ❌ Target question not in this pack")
                        # Show first few questions for reference
                        print(f"         Pack contains: {[q.get('id', 'N/A')[:8] for q in pack_data[:3]]}...")
        
        print(f"   ❌ Target question not found in any of the 3 adaptive sessions")
        return False
    
    def test_question_action_logging(self, session_id, question):
        """Test question action logging with the target question"""
        print(f"      🧪 Testing question action logging...")
        
        log_data = {
            "session_id": session_id,
            "question_id": question.get('id'),
            "action": "submit",
            "data": {
                "user_answer": "test answer",
                "time_taken": 30
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        success, log_response = self.run_test(
            "Test Question Action Logging", 
            "POST", 
            "log/question-action", 
            [200, 500], 
            log_data, 
            self.auth_headers
        )
        
        if success and log_response.get('success'):
            result = log_response.get('result', {})
            correct_answer = result.get('correct_answer', '')
            
            print(f"         ✅ Question action logging successful")
            print(f"         📊 Returned correct answer: '{correct_answer}'")
            
            # Compare with question data
            original_answer = question.get('answer', '')
            if correct_answer == original_answer:
                print(f"         ✅ Answer consistency maintained")
            else:
                print(f"         ❌ Answer mismatch!")
                print(f"            Original: '{original_answer}'")
                print(f"            Returned: '{correct_answer}'")
        else:
            print(f"         ❌ Question action logging failed: {log_response}")
    
    def run_investigation(self):
        """Run complete investigation for the specific question"""
        print("🔍 SPECIFIC QUESTION INVESTIGATION")
        print("=" * 80)
        print(f"TARGET: Question ID {self.target_question_id}")
        print("OBJECTIVE: Investigate data flow for specific question mentioned in review")
        print("=" * 80)
        
        if not self.authenticate():
            print("❌ Authentication failed")
            return False
        
        print(f"✅ Authentication successful")
        
        # Search in questions table
        found_in_db = self.search_in_questions_table()
        
        # Test adaptive sessions
        found_in_session = self.test_adaptive_session_for_target()
        
        # Final results
        print("\n" + "=" * 80)
        print("🔍 SPECIFIC QUESTION INVESTIGATION RESULTS")
        print("=" * 80)
        
        print(f"Target Question ID: {self.target_question_id}")
        print(f"Found in Questions Table: {'✅ YES' if found_in_db else '❌ NO'}")
        print(f"Found in Adaptive Sessions: {'✅ YES' if found_in_session else '❌ NO'}")
        
        if found_in_db and found_in_session:
            print("\n✅ INVESTIGATION COMPLETE: Question found and data flow verified")
        elif found_in_db and not found_in_session:
            print("\n⚠️ Question exists in database but not appearing in sessions")
            print("   - May be filtered out by quality_verified or is_active flags")
            print("   - Check question selection criteria in Blueprint planner")
        elif not found_in_db:
            print("\n❌ Question not found in database")
            print("   - Question ID may be incorrect or question may have been deleted")
            print("   - Check if this is the correct question ID from the frontend")
        
        return found_in_db or found_in_session

if __name__ == "__main__":
    investigator = SpecificQuestionInvestigator()
    investigator.run_investigation()