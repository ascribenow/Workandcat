#!/usr/bin/env python3
"""
🎯 STEP 4 FROM DIAGNOSTIC RUNBOOK: Black-box test the three adaptive endpoints with proper authentication.

SPECIFIC TESTS NEEDED:
1. **Authentication**: Login with sp@theskinmantra.com/student123 to get valid JWT token
2. **Plan-Next Endpoint**: Test POST /api/adapt/plan-next with proper Idempotency-Key
3. **Fetch Pack Endpoint**: Test GET /api/adapt/pack  
4. **Mark Served Endpoint**: Test POST /api/adapt/mark-served

For each endpoint, capture:
- Request URL (confirm which API base it's hitting)
- Response status code (200/400/401/403/404/409)  
- Response body (especially pack structure and count)
- Headers (CORS, Content-Type, etc.)

AUTHENTICATION CREDENTIALS: sp@theskinmantra.com/student123
API BASE: Test both https://learning-tutor.preview.emergentagent.com and https://adaptive-quant.emergent.host

EXPECTED RESPONSES:
- plan-next: { status:"ok", reused: false|true, pack:[…12…] }
- pack: { pack_json:[…12…], count:12, … }  
- mark-served: { status:"ok" }

LOG ALL HTTP ERRORS: 404 not planned, 403 adaptive disabled, 401 auth issues, 409 constraint violations
"""

import requests
import json
import uuid
import time
from datetime import datetime

def test_adaptive_endpoints(base_url):
    """Test the three adaptive endpoints with proper authentication"""
    print(f"\n{'='*80}")
    print(f"🎯 TESTING ADAPTIVE ENDPOINTS: {base_url}")
    print(f"{'='*80}")
    
    results = {
        "api_base": base_url,
        "authentication": {"success": False, "details": {}},
        "plan_next": {"success": False, "details": {}},
        "fetch_pack": {"success": False, "details": {}},
        "mark_served": {"success": False, "details": {}}
    }
    
    # PHASE 1: AUTHENTICATION
    print("\n🔐 PHASE 1: AUTHENTICATION")
    print("-" * 60)
    
    auth_url = f"{base_url}/auth/login"
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    print(f"📋 Request URL: {auth_url}")
    print(f"📋 Credentials: {auth_data['email']}/{'*' * len(auth_data['password'])}")
    
    try:
        auth_response = requests.post(
            auth_url, 
            json=auth_data, 
            headers={'Content-Type': 'application/json'},
            timeout=30,
            verify=False
        )
        
        print(f"📊 Status Code: {auth_response.status_code}")
        print(f"📊 Headers: {dict(auth_response.headers)}")
        
        if auth_response.status_code == 200:
            auth_json = auth_response.json()
            token = auth_json.get('access_token')
            user_data = auth_json.get('user', {})
            user_id = user_data.get('id')
            adaptive_enabled = user_data.get('adaptive_enabled', False)
            
            results["authentication"]["success"] = True
            results["authentication"]["details"] = {
                "status_code": auth_response.status_code,
                "token_length": len(token) if token else 0,
                "user_id": user_id[:8] + "..." if user_id else None,
                "adaptive_enabled": adaptive_enabled,
                "response_body": auth_json
            }
            
            print(f"✅ Authentication successful")
            print(f"📊 JWT Token length: {len(token)} characters")
            print(f"📊 User ID: {user_id[:8]}...")
            print(f"📊 Adaptive enabled: {adaptive_enabled}")
            
            if not adaptive_enabled:
                print("⚠️ User does not have adaptive enabled - tests may fail")
            
        else:
            results["authentication"]["details"] = {
                "status_code": auth_response.status_code,
                "response_body": auth_response.text
            }
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(f"📊 Response: {auth_response.text}")
            return results
            
    except Exception as e:
        results["authentication"]["details"] = {"error": str(e)}
        print(f"❌ Authentication error: {e}")
        return results
    
    # Setup headers for authenticated requests
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Generate session IDs for testing
    session_id = f"session_{uuid.uuid4()}"
    last_session_id = f"session_{uuid.uuid4()}"
    
    # PHASE 2: PLAN-NEXT ENDPOINT
    print("\n🔄 PHASE 2: PLAN-NEXT ENDPOINT")
    print("-" * 60)
    
    plan_next_url = f"{base_url}/adapt/plan-next"
    plan_data = {
        "user_id": user_id,
        "last_session_id": last_session_id,
        "next_session_id": session_id
    }
    
    # Add Idempotency-Key header
    idempotency_key = f"{user_id}:{last_session_id}:{session_id}"
    plan_headers = headers.copy()
    plan_headers['Idempotency-Key'] = idempotency_key
    
    print(f"📋 Request URL: {plan_next_url}")
    print(f"📋 Idempotency-Key: {idempotency_key}")
    print(f"📋 Request Body: {plan_data}")
    
    try:
        start_time = time.time()
        plan_response = requests.post(
            plan_next_url,
            json=plan_data,
            headers=plan_headers,
            timeout=60,
            verify=False
        )
        response_time = time.time() - start_time
        
        print(f"📊 Status Code: {plan_response.status_code}")
        print(f"📊 Response Time: {response_time:.2f}s")
        print(f"📊 Headers: {dict(plan_response.headers)}")
        
        if plan_response.status_code == 200:
            plan_json = plan_response.json()
            results["plan_next"]["success"] = True
            results["plan_next"]["details"] = {
                "status_code": plan_response.status_code,
                "response_time": response_time,
                "response_body": plan_json
            }
            
            print(f"✅ Plan-next successful")
            print(f"📊 Response: {json.dumps(plan_json, indent=2)}")
            
            # Check expected response structure
            if plan_json.get('status') in ['ok', 'planned']:
                print(f"✅ Valid status: {plan_json.get('status')}")
            if 'constraint_report' in plan_json:
                print(f"✅ Constraint report present")
            if 'pack' in plan_json:
                pack = plan_json.get('pack', [])
                print(f"✅ Pack present with {len(pack)} questions")
                
        else:
            results["plan_next"]["details"] = {
                "status_code": plan_response.status_code,
                "response_time": response_time,
                "response_body": plan_response.text
            }
            print(f"❌ Plan-next failed: {plan_response.status_code}")
            print(f"📊 Response: {plan_response.text}")
            
    except Exception as e:
        results["plan_next"]["details"] = {"error": str(e)}
        print(f"❌ Plan-next error: {e}")
    
    # PHASE 3: FETCH PACK ENDPOINT
    print("\n📦 PHASE 3: FETCH PACK ENDPOINT")
    print("-" * 60)
    
    fetch_pack_url = f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}"
    
    print(f"📋 Request URL: {fetch_pack_url}")
    
    try:
        start_time = time.time()
        pack_response = requests.get(
            fetch_pack_url,
            headers=headers,
            timeout=30,
            verify=False
        )
        response_time = time.time() - start_time
        
        print(f"📊 Status Code: {pack_response.status_code}")
        print(f"📊 Response Time: {response_time:.2f}s")
        print(f"📊 Headers: {dict(pack_response.headers)}")
        
        if pack_response.status_code == 200:
            pack_json = pack_response.json()
            results["fetch_pack"]["success"] = True
            results["fetch_pack"]["details"] = {
                "status_code": pack_response.status_code,
                "response_time": response_time,
                "response_body": pack_json
            }
            
            print(f"✅ Fetch pack successful")
            print(f"📊 Response: {json.dumps(pack_json, indent=2)}")
            
            # Check expected response structure
            pack_data = pack_json.get('pack') or pack_json.get('pack_json', [])
            if isinstance(pack_data, list):
                print(f"✅ Pack contains {len(pack_data)} questions")
                if len(pack_data) == 12:
                    print(f"✅ Pack has exactly 12 questions as expected")
                else:
                    print(f"⚠️ Pack has {len(pack_data)} questions (expected 12)")
            
            if pack_json.get('count'):
                print(f"✅ Count field: {pack_json.get('count')}")
                
        else:
            results["fetch_pack"]["details"] = {
                "status_code": pack_response.status_code,
                "response_time": response_time,
                "response_body": pack_response.text
            }
            print(f"❌ Fetch pack failed: {pack_response.status_code}")
            print(f"📊 Response: {pack_response.text}")
            
    except Exception as e:
        results["fetch_pack"]["details"] = {"error": str(e)}
        print(f"❌ Fetch pack error: {e}")
    
    # PHASE 4: MARK SERVED ENDPOINT
    print("\n✅ PHASE 4: MARK SERVED ENDPOINT")
    print("-" * 60)
    
    mark_served_url = f"{base_url}/adapt/mark-served"
    mark_data = {
        "user_id": user_id,
        "session_id": session_id
    }
    
    print(f"📋 Request URL: {mark_served_url}")
    print(f"📋 Request Body: {mark_data}")
    
    try:
        start_time = time.time()
        served_response = requests.post(
            mark_served_url,
            json=mark_data,
            headers=headers,
            timeout=30,
            verify=False
        )
        response_time = time.time() - start_time
        
        print(f"📊 Status Code: {served_response.status_code}")
        print(f"📊 Response Time: {response_time:.2f}s")
        print(f"📊 Headers: {dict(served_response.headers)}")
        
        if served_response.status_code == 200:
            served_json = served_response.json()
            results["mark_served"]["success"] = True
            results["mark_served"]["details"] = {
                "status_code": served_response.status_code,
                "response_time": response_time,
                "response_body": served_json
            }
            
            print(f"✅ Mark served successful")
            print(f"📊 Response: {json.dumps(served_json, indent=2)}")
            
            # Check expected response structure
            if served_json.get('ok') or served_json.get('status') == 'ok':
                print(f"✅ Valid response: {served_json}")
                
        else:
            results["mark_served"]["details"] = {
                "status_code": served_response.status_code,
                "response_time": response_time,
                "response_body": served_response.text
            }
            print(f"❌ Mark served failed: {served_response.status_code}")
            print(f"📊 Response: {served_response.text}")
            
            # Log specific error types as requested
            if served_response.status_code == 404:
                print(f"📊 404 Not Planned Error (as expected)")
            elif served_response.status_code == 403:
                print(f"📊 403 Adaptive Disabled Error")
            elif served_response.status_code == 401:
                print(f"📊 401 Auth Issues Error")
            elif served_response.status_code == 409:
                print(f"📊 409 Constraint Violations Error")
            
    except Exception as e:
        results["mark_served"]["details"] = {"error": str(e)}
        print(f"❌ Mark served error: {e}")
    
    return results

def main():
    """Main function to test both API bases"""
    print("🎯 STEP 4 FROM DIAGNOSTIC RUNBOOK: Black-box test the three adaptive endpoints")
    print("=" * 100)
    
    # Test both API bases mentioned in the review request
    api_bases = [
        "https://learning-tutor.preview.emergentagent.com/api",
        "https://adaptive-quant.emergent.host/api"
    ]
    
    all_results = {}
    
    for base_url in api_bases:
        results = test_adaptive_endpoints(base_url)
        all_results[base_url] = results
        
        # Summary for this API base
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY FOR: {base_url}")
        print(f"{'='*80}")
        
        auth_success = results["authentication"]["success"]
        plan_success = results["plan_next"]["success"]
        pack_success = results["fetch_pack"]["success"]
        served_success = results["mark_served"]["success"]
        
        print(f"Authentication: {'✅ PASS' if auth_success else '❌ FAIL'}")
        print(f"Plan-Next Endpoint: {'✅ PASS' if plan_success else '❌ FAIL'}")
        print(f"Fetch Pack Endpoint: {'✅ PASS' if pack_success else '❌ FAIL'}")
        print(f"Mark Served Endpoint: {'✅ PASS' if served_success else '❌ FAIL'}")
        
        total_success = sum([auth_success, plan_success, pack_success, served_success])
        success_rate = (total_success / 4) * 100
        
        print(f"Overall Success Rate: {total_success}/4 ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print(f"🎉 ADAPTIVE ENDPOINTS FUNCTIONAL for {base_url}")
        else:
            print(f"❌ ADAPTIVE ENDPOINTS ISSUES DETECTED for {base_url}")
    
    # Final comprehensive summary
    print(f"\n{'='*100}")
    print(f"🎯 FINAL COMPREHENSIVE SUMMARY")
    print(f"{'='*100}")
    
    for base_url, results in all_results.items():
        print(f"\n{base_url}:")
        for endpoint, data in results.items():
            if endpoint != "api_base":
                status = "✅ PASS" if data["success"] else "❌ FAIL"
                print(f"  {endpoint.replace('_', ' ').title():<20} {status}")
    
    print(f"\n🔍 DETAILED RESULTS:")
    print(json.dumps(all_results, indent=2, default=str))

if __name__ == "__main__":
    main()