#!/usr/bin/env python3
"""
Session Creation Debug Test
Debug why sessions are only generating 3 questions instead of 12
"""

import requests
import json
import time

class SessionDebugTester:
    def __init__(self):
        self.base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
        self.admin_token = None
        self.session_id = None
        
    def authenticate_admin(self):
        """Authenticate admin user"""
        print("🔐 Authenticating admin user...")
        
        login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        try:
            response = requests.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get('access_token')
                user = data.get('user', {})
                print(f"✅ Admin authenticated: {user.get('email')}")
                print(f"   Admin privileges: {user.get('is_admin')}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def check_question_pool(self):
        """Check available questions in database"""
        print("\n📊 Checking question pool...")
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{self.base_url}/questions?limit=50", headers=headers)
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                active_questions = [q for q in questions if q.get('is_active', False)]
                
                print(f"   Total questions: {len(questions)}")
                print(f"   Active questions: {len(active_questions)}")
                
                if len(active_questions) >= 12:
                    print(f"   ✅ Sufficient questions for 12-question session")
                else:
                    print(f"   ❌ Insufficient active questions (need 12, have {len(active_questions)})")
                
                # Show sample questions
                print("   Sample active questions:")
                for i, q in enumerate(active_questions[:5]):
                    print(f"     {i+1}. ID: {q.get('id')}")
                    print(f"        Stem: {q.get('stem', '')[:60]}...")
                    print(f"        Subcategory: {q.get('subcategory')}")
                    print(f"        Difficulty: {q.get('difficulty_band')}")
                
                return len(active_questions)
            else:
                print(f"   ❌ Failed to get questions: {response.status_code}")
                return 0
        except Exception as e:
            print(f"   ❌ Error checking questions: {e}")
            return 0
    
    def test_session_start(self):
        """Test session creation"""
        print("\n🎯 Testing session creation...")
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        session_data = {"target_minutes": 30}
        
        try:
            response = requests.post(f"{self.base_url}/sessions/start", json=session_data, headers=headers)
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get('session_id')
                total_questions = data.get('total_questions')
                session_type = data.get('session_type')
                
                print(f"   ✅ Session created successfully")
                print(f"   Session ID: {self.session_id}")
                print(f"   Total questions: {total_questions}")
                print(f"   Session type: {session_type}")
                
                # Check personalization data
                if 'personalization' in data:
                    personalization = data['personalization']
                    print(f"   Personalization:")
                    print(f"     Applied: {personalization.get('applied')}")
                    print(f"     Learning stage: {personalization.get('learning_stage')}")
                    print(f"     Recent accuracy: {personalization.get('recent_accuracy')}")
                    print(f"     Difficulty distribution: {personalization.get('difficulty_distribution')}")
                    print(f"     Category distribution: {personalization.get('category_distribution')}")
                
                # Critical analysis
                if total_questions == 12:
                    print("   ✅ CORRECT: Session has 12 questions")
                elif total_questions == 3:
                    print("   ❌ ISSUE CONFIRMED: Session has only 3 questions (expected 12)")
                else:
                    print(f"   ⚠️ UNEXPECTED: Session has {total_questions} questions (expected 12)")
                
                return total_questions
            else:
                print(f"   ❌ Session creation failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Raw error: {response.text}")
                return 0
        except Exception as e:
            print(f"   ❌ Session creation error: {e}")
            return 0
    
    def test_session_status(self):
        """Test session status API"""
        print("\n📊 Testing session status...")
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{self.base_url}/sessions/current-status", headers=headers)
            if response.status_code == 200:
                data = response.json()
                active_session = data.get('active_session')
                
                print(f"   Active session: {active_session}")
                
                if active_session:
                    progress = data.get('progress', {})
                    print(f"   Session ID: {data.get('session_id')}")
                    print(f"   Progress:")
                    print(f"     Answered: {progress.get('answered', 0)}")
                    print(f"     Total: {progress.get('total', 0)}")
                    print(f"     Next question: {progress.get('next_question', 0)}")
                    
                    total_in_status = progress.get('total', 0)
                    if total_in_status == 12:
                        print("   ✅ Status shows 12 questions")
                    elif total_in_status == 3:
                        print("   ❌ Status shows only 3 questions")
                    else:
                        print(f"   ⚠️ Status shows {total_in_status} questions")
                    
                    return total_in_status
                else:
                    print("   ⚠️ No active session found")
                    return 0
            else:
                print(f"   ❌ Status check failed: {response.status_code}")
                return 0
        except Exception as e:
            print(f"   ❌ Status check error: {e}")
            return 0
    
    def test_next_question(self):
        """Test getting next question"""
        print("\n❓ Testing next question API...")
        
        if not self.session_id:
            print("   ❌ No session ID available")
            return 0
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{self.base_url}/sessions/{self.session_id}/next-question", headers=headers)
            if response.status_code == 200:
                data = response.json()
                question = data.get('question')
                session_progress = data.get('session_progress', {})
                session_complete = data.get('session_complete', False)
                
                if question:
                    print(f"   ✅ Question retrieved")
                    print(f"   Question ID: {question.get('id')}")
                    print(f"   Stem: {question.get('stem', '')[:60]}...")
                    print(f"   Subcategory: {question.get('subcategory')}")
                    print(f"   Difficulty: {question.get('difficulty_band')}")
                    
                    print(f"   Session progress:")
                    print(f"     Current: {session_progress.get('current_question')}")
                    print(f"     Total: {session_progress.get('total_questions')}")
                    print(f"     Remaining: {session_progress.get('questions_remaining')}")
                    print(f"     Progress: {session_progress.get('progress_percentage')}%")
                    
                    return session_progress.get('total_questions', 0)
                elif session_complete:
                    print("   ⚠️ Session already complete")
                    return 0
                else:
                    print("   ❌ No question available")
                    return 0
            else:
                print(f"   ❌ Next question failed: {response.status_code}")
                return 0
        except Exception as e:
            print(f"   ❌ Next question error: {e}")
            return 0
    
    def investigate_session_questions(self):
        """Try to get all questions in the session"""
        print("\n🔍 Investigating session question count...")
        
        if not self.session_id:
            print("   ❌ No session ID available")
            return []
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        question_ids = []
        
        # Try to get multiple questions to see the pattern
        for i in range(15):  # Try up to 15 questions
            try:
                response = requests.get(f"{self.base_url}/sessions/{self.session_id}/next-question", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    question = data.get('question')
                    session_complete = data.get('session_complete', False)
                    
                    if question:
                        q_id = question.get('id')
                        if q_id not in question_ids:
                            question_ids.append(q_id)
                            print(f"     Question {len(question_ids)}: {q_id}")
                        
                        # Submit a dummy answer to move to next question
                        answer_data = {
                            "question_id": q_id,
                            "user_answer": "A",
                            "time_sec": 30,
                            "hint_used": False
                        }
                        
                        requests.post(f"{self.base_url}/sessions/{self.session_id}/submit-answer", 
                                    json=answer_data, headers=headers)
                        
                    elif session_complete:
                        print(f"     Session complete after {len(question_ids)} questions")
                        break
                    else:
                        break
                else:
                    break
            except:
                break
        
        print(f"   Total unique questions found: {len(question_ids)}")
        return question_ids
    
    def run_debug_test(self):
        """Run complete debug test"""
        print("🔍 SESSION CREATION DEBUG TEST")
        print("=" * 60)
        print("Debugging why sessions are only generating 3 questions instead of 12")
        print("Expected: Sessions should create exactly 12 questions")
        print("=" * 60)
        
        # Step 1: Authenticate
        if not self.authenticate_admin():
            return False
        
        # Step 2: Check question pool
        active_count = self.check_question_pool()
        
        # Step 3: Test session creation
        session_questions = self.test_session_start()
        
        # Step 4: Test session status
        status_questions = self.test_session_status()
        
        # Step 5: Test next question
        next_questions = self.test_next_question()
        
        # Step 6: Investigate actual question count
        actual_questions = self.investigate_session_questions()
        
        # Final analysis
        print("\n" + "=" * 60)
        print("DEBUG ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"Active questions in database: {active_count}")
        print(f"Questions reported in session creation: {session_questions}")
        print(f"Questions reported in session status: {status_questions}")
        print(f"Questions reported in next question: {next_questions}")
        print(f"Actual unique questions found: {len(actual_questions)}")
        
        print("\n🎯 CONCLUSIONS:")
        
        if active_count < 12:
            print("❌ ROOT CAUSE: Insufficient active questions in database")
            print("   SOLUTION: Activate more questions or create additional questions")
        elif session_questions == 3:
            print("❌ ISSUE: Session creation logic is limiting to 3 questions")
            print("   INVESTIGATION NEEDED: Check adaptive_session_logic.py")
            print("   - Look for hardcoded limits")
            print("   - Check fallback mechanisms")
            print("   - Verify personalization logic")
        elif len(actual_questions) != session_questions:
            print("❌ INCONSISTENCY: Reported vs actual question count mismatch")
            print("   INVESTIGATION NEEDED: Check session.units field in database")
        else:
            print("✅ Session creation appears to be working correctly")
        
        print("\n📋 RECOMMENDATIONS:")
        print("1. Check adaptive_session_logic.py for question count limits")
        print("2. Verify question filtering criteria in session creation")
        print("3. Check if personalization is reducing available questions")
        print("4. Review fallback session creation logic")
        print("5. Ensure sufficient active questions in database")
        
        return True

if __name__ == "__main__":
    tester = SessionDebugTester()
    tester.run_debug_test()