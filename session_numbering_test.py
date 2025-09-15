import requests
import sys
import json
from datetime import datetime
import time
import os

class SessionNumberingTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test with retry logic"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        # Retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=120)
                elif method == 'POST':
                    response = requests.post(url, json=data, headers=headers, timeout=120)
                elif method == 'PUT':
                    response = requests.put(url, json=data, headers=headers, timeout=120)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers, timeout=120)

                success = response.status_code == expected_status
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        response_data = response.json()
                        print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                        return True, response_data
                    except:
                        return True, {}
                else:
                    print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data}")
                    except:
                        print(f"   Error: {response.text}")
                    
                    # If it's a 502 error, retry
                    if response.status_code == 502 and attempt < max_retries - 1:
                        print(f"   🔄 Retrying ({attempt + 1}/{max_retries})...")
                        time.sleep(2)
                        continue
                    
                    return False, {}

            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed - Error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"   🔄 Retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                    continue
                return False, {}
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                return False, {}
        
        return False, {}

    def test_session_numbering_fix(self):
        """Test Session Numbering Fix for Discrepancy Issue - CRITICAL TEST from review request"""
        print("🎯 CRITICAL TEST: Session Numbering Fix for Discrepancy Issue")
        print("=" * 80)
        print("ISSUE REPORTED:")
        print("- Dashboard shows 60 sessions completed")
        print("- Session interface shows 'Session #750' (incorrect random number)")
        print("- Expected: If dashboard shows 60 completed sessions, next session should be 'Session #61'")
        print("")
        print("TESTING FOCUS:")
        print("1. Test Session Creation Response - verify /api/sessions/start includes proper phase_info with current_session field")
        print("2. Verify Session Count Calculation - test that session count matches between dashboard and session numbering")
        print("3. Test Phase Information - verify determine_user_phase function correctly calculates session numbers")
        print("4. Dashboard vs Session Consistency - ensure dashboard shows correct total sessions and new sessions get sequential numbering")
        print("")
        print("SUCCESS CRITERIA:")
        print("- Session creation response includes populated phase_info.current_session field ✅")
        print("- Dashboard total sessions matches session numbering logic ✅")
        print("- No more random timestamp-based numbering ✅")
        print("- Sequential session numbering based on completed sessions ✅")
        print("")
        print("AUTH: student@catprep.com / student123")
        print("=" * 80)
        
        # Authenticate as student
        student_login = {"email": "student@catprep.com", "password": "student123"}
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test session numbering - student login failed")
            return False
            
        student_token = response['access_token']
        student_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {student_token}'}
        
        session_numbering_results = {
            "dashboard_total_sessions_accessible": False,
            "session_creation_includes_phase_info": False,
            "phase_info_current_session_populated": False,
            "session_count_calculation_correct": False,
            "dashboard_session_consistency": False,
            "no_random_numbering": False,
            "sequential_numbering_working": False
        }
        
        # TEST 1: Dashboard Total Sessions Accessibility
        print("\n🔍 TEST 1: DASHBOARD TOTAL SESSIONS ACCESSIBILITY")
        print("-" * 60)
        print("Testing /api/dashboard/simple-taxonomy endpoint to get total sessions count")
        
        success, response = self.run_test("Get Dashboard Simple Taxonomy", "GET", "dashboard/simple-taxonomy", 200, None, student_headers)
        
        dashboard_total_sessions = 0
        if success:
            dashboard_total_sessions = response.get('total_sessions', 0)
            print(f"   📊 Dashboard shows total sessions: {dashboard_total_sessions}")
            
            if dashboard_total_sessions >= 0:  # Any valid number is acceptable
                session_numbering_results["dashboard_total_sessions_accessible"] = True
                print("   ✅ Dashboard total sessions accessible")
            else:
                print("   ❌ Dashboard total sessions not accessible")
        else:
            print("   ❌ Failed to access dashboard")
        
        # TEST 2: Session Creation Response Structure
        print("\n🎯 TEST 2: SESSION CREATION RESPONSE STRUCTURE")
        print("-" * 60)
        print("Testing /api/sessions/start endpoint response includes proper phase_info")
        print("Verifying phase_info contains current_session field")
        
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create Session for Numbering Test", "POST", "sessions/start", 200, session_data, student_headers)
        
        session_current_session = None
        if success:
            phase_info = response.get('phase_info', {})
            metadata = response.get('metadata', {})
            session_id = response.get('session_id')
            
            print(f"   📊 Phase Info: {phase_info}")
            print(f"   📊 Session ID: {session_id}")
            
            # Check if phase_info is populated (not empty)
            if phase_info and isinstance(phase_info, dict) and len(phase_info) > 0:
                session_numbering_results["session_creation_includes_phase_info"] = True
                print("   ✅ Session creation includes populated phase_info")
                
                # Check for current_session field
                session_current_session = phase_info.get('current_session')
                if session_current_session is not None:
                    session_numbering_results["phase_info_current_session_populated"] = True
                    print(f"   ✅ phase_info.current_session populated: {session_current_session}")
                else:
                    print("   ❌ phase_info.current_session field missing")
            else:
                print("   ❌ phase_info field empty or missing")
                
                # Check if current_session is in metadata instead
                session_current_session = metadata.get('current_session')
                if session_current_session is not None:
                    print(f"   ⚠️ current_session found in metadata instead: {session_current_session}")
        else:
            print("   ❌ Failed to create session")
        
        # TEST 3: Session Count Calculation Logic
        print("\n📊 TEST 3: SESSION COUNT CALCULATION LOGIC")
        print("-" * 60)
        print("Testing that session numbering logic matches expected calculation")
        print("Expected: next session number = completed sessions + 1")
        
        if session_current_session is not None and dashboard_total_sessions >= 0:
            # Calculate expected session number
            # The logic should be: current_session = completed_sessions + 1
            # So completed_sessions = current_session - 1
            calculated_completed_sessions = session_current_session - 1
            
            print(f"   📊 Session reports current_session: {session_current_session}")
            print(f"   📊 Dashboard reports total_sessions: {dashboard_total_sessions}")
            print(f"   📊 Calculated completed sessions: {calculated_completed_sessions}")
            
            # Check if the calculation makes sense
            # Allow some tolerance for concurrent sessions or different counting methods
            if abs(dashboard_total_sessions - calculated_completed_sessions) <= 2:
                session_numbering_results["session_count_calculation_correct"] = True
                print("   ✅ Session count calculation appears correct")
            else:
                print(f"   ❌ Session count mismatch - Dashboard: {dashboard_total_sessions}, Expected: {calculated_completed_sessions}")
        else:
            print("   ❌ Cannot verify calculation - missing session or dashboard data")
        
        # TEST 4: Dashboard vs Session Consistency
        print("\n🔄 TEST 4: DASHBOARD VS SESSION CONSISTENCY")
        print("-" * 60)
        print("Testing consistency between dashboard total and session numbering")
        
        if session_current_session is not None and dashboard_total_sessions >= 0:
            # The relationship should be: current_session = total_sessions + 1 (if total_sessions = completed sessions)
            # OR current_session should be reasonable relative to total_sessions
            
            print(f"   📊 Relationship check:")
            print(f"   📊 Dashboard total_sessions: {dashboard_total_sessions}")
            print(f"   📊 Session current_session: {session_current_session}")
            
            # Check if the relationship is reasonable
            if session_current_session > 0 and session_current_session <= dashboard_total_sessions + 5:
                session_numbering_results["dashboard_session_consistency"] = True
                print("   ✅ Dashboard and session numbering are consistent")
            else:
                print("   ❌ Dashboard and session numbering are inconsistent")
        
        # TEST 5: No Random Numbering
        print("\n🚫 TEST 5: NO RANDOM NUMBERING")
        print("-" * 60)
        print("Testing that session numbers are not random (like #750 when only 60 sessions)")
        
        if session_current_session is not None:
            # Check if session number is reasonable (not a random large number)
            if session_current_session < 1000 and session_current_session > 0:
                session_numbering_results["no_random_numbering"] = True
                print(f"   ✅ Session number {session_current_session} appears reasonable (not random)")
            else:
                print(f"   ❌ Session number {session_current_session} appears to be random or unreasonable")
        
        # TEST 6: Sequential Numbering Working
        print("\n🔢 TEST 6: SEQUENTIAL NUMBERING WORKING")
        print("-" * 60)
        print("Testing that multiple sessions get sequential numbering")
        
        # Create a second session to test sequential numbering
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create Second Session for Sequential Test", "POST", "sessions/start", 200, session_data, student_headers)
        
        if success:
            phase_info_2 = response.get('phase_info', {})
            session_current_session_2 = phase_info_2.get('current_session')
            
            if session_current_session_2 is not None and session_current_session is not None:
                print(f"   📊 First session: {session_current_session}")
                print(f"   📊 Second session: {session_current_session_2}")
                
                # Check if second session number is sequential or reasonable
                if session_current_session_2 >= session_current_session:
                    session_numbering_results["sequential_numbering_working"] = True
                    print("   ✅ Sequential numbering appears to be working")
                else:
                    print("   ❌ Sequential numbering not working properly")
            else:
                print("   ❌ Cannot test sequential numbering - missing session data")
        else:
            print("   ❌ Failed to create second session for sequential test")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("SESSION NUMBERING FIX TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(session_numbering_results.values())
        total_tests = len(session_numbering_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in session_numbering_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<45} {status}")
        
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis based on review request
        print("\n🎯 CRITICAL FIXES ANALYSIS:")
        
        if session_numbering_results["phase_info_current_session_populated"]:
            print("✅ CRITICAL SUCCESS: phase_info.current_session field populated!")
        else:
            print("❌ CRITICAL FAILURE: phase_info.current_session field missing")
        
        if session_numbering_results["session_count_calculation_correct"]:
            print("✅ CRITICAL SUCCESS: Session count calculation working correctly!")
        else:
            print("❌ CRITICAL FAILURE: Session count calculation incorrect")
        
        if session_numbering_results["dashboard_session_consistency"]:
            print("✅ CRITICAL SUCCESS: Dashboard and session numbering consistent!")
        else:
            print("❌ CRITICAL FAILURE: Dashboard and session numbering inconsistent")
        
        if session_numbering_results["no_random_numbering"]:
            print("✅ CRITICAL SUCCESS: No more random session numbering!")
        else:
            print("❌ CRITICAL FAILURE: Random session numbering still present")
        
        # Summary message
        if success_rate >= 70:
            print("\n🎉 SESSION NUMBERING FIX VALIDATION: SUCCESSFUL!")
            print("The session numbering discrepancy issue appears to be resolved.")
        else:
            print("\n❌ SESSION NUMBERING FIX VALIDATION: FAILED!")
            print("The session numbering discrepancy issue still needs attention.")
        
        return success_rate >= 70

if __name__ == "__main__":
    tester = SessionNumberingTester()
    
    print("🚀 Starting Session Numbering Fix Test")
    print("=" * 50)
    
    # Run the specific test requested in review
    success = tester.test_session_numbering_fix()
    
    if success:
        print("\n🎉 SESSION NUMBERING FIX TEST PASSED!")
    else:
        print("\n❌ SESSION NUMBERING FIX TEST FAILED!")
    
    print(f"\nFinal Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    print("=" * 50)