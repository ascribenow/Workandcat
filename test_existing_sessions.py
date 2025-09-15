#!/usr/bin/env python3
"""
Test pack fetch with known session IDs from logs
"""

import requests
import json

def test_existing_sessions():
    base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
    
    # Step 1: Authenticate
    print("🔐 Step 1: Authentication")
    login_data = {"email": "sp@theskinmantra.com", "password": "student123"}
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            token = data['access_token']
            user_id = data['user']['id']
            print(f"✅ Authentication successful")
            print(f"📊 User ID: {user_id}")
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: Test pack fetch with session ID from logs that returned 200 OK
    print(f"\n📦 Step 2: Test pack fetch with known working session ID")
    
    # From the logs, I saw this session ID returned 200 OK:
    test_session_id = "7409bbc3-d8a3-4d9e-8337-f37685d60d58"
    
    try:
        response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={test_session_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            pack_result = response.json()
            print(f"✅ Pack fetch successful with known session ID")
            print(f"📊 Pack size: {len(pack_result.get('pack', []))}")
            print(f"📊 Status: {pack_result.get('status')}")
            print(f"📊 Session ID: {pack_result.get('session_id')}")
            
            # Show first question
            pack = pack_result.get('pack', [])
            if pack:
                first_q = pack[0]
                print(f"📊 First question: {first_q.get('why', 'N/A')[:80]}...")
                
        elif response.status_code == 404:
            print(f"❌ Pack fetch failed: 404 Not Found")
            print(f"📊 Response: {response.text}")
        else:
            print(f"❌ Pack fetch failed: {response.status_code}")
            print(f"📊 Response: {response.text}")
    except Exception as e:
        print(f"❌ Pack fetch error: {e}")
    
    # Step 3: Test with another session ID that had 404
    print(f"\n📦 Step 3: Test pack fetch with session ID that had 404")
    
    test_session_id_404 = "ac23d01f-e829-4191-bb18-8e72d3ce345d"
    
    try:
        response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={test_session_id_404}", headers=headers, timeout=10)
        if response.status_code == 200:
            pack_result = response.json()
            print(f"✅ Pack fetch successful (unexpected)")
            print(f"📊 Pack size: {len(pack_result.get('pack', []))}")
        elif response.status_code == 404:
            print(f"❌ Pack fetch failed: 404 Not Found (as expected)")
            print(f"📊 Response: {response.text}")
        else:
            print(f"❌ Pack fetch failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Pack fetch error: {e}")

if __name__ == "__main__":
    test_existing_sessions()