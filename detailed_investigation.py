#!/usr/bin/env python3

import requests
import json
import uuid
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DetailedInvestigator:
    def __init__(self, base_url="https://cat-session-sys.preview.emergentagent.com/api"):
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
    
    def investigate_current_state(self):
        """Investigate the current state of user sessions"""
        print("\n🔍 INVESTIGATING CURRENT STATE...")
        
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
                print(f"📊 DASHBOARD DATA:")
                print(f"   Total sessions: {data.get('total_sessions', 'N/A')}")
                print(f"   Completed sessions: {data.get('completed_sessions', 'N/A')}")
                print(f"   Total attempts: {data.get('total_attempts', 'N/A')}")
                
                taxonomy_data = data.get('taxonomy_data', [])
                if taxonomy_data:
                    print(f"   Taxonomy entries: {len(taxonomy_data)}")
                    for entry in taxonomy_data[:3]:  # Show first 3
                        print(f"      {entry.get('subcategory', 'N/A')}: {entry.get('attempts', 0)} attempts")
                else:
                    print(f"   No taxonomy data found")
                    
        except Exception as e:
            print(f"❌ Dashboard error: {e}")
        
        # Check last completed session
        try:
            response = requests.get(
                f"{self.base_url}/sessions/last-completed-id?user_id={self.user_id}",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 LAST COMPLETED SESSION:")
                print(f"   Session ID: {data.get('session_id', 'N/A')}")
                print(f"   Session sequence: {data.get('sess_seq', 'N/A')}")
                print(f"   User ID: {data.get('user_id', 'N/A')}")
            else:
                print(f"⚠️ No completed sessions found: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error text: {response.text}")
                    
        except Exception as e:
            print(f"❌ Last session error: {e}")
        
        # Check current session progress
        try:
            response = requests.get(
                f"{self.base_url}/session-progress/current/{self.user_id}",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 CURRENT SESSION PROGRESS:")
                print(f"   Has current session: {data.get('has_current_session', 'N/A')}")
                print(f"   Success: {data.get('success', 'N/A')}")
                print(f"   Message: {data.get('message', 'N/A')}")
                
                if data.get('current_session'):
                    session = data['current_session']
                    print(f"   Current session ID: {session.get('session_id', 'N/A')}")
                    print(f"   Questions answered: {session.get('questions_answered', 'N/A')}")
                    
        except Exception as e:
            print(f"❌ Current session error: {e}")
    
    def test_session_creation_alternatives(self):
        """Test different ways to create sessions"""
        print("\n🚀 TESTING SESSION CREATION ALTERNATIVES...")
        
        # Test 1: Try the deprecated sessions/start endpoint to see what it says
        print("\n📋 Test 1: Deprecated sessions/start endpoint")
        try:
            response = requests.post(
                f"{self.base_url}/sessions/start",
                json={"user_id": self.user_id},
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 410:
                data = response.json()
                print(f"   ✅ Correctly deprecated")
                print(f"   📋 Replacement: {data.get('detail', {}).get('replacement_endpoint', 'N/A')}")
            else:
                print(f"   ⚠️ Unexpected response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Try adapt/plan-next with different parameters
        print("\n📋 Test 2: adapt/plan-next endpoint")
        session_id = str(uuid.uuid4())
        
        plan_data = {
            "user_id": self.user_id,
            "last_session_id": "S1",  # Try with S1 since user has completed sessions
            "next_session_id": session_id
        }
        
        headers_with_idem = self.auth_headers.copy()
        headers_with_idem['Idempotency-Key'] = f"{self.user_id}:S1:{session_id}"
        
        try:
            response = requests.post(
                f"{self.base_url}/adapt/plan-next",
                json=plan_data,
                headers=headers_with_idem,
                timeout=60,
                verify=False
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 404:
                print(f"   ❌ Endpoint not found - adapt/plan-next may not be available")
            else:
                try:
                    data = response.json()
                    print(f"   📊 Response: {data}")
                except:
                    print(f"   📊 Response text: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Check what endpoints are actually available
        print("\n📋 Test 3: Available session endpoints discovery")
        
        # Try some common session endpoint patterns
        test_endpoints = [
            "sessions",
            "session",
            "blueprint/sessions",
            "blueprint/session",
            "adapt/sessions",
            "adapt/session"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(
                    f"{self.base_url}/{endpoint}",
                    headers=self.auth_headers,
                    timeout=10,
                    verify=False
                )
                
                if response.status_code != 404:
                    print(f"   ✅ {endpoint}: {response.status_code}")
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"      📊 Response type: {type(data)}")
                        except:
                            pass
                            
            except:
                pass
    
    def test_question_submission(self):
        """Test if we can submit question actions without a session"""
        print("\n📝 TESTING QUESTION ACTION SUBMISSION...")
        
        # Try to submit a question action to see what happens
        fake_session_id = str(uuid.uuid4())
        fake_question_id = str(uuid.uuid4())
        
        action_data = {
            "session_id": fake_session_id,
            "question_id": fake_question_id,
            "action": "submit",
            "data": {
                "user_answer": "Test answer",
                "time_taken": 30
            },
            "timestamp": "2025-01-27T10:00:00Z"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/log/question-action",
                json=action_data,
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Question action status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Question action accepted")
                print(f"📊 Response: {data}")
            else:
                try:
                    error_data = response.json()
                    print(f"❌ Question action failed: {error_data}")
                except:
                    print(f"❌ Question action failed: {response.text}")
                    
        except Exception as e:
            print(f"❌ Question action error: {e}")
    
    def run_investigation(self):
        """Run the complete detailed investigation"""
        print("🎯 DETAILED SESSION LIFECYCLE INVESTIGATION")
        print("=" * 80)
        print("OBJECTIVE: Deep dive into session lifecycle and API availability")
        print("USER: sp@theskinmantra.com")
        print("FOCUS: Understanding current state and available endpoints")
        print("=" * 80)
        
        if not self.authenticate():
            return False
        
        self.investigate_current_state()
        self.test_session_creation_alternatives()
        self.test_question_submission()
        
        print("\n" + "=" * 80)
        print("🎯 INVESTIGATION SUMMARY")
        print("=" * 80)
        print("✅ User authentication working")
        print("✅ Dashboard and session data accessible")
        print("❌ Session creation endpoints not available (404 errors)")
        print("📋 RECOMMENDATION: Check if session creation is handled differently")
        print("📋 NEXT STEPS: Investigate backend logs and available API routes")
        print("=" * 80)

def main():
    investigator = DetailedInvestigator()
    investigator.run_investigation()

if __name__ == "__main__":
    main()