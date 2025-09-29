#!/usr/bin/env python3
"""
Quick test of the three adaptive endpoints as requested in the review
"""

import requests
import json
import uuid
import time

def quick_test():
    """Quick test of adaptive endpoints"""
    print("🎯 QUICK ADAPTIVE ENDPOINTS TEST")
    print("=" * 60)
    
    # Test with the primary API base
    base_url = "https://adaptive-insights-1.preview.emergentagent.com/api"
    
    # 1. Authentication
    print("\n1. 🔐 AUTHENTICATION TEST")
    auth_response = requests.post(
        f"{base_url}/auth/login",
        json={"email": "sp@theskinmantra.com", "password": "student123"},
        timeout=10,
        verify=False
    )
    
    print(f"   Status: {auth_response.status_code}")
    if auth_response.status_code == 200:
        auth_data = auth_response.json()
        token = auth_data.get('access_token')
        user_id = auth_data.get('user', {}).get('id')
        adaptive_enabled = auth_data.get('user', {}).get('adaptive_enabled')
        
        print(f"   ✅ Auth successful - Token: {len(token)} chars, Adaptive: {adaptive_enabled}")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Generate session IDs
        session_id = f"session_{uuid.uuid4()}"
        last_session_id = f"session_{uuid.uuid4()}"
        
        # 2. Plan-Next Endpoint
        print("\n2. 🔄 PLAN-NEXT ENDPOINT TEST")
        plan_data = {
            "user_id": user_id,
            "last_session_id": last_session_id,
            "next_session_id": session_id
        }
        
        plan_headers = headers.copy()
        plan_headers['Idempotency-Key'] = f"{user_id}:{last_session_id}:{session_id}"
        
        try:
            plan_response = requests.post(
                f"{base_url}/adapt/plan-next",
                json=plan_data,
                headers=plan_headers,
                timeout=30,
                verify=False
            )
            
            print(f"   Status: {plan_response.status_code}")
            if plan_response.status_code == 200:
                plan_json = plan_response.json()
                print(f"   ✅ Plan-next successful - Status: {plan_json.get('status')}")
                print(f"   📊 Response keys: {list(plan_json.keys())}")
            else:
                print(f"   ❌ Plan-next failed: {plan_response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Plan-next error: {e}")
        
        # 3. Fetch Pack Endpoint
        print("\n3. 📦 FETCH PACK ENDPOINT TEST")
        try:
            pack_response = requests.get(
                f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}",
                headers=headers,
                timeout=10,
                verify=False
            )
            
            print(f"   Status: {pack_response.status_code}")
            if pack_response.status_code == 200:
                pack_json = pack_response.json()
                pack_data = pack_json.get('pack', [])
                print(f"   ✅ Fetch pack successful - Pack size: {len(pack_data)}")
                print(f"   📊 Response keys: {list(pack_json.keys())}")
            else:
                print(f"   ❌ Fetch pack failed: {pack_response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Fetch pack error: {e}")
        
        # 4. Mark Served Endpoint
        print("\n4. ✅ MARK SERVED ENDPOINT TEST")
        try:
            served_response = requests.post(
                f"{base_url}/adapt/mark-served",
                json={"user_id": user_id, "session_id": session_id},
                headers=headers,
                timeout=10,
                verify=False
            )
            
            print(f"   Status: {served_response.status_code}")
            if served_response.status_code == 200:
                served_json = served_response.json()
                print(f"   ✅ Mark served successful")
                print(f"   📊 Response: {served_json}")
            else:
                print(f"   ❌ Mark served failed: {served_response.text[:200]}")
                if served_response.status_code == 409:
                    print(f"   📊 409 Conflict (expected for already served pack)")
                    
        except Exception as e:
            print(f"   ❌ Mark served error: {e}")
            
    else:
        print(f"   ❌ Auth failed: {auth_response.text}")
    
    print("\n" + "=" * 60)
    print("🎯 QUICK TEST COMPLETE")

if __name__ == "__main__":
    quick_test()