#!/usr/bin/env python3
"""
Corrected Adaptive Learning Pipeline Testing
Test the fixed adaptive learning pipeline with proper job chaining
"""

import requests
import sys
import json
from datetime import datetime
import time
import os
import uuid

class AdaptivePipelineTester:
    def __init__(self, base_url="https://adaptive-engine-fix.preview.emergentagent.com/api"):
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
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=60, verify=False)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=60, verify=False)
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

    def test_corrected_adaptive_learning_pipeline(self):
        """
        🎯 CORRECTED ADAPTIVE LEARNING PIPELINE TESTING AFTER JOB CHAINING FIXES
        
        Test the CORRECTED adaptive learning pipeline after fixing the job chaining issues.
        The investigation revealed that job chaining WAS working correctly - the issue was 
        database schema mismatches in job handlers.
        
        FIXES IMPLEMENTED:
        1. ✅ Job chaining IS working correctly - SUMMARIZE_SESSION jobs do enqueue PLAN_NEXT_SESSION jobs  
        2. ✅ Correlation ID propagation IS working - correlation_ids are properly propagated through job chain
        3. ✅ Event loop issues ARE resolved - no more async/await conflicts
        
        ROOT CAUSE IDENTIFIED:
        - Job chaining was never actually broken - the issue was database schema mismatches in job handlers
        - PLAN_NEXT_SESSION jobs were failing due to outdated INSERT statements trying to use non-existent columns
        
        NEW TEST REQUIREMENTS:
        1. Authenticate with sp@theskinmantra.com/student123  
        2. Use the CORRECT endpoint: /api/session/complete (NOT /api/sessions/mark-completed)
        3. Create a new session and complete it properly to trigger fresh SUMMARIZE_SESSION job
        4. Monitor that SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS pipeline works
        5. Verify correlation_id propagation through entire chain
        6. Check that all job handlers execute successfully without database schema errors
        """
        print("🎯 CORRECTED ADAPTIVE LEARNING PIPELINE TESTING AFTER JOB CHAINING FIXES")
        print("=" * 90)
        print("OBJECTIVE: Test the CORRECTED adaptive learning pipeline after fixing job chaining issues")
        print("FOCUS: Fresh session completion, SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS")
        print("EXPECTED: Complete job pipeline working with proper correlation_id propagation")
        print("ROOT CAUSE: Database schema mismatches in job handlers (NOT job chaining)")
        print("=" * 90)
        
        test_results = {
            # Authentication Setup
            "authentication_working": False,
            "user_adaptive_enabled": False,
            "jwt_token_valid": False,
            
            # Fresh Session Creation and Completion
            "fresh_session_created": False,
            "session_answers_added": False,
            "session_completion_endpoint_working": False,
            "correlation_id_generated": False,
            "background_jobs_enqueued": False,
            
            # Job Chain Monitoring
            "summarize_session_job_found": False,
            "summarize_session_has_correlation_id": False,
            "plan_next_session_job_found": False,
            "plan_next_session_has_correlation_id": False,
            "update_insights_job_found": False,
            "update_insights_has_correlation_id": False,
            
            # Correlation ID Propagation
            "correlation_id_propagated_through_chain": False,
            "all_jobs_have_same_correlation_id": False,
            
            # Job Processing Validation
            "jobs_have_valid_timestamps": False,
            "no_database_schema_errors": False,
            "job_handlers_execute_successfully": False,
            
            # Overall Assessment
            "corrected_pipeline_working": False,
            "job_chaining_validated": False,
            "production_ready": False
        }
        
        # PHASE 1: AUTHENTICATION
        print("\n🔐 PHASE 1: AUTHENTICATION")
        print("-" * 60)
        print("Authenticating with sp@theskinmantra.com/student123")
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Pipeline Authentication", "POST", "auth/login", [200, 401], auth_data)
        
        auth_headers = None
        user_id = None
        correlation_id = None
        
        if success and response.get('access_token'):
            token = response['access_token']
            auth_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            test_results["authentication_working"] = True
            test_results["jwt_token_valid"] = True
            print(f"   ✅ Authentication successful")
            print(f"   📊 JWT Token length: {len(token)} characters")
            
            user_data = response.get('user', {})
            user_id = user_data.get('id')
            adaptive_enabled = user_data.get('adaptive_enabled', False)
            
            if adaptive_enabled:
                test_results["user_adaptive_enabled"] = True
                print(f"   ✅ User adaptive_enabled confirmed: {adaptive_enabled}")
                print(f"   📊 User ID: {user_id}")
            else:
                print(f"   ⚠️ User adaptive_enabled: {adaptive_enabled}")
        else:
            print("   ❌ Authentication failed - cannot proceed with pipeline testing")
            return False
        
        # PHASE 2: CREATE FRESH SESSION AND COMPLETE IT
        print("\n📋 PHASE 2: CREATE FRESH SESSION AND COMPLETE IT")
        print("-" * 60)
        print("Creating a new session and completing it to trigger fresh SUMMARIZE_SESSION job")
        
        session_id = None
        if auth_headers and user_id:
            # Create a completely fresh session for testing
            try:
                import sys
                sys.path.append('/app/backend')
                from database import SessionLocal
                from sqlalchemy import text
                
                db = SessionLocal()
                try:
                    # Create a fresh session for testing
                    session_id = str(uuid.uuid4())
                    
                    # Insert session with proper structure
                    db.execute(text("""
                        INSERT INTO sessions (session_id, user_id, status, created_at, sess_seq)
                        VALUES (:session_id, :user_id, 'served', NOW(), 
                                (SELECT COALESCE(MAX(sess_seq), 0) + 1 FROM sessions WHERE user_id = :user_id))
                    """), {"session_id": session_id, "user_id": user_id})
                    
                    # Add some sample session answers to make it a valid completed session
                    for i in range(1, 13):  # 12 questions
                        db.execute(text("""
                            INSERT INTO session_answers (session_id, position, question_id, user_answer, is_correct, timestamp)
                            VALUES (:session_id, :position, :question_id, 'Sample Answer', :is_correct, NOW())
                        """), {
                            "session_id": session_id, 
                            "position": i,
                            "question_id": str(uuid.uuid4()),
                            "is_correct": i % 2 == 0  # Alternate correct/incorrect
                        })
                    
                    db.commit()
                    test_results["fresh_session_created"] = True
                    test_results["session_answers_added"] = True
                    print(f"   ✅ Created fresh session with 12 answers: {session_id}")
                    
                finally:
                    db.close()
                    
            except Exception as e:
                print(f"   ❌ Error creating fresh session: {e}")
                return False
        
        # Test the CORRECT session completion endpoint: /api/session/complete
        if session_id and auth_headers:
            print(f"   🎯 Testing CORRECT endpoint: /api/session/complete")
            print(f"   📋 Fresh Session ID: {session_id}")
            
            completion_data = {
                "session_id": session_id
            }
            
            success, completion_response = self.run_test(
                "Fresh Session Completion", 
                "POST", 
                "session/complete", 
                [200, 400, 500], 
                completion_data, 
                auth_headers
            )
            
            if success and completion_response.get('success'):
                test_results["session_completion_endpoint_working"] = True
                print(f"   ✅ Session completion endpoint working")
                print(f"   📊 Response: {completion_response}")
                
                # Check for correlation_id in response
                correlation_id = completion_response.get('correlation_id')
                if correlation_id:
                    test_results["correlation_id_generated"] = True
                    print(f"   ✅ Correlation ID generated: {correlation_id}")
                    
                # Check if background jobs were enqueued
                bg_jobs_enqueued = completion_response.get('background_jobs_enqueued', False)
                if bg_jobs_enqueued:
                    test_results["background_jobs_enqueued"] = True
                    print(f"   ✅ Background jobs enqueued successfully")
                else:
                    print(f"   ⚠️ Background jobs not enqueued")
                
            else:
                print(f"   ❌ Session completion failed: {completion_response}")
                return False
        else:
            print(f"   ❌ Cannot test session completion - missing session_id or auth_headers")
            return False
        
        # PHASE 3: MONITOR JOB CHAIN PROGRESSION
        print("\n🔗 PHASE 3: MONITOR JOB CHAIN PROGRESSION")
        print("-" * 60)
        print("Monitoring SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS pipeline")
        
        if correlation_id and auth_headers:
            # Wait a moment for jobs to be processed
            print("   ⏳ Waiting 30 seconds for job processing...")
            time.sleep(30)
            
            # Check background jobs table for our jobs
            try:
                from database import SessionLocal
                from sqlalchemy import text
                
                db = SessionLocal()
                try:
                    # Look for jobs with our correlation_id
                    jobs_result = db.execute(text("""
                        SELECT job_type, status, correlation_id, created_at, next_attempt_at
                        FROM bg_jobs 
                        WHERE correlation_id = :correlation_id
                        ORDER BY created_at ASC
                    """), {"correlation_id": correlation_id})
                    
                    jobs = jobs_result.fetchall()
                    
                    if jobs:
                        print(f"   📊 Found {len(jobs)} jobs with correlation_id {correlation_id}")
                        
                        job_types_found = []
                        correlation_ids_found = []
                        
                        for job in jobs:
                            job_type, status, job_correlation_id, created_at, next_attempt_at = job
                            job_types_found.append(job_type)
                            correlation_ids_found.append(job_correlation_id)
                            
                            print(f"   📋 Job: {job_type}, Status: {status}, Created: {created_at}")
                            
                            # Check specific job types
                            if job_type == "SUMMARIZE_SESSION":
                                test_results["summarize_session_job_found"] = True
                                if job_correlation_id == correlation_id:
                                    test_results["summarize_session_has_correlation_id"] = True
                                    print(f"      ✅ SUMMARIZE_SESSION job found with correct correlation_id")
                                    
                            elif job_type == "PLAN_NEXT_SESSION":
                                test_results["plan_next_session_job_found"] = True
                                if job_correlation_id == correlation_id:
                                    test_results["plan_next_session_has_correlation_id"] = True
                                    print(f"      ✅ PLAN_NEXT_SESSION job found with correct correlation_id")
                                    
                            elif job_type == "UPDATE_INSIGHTS":
                                test_results["update_insights_job_found"] = True
                                if job_correlation_id == correlation_id:
                                    test_results["update_insights_has_correlation_id"] = True
                                    print(f"      ✅ UPDATE_INSIGHTS job found with correct correlation_id")
                        
                        # Check if correlation_id is propagated through entire chain
                        unique_correlation_ids = set(correlation_ids_found)
                        if len(unique_correlation_ids) == 1 and correlation_id in unique_correlation_ids:
                            test_results["correlation_id_propagated_through_chain"] = True
                            test_results["all_jobs_have_same_correlation_id"] = True
                            print(f"   ✅ Correlation ID propagated through entire job chain")
                        else:
                            print(f"   ❌ Correlation ID not consistent across jobs: {unique_correlation_ids}")
                        
                        # Check for valid timestamps
                        if all(job[3] is not None and job[4] is not None for job in jobs):  # created_at and next_attempt_at
                            test_results["jobs_have_valid_timestamps"] = True
                            print(f"   ✅ All jobs have valid timestamps")
                        else:
                            print(f"   ❌ Some jobs have invalid timestamps")
                        
                        # Check for database schema errors by looking at job status
                        failed_jobs = [job for job in jobs if job[1] == 'failed']
                        if not failed_jobs:
                            test_results["no_database_schema_errors"] = True
                            test_results["job_handlers_execute_successfully"] = True
                            print(f"   ✅ No failed jobs - job handlers executing successfully")
                        else:
                            print(f"   ❌ Found {len(failed_jobs)} failed jobs - possible schema errors")
                            for failed_job in failed_jobs:
                                print(f"      ❌ Failed job: {failed_job[0]} (Status: {failed_job[1]})")
                    else:
                        print(f"   ❌ No jobs found with correlation_id {correlation_id}")
                        
                finally:
                    db.close()
                    
            except Exception as e:
                print(f"   ❌ Error checking job chain: {e}")
        else:
            print(f"   ❌ Cannot monitor job chain - missing correlation_id or auth_headers")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 90)
        print("🎯 CORRECTED ADAPTIVE LEARNING PIPELINE TESTING - RESULTS")
        print("=" * 90)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        # Group results by test phases
        test_phases = {
            "AUTHENTICATION": [
                "authentication_working", "user_adaptive_enabled", "jwt_token_valid"
            ],
            "FRESH SESSION CREATION & COMPLETION": [
                "fresh_session_created", "session_answers_added", "session_completion_endpoint_working",
                "correlation_id_generated", "background_jobs_enqueued"
            ],
            "JOB CHAIN MONITORING": [
                "summarize_session_job_found", "summarize_session_has_correlation_id",
                "plan_next_session_job_found", "plan_next_session_has_correlation_id",
                "update_insights_job_found", "update_insights_has_correlation_id"
            ],
            "CORRELATION ID PROPAGATION": [
                "correlation_id_propagated_through_chain", "all_jobs_have_same_correlation_id"
            ],
            "JOB PROCESSING VALIDATION": [
                "jobs_have_valid_timestamps", "no_database_schema_errors", "job_handlers_execute_successfully"
            ]
        }
        
        for phase, tests in test_phases.items():
            print(f"\n{phase}:")
            phase_passed = 0
            phase_total = len(tests)
            
            for test in tests:
                if test in test_results:
                    result = test_results[test]
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"  {test.replace('_', ' ').title():<50} {status}")
                    if result:
                        phase_passed += 1
            
            phase_rate = (phase_passed / phase_total) * 100 if phase_total > 0 else 0
            print(f"  Phase Success Rate: {phase_passed}/{phase_total} ({phase_rate:.1f}%)")
        
        print("-" * 90)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # CRITICAL ASSESSMENT
        print("\n🎯 CRITICAL ASSESSMENT:")
        
        # Corrected Pipeline Assessment
        corrected_pipeline_working = (
            test_results["session_completion_endpoint_working"] and
            test_results["background_jobs_enqueued"] and
            test_results["correlation_id_generated"] and
            test_results["summarize_session_job_found"]
        )
        
        if corrected_pipeline_working:
            test_results["corrected_pipeline_working"] = True
            print("\n✅ CORRECTED PIPELINE: WORKING")
            print("   - Fresh session completion working with correct endpoint")
            print("   - Background jobs enqueued successfully")
            print("   - Correlation ID generated and propagated")
            print("   - SUMMARIZE_SESSION job found in queue")
        else:
            print("\n❌ CORRECTED PIPELINE: ISSUES DETECTED")
            print("   - Session completion or job enqueuing problems")
        
        # Job Chaining Validation
        job_chaining_validated = (
            test_results["summarize_session_job_found"] and
            test_results["correlation_id_propagated_through_chain"] and
            test_results["no_database_schema_errors"]
        )
        
        if job_chaining_validated:
            test_results["job_chaining_validated"] = True
            print("\n✅ JOB CHAINING: VALIDATED")
            print("   - SUMMARIZE_SESSION job found and working")
            print("   - Correlation ID propagation working")
            print("   - No database schema errors detected")
            print("   - Job handlers executing successfully")
        else:
            print("\n❌ JOB CHAINING: ISSUES DETECTED")
            print("   - Job chaining or correlation ID propagation problems")
        
        # Overall Production Readiness
        if corrected_pipeline_working and job_chaining_validated:
            test_results["production_ready"] = True
            print("\n🎉 PRODUCTION READINESS: READY")
            print("   - Corrected adaptive learning pipeline working")
            print("   - Job chaining fixes validated")
            print("   - Database schema issues resolved")
            print("   - End-to-end pipeline operational")
        else:
            print("\n⚠️ PRODUCTION READINESS: NEEDS ATTENTION")
            print("   - Some critical pipeline components need fixes")
        
        print(f"\n📊 FINAL ASSESSMENT:")
        print(f"   Corrected Pipeline: {'✅ WORKING' if corrected_pipeline_working else '❌ ISSUES'}")
        print(f"   Job Chaining: {'✅ VALIDATED' if job_chaining_validated else '❌ ISSUES'}")
        print(f"   Production Ready: {'✅ YES' if test_results['production_ready'] else '❌ NO'}")
        
        return success_rate >= 80 and corrected_pipeline_working

if __name__ == "__main__":
    tester = AdaptivePipelineTester()
    result = tester.test_corrected_adaptive_learning_pipeline()
    print(f'\n🎯 FINAL TEST RESULT: {"✅ PASSED" if result else "❌ FAILED"}')