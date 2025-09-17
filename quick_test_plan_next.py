#!/usr/bin/env python3
"""
Quick test of the plan-next endpoint to verify fixes
"""

import requests
import json
import uuid

# Test configuration
BASE_URL = "https://learning-tutor.preview.emergentagent.com/api"

def test_plan_next_endpoint():
    print("🎯 QUICK PHASE 4 PLAN-NEXT ENDPOINT TEST")
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
    print(f"📊 User ID: {user_id[:8]}...")
    
    # Step 2: Test plan-next endpoint
    print("\n📋 Step 2: Testing plan-next endpoint")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    plan_data = {
        "user_id": user_id,
        "last_session_id": f"session_{uuid.uuid4()}",
        "next_session_id": f"session_{uuid.uuid4()}"
    }
    
    print(f"📊 Next session ID: {plan_data['next_session_id'][:20]}...")
    
    response = requests.post(f"{BASE_URL}/adapt/plan-next", json=plan_data, headers=headers, verify=False)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Plan-next endpoint working!")
        print(f"📊 Response keys: {list(result.keys())}")
        print(f"📊 Status: {result.get('status')}")
        return True
    else:
        print(f"❌ Plan-next endpoint failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"📊 Error: {error_data}")
        except:
            print(f"📊 Error text: {response.text}")
        return False

if __name__ == "__main__":
    success = test_plan_next_endpoint()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'FAILED'}")