#!/usr/bin/env python3
"""
Direct pack fetch test with known session IDs
"""

import requests
import json

def test_pack_fetch_direct():
    base_url = "https://learning-tutor.preview.emergentagent.com/api"
    
    # Step 1: Authenticate (with longer timeout)
    print("🔐 Step 1: Authentication")
    login_data = {"email": "sp@theskinmantra.com", "password": "student123"}
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=15)
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
    
    # Step 2: Test pack fetch with known session IDs from database
    print(f"\n📦 Step 2: Test pack fetch with known session IDs")
    
    # These session IDs are confirmed to exist in the database with 12-question packs
    test_sessions = [
        "7409bbc3-d8a3-4d9e-8337-f37685d60d58",  # Seq 44, Status planned
        "ac23d01f-e829-4191-bb18-8e72d3ce345d"   # Seq 45, Status planned
    ]
    
    for i, session_id in enumerate(test_sessions, 1):
        print(f"\n   🔍 Test {i}: Session {session_id}")
        
        try:
            response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}", headers=headers, timeout=10)
            
            print(f"   📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                pack_result = response.json()
                print(f"   ✅ Pack fetch successful")
                print(f"   📊 Pack size: {len(pack_result.get('pack', []))}")
                print(f"   📊 Status: {pack_result.get('status')}")
                print(f"   📊 User ID: {pack_result.get('user_id')}")
                print(f"   📊 Session ID: {pack_result.get('session_id')}")
                
                # Show first question
                pack = pack_result.get('pack', [])
                if pack:
                    first_q = pack[0]
                    print(f"   📊 First question: {first_q.get('why', 'N/A')[:60]}...")
                    
            elif response.status_code == 404:
                print(f"   ❌ Pack fetch failed: 404 Not Found")
                try:
                    error_data = response.json()
                    print(f"   📊 Error response: {error_data}")
                except:
                    print(f"   📊 Error text: {response.text}")
                    
            elif response.status_code == 403:
                print(f"   ❌ Pack fetch failed: 403 Forbidden")
                print(f"   🔍 This suggests an authentication/authorization issue")
                try:
                    error_data = response.json()
                    print(f"   📊 Error response: {error_data}")
                except:
                    print(f"   📊 Error text: {response.text}")
                    
            else:
                print(f"   ❌ Pack fetch failed: {response.status_code}")
                print(f"   📊 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Pack fetch error: {e}")
    
    # Step 3: Test with a non-existent session ID
    print(f"\n📦 Step 3: Test with non-existent session ID (control test)")
    fake_session_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={fake_session_id}", headers=headers, timeout=10)
        print(f"   📊 Response status: {response.status_code}")
        
        if response.status_code == 404:
            print(f"   ✅ Expected 404 for non-existent session")
        else:
            print(f"   ⚠️ Unexpected response for non-existent session")
            
    except Exception as e:
        print(f"   ❌ Control test error: {e}")

if __name__ == "__main__":
    test_pack_fetch_direct()