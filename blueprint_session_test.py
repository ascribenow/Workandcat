#!/usr/bin/env python3

import requests
import json
import uuid
import urllib3
from datetime import datetime
import time

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BlueprintSessionTester:
    def __init__(self, base_url="https://smart-tutor-50.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate with the specific user credentials"""
        print("🔐 AUTHENTICATING...")
        
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
                self.user_id = data.get('user', {}).get('id')
                
                self.auth_headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                print(f"✅ Authentication successful")
                print(f"📊 User ID: {self.user_id}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def check_current_state(self):
        """Check current session state"""
        print("\n📊 CHECKING CURRENT STATE...")
        
        # Check dashboard
        try:
            response = requests.get(
                f"{self.base_url}/dashboard/simple-taxonomy",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                total_sessions = data.get('total_sessions', 0)
                total_attempts = data.get('total_attempts', 0)
                
                print(f"✅ Dashboard accessible")
                print(f"📊 Total sessions: {total_sessions}")
                print(f"📊 Total attempts: {total_attempts}")
                
                # Show taxonomy breakdown
                taxonomy_data = data.get('taxonomy_data', [])
                if taxonomy_data:
                    print(f"📊 Question categories attempted:")
                    for entry in taxonomy_data[:5]:  # Show first 5
                        subcategory = entry.get('subcategory', 'Unknown')
                        attempts = entry.get('attempts', 0)
                        correct = entry.get('correct', 0)
                        accuracy = entry.get('accuracy', 0)
                        print(f"   {subcategory}: {attempts} attempts, {correct} correct ({accuracy}%)")
                
                return total_sessions
            else:
                print(f"❌ Dashboard failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return None
    
    def check_last_completed_session(self):
        """Check the last completed session details"""
        print("\n🔍 CHECKING LAST COMPLETED SESSION...")
        
        try:
            response = requests.get(
                f"{self.base_url}/sessions/last-completed-id?user_id={self.user_id}",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Last completed session found")
                print(f"📊 Session ID: {data.get('session_id', 'N/A')}")
                print(f"📊 Session sequence: {data.get('sess_seq', 'N/A')}")
                return data
            else:
                print(f"⚠️ No completed sessions: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Last session error: {e}")
            return None
    
    def test_blueprint_session_creation(self):
        """Test creating a new Blueprint session"""
        print("\n🚀 TESTING BLUEPRINT SESSION CREATION...")
        
        session_data = {
            "user_id": self.user_id
        }
        
        try:
            print(f"📋 Creating new Blueprint session...")
            
            response = requests.post(
                f"{self.base_url}/session/start",
                json=session_data,
                headers=self.auth_headers,
                timeout=60,
                verify=False
            )
            
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                session_id = data.get('session_id')
                session_number = data.get('session_number')
                total_questions = data.get('total_questions')
                
                print(f"✅ Blueprint session created successfully")
                print(f"📊 Session ID: {session_id}")
                print(f"📊 Session number: {session_number}")
                print(f"📊 Total questions: {total_questions}")
                print(f"📊 Session type: {data.get('session_type')}")
                
                return session_id
            else:
                print(f"❌ Session creation failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📊 Error details: {error_data}")
                except:
                    print(f"📊 Error text: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Session creation error: {e}")
            return None
    
    def test_session_questions(self, session_id):
        """Test retrieving session questions"""
        print(f"\n📚 TESTING SESSION QUESTIONS FOR {session_id[:8]}...")
        
        try:
            response = requests.get(
                f"{self.base_url}/session/questions/{session_id}",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                
                print(f"✅ Retrieved {len(questions)} questions")
                
                if questions:
                    # Show first question details
                    first_q = questions[0]
                    print(f"📊 First question:")
                    print(f"   ID: {first_q.get('id', 'N/A')}")
                    print(f"   Position: {first_q.get('position', 'N/A')}")
                    print(f"   Stem: {first_q.get('stem', 'N/A')[:100]}...")
                    print(f"   Options: A={first_q.get('option_a', 'N/A')[:20]}, B={first_q.get('option_b', 'N/A')[:20]}")
                    print(f"   Category: {first_q.get('subcategory', 'N/A')}")
                    
                return questions
            else:
                print(f"❌ Questions retrieval failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Questions retrieval error: {e}")
            return None
    
    def test_answer_submission(self, session_id, questions):
        """Test submitting answers to questions"""
        print(f"\n📝 TESTING ANSWER SUBMISSION FOR {session_id[:8]}...")
        
        if not questions:
            print("❌ No questions available for answer submission")
            return False
        
        # Submit answers to first 3 questions
        for i in range(min(3, len(questions))):
            question = questions[i]
            position = question.get('position', i + 1)
            
            # Submit a test answer (option A)
            answer_data = {
                "session_id": session_id,
                "position": position,
                "answer": question.get('option_a', 'A')
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/session/submit",
                    json=answer_data,
                    headers=self.auth_headers,
                    timeout=30,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    is_correct = data.get('is_correct', False)
                    correct_answer = data.get('correct_answer', 'N/A')
                    
                    print(f"✅ Question {position} submitted: {'Correct' if is_correct else 'Incorrect'}")
                    print(f"   User answer: {answer_data['answer']}")
                    print(f"   Correct answer: {correct_answer}")
                    
                    # Check solution feedback
                    solution_feedback = data.get('solution_feedback', {})
                    feedback_available = any(solution_feedback.values())
                    print(f"   Solution feedback: {'Available' if feedback_available else 'Not available'}")
                    
                else:
                    print(f"❌ Question {position} submission failed: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data}")
                    except:
                        print(f"   Error text: {response.text}")
                        
            except Exception as e:
                print(f"❌ Question {position} submission error: {e}")
        
        return True
    
    def test_session_completion(self, session_id):
        """Test completing a session"""
        print(f"\n🏁 TESTING SESSION COMPLETION FOR {session_id[:8]}...")
        
        completion_data = {
            "session_id": session_id
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/session/complete",
                json=completion_data,
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Completion response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session completion successful")
                
                summary = data.get('summary', {})
                if summary:
                    print(f"📊 Session summary:")
                    print(f"   Total questions: {summary.get('total_questions', 'N/A')}")
                    print(f"   Correct answers: {summary.get('correct_answers', 'N/A')}")
                    print(f"   Accuracy: {summary.get('accuracy', 'N/A')}%")
                    print(f"   Adaptive processing: {summary.get('adaptive_processing', 'N/A')}")
                
                return True
            else:
                print(f"❌ Session completion failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"📊 Error details: {error_data}")
                except:
                    print(f"📊 Error text: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Session completion error: {e}")
            return False
    
    def run_complete_investigation(self):
        """Run the complete session lifecycle investigation"""
        print("🎯 BLUEPRINT SESSION LIFECYCLE INVESTIGATION")
        print("=" * 80)
        print("OBJECTIVE: Test complete Blueprint session lifecycle")
        print("USER: sp@theskinmantra.com")
        print("FOCUS: Session creation → Questions → Answers → Completion")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate():
            print("\n❌ INVESTIGATION FAILED: Cannot authenticate")
            return False
        
        # Step 2: Check current state
        initial_sessions = self.check_current_state()
        if initial_sessions is None:
            print("\n❌ INVESTIGATION FAILED: Cannot check current state")
            return False
        
        print(f"\n📊 INITIAL STATE: {initial_sessions} total sessions")
        
        # Step 3: Check last completed session
        last_session = self.check_last_completed_session()
        if last_session:
            print(f"📊 User has completed sessions (last: Session #{last_session.get('sess_seq', 'N/A')})")
        else:
            print(f"📊 No completed sessions found")
        
        # Step 4: Test session creation
        session_id = self.test_blueprint_session_creation()
        if not session_id:
            print("\n❌ INVESTIGATION RESULT: Blueprint session creation is failing")
            print("🔍 ROOT CAUSE: Cannot create new Blueprint sessions")
            return False
        
        # Step 5: Test question retrieval
        questions = self.test_session_questions(session_id)
        if not questions:
            print("\n❌ INVESTIGATION RESULT: Question retrieval is failing")
            print("🔍 ROOT CAUSE: Cannot retrieve questions for Blueprint session")
            return False
        
        # Step 6: Test answer submission
        if not self.test_answer_submission(session_id, questions):
            print("\n⚠️ WARNING: Answer submission may have issues")
        
        # Step 7: Test session completion
        if not self.test_session_completion(session_id):
            print("\n❌ INVESTIGATION RESULT: Session completion is failing")
            print("🔍 ROOT CAUSE: Cannot complete Blueprint sessions")
            return False
        
        # Step 8: Check final state
        print("\n🔍 CHECKING FINAL STATE...")
        time.sleep(2)  # Wait for background processing
        
        final_sessions = self.check_current_state()
        if final_sessions is None:
            print("\n⚠️ WARNING: Cannot verify final session count")
        else:
            print(f"\n📊 FINAL STATE: {final_sessions} total sessions")
            
            if final_sessions > initial_sessions:
                print("\n✅ INVESTIGATION RESULT: Blueprint session lifecycle is working!")
                print("🎉 SUCCESS: New session created and completed successfully")
                print("📋 FINDING: User can create and complete Blueprint sessions")
                print("📋 RECOMMENDATION: The missing Session #2 issue may be resolved")
                return True
            else:
                print("\n❌ INVESTIGATION RESULT: Session completion not persisting")
                print("🔍 ROOT CAUSE: Sessions complete but don't update session count")
                return False

def main():
    tester = BlueprintSessionTester()
    success = tester.run_complete_investigation()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 INVESTIGATION COMPLETE: Blueprint session lifecycle is working")
        print("✅ User can create and complete new Blueprint sessions")
        print("📋 CONCLUSION: The missing Session #2 issue appears to be resolved")
        print("📋 NEXT STEPS: User should try creating a new session manually")
    else:
        print("❌ INVESTIGATION COMPLETE: Issues found in Blueprint session lifecycle")
        print("⚠️ Session creation, question retrieval, or completion is failing")
        print("📋 RECOMMENDATION: Check backend logs for specific error details")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    main()