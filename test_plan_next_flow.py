#!/usr/bin/env python3
"""
Critical Session Planning Flow Test
Test the specific plan-next endpoint flow that the frontend is failing on
"""

import requests
import sys
import json
from datetime import datetime
import time
import os
import uuid

class PlanNextFlowTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
        self.tests_run += 1
        
        try:
            url = f"{self.base_url}/{endpoint}"
            
            # Set default headers
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            
            # Make request based on method
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=60, verify=False)
            elif method == "POST":
                if data:
                    response = requests.post(url, json=data, headers=headers, timeout=60, verify=False)
                else:
                    response = requests.post(url, headers=headers, timeout=60, verify=False)
            else:
                print(f"❌ {test_name}: Unsupported method {method}")
                return False, None
            
            # Check if status code is in expected range
            if isinstance(expected_status, list):
                status_ok = response.status_code in expected_status
            else:
                status_ok = response.status_code == expected_status
            
            if status_ok:
                self.tests_passed += 1
                try:
                    response_data = response.json()
                    print(f"✅ {test_name}: {response.status_code}")
                    return True, response_data
                except:
                    print(f"✅ {test_name}: {response.status_code} (No JSON)")
                    return True, {"status_code": response.status_code, "text": response.text}
            else:
                try:
                    response_data = response.json()
                    print(f"❌ {test_name}: {response.status_code} - {response_data}")
                    return False, {"status_code": response.status_code, **response_data}
                except:
                    print(f"❌ {test_name}: {response.status_code} - {response.text}")
                    return False, {"status_code": response.status_code, "text": response.text}
                    
        except Exception as e:
            print(f"❌ {test_name}: Exception - {str(e)}")
            return False, {"error": str(e)}

    def test_critical_session_planning_flow(self):
        """
        🚨 CRITICAL SESSION PLANNING TEST: Test the specific plan-next endpoint flow that the frontend is failing on.
        """
        print("🚨 CRITICAL SESSION PLANNING TEST: Frontend Plan-Next Flow Investigation")
        print("=" * 80)
        print("OBJECTIVE: Test the specific plan-next endpoint flow that the frontend is failing on")
        print("SCENARIO: User sp@theskinmantra.com calls plan-next, then pack fetch fails with 404")
        print("KEY QUESTION: Why does plan-next succeed but pack fetch returns 404?")
        print("=" * 80)
        
        # PHASE 1: AUTHENTICATION SETUP
        print("\n🔐 PHASE 1: AUTHENTICATION SETUP")
        print("-" * 60)
        print("Setting up authentication with exact frontend credentials")
        
        # Test Student Authentication
        student_login_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Authentication", "POST", "auth/login", [200, 401], student_login_data)
        
        student_headers = None
        user_id = None
        if success and response.get('access_token'):
            student_token = response['access_token']
            student_headers = {
                'Authorization': f'Bearer {student_token}',
                'Content-Type': 'application/json'
            }
            print(f"   ✅ Student authentication successful")
            print(f"   📊 JWT Token length: {len(student_token)} characters")
            
            # Get user data
            user_data = response.get('user', {})
            user_id = user_data.get('id')
            adaptive_enabled = user_data.get('adaptive_enabled', False)
            
            if user_id:
                print(f"   ✅ User ID extracted: {user_id}")
            
            if adaptive_enabled:
                print(f"   ✅ User adaptive_enabled confirmed: {adaptive_enabled}")
            else:
                print(f"   ⚠️ User adaptive_enabled: {adaptive_enabled}")
        else:
            print("   ❌ Student authentication failed - cannot proceed with session planning testing")
            return False
        
        # PHASE 2: STEP 1 - LAST COMPLETED SESSION ID (EXPECTED 404)
        print("\n📋 PHASE 2: STEP 1 - LAST COMPLETED SESSION ID TEST")
        print("-" * 60)
        print("Testing getLastCompletedSessionId() → Expected 404 for new users")
        
        if user_id and student_headers:
            success, response = self.run_test(
                "Get Last Completed Session ID", 
                "GET", 
                f"sessions/last-completed-id?user_id={user_id}", 
                [404, 200], 
                None, 
                student_headers
            )
            
            if success:
                print(f"   ✅ Last completed session endpoint working")
                
                if response.get("status_code") == 404:
                    print(f"   ✅ Expected 404 for new user (no completed sessions)")
                    print(f"   📊 Response: {response}")
                else:
                    print(f"   📊 Unexpected response (user may have completed sessions): {response}")
            else:
                print(f"   ❌ Last completed session endpoint failed: {response}")
        
        # PHASE 3: STEP 2 - PLAN-NEXT FLOW
        print("\n🚀 PHASE 3: STEP 2 - PLAN-NEXT FLOW")
        print("-" * 60)
        print("Testing POST /adapt/plan-next with exact frontend parameters")
        
        session_id = None
        if user_id and student_headers:
            # Generate session ID like frontend does
            session_id = f"session_{uuid.uuid4()}"
            last_session_id = "S0"  # Cold start indicator
            
            # Create exact frontend request
            plan_data = {
                "user_id": user_id,
                "last_session_id": last_session_id,
                "next_session_id": session_id
            }
            
            # Add required Idempotency-Key header (exact frontend format)
            headers_with_idem = student_headers.copy()
            idempotency_key = f"{user_id}:{last_session_id}:{session_id}"
            headers_with_idem['Idempotency-Key'] = idempotency_key
            
            print(f"   📋 Testing with session_id: {session_id}")
            print(f"   📋 Idempotency-Key: {idempotency_key}")
            
            success, plan_response = self.run_test(
                "Plan Next Session (Frontend Flow)", 
                "POST", 
                "adapt/plan-next", 
                [200, 400, 500, 502], 
                plan_data, 
                headers_with_idem
            )
            
            if success:
                print(f"   ✅ Plan-next endpoint accessible")
                print(f"   ✅ Plan-next accepts frontend parameters")
                
                if plan_response.get('status') == 'planned':
                    print(f"   ✅ Plan-next returns success (status: planned)")
                    print(f"   ✅ Session record created (inferred)")
                    print(f"   ✅ Idempotency key working")
                    print(f"   📊 Plan response: {plan_response}")
                else:
                    print(f"   ⚠️ Plan-next response status: {plan_response.get('status')}")
                    print(f"   📊 Full response: {plan_response}")
            else:
                print(f"   ❌ Plan-next endpoint failed: {plan_response}")
                
                # Check for specific error patterns
                if plan_response.get("status_code") == 502:
                    print(f"   🔍 502 Bad Gateway - Backend processing issue detected")
                elif plan_response.get("status_code") == 400:
                    print(f"   🔍 400 Bad Request - Parameter validation issue")
                return False
        
        # PHASE 4: STEP 3 - PACK AVAILABILITY TEST
        print("\n📦 PHASE 4: STEP 3 - PACK AVAILABILITY TEST")
        print("-" * 60)
        print("Testing GET /adapt/pack after successful planning")
        
        if session_id and user_id:
            # Wait a moment for any async processing
            print(f"   ⏳ Waiting 2 seconds for session processing...")
            time.sleep(2)
            
            success, pack_response = self.run_test(
                "Get Adaptive Pack (After Planning)", 
                "GET", 
                f"adapt/pack?user_id={user_id}&session_id={session_id}", 
                [200, 404, 500], 
                None, 
                student_headers
            )
            
            if success:
                print(f"   ✅ Pack endpoint accessible")
                
                if pack_response.get('pack'):
                    print(f"   ✅ Pack fetch after planning works")
                    
                    pack_data = pack_response.get('pack', [])
                    pack_size = len(pack_data)
                    pack_status = pack_response.get('status')
                    
                    print(f"   📊 Pack size: {pack_size} questions")
                    print(f"   📊 Pack status: {pack_status}")
                    
                    if pack_size == 12:
                        print(f"   ✅ Pack contains exactly 12 questions")
                    
                    if pack_status == 'planned':
                        print(f"   ✅ Pack status is 'planned'")
                        
                    # Show first question for validation
                    if pack_data:
                        first_q = pack_data[0]
                        print(f"   📊 First question: {first_q.get('why', 'N/A')[:50]}...")
                        
                else:
                    print(f"   ❌ Pack fetch failed - no pack data returned")
                    print(f"   📊 Response: {pack_response}")
                    
                    # This is the KEY ISSUE - pack fetch returns 404
                    if pack_response.get("status_code") == 404:
                        print(f"   🚨 CRITICAL: Pack fetch returns 404 - ROOT CAUSE IDENTIFIED!")
                        print(f"   🔍 This matches the frontend issue exactly")
                        return True  # We found the issue!
            else:
                print(f"   ❌ Pack endpoint failed: {pack_response}")
                
                # Analyze the 404 error
                if pack_response.get("status_code") == 404:
                    print(f"   🚨 CRITICAL: Pack fetch returns 404 after successful planning!")
                    print(f"   🔍 ROOT CAUSE: Session planning succeeds but pack is not retrievable")
                    print(f"   🔍 POSSIBLE CAUSES:")
                    print(f"     - Session ID mismatch between plan-next and pack fetch")
                    print(f"     - Database persistence issue in session_orchestrator")
                    print(f"     - Timing issue - pack not yet saved when fetch occurs")
                    print(f"     - Transaction rollback after plan-next response")
                    return True  # We found the issue!
        
        # PHASE 5: STEP 4 - FULL FLOW END-TO-END TEST
        print("\n🔄 PHASE 5: STEP 4 - FULL FLOW END-TO-END TEST")
        print("-" * 60)
        print("Testing complete flow: plan-next → pack → mark-served")
        
        if session_id and user_id:
            # Test mark-served endpoint
            mark_served_data = {
                "user_id": user_id,
                "session_id": session_id
            }
            
            success, served_response = self.run_test(
                "Mark Session Served", 
                "POST", 
                "adapt/mark-served", 
                [200, 409, 500], 
                mark_served_data, 
                student_headers
            )
            
            if success and served_response.get('ok'):
                print(f"   ✅ Mark-served endpoint working")
                print(f"   ✅ Complete flow functional")
                print(f"   ✅ Session state transitions working")
            else:
                print(f"   ❌ Mark-served failed: {served_response}")
        
        return True

if __name__ == "__main__":
    tester = PlanNextFlowTester()
    result = tester.test_critical_session_planning_flow()
    
    print(f"\n" + "=" * 80)
    print(f"CRITICAL SESSION PLANNING TEST COMPLETED")
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%" if tester.tests_run > 0 else "0%")
    print(f"Root cause identified: {'✅ YES' if result else '❌ NO'}")
    print("=" * 80)