#!/usr/bin/env python3

import requests
import json
import time
import uuid

def test_llm_planner_fix_simple():
    """Simple test for LLM planner fix verification"""
    print("🚨 CRITICAL LLM PLANNER FIX VERIFICATION - SIMPLE TEST")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:8001/api"
    
    # Test 1: Authentication
    print("\n🔐 Testing Authentication...")
    auth_data = {"email": "sp@theskinmantra.com", "password": "student123"}
    
    try:
        auth_response = requests.post(f"{base_url}/auth/login", json=auth_data, timeout=10)
        print(f"Auth Status: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            token = auth_data.get('access_token')
            user_id = auth_data.get('user', {}).get('id')
            print(f"✅ Authentication successful")
            print(f"📊 User ID: {user_id}")
            
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            
            # Test 2: Plan-Next Performance
            print(f"\n🚀 Testing Plan-Next Performance...")
            session_id = f"test_{uuid.uuid4()}"
            plan_data = {
                "user_id": user_id,
                "last_session_id": "S0",
                "next_session_id": session_id
            }
            
            test_headers = headers.copy()
            test_headers['Idempotency-Key'] = f"{user_id}:S0:{session_id}"
            
            start_time = time.time()
            plan_response = requests.post(f"{base_url}/adapt/plan-next", json=plan_data, headers=test_headers, timeout=45)
            response_time = time.time() - start_time
            
            print(f"Plan-Next Status: {plan_response.status_code}")
            print(f"Response Time: {response_time:.2f}s")
            
            if plan_response.status_code == 200:
                response_data = plan_response.json()
                print(f"✅ Plan-next successful")
                
                # Check constraint_report
                if response_data.get('constraint_report'):
                    print(f"✅ constraint_report present")
                    print(f"📊 constraint_report keys: {list(response_data['constraint_report'].keys())}")
                else:
                    print(f"❌ constraint_report missing")
                
                # Check status
                if response_data.get('status') == 'planned':
                    print(f"✅ Session planning successful")
                else:
                    print(f"⚠️ Session status: {response_data.get('status')}")
                
                # Performance assessment
                if response_time <= 30:
                    print(f"✅ Performance good (≤30s)")
                    if response_time <= 10:
                        print(f"✅ Excellent performance (≤10s)")
                else:
                    print(f"⚠️ Performance slow (>30s)")
                
                # Test 3: Pack Fetch
                print(f"\n📦 Testing Pack Fetch...")
                pack_response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}", headers=headers, timeout=10)
                print(f"Pack Fetch Status: {pack_response.status_code}")
                
                if pack_response.status_code == 200:
                    pack_data = pack_response.json()
                    pack = pack_data.get('pack', [])
                    print(f"✅ Pack fetch successful")
                    print(f"📊 Pack size: {len(pack)} questions")
                    
                    if len(pack) == 12:
                        print(f"✅ Pack contains 12 questions")
                        
                        # Test 4: Mark Served
                        print(f"\n✅ Testing Mark Served...")
                        mark_data = {"user_id": user_id, "session_id": session_id}
                        mark_response = requests.post(f"{base_url}/adapt/mark-served", json=mark_data, headers=headers, timeout=10)
                        print(f"Mark Served Status: {mark_response.status_code}")
                        
                        if mark_response.status_code == 200:
                            print(f"✅ Mark served successful")
                            print(f"✅ Complete end-to-end flow working")
                        else:
                            print(f"❌ Mark served failed")
                    else:
                        print(f"⚠️ Pack size incorrect: {len(pack)}")
                else:
                    print(f"❌ Pack fetch failed")
            else:
                print(f"❌ Plan-next failed: {plan_response.text}")
        else:
            print(f"❌ Authentication failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n" + "=" * 60)
    print("🎯 SUMMARY: Check the results above for LLM planner fix verification")

if __name__ == "__main__":
    test_llm_planner_fix_simple()