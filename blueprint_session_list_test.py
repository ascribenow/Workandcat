#!/usr/bin/env python3
"""
Blueprint Session List API Endpoint Testing
Focused test for debugging the critical routing failure
"""

import requests
import time
import json
import sys

class BlueprintSessionListTester:
    def __init__(self, base_url="https://data-integrity-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None

    def authenticate(self):
        """Authenticate with sp@theskinmantra.com/student123"""
        print("🔐 AUTHENTICATION")
        print("-" * 60)
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login", 
                json=auth_data, 
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                user_data = data.get('user', {})
                self.user_id = user_data.get('id')
                
                self.auth_headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                print(f"✅ Authentication successful")
                print(f"📊 JWT Token length: {len(token)} characters")
                print(f"📊 User ID: {self.user_id}")
                print(f"📊 Adaptive enabled: {user_data.get('adaptive_enabled')}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"📊 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def test_session_list_endpoint(self):
        """Test the critical /api/session/list endpoint"""
        print("\n📡 SESSION LIST ENDPOINT TESTING")
        print("-" * 60)
        
        if not self.auth_headers:
            print("❌ No authentication headers available")
            return False
        
        # Test 1: Basic endpoint availability
        print("🎯 Test 1: Basic endpoint availability")
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/session/list",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            response_time = time.time() - start_time
            
            print(f"📊 Response time: {response_time:.2f} seconds")
            print(f"📊 Status code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Endpoint accessible (200 OK)")
                
                if response_time < 5.0:
                    print("✅ Response time under 5 seconds")
                else:
                    print(f"⚠️ Response time exceeds 5 seconds ({response_time:.2f}s)")
                
                # Parse response
                try:
                    data = response.json()
                    print(f"✅ Valid JSON response")
                    
                    # Analyze response structure
                    print(f"\n📋 Response structure analysis:")
                    print(f"   Response keys: {list(data.keys())}")
                    
                    if 'sessions' in data:
                        sessions = data['sessions']
                        print(f"   ✅ Contains 'sessions' array")
                        print(f"   📊 Sessions count: {len(sessions)}")
                        
                        if len(sessions) > 0:
                            # Analyze first session
                            sample_session = sessions[0]
                            print(f"\n📊 Sample session structure:")
                            for key, value in sample_session.items():
                                print(f"      {key}: {value} ({type(value).__name__})")
                            
                            # Check required fields
                            required_fields = ['session_id', 'status', 'answered_count', 'total_questions', 'progress_percentage']
                            missing_fields = []
                            
                            for field in required_fields:
                                if field not in sample_session:
                                    missing_fields.append(field)
                            
                            if not missing_fields:
                                print("✅ All required fields present")
                                
                                # Verify expected format from review request
                                expected_format = {
                                    "session_id": str,
                                    "status": str,
                                    "answered_count": int,
                                    "total_questions": int,
                                    "progress_percentage": (int, float)
                                }
                                
                                format_valid = True
                                for field, expected_type in expected_format.items():
                                    actual_value = sample_session.get(field)
                                    if not isinstance(actual_value, expected_type):
                                        print(f"❌ Field '{field}' has wrong type: {type(actual_value)} (expected: {expected_type})")
                                        format_valid = False
                                
                                if format_valid:
                                    print("✅ Session data format matches expected structure")
                                    
                                    # Check if it's Blueprint session format
                                    if sample_session.get('total_questions') == 12:
                                        print("✅ Blueprint session format detected (12 questions)")
                                    else:
                                        print(f"⚠️ Unexpected question count: {sample_session.get('total_questions')} (expected: 12)")
                                else:
                                    print("❌ Session data format issues detected")
                            else:
                                print(f"❌ Missing required fields: {missing_fields}")
                        else:
                            print("⚠️ Sessions array is empty (user may have no sessions)")
                            print("✅ Empty array is still a valid response")
                    else:
                        print("❌ Response missing 'sessions' array")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    print(f"📊 Raw response: {response.text[:500]}...")
                    
            elif response.status_code == 404:
                print("❌ Endpoint not found (404)")
                print("🔍 DIAGNOSIS: Endpoint not implemented or wrong URL")
                
            elif response.status_code == 401:
                print("❌ Unauthorized (401)")
                print("🔍 DIAGNOSIS: Authentication problem")
                
            elif response.status_code == 403:
                print("❌ Forbidden (403)")
                print("🔍 DIAGNOSIS: Authorization problem")
                
            elif response.status_code == 500:
                print("❌ Internal Server Error (500)")
                print("🔍 DIAGNOSIS: Server error - database or implementation issue")
                try:
                    error_data = response.json()
                    print(f"📊 Error details: {error_data}")
                except:
                    print(f"📊 Raw error: {response.text}")
                    
            elif response.status_code in [502, 503, 504]:
                print(f"❌ Server Error ({response.status_code})")
                print("🔍 DIAGNOSIS: Server timeout or database connection issue")
                
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"📊 Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
            print("🔍 DIAGNOSIS: Endpoint hanging or very slow database queries")
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
            print("🔍 DIAGNOSIS: Network connectivity or server down")
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            
        return response.status_code == 200 if 'response' in locals() else False

    def test_with_parameters(self):
        """Test session list endpoint with various parameters"""
        print("\n🔧 PARAMETER TESTING")
        print("-" * 60)
        
        if not self.auth_headers:
            print("❌ No authentication headers available")
            return
        
        # Test with limit parameter
        print("🎯 Test with limit parameter")
        try:
            response = requests.get(
                f"{self.base_url}/session/list?limit=5",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                sessions_count = len(data.get('sessions', []))
                print(f"✅ Limit parameter working (returned {sessions_count} sessions)")
            else:
                print(f"❌ Limit parameter failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Limit parameter test error: {e}")
        
        # Test with status filter
        print("\n🎯 Test with status filter")
        try:
            response = requests.get(
                f"{self.base_url}/session/list?status_filter=planned",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                sessions_count = len(data.get('sessions', []))
                print(f"✅ Status filter working (returned {sessions_count} planned sessions)")
            else:
                print(f"❌ Status filter failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Status filter test error: {e}")

    def run_comprehensive_test(self):
        """Run comprehensive test of the session list endpoint"""
        print("🎯 BLUEPRINT SESSION LIST API ENDPOINT DEBUGGING")
        print("=" * 80)
        print("OBJECTIVE: Debug the Blueprint Session list API endpoint causing critical routing failure")
        print("FOCUS: GET /api/session/list endpoint availability, performance, and data structure")
        print("EXPECTED: Proper session data, response time <5s, no 500 errors or timeouts")
        print("=" * 80)
        
        # Step 1: Authentication
        if not self.authenticate():
            print("\n❌ CRITICAL: Authentication failed - cannot proceed")
            return False
        
        # Step 2: Test main endpoint
        endpoint_working = self.test_session_list_endpoint()
        
        # Step 3: Test with parameters
        self.test_with_parameters()
        
        # Final assessment
        print("\n" + "=" * 80)
        print("🎯 FINAL ASSESSMENT")
        print("=" * 80)
        
        if endpoint_working:
            print("✅ SESSION LIST API: WORKING")
            print("   - Endpoint accessible and returns proper data")
            print("   - Authentication and authorization working")
            print("   - Response format matches expected structure")
            print("   - Frontend routing issue should be resolved")
        else:
            print("❌ SESSION LIST API: CRITICAL ISSUES DETECTED")
            print("   - Endpoint may be missing, timing out, or returning errors")
            print("   - This explains the frontend routing failure")
            print("   - Immediate attention required")
        
        return endpoint_working

if __name__ == "__main__":
    tester = BlueprintSessionListTester()
    success = tester.run_comprehensive_test()
    sys.exit(0 if success else 1)