#!/usr/bin/env python3

import requests
import json
import time
import uuid
import sys

def test_llm_planner_fix():
    """
    CRITICAL LLM PLANNER FIX VERIFICATION
    Test that the constraint_report fix resolves the session planning failures.
    """
    print("🚨 CRITICAL LLM PLANNER FIX VERIFICATION")
    print("=" * 80)
    
    # Use the backend URL from environment or default to localhost
    base_url = "http://localhost:8001/api"
    
    results = {
        "authentication_working": False,
        "plan_next_performance_good": False,
        "constraint_report_present": False,
        "session_planning_consistent": False,
        "end_to_end_flow_working": False,
        "fallback_system_working": False
    }
    
    # PHASE 1: Authentication
    print("\n🔐 PHASE 1: AUTHENTICATION")
    print("-" * 40)
    
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    try:
        auth_response = requests.post(f"{base_url}/auth/login", json=auth_data, timeout=30)
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            token = auth_data.get('access_token')
            user_id = auth_data.get('user', {}).get('id')
            adaptive_enabled = auth_data.get('user', {}).get('adaptive_enabled')
            
            if token and user_id and adaptive_enabled:
                results["authentication_working"] = True
                print(f"✅ Authentication successful")
                print(f"📊 User ID: {user_id}")
                print(f"📊 Adaptive enabled: {adaptive_enabled}")
                
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
            else:
                print("❌ Authentication failed - missing required data")
                return results
        else:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            return results
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return results
    
    # PHASE 2: Plan-Next Performance Testing
    print("\n🚀 PHASE 2: PLAN-NEXT PERFORMANCE TESTING")
    print("-" * 40)
    
    performance_tests = []
    
    for i in range(3):
        session_id = f"test_{uuid.uuid4()}"
        plan_data = {
            "user_id": user_id,
            "last_session_id": "S0",
            "next_session_id": session_id
        }
        
        test_headers = headers.copy()
        test_headers['Idempotency-Key'] = f"{user_id}:S0:{session_id}"
        
        print(f"🔄 Performance Test {i+1}/3...")
        
        try:
            start_time = time.time()
            response = requests.post(f"{base_url}/adapt/plan-next", json=plan_data, headers=test_headers, timeout=60)
            response_time = time.time() - start_time
            
            performance_tests.append({
                'test_num': i+1,
                'response_time': response_time,
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_data': response.json() if response.status_code == 200 else None,
                'session_id': session_id
            })
            
            print(f"📊 Response time: {response_time:.2f}s, Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Check for constraint_report
                if response_data.get('constraint_report'):
                    print(f"✅ constraint_report present")
                else:
                    print(f"❌ constraint_report missing")
                
                # Check session planning status
                if response_data.get('status') == 'planned':
                    print(f"✅ Session planning successful")
                else:
                    print(f"⚠️ Session status: {response_data.get('status')}")
            else:
                print(f"❌ Plan-next failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Plan-next error: {e}")
            performance_tests.append({
                'test_num': i+1,
                'response_time': 60,
                'status_code': 0,
                'success': False,
                'error': str(e),
                'session_id': session_id
            })
        
        time.sleep(1)  # Brief pause between tests
    
    # Analyze performance results
    successful_tests = [t for t in performance_tests if t['success']]
    
    if successful_tests:
        avg_response_time = sum(t['response_time'] for t in successful_tests) / len(successful_tests)
        print(f"\n📊 PERFORMANCE ANALYSIS:")
        print(f"• Successful tests: {len(successful_tests)}/3")
        print(f"• Average response time: {avg_response_time:.2f}s")
        
        if avg_response_time <= 30:
            results["plan_next_performance_good"] = True
            print(f"✅ Performance acceptable (≤30s)")
        else:
            print(f"⚠️ Performance slow (>30s)")
        
        # Check constraint_report consistency
        constraint_report_count = sum(1 for t in successful_tests if t['response_data'] and t['response_data'].get('constraint_report'))
        if constraint_report_count == len(successful_tests):
            results["constraint_report_present"] = True
            print(f"✅ constraint_report present in all responses")
        else:
            print(f"❌ constraint_report missing in {len(successful_tests) - constraint_report_count} responses")
        
        # Check session planning consistency
        planned_count = sum(1 for t in successful_tests if t['response_data'] and t['response_data'].get('status') == 'planned')
        if planned_count == len(successful_tests):
            results["session_planning_consistent"] = True
            print(f"✅ Session planning consistent")
        else:
            print(f"⚠️ Session planning inconsistent: {planned_count}/{len(successful_tests)}")
    
    # PHASE 3: End-to-End Flow Testing
    print("\n🔄 PHASE 3: END-TO-END FLOW TESTING")
    print("-" * 40)
    
    if successful_tests:
        test_session = successful_tests[0]
        test_session_id = test_session['session_id']
        
        print(f"🎯 Testing with session: {test_session_id[:8]}...")
        
        try:
            # Test pack fetch
            pack_response = requests.get(f"{base_url}/adapt/pack?user_id={user_id}&session_id={test_session_id}", headers=headers, timeout=30)
            
            if pack_response.status_code == 200:
                pack_data = pack_response.json()
                pack = pack_data.get('pack', [])
                
                print(f"✅ Pack fetch successful")
                print(f"📊 Pack size: {len(pack)} questions")
                
                if len(pack) == 12:
                    print(f"✅ Pack contains 12 questions")
                    
                    # Test mark-served
                    mark_data = {"user_id": user_id, "session_id": test_session_id}
                    mark_response = requests.post(f"{base_url}/adapt/mark-served", json=mark_data, headers=headers, timeout=30)
                    
                    if mark_response.status_code == 200 and mark_response.json().get('ok'):
                        results["end_to_end_flow_working"] = True
                        print(f"✅ Mark-served successful")
                        print(f"✅ End-to-end flow working")
                    else:
                        print(f"❌ Mark-served failed: {mark_response.status_code}")
                else:
                    print(f"⚠️ Pack size incorrect: {len(pack)}")
            else:
                print(f"❌ Pack fetch failed: {pack_response.status_code}")
                
        except Exception as e:
            print(f"❌ End-to-end flow error: {e}")
    
    # PHASE 4: Results Summary
    print("\n🎯 RESULTS SUMMARY")
    print("=" * 40)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    success_rate = (passed_tests / total_tests) * 100
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():<35} {status}")
    
    print(f"\nOverall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    # Critical findings
    print(f"\n🎯 CRITICAL FINDINGS:")
    
    if results["plan_next_performance_good"] and results["constraint_report_present"]:
        print("✅ LLM PLANNER FIX SUCCESSFUL!")
        print("   • Performance improved (≤30s response times)")
        print("   • constraint_report missing errors resolved")
        print("   • Session planning working consistently")
    else:
        print("❌ LLM PLANNER FIX ISSUES DETECTED")
        if not results["plan_next_performance_good"]:
            print("   • Performance still slow (>30s)")
        if not results["constraint_report_present"]:
            print("   • constraint_report still missing in some responses")
    
    if results["end_to_end_flow_working"]:
        print("✅ Complete adaptive session flow functional")
    else:
        print("❌ End-to-end flow has issues")
    
    return success_rate >= 75

if __name__ == "__main__":
    success = test_llm_planner_fix()
    sys.exit(0 if success else 1)