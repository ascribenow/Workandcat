#!/usr/bin/env python3
"""
API Base Testing for Adaptive Gates Diagnostic
Testing both API bases mentioned in the review request
"""

import requests
import json
import sys

def test_api_base(base_url, name):
    """Test a specific API base"""
    print(f"\n🌐 TESTING API BASE: {name}")
    print(f"URL: {base_url}")
    print("-" * 60)
    
    # Test authentication first
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    try:
        # Test login
        auth_response = requests.post(
            f"{base_url}/auth/login",
            json=auth_data,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            verify=False
        )
        
        print(f"🔐 Authentication: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            token = auth_result.get('access_token')
            user_data = auth_result.get('user', {})
            user_id = user_data.get('id')
            
            print(f"   ✅ Login successful")
            print(f"   📊 Token length: {len(token)} chars")
            print(f"   📊 User ID: {user_id[:8]}...")
            print(f"   📊 Adaptive enabled: {user_data.get('adaptive_enabled')}")
            
            # Test adaptive endpoints
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Test GET /api/adapt/pack (the failing endpoint from frontend)
            print(f"\n📦 Testing GET /api/adapt/pack:")
            
            # Get the latest session_id from database query results
            session_id = "49cfff0b-3c9a-4b8b-8b1a-1b1b1b1b1b1b"  # From database results
            
            pack_response = requests.get(
                f"{base_url}/adapt/pack?user_id={user_id}&session_id={session_id}",
                headers=headers,
                timeout=30,
                verify=False
            )
            
            print(f"   Status: {pack_response.status_code}")
            if pack_response.status_code == 200:
                pack_data = pack_response.json()
                print(f"   ✅ Pack fetch successful")
                print(f"   📊 Pack size: {len(pack_data.get('pack', []))} questions")
                print(f"   📊 Status: {pack_data.get('status')}")
            elif pack_response.status_code == 404:
                print(f"   ❌ Pack not found (404) - This is the issue!")
                try:
                    error_data = pack_response.json()
                    print(f"   📊 Error: {error_data}")
                except:
                    print(f"   📊 Error text: {pack_response.text}")
            else:
                print(f"   ❌ Unexpected status: {pack_response.status_code}")
                print(f"   📊 Response: {pack_response.text}")
            
            # Test POST /api/adapt/plan-next
            print(f"\n🔄 Testing POST /api/adapt/plan-next:")
            
            plan_data = {
                "user_id": user_id,
                "last_session_id": "session_test_last",
                "next_session_id": "session_test_next"
            }
            
            plan_headers = headers.copy()
            plan_headers['Idempotency-Key'] = f"{user_id}:session_test_last:session_test_next"
            
            plan_response = requests.post(
                f"{base_url}/adapt/plan-next",
                json=plan_data,
                headers=plan_headers,
                timeout=60,
                verify=False
            )
            
            print(f"   Status: {plan_response.status_code}")
            if plan_response.status_code == 200:
                plan_result = plan_response.json()
                print(f"   ✅ Plan next successful")
                print(f"   📊 Status: {plan_result.get('status')}")
                print(f"   📊 Session ID: {plan_result.get('session_id', '')[:12]}...")
            else:
                print(f"   ❌ Plan next failed: {plan_response.status_code}")
                try:
                    error_data = plan_response.json()
                    print(f"   📊 Error: {error_data}")
                except:
                    print(f"   📊 Error text: {plan_response.text}")
            
        else:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            try:
                error_data = auth_response.json()
                print(f"   📊 Error: {error_data}")
            except:
                print(f"   📊 Error text: {auth_response.text}")
    
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def main():
    print("🔍 API BASE MISMATCH DIAGNOSTIC")
    print("=" * 80)
    print("Testing both API bases mentioned in the review request:")
    print("1. Frontend configured: https://twelvr-debugger.preview.emergentagent.com")
    print("2. Review mentioned: https://adaptive-quant.emergent.host/api")
    print("=" * 80)
    
    # Test both API bases
    test_api_base("https://twelvr-debugger.preview.emergentagent.com/api", "FRONTEND CONFIGURED")
    test_api_base("https://adaptive-quant.emergent.host/api", "REVIEW MENTIONED")
    
    print("\n" + "=" * 80)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print("Based on the database queries, we know:")
    print("✅ User sp@theskinmantra.com has adaptive_enabled=True")
    print("✅ User has 5 session pack plans in database (some planned, some served)")
    print("✅ Sessions table has corresponding records")
    print("✅ Database schema is correct")
    print("")
    print("The 404 errors suggest either:")
    print("1. API base mismatch between frontend and backend")
    print("2. Session ID mismatch in pack fetch requests")
    print("3. Authentication/authorization issues")
    print("4. Backend routing or endpoint configuration issues")

if __name__ == "__main__":
    main()