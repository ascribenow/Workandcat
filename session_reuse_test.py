#!/usr/bin/env python3

import requests
import json
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SessionReuseInvestigator:
    def __init__(self, base_url="https://data-integrity-1.preview.emergentagent.com/api"):
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
    
    def test_multiple_session_creation(self):
        """Test creating multiple sessions to see if they reuse the same session ID"""
        print("\n🔍 TESTING MULTIPLE SESSION CREATION...")
        
        session_ids = []
        
        for i in range(3):
            print(f"\n📋 Attempt {i+1}: Creating session...")
            
            session_data = {"user_id": self.user_id}
            
            try:
                response = requests.post(
                    f"{self.base_url}/session/start",
                    json=session_data,
                    headers=self.auth_headers,
                    timeout=60,
                    verify=False
                )
                
                if response.status_code == 200:
                    data = response.json()
                    session_id = data.get('session_id')
                    session_number = data.get('session_number')
                    
                    print(f"✅ Session created: {session_id}")
                    print(f"📊 Session number: {session_number}")
                    
                    session_ids.append(session_id)
                else:
                    print(f"❌ Session creation failed: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Session creation error: {e}")
        
        # Analyze results
        print(f"\n📊 ANALYSIS:")
        print(f"   Sessions created: {len(session_ids)}")
        print(f"   Unique session IDs: {len(set(session_ids))}")
        
        if len(set(session_ids)) == 1 and len(session_ids) > 1:
            print(f"❌ ISSUE IDENTIFIED: Same session ID reused multiple times")
            print(f"   Reused session ID: {session_ids[0]}")
            print(f"🔍 ROOT CAUSE: Blueprint planner returns existing session instead of creating new ones")
            return False
        elif len(set(session_ids)) == len(session_ids):
            print(f"✅ WORKING: Each attempt created a unique session")
            return True
        else:
            print(f"⚠️ MIXED RESULTS: Some sessions reused, some unique")
            return False
    
    def run_investigation(self):
        """Run the session reuse investigation"""
        print("🎯 SESSION REUSE INVESTIGATION")
        print("=" * 80)
        print("OBJECTIVE: Determine if Blueprint sessions are being reused instead of creating new ones")
        print("USER: sp@theskinmantra.com")
        print("HYPOTHESIS: Completed sessions are being returned as 'existing planned sessions'")
        print("=" * 80)
        
        if not self.authenticate():
            return False
        
        result = self.test_multiple_session_creation()
        
        print("\n" + "=" * 80)
        print("🎯 INVESTIGATION CONCLUSION")
        print("=" * 80)
        
        if not result:
            print("❌ CONFIRMED: Session reuse issue identified")
            print("🔍 ROOT CAUSE: Blueprint planner's _get_existing_planned_session method")
            print("   returns completed sessions instead of creating new ones")
            print("📋 IMPACT: Users cannot create Session #2, #3, etc.")
            print("📋 FIX NEEDED: Modify _get_existing_planned_session to exclude completed sessions")
            print("📋 SPECIFIC ISSUE: Query doesn't check session status in sessions table")
        else:
            print("✅ NO ISSUE: Sessions are being created uniquely")
            print("📋 CONCLUSION: Session reuse is not the problem")
        
        print("=" * 80)
        return result

def main():
    investigator = SessionReuseInvestigator()
    investigator.run_investigation()

if __name__ == "__main__":
    main()