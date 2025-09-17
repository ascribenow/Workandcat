#!/usr/bin/env python3
"""
Quick Plan-Next Flow Test with shorter timeout
"""

import requests
import json
import uuid
import time

def test_quick_flow():
    base_url = "https://learning-tutor.preview.emergentagent.com/api"
    
    # Step 1: Authenticate
    print("🔐 Step 1: Authentication")
    login_data = {"email": "sp@theskinmantra.com", "password": "student123"}
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
        if response.status_code == 200:
            data = response.json()
            token = data['access_token']
            user_id = data['user']['id']
            print(f"✅ Authentication successful")
            print(f"📊 User ID: {user_id}")
            print(f"📊 Adaptive enabled: {data['user']['adaptive_enabled']}")
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
    
    # Step 2: Test plan-next with shorter timeout
    print("\n🚀 Step 2: Plan-Next (30s timeout)")
    session_id = f"session_{uuid.uuid4()}"
    plan_data = {
        "user_id": user_id,
        "last_session_id": "S0",
        "next_session_id": session_id
    }
    
    headers_with_idem = headers.copy()
    headers_with_idem['Idempotency-Key'] = f"{user_id}:S0:{session_id}"
    
    print(f"📋 Session ID: {session_id}")
    
    try:
        response = requests.post(f"{base_url}/adapt/plan-next", json=plan_data, headers=headers_with_idem, timeout=30)
        if response.status_code == 200:
            plan_result = response.json()
            print(f"✅ Plan-next successful")
            print(f"📊 Status: {plan_result.get('status')}")
            print(f"📊 Response: {plan_result}")
        else:
            print(f"❌ Plan-next failed: {response.status_code}")
            print(f"📊 Response: {response.text}")
            return
    except requests.exceptions.Timeout:
        print(f"⏰ Plan-next timed out after 30 seconds")
        print(f"🔍 This indicates the LLM planner is taking too long")
        return
    except Exception as e:
        print(f"❌ Plan-next error: {e}")
        return
    
    # Step 3: Test pack fetch immediately
    print(f"\n📦 Step 3: Pack Fetch (immediate)")
    try:
        response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            pack_result = response.json()
            print(f"✅ Pack fetch successful")
            print(f"📊 Pack size: {len(pack_result.get('pack', []))}")
            print(f"📊 Status: {pack_result.get('status')}")
        elif response.status_code == 404:
            print(f"❌ Pack fetch failed: 404 Not Found")
            print(f"🚨 ROOT CAUSE CONFIRMED: Plan-next succeeds but pack is not retrievable")
            print(f"📊 Response: {response.text}")
        else:
            print(f"❌ Pack fetch failed: {response.status_code}")
            print(f"📊 Response: {response.text}")
    except Exception as e:
        print(f"❌ Pack fetch error: {e}")
    
    # Step 4: Wait and try pack fetch again
    print(f"\n⏳ Step 4: Pack Fetch (after 5s delay)")
    time.sleep(5)
    try:
        response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            pack_result = response.json()
            print(f"✅ Pack fetch successful after delay")
            print(f"📊 Pack size: {len(pack_result.get('pack', []))}")
            print(f"📊 Status: {pack_result.get('status')}")
        elif response.status_code == 404:
            print(f"❌ Pack fetch still fails: 404 Not Found")
            print(f"🔍 This confirms a persistent database/persistence issue")
        else:
            print(f"❌ Pack fetch failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Pack fetch error: {e}")

if __name__ == "__main__":
    test_quick_flow()