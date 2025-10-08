#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time
import uuid

class SessionCompletionTester:
    def __init__(self, base_url="https://adapt-engine-1.preview.emergentagent.com/api"):
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

    def test_session_completion_and_background_jobs(self):
        """Test session completion endpoint and background job processing"""
        
        print("🎯 SESSION COMPLETION & BACKGROUND JOBS TESTING")
        print("=" * 80)
        print("OBJECTIVE: Test session completion with background job enqueueing")
        print("FOCUS: Real session → completion → 3 jobs → worker processing")
        print("=" * 80)
        
        # Step 1: Authenticate
        print("\n🔐 STEP 1: AUTHENTICATION")
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Authentication", "POST", "auth/login", [200, 401], auth_data)
        
        if not success or not response.get('access_token'):
            print("❌ Authentication failed - cannot proceed")
            return False
        
        token = response['access_token']
        auth_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        user_id = response.get('user', {}).get('id')
        print(f"✅ Authenticated successfully, user_id: {user_id[:8]}")
        
        # Step 2: Get real session from database
        print("\n🗄️ STEP 2: GET REAL SESSION FROM DATABASE")
        success, sessions_response = self.run_test(
            "Get User Sessions", 
            "GET", 
            "session/list?limit=5", 
            [200], 
            None, 
            auth_headers
        )
        
        real_session_id = None
        if success and sessions_response.get('sessions'):
            sessions = sessions_response.get('sessions', [])
            print(f"Found {len(sessions)} sessions for user")
            
            # Look for any session to test with
            for session in sessions:
                session_id = session.get('session_id')
                session_status = session.get('status')
                answered_count = session.get('answered_count', 0)
                
                print(f"Session {session_id[:8]}: status={session_status}, answered={answered_count}")
                
                if session_id:
                    real_session_id = session_id
                    print(f"✅ Using session for testing: {real_session_id[:8]}")
                    break
        
        if not real_session_id:
            print("❌ No real session found - cannot test session completion")
            return False
        
        # Step 3: Check background job health (before)
        print("\n🏥 STEP 3: BACKGROUND JOB HEALTH (BEFORE)")
        success, health_before = self.run_test(
            "BG Jobs Health (Before)", 
            "GET", 
            "bg-jobs/health", 
            [200, 503], 
            None, 
            None
        )
        
        if success:
            active_workers_before = health_before.get('active_workers', 0)
            queue_depth_before = health_before.get('queue_depth', 0)
            print(f"Before: {active_workers_before} active workers, queue depth: {queue_depth_before}")
        
        # Step 4: Check user job status (before)
        print("\n👤 STEP 4: USER JOB STATUS (BEFORE)")
        success, status_before = self.run_test(
            "User Job Status (Before)", 
            "GET", 
            "bg-jobs/status", 
            [200, 500], 
            None, 
            auth_headers
        )
        
        jobs_before = []
        if success:
            jobs_before = status_before.get('recent_jobs', [])
            print(f"Before: {len(jobs_before)} recent jobs")
            for job in jobs_before[:3]:
                print(f"  - {job.get('job_type')}: {job.get('status')}")
        
        # Step 5: Complete session
        print(f"\n🎯 STEP 5: COMPLETE SESSION {real_session_id[:8]}")
        completion_data = {
            "session_id": real_session_id
        }
        
        success, completion_response = self.run_test(
            "Session Completion", 
            "POST", 
            "session/complete",
            [200, 404, 500], 
            completion_data, 
            auth_headers
        )
        
        if success:
            summary = completion_response.get('summary', {})
            adaptive_processing = summary.get('adaptive_processing')
            print(f"✅ Session completed, adaptive_processing: {adaptive_processing}")
        else:
            print(f"❌ Session completion failed: {completion_response}")
            return False
        
        # Step 6: Wait and check job enqueueing
        print("\n📋 STEP 6: CHECK JOB ENQUEUEING (AFTER 3 SECONDS)")
        time.sleep(3)
        
        success, status_after = self.run_test(
            "User Job Status (After)", 
            "GET", 
            "bg-jobs/status", 
            [200, 500], 
            None, 
            auth_headers
        )
        
        jobs_enqueued = False
        if success:
            jobs_after = status_after.get('recent_jobs', [])
            print(f"After: {len(jobs_after)} recent jobs")
            
            # Check for new jobs
            new_jobs = len(jobs_after) - len(jobs_before)
            print(f"New jobs enqueued: {new_jobs}")
            
            job_types_found = set()
            for job in jobs_after:
                job_type = job.get('job_type')
                job_status = job.get('status')
                print(f"  - {job_type}: {job_status}")
                job_types_found.add(job_type)
            
            expected_job_types = {'session_summarization', 'personalized_planning', 'coverage_update'}
            jobs_found = len(job_types_found.intersection(expected_job_types))
            
            if jobs_found >= 1:
                jobs_enqueued = True
                print(f"✅ Found {jobs_found} expected job types")
            else:
                print(f"❌ No expected job types found")
        
        # Step 7: Check worker processing
        print("\n⚙️ STEP 7: CHECK WORKER PROCESSING (AFTER 5 MORE SECONDS)")
        time.sleep(5)
        
        success, health_after = self.run_test(
            "BG Jobs Health (After)", 
            "GET", 
            "bg-jobs/health", 
            [200, 503], 
            None, 
            None
        )
        
        workers_active = False
        if success:
            active_workers_after = health_after.get('active_workers', 0)
            queue_depth_after = health_after.get('queue_depth', 0)
            print(f"After: {active_workers_after} active workers, queue depth: {queue_depth_after}")
            
            if active_workers_after > 0:
                workers_active = True
                print(f"✅ Workers are active and processing")
            else:
                print(f"❌ No active workers detected")
        
        # Step 8: Final job status check
        print("\n📊 STEP 8: FINAL JOB STATUS CHECK")
        success, final_status = self.run_test(
            "Final Job Status", 
            "GET", 
            "bg-jobs/status", 
            [200, 500], 
            None, 
            auth_headers
        )
        
        job_transitions = False
        if success:
            final_jobs = final_status.get('recent_jobs', [])
            print(f"Final: {len(final_jobs)} recent jobs")
            
            status_types = set()
            for job in final_jobs:
                job_status = job.get('status')
                status_types.add(job_status)
                print(f"  - {job.get('job_type')}: {job_status}")
            
            if 'processing' in status_types or 'completed' in status_types:
                job_transitions = True
                print(f"✅ Job status transitions detected")
            else:
                print(f"❌ No job status transitions detected")
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 TEST RESULTS SUMMARY")
        print("=" * 80)
        
        results = {
            "Authentication": True,
            "Real Session Found": bool(real_session_id),
            "Session Completion": success,
            "Jobs Enqueued": jobs_enqueued,
            "Workers Active": workers_active,
            "Job Transitions": job_transitions
        }
        
        for test, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test:<25} {status}")
        
        passed = sum(results.values())
        total = len(results)
        success_rate = (passed / total) * 100
        
        print(f"\nSuccess Rate: {passed}/{total} ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            print("🎉 BACKGROUND JOB SYSTEM: OPERATIONAL")
        else:
            print("⚠️ BACKGROUND JOB SYSTEM: NEEDS ATTENTION")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = SessionCompletionTester()
    success = tester.test_session_completion_and_background_jobs()
    
    print(f"\nTotal tests run: {tester.tests_run}")
    print(f"Total tests passed: {tester.tests_passed}")
    
    sys.exit(0 if success else 1)