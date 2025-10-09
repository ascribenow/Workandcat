#!/usr/bin/env python3
"""
Quick test for the specific 404 endpoints mentioned in the review request
"""
import requests
import json

def test_endpoints():
    # API base from frontend .env (empty) - let's use the one from review request
    base_url = "https://mcq-platform-1.preview.emergentagent.com/api"
    
    print("🚨 QUICK ENDPOINT TEST FOR 404 ERRORS")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    
    # First authenticate
    print("\n1. Testing Authentication...")
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    try:
        auth_response = requests.post(f"{base_url}/auth/login", json=auth_data, timeout=30, verify=False)
        print(f"   Auth Status: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            auth_result = auth_response.json()
            token = auth_result.get('access_token')
            user_data = auth_result.get('user', {})
            user_id = user_data.get('id')
            adaptive_enabled = user_data.get('adaptive_enabled')
            
            print(f"   ✅ Authentication successful")
            print(f"   📊 User ID: {user_id[:8] if user_id else 'N/A'}...")
            print(f"   📊 Adaptive enabled: {adaptive_enabled}")
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Test the specific endpoints from review request
            print("\n2. Testing Problem Endpoints...")
            
            # Test GET /api/adapt/pack with review request parameters
            test_user_id = "2d2d43a9-c26a-4a69-b74d-ffde3d9c71e1"
            test_session_id = "7409bbc3-d8a3-4d9e-8337-f37685d60d58"
            
            print(f"\n   Testing GET /api/adapt/pack")
            print(f"   Parameters: user_id={test_user_id}, session_id={test_session_id}")
            
            try:
                pack_response = requests.get(
                    f"{base_url}/adapt/pack?user_id={test_user_id}&session_id={test_session_id}",
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                print(f"   Status: {pack_response.status_code}")
                if pack_response.status_code == 404:
                    print(f"   ❌ 404 NOT FOUND - as reported in review")
                elif pack_response.status_code == 403:
                    print(f"   ⚠️ 403 FORBIDDEN - authorization issue")
                elif pack_response.status_code == 200:
                    print(f"   ✅ 200 OK - endpoint working")
                    result = pack_response.json()
                    print(f"   📊 Response: {result}")
                else:
                    print(f"   ⚠️ {pack_response.status_code} - unexpected status")
                    print(f"   📊 Response: {pack_response.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test with current user ID
            print(f"\n   Testing GET /api/adapt/pack with current user")
            print(f"   Parameters: user_id={user_id}, session_id={test_session_id}")
            
            try:
                pack_response = requests.get(
                    f"{base_url}/adapt/pack?user_id={user_id}&session_id={test_session_id}",
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                print(f"   Status: {pack_response.status_code}")
                if pack_response.status_code == 404:
                    print(f"   ❌ 404 NOT FOUND - session not found")
                elif pack_response.status_code == 200:
                    print(f"   ✅ 200 OK - endpoint working")
                    result = pack_response.json()
                    print(f"   📊 Response: {result}")
                else:
                    print(f"   ⚠️ {pack_response.status_code}")
                    print(f"   📊 Response: {pack_response.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test GET /api/sessions/last-completed-id
            print(f"\n   Testing GET /api/sessions/last-completed-id")
            print(f"   Parameters: user_id={test_user_id}")
            
            try:
                last_session_response = requests.get(
                    f"{base_url}/sessions/last-completed-id?user_id={test_user_id}",
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                print(f"   Status: {last_session_response.status_code}")
                if last_session_response.status_code == 404:
                    print(f"   ❌ 404 NOT FOUND - as reported in review")
                    result = last_session_response.json()
                    print(f"   📊 Response: {result}")
                elif last_session_response.status_code == 200:
                    print(f"   ✅ 200 OK - endpoint working")
                    result = last_session_response.json()
                    print(f"   📊 Response: {result}")
                else:
                    print(f"   ⚠️ {last_session_response.status_code}")
                    print(f"   📊 Response: {last_session_response.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test with current user ID
            print(f"\n   Testing GET /api/sessions/last-completed-id with current user")
            print(f"   Parameters: user_id={user_id}")
            
            try:
                last_session_response = requests.get(
                    f"{base_url}/sessions/last-completed-id?user_id={user_id}",
                    headers=headers,
                    timeout=30,
                    verify=False
                )
                print(f"   Status: {last_session_response.status_code}")
                if last_session_response.status_code == 404:
                    print(f"   ❌ 404 NOT FOUND - no completed sessions")
                    result = last_session_response.json()
                    print(f"   📊 Response: {result}")
                elif last_session_response.status_code == 200:
                    print(f"   ✅ 200 OK - endpoint working")
                    result = last_session_response.json()
                    print(f"   📊 Response: {result}")
                else:
                    print(f"   ⚠️ {last_session_response.status_code}")
                    print(f"   📊 Response: {last_session_response.text}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test working endpoints for comparison
            print("\n3. Testing Known Working Endpoints...")
            
            working_endpoints = [
                ("GET", "/user/session-limit-status", {}),
                ("GET", "/sessions/current-status", {}),
                ("POST", "/sessions/start", {}),
                ("GET", "/dashboard/simple-taxonomy", {})
            ]
            
            for method, endpoint, data in working_endpoints:
                print(f"\n   Testing {method} {endpoint}")
                try:
                    if method == "GET":
                        response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=30, verify=False)
                    else:
                        response = requests.post(f"{base_url}{endpoint}", json=data, headers=headers, timeout=30, verify=False)
                    
                    print(f"   Status: {response.status_code}")
                    if response.status_code == 200:
                        print(f"   ✅ Working as expected")
                    else:
                        print(f"   ⚠️ Unexpected status")
                        print(f"   📊 Response: {response.text[:200]}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        else:
            print(f"   ❌ Authentication failed: {auth_response.status_code}")
            print(f"   📊 Response: {auth_response.text}")
    
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")

if __name__ == "__main__":
    test_endpoints()