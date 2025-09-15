#!/usr/bin/env python3
"""
Quick test of the start-first endpoint (cold-start convenience)
"""

import requests
import json
import uuid

# Test configuration
BASE_URL = "https://twelvr-debugger.preview.emergentagent.com/api"

def test_start_first_endpoint():
    print("🎯 QUICK PHASE 4 START-FIRST ENDPOINT TEST")
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
    
    # Step 2: Test start-first endpoint
    print("\n🚀 Step 2: Testing start-first endpoint")
    
    session_id = f"session_{uuid.uuid4()}"
    start_first_data = {
        "user_id": user_id,
        "next_session_id": session_id
    }
    
    response = requests.post(f"{BASE_URL}/adapt/start-first", json=start_first_data, headers=headers, verify=False)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        pack = result.get('pack', [])
        
        print(f"✅ Start-first endpoint working!")
        print(f"📊 Response keys: {list(result.keys())}")
        print(f"📊 Pack size: {len(pack)} questions")
        
        # Check if it returns pack immediately (convenience feature)
        if pack and len(pack) == 12:
            # Check difficulty distribution
            difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0}
            for question in pack:
                difficulty = question.get('bucket', question.get('difficulty_band', 'Unknown'))
                if difficulty in difficulty_counts:
                    difficulty_counts[difficulty] += 1
            
            print(f"📊 Difficulty distribution: {difficulty_counts}")
            print(f"✅ Cold-start convenience working - returns pack immediately!")
            return True
        else:
            print(f"⚠️ Pack not returned immediately or wrong size")
            return False
    else:
        print(f"❌ Start-first endpoint failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"📊 Error: {error_data}")
        except:
            print(f"📊 Error text: {response.text}")
        return False

if __name__ == "__main__":
    success = test_start_first_endpoint()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'NEEDS ATTENTION'}")