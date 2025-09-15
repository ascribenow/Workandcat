#!/usr/bin/env python3
"""
Quick test of the pack endpoint to verify 12-question packs with 3-6-3 distribution
"""

import requests
import json
import uuid

# Test configuration
BASE_URL = "https://twelvr-debugger.preview.emergentagent.com/api"

def test_pack_endpoint():
    print("🎯 QUICK PHASE 4 PACK ENDPOINT TEST")
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
    
    # Step 3: Get the pack
    print("\n📦 Step 3: Getting the pack")
    
    pack_url = f"{BASE_URL}/adapt/pack?user_id={user_id}&session_id={session_id}"
    response = requests.get(pack_url, headers=headers, verify=False)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        pack = result.get('pack', [])
        
        print(f"✅ Pack endpoint working!")
        print(f"📊 Pack size: {len(pack)} questions")
        
        # Check difficulty distribution
        difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0}
        for question in pack:
            difficulty = question.get('bucket', question.get('difficulty_band', 'Unknown'))
            if difficulty in difficulty_counts:
                difficulty_counts[difficulty] += 1
        
        print(f"📊 Difficulty distribution: {difficulty_counts}")
        
        # Check if it meets 3-6-3 requirement
        if (len(pack) == 12 and 
            difficulty_counts.get('Easy', 0) == 3 and 
            difficulty_counts.get('Medium', 0) == 6 and 
            difficulty_counts.get('Hard', 0) == 3):
            print(f"✅ Perfect 3-6-3 difficulty distribution!")
            return True
        else:
            print(f"⚠️ Difficulty distribution doesn't match 3-6-3 requirement")
            return False
    else:
        print(f"❌ Pack endpoint failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"📊 Error: {error_data}")
        except:
            print(f"📊 Error text: {response.text}")
        return False

if __name__ == "__main__":
    success = test_pack_endpoint()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'NEEDS ATTENTION'}")