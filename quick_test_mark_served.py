#!/usr/bin/env python3
"""
Quick test of the mark-served endpoint to verify state transitions
"""

import requests
import json
import uuid

# Test configuration
BASE_URL = "https://twelvr-debugger.preview.emergentagent.com/api"

def test_mark_served_endpoint():
    print("🎯 QUICK PHASE 4 MARK-SERVED ENDPOINT TEST")
    print("=" * 60)
    
    # Step 1: Authenticate
    print("🔐 Step 1: Authentication")
    login_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data, verify=False)
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return False
    
    auth_data = response.json()
    token = auth_data.get('access_token')
    user_id = auth_data.get('user', {}).get('id')
    
    print(f"✅ Authentication successful")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: Plan a session first
    print("\n📋 Step 2: Planning a session")
    
    session_id = f"session_{uuid.uuid4()}"
    plan_data = {
        "user_id": user_id,
        "last_session_id": f"session_{uuid.uuid4()}",
        "next_session_id": session_id
    }
    
    response = requests.post(f"{BASE_URL}/adapt/plan-next", json=plan_data, headers=headers, verify=False)
    if response.status_code != 200:
        print(f"❌ Planning failed: {response.status_code}")
        return False
    
    print(f"✅ Session planned successfully")
    
    # Step 3: Mark as served
    print("\n✅ Step 3: Marking session as served")
    
    mark_served_data = {
        "user_id": user_id,
        "session_id": session_id
    }
    
    response = requests.post(f"{BASE_URL}/adapt/mark-served", json=mark_served_data, headers=headers, verify=False)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Mark-served endpoint working!")
        print(f"📊 Response: {result}")
        
        if result.get('ok') == True:
            print(f"✅ State transition successful!")
            return True
        else:
            print(f"⚠️ State transition may have failed")
            return False
    else:
        print(f"❌ Mark-served endpoint failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"📊 Error: {error_data}")
        except:
            print(f"📊 Error text: {response.text}")
        return False

if __name__ == "__main__":
    success = test_mark_served_endpoint()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'NEEDS ATTENTION'}")