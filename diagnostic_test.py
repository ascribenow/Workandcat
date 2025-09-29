#!/usr/bin/env python3
"""
Test both API bases mentioned in the review request
"""

import requests
import json
import uuid
import time

def test_api_base(base_url, name):
    """Test a specific API base"""
    print(f"\n🎯 TESTING {name}: {base_url}")
    print("=" * 80)
    
    results = {
        "auth": False,
        "plan_next": False,
        "fetch_pack": False,
        "mark_served": False
    }
    
    # 1. Authentication
    print("\n1. 🔐 AUTHENTICATION")
    try:
        auth_response = requests.post(
            f"{base_url}/auth/login",
            json={"email": "sp@theskinmantra.com", "password": "student123"},
            timeout=15,
            verify=False
        )
        
        print(f"   Request URL: {base_url}/auth/login")
        print(f"   Status Code: {auth_response.status_code}")
        print(f"   Headers: {dict(auth_response.headers)}")
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            token = auth_data.get('access_token')
            user_id = auth_data.get('user', {}).get('id')
            adaptive_enabled = auth_data.get('user', {}).get('adaptive_enabled')
            
            results["auth"] = True
            print(f"   ✅ Authentication successful")
            print(f"   📊 JWT Token: {len(token)} characters")
            print(f"   📊 User ID: {user_id[:8]}...")
            print(f"   📊 Adaptive enabled: {adaptive_enabled}")
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Generate session IDs
            session_id = f"session_{uuid.uuid4()}"
            last_session_id = f"session_{uuid.uuid4()}"
            
            # 2. Plan-Next Endpoint
            print("\n2. 🔄 PLAN-NEXT ENDPOINT")
            plan_data = {
                "user_id": user_id,
                "last_session_id": last_session_id,
                "next_session_id": session_id
            }
            
            plan_headers = headers.copy()
            idempotency_key = f"{user_id}:{last_session_id}:{session_id}"
            plan_headers['Idempotency-Key'] = idempotency_key
            
            print(f"   Request URL: {base_url}/adapt/plan-next")
            print(f"   Idempotency-Key: {idempotency_key}")
            
            try:
                start_time = time.time()
                plan_response = requests.post(
                    f"{base_url}/adapt/plan-next",
                    json=plan_data,
                    headers=plan_headers,
                    timeout=45,
                    verify=False
                )
                response_time = time.time() - start_time
                
                print(f"   Status Code: {plan_response.status_code}")
                print(f"   Response Time: {response_time:.2f}s")
                print(f"   Headers: {dict(plan_response.headers)}")
                
                if plan_response.status_code == 200:
                    plan_json = plan_response.json()
                    results["plan_next"] = True
                    print(f"   ✅ Plan-next successful")
                    print(f"   📊 Response status: {plan_json.get('status')}")
                    print(f"   📊 Response keys: {list(plan_json.keys())}")
                    
                    # Check for expected structure
                    if 'pack' in plan_json:
                        pack = plan_json.get('pack', [])
                        print(f"   📊 Pack in response: {len(pack)} questions")
                    if 'constraint_report' in plan_json:
                        print(f"   📊 Constraint report present")
                        
                else:
                    print(f"   ❌ Plan-next failed: {plan_response.status_code}")
                    print(f"   📊 Response body: {plan_response.text[:300]}")
                    
            except Exception as e:
                print(f"   ❌ Plan-next error: {e}")
            
            # 3. Fetch Pack Endpoint
            print("\n3. 📦 FETCH PACK ENDPOINT")
            pack_url = f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}"
            print(f"   Request URL: {pack_url}")
            
            try:
                start_time = time.time()
                pack_response = requests.get(
                    pack_url,
                    headers=headers,
                    timeout=15,
                    verify=False
                )
                response_time = time.time() - start_time
                
                print(f"   Status Code: {pack_response.status_code}")
                print(f"   Response Time: {response_time:.2f}s")
                print(f"   Headers: {dict(pack_response.headers)}")
                
                if pack_response.status_code == 200:
                    pack_json = pack_response.json()
                    results["fetch_pack"] = True
                    print(f"   ✅ Fetch pack successful")
                    
                    # Check pack structure
                    pack_data = pack_json.get('pack') or pack_json.get('pack_json', [])
                    count = pack_json.get('count', 0)
                    
                    print(f"   📊 Pack size: {len(pack_data) if isinstance(pack_data, list) else 'N/A'}")
                    print(f"   📊 Count field: {count}")
                    print(f"   📊 Response keys: {list(pack_json.keys())}")
                    
                    if isinstance(pack_data, list) and len(pack_data) == 12:
                        print(f"   ✅ Pack has exactly 12 questions as expected")
                    
                else:
                    print(f"   ❌ Fetch pack failed: {pack_response.status_code}")
                    print(f"   📊 Response body: {pack_response.text[:300]}")
                    
                    # Log specific error types
                    if pack_response.status_code == 404:
                        print(f"   📊 404 Not Planned (pack not available)")
                        
            except Exception as e:
                print(f"   ❌ Fetch pack error: {e}")
            
            # 4. Mark Served Endpoint
            print("\n4. ✅ MARK SERVED ENDPOINT")
            mark_data = {"user_id": user_id, "session_id": session_id}
            print(f"   Request URL: {base_url}/adapt/mark-served")
            print(f"   Request Body: {mark_data}")
            
            try:
                start_time = time.time()
                served_response = requests.post(
                    f"{base_url}/adapt/mark-served",
                    json=mark_data,
                    headers=headers,
                    timeout=15,
                    verify=False
                )
                response_time = time.time() - start_time
                
                print(f"   Status Code: {served_response.status_code}")
                print(f"   Response Time: {response_time:.2f}s")
                print(f"   Headers: {dict(served_response.headers)}")
                
                if served_response.status_code == 200:
                    served_json = served_response.json()
                    results["mark_served"] = True
                    print(f"   ✅ Mark served successful")
                    print(f"   📊 Response: {served_json}")
                    
                    # Check expected response structure
                    if served_json.get('ok') or served_json.get('status') == 'ok':
                        print(f"   ✅ Valid response structure")
                        
                else:
                    print(f"   ❌ Mark served failed: {served_response.status_code}")
                    print(f"   📊 Response body: {served_response.text[:300]}")
                    
                    # Log specific error types as requested
                    if served_response.status_code == 404:
                        print(f"   📊 404 Not Planned Error")
                    elif served_response.status_code == 403:
                        print(f"   📊 403 Adaptive Disabled Error")
                    elif served_response.status_code == 401:
                        print(f"   📊 401 Auth Issues Error")
                    elif served_response.status_code == 409:
                        print(f"   📊 409 Constraint Violations Error")
                        
            except Exception as e:
                print(f"   ❌ Mark served error: {e}")
                
        else:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            print(f"   📊 Response: {auth_response.text[:300]}")
            
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
    
    return results

def main():
    """Test both API bases"""
    print("🎯 STEP 4 FROM DIAGNOSTIC RUNBOOK: Black-box test the three adaptive endpoints")
    print("Authentication: sp@theskinmantra.com/student123")
    print("Testing both API bases mentioned in review request")
    
    # Test both API bases
    api_bases = [
        ("https://adaptive-insights-1.preview.emergentagent.com/api", "PRIMARY API BASE"),
        ("https://adaptive-quant.emergent.host/api", "SECONDARY API BASE")
    ]
    
    all_results = {}
    
    for base_url, name in api_bases:
        results = test_api_base(base_url, name)
        all_results[base_url] = results
        
        # Summary for this API base
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY FOR {name}")
        print(f"{'='*80}")
        
        success_count = sum(results.values())
        total_tests = len(results)
        success_rate = (success_count / total_tests) * 100
        
        for test, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test.replace('_', ' ').title():<20} {status}")
        
        print(f"\nOverall Success Rate: {success_count}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print(f"🎉 ADAPTIVE ENDPOINTS FUNCTIONAL")
        else:
            print(f"❌ ADAPTIVE ENDPOINTS ISSUES DETECTED")
    
    # Final summary
    print(f"\n{'='*100}")
    print(f"🎯 FINAL DIAGNOSTIC SUMMARY")
    print(f"{'='*100}")
    
    for base_url, results in all_results.items():
        success_count = sum(results.values())
        total_tests = len(results)
        success_rate = (success_count / total_tests) * 100
        
        print(f"\n{base_url}:")
        print(f"  Success Rate: {success_count}/{total_tests} ({success_rate:.1f}%)")
        
        for test, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {test}: {status}")

if __name__ == "__main__":
    main()