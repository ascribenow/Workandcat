#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time
import os
import uuid
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SessionLifecycleTester:
    def __init__(self, base_url="https://twelvr-auth-fix.preview.emergentagent.com/api"):
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
                print(f"📊 Token length: {len(token)} chars")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def check_current_sessions(self):
        """Check current session count from dashboard"""
        print("\n📊 CHECKING CURRENT SESSION COUNT...")
        
        try:
            response = requests.get(
                f"{self.base_url}/dashboard/simple-taxonomy",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                completed_sessions = data.get('completed_sessions', 0)
                total_attempts = data.get('total_attempts', 0)
                
                print(f"✅ Dashboard accessible")
                print(f"📊 Completed sessions: {completed_sessions}")
                print(f"📊 Total attempts: {total_attempts}")
                return completed_sessions
            else:
                print(f"❌ Dashboard failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
            return None
    
    def test_session_creation(self):
        """Test creating a new session"""
        print("\n🚀 TESTING SESSION CREATION...")
        
        session_id = str(uuid.uuid4())
        
        # Try Blueprint sessions API first
        plan_data = {
            "user_id": self.user_id,
            "last_session_id": "S1",
            "next_session_id": session_id
        }
        
        headers_with_idem = self.auth_headers.copy()
        headers_with_idem['Idempotency-Key'] = f"{self.user_id}:S1:{session_id}"
        
        try:
            print(f"📋 Creating session: {session_id[:8]}...")
            
            response = requests.post(
                f"{self.base_url}/adapt/plan-next",
                json=plan_data,
                headers=headers_with_idem,
                timeout=60,
                verify=False
            )
            
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                print(f"✅ Session creation successful")
                print(f"📊 Status: {status}")
                
                if status == 'planned':
                    # Test pack fetch
                    pack_response = requests.get(
                        f"{self.base_url}/adapt/pack?user_id={self.user_id}&session_id={session_id}",
                        headers=self.auth_headers,
                        timeout=30,
                        verify=False
                    )
                    
                    if pack_response.status_code == 200:
                        pack_data = pack_response.json()
                        pack_questions = pack_data.get('pack', [])
                        print(f"✅ Session pack retrieved: {len(pack_questions)} questions")
                        return session_id
                    else:
                        print(f"❌ Pack fetch failed: {pack_response.status_code}")
                        return None
                else:
                    print(f"⚠️ Session status: {status}")
                    return None
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
    
    def test_question_actions(self, session_id):
        """Test logging question actions"""
        print(f"\n📝 TESTING QUESTION ACTIONS FOR SESSION {session_id[:8]}...")
        
        # Simulate answering a few questions
        for i in range(3):
            question_id = f"test_q_{i}_{uuid.uuid4()}"
            
            action_data = {
                "session_id": session_id,
                "question_id": question_id,
                "action": "submit",
                "data": {
                    "user_answer": f"Test answer {i+1}",
                    "time_taken": 30 + i * 10
                },
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/log/question-action",
                    json=action_data,
                    headers=self.auth_headers,
                    timeout=30,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        print(f"✅ Question {i+1} action logged")
                    else:
                        print(f"⚠️ Question {i+1} logged with issues: {data}")
                else:
                    print(f"❌ Question {i+1} action failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Question {i+1} action error: {e}")
        
        return True
    
    def test_session_completion(self, session_id):
        """Test completing a session"""
        print(f"\n🏁 TESTING SESSION COMPLETION FOR {session_id[:8]}...")
        
        completion_data = {
            "session_id": session_id,
            "user_id": self.user_id
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sessions/complete",
                json=completion_data,
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Completion response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session completion successful")
                print(f"📊 Response: {data}")
                
                # Check if background processing triggered
                if data.get('adaptive_processing'):
                    print(f"✅ Background processing: {data['adaptive_processing']}")
                
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
    
    def run_investigation(self):
        """Run the complete session lifecycle investigation"""
        print("🎯 SESSION LIFECYCLE INVESTIGATION - USER REPORTS MISSING SECOND SESSION")
        print("=" * 80)
        print("OBJECTIVE: Investigate why user's second session is missing from database")
        print("USER: sp@theskinmantra.com")
        print("ISSUE: User reports completing Session #2, but database shows only 1 session")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate():
            print("\n❌ INVESTIGATION FAILED: Cannot authenticate")
            return False
        
        # Step 2: Check current state
        initial_sessions = self.check_current_sessions()
        if initial_sessions is None:
            print("\n❌ INVESTIGATION FAILED: Cannot check current sessions")
            return False
        
        print(f"\n📊 INITIAL STATE: {initial_sessions} completed sessions")
        
        # Step 3: Test session creation
        session_id = self.test_session_creation()
        if not session_id:
            print("\n❌ INVESTIGATION RESULT: Session creation is failing")
            print("🔍 ROOT CAUSE: New sessions cannot be created")
            return False
        
        # Step 4: Test question actions
        if not self.test_question_actions(session_id):
            print("\n⚠️ WARNING: Question action logging may have issues")
        
        # Step 5: Test session completion
        if not self.test_session_completion(session_id):
            print("\n❌ INVESTIGATION RESULT: Session completion is failing")
            print("🔍 ROOT CAUSE: Sessions cannot be completed properly")
            return False
        
        # Step 6: Check final state
        print("\n🔍 CHECKING FINAL STATE...")
        time.sleep(2)  # Wait for background processing
        
        final_sessions = self.check_current_sessions()
        if final_sessions is None:
            print("\n⚠️ WARNING: Cannot verify final session count")
        else:
            print(f"\n📊 FINAL STATE: {final_sessions} completed sessions")
            
            if final_sessions > initial_sessions:
                print("\n✅ INVESTIGATION RESULT: Session lifecycle is working!")
                print("🎉 SUCCESS: New session created and completed successfully")
                print("📋 RECOMMENDATION: User should try creating a new session")
                return True
            else:
                print("\n❌ INVESTIGATION RESULT: Session completion not persisting")
                print("🔍 ROOT CAUSE: Sessions complete but don't update database count")
                return False

def main():
    tester = SessionLifecycleTester()
    success = tester.run_investigation()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 INVESTIGATION COMPLETE: Session lifecycle is working")
        print("✅ User can create and complete new sessions")
    else:
        print("❌ INVESTIGATION COMPLETE: Issues found in session lifecycle")
        print("⚠️ Session creation or completion is failing")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    main()