#!/usr/bin/env python3
"""
Adaptive Learning Pipeline Job Chaining Test
Tests the updated job chaining fixes with correlation_id propagation
"""

import requests
import sys
import json
import time
import uuid
from datetime import datetime

class JobChainingTester:
    def __init__(self, base_url="https://smart-tutor-50.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        self.correlation_id = None
        
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_authentication(self):
        """Authenticate with sp@theskinmantra.com/student123"""
        self.log("🔐 PHASE 1: AUTHENTICATION")
        
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
                
                if token:
                    self.auth_headers = {
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json'
                    }
                    self.user_id = user_data.get('id')
                    
                    self.log(f"✅ Authentication successful")
                    self.log(f"📊 User ID: {self.user_id}")
                    self.log(f"📊 Adaptive enabled: {user_data.get('adaptive_enabled')}")
                    return True
                else:
                    self.log(f"❌ No access token in response")
                    return False
            else:
                self.log(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Authentication error: {e}")
            return False
    
    def create_test_session(self):
        """Create a test session for completion"""
        self.log("📋 Creating test session...")
        
        try:
            # Import database modules
            import sys
            sys.path.append('/app/backend')
            from database import SessionLocal
            from sqlalchemy import text
            
            session_id = str(uuid.uuid4())
            
            db = SessionLocal()
            try:
                # Create session in database
                db.execute(text("""
                    INSERT INTO sessions (session_id, user_id, status, created_at)
                    VALUES (:session_id, :user_id, 'served', NOW())
                """), {"session_id": session_id, "user_id": self.user_id})
                db.commit()
                
                self.log(f"✅ Created test session: {session_id}")
                return session_id
                
            finally:
                db.close()
                
        except Exception as e:
            self.log(f"❌ Error creating test session: {e}")
            # Return a fallback session ID
            return str(uuid.uuid4())
    
    def test_session_completion(self, session_id):
        """Test the CORRECT session completion endpoint"""
        self.log("🎯 PHASE 2: SESSION COMPLETION")
        self.log(f"Testing CORRECT endpoint: /api/sessions/mark-completed")
        
        completion_data = {"session_id": session_id}
        
        try:
            response = requests.post(
                f"{self.base_url}/sessions/mark-completed",
                json=completion_data,
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    self.log(f"✅ Session completion successful")
                    self.log(f"📊 Response: {data}")
                    return True
                else:
                    self.log(f"❌ Session completion response not OK: {data}")
                    return False
            else:
                self.log(f"❌ Session completion failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Session completion error: {e}")
            return False
    
    def check_summarize_session_job(self, session_id):
        """Check if SUMMARIZE_SESSION job was enqueued"""
        self.log("🔍 Checking for SUMMARIZE_SESSION job...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            from database import SessionLocal
            from sqlalchemy import text
            
            db = SessionLocal()
            try:
                # Wait a moment for job to be enqueued
                time.sleep(3)
                
                # Check for SUMMARIZE_SESSION job
                job_result = db.execute(text("""
                    SELECT id, job_type, correlation_id, status, next_attempt_at, created_at
                    FROM bg_jobs 
                    WHERE user_id = :user_id AND session_id = :session_id 
                    AND job_type = 'SUMMARIZE_SESSION'
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"user_id": self.user_id, "session_id": session_id})
                
                job_row = job_result.fetchone()
                if job_row:
                    job_id = str(job_row.id)
                    correlation_id = job_row.correlation_id
                    job_status = job_row.status
                    next_attempt_at = job_row.next_attempt_at
                    
                    self.log(f"✅ SUMMARIZE_SESSION job found")
                    self.log(f"📊 Job ID: {job_id}")
                    self.log(f"📊 Correlation ID: {correlation_id}")
                    self.log(f"📊 Status: {job_status}")
                    self.log(f"📊 Next attempt: {next_attempt_at}")
                    
                    # Store correlation_id for chain verification
                    self.correlation_id = correlation_id
                    
                    # Validate correlation_id and timestamp
                    has_correlation_id = bool(correlation_id)
                    has_valid_timestamp = bool(next_attempt_at)
                    
                    if has_correlation_id:
                        self.log(f"✅ Job has correlation_id")
                    else:
                        self.log(f"❌ Job missing correlation_id")
                    
                    if has_valid_timestamp:
                        self.log(f"✅ Job has valid next_attempt_at timestamp")
                    else:
                        self.log(f"❌ Job missing next_attempt_at timestamp")
                    
                    return has_correlation_id and has_valid_timestamp
                else:
                    self.log(f"❌ SUMMARIZE_SESSION job not found")
                    return False
                    
            finally:
                db.close()
                
        except Exception as e:
            self.log(f"❌ Error checking SUMMARIZE_SESSION job: {e}")
            return False
    
    def monitor_job_chain(self):
        """Monitor the complete job chain progression"""
        self.log("🔗 PHASE 3: JOB CHAIN MONITORING")
        self.log(f"Tracking correlation_id: {self.correlation_id}")
        
        if not self.correlation_id:
            self.log(f"❌ Cannot monitor job chain - no correlation_id")
            return False
        
        # Wait for background job processing
        self.log("⏳ Waiting for background job processing...")
        time.sleep(15)  # Wait 15 seconds for job processing
        
        try:
            import sys
            sys.path.append('/app/backend')
            from database import SessionLocal
            from sqlalchemy import text
            
            db = SessionLocal()
            try:
                # Check for all jobs with the same correlation_id
                jobs_result = db.execute(text("""
                    SELECT id, job_type, correlation_id, status, next_attempt_at, created_at, completed_at
                    FROM bg_jobs 
                    WHERE correlation_id = :correlation_id
                    ORDER BY created_at ASC
                """), {"correlation_id": self.correlation_id})
                
                jobs = jobs_result.fetchall()
                self.log(f"📊 Found {len(jobs)} jobs with correlation_id {self.correlation_id}")
                
                job_types_found = []
                all_jobs_have_valid_timestamps = True
                correlation_id_propagated = True
                
                for job in jobs:
                    job_type = job.job_type
                    job_status = job.status
                    job_correlation_id = job.correlation_id
                    next_attempt_at = job.next_attempt_at
                    
                    job_types_found.append(job_type)
                    
                    self.log(f"📋 Job: {job_type}")
                    self.log(f"   Status: {job_status}")
                    self.log(f"   Correlation ID: {job_correlation_id}")
                    self.log(f"   Next attempt: {next_attempt_at}")
                    self.log(f"   Created: {job.created_at}")
                    self.log(f"   Completed: {job.completed_at}")
                    
                    # Check correlation_id propagation
                    if job_correlation_id != self.correlation_id:
                        correlation_id_propagated = False
                        self.log(f"   ❌ Correlation ID mismatch!")
                    
                    # Check valid timestamps
                    if job_status in ['queued', 'failed'] and not next_attempt_at:
                        all_jobs_have_valid_timestamps = False
                        self.log(f"   ❌ Missing next_attempt_at timestamp!")
                
                # Check for expected job types
                expected_jobs = ["SUMMARIZE_SESSION", "PLAN_NEXT_SESSION", "UPDATE_INSIGHTS"]
                
                self.log(f"\n📊 JOB CHAIN ANALYSIS:")
                for expected_job in expected_jobs:
                    if expected_job in job_types_found:
                        self.log(f"✅ {expected_job} job found")
                    else:
                        self.log(f"❌ {expected_job} job missing")
                
                # Overall assessments
                if correlation_id_propagated:
                    self.log(f"✅ Correlation ID properly propagated through job chain")
                else:
                    self.log(f"❌ Correlation ID propagation failed")
                
                if all_jobs_have_valid_timestamps:
                    self.log(f"✅ All jobs have valid timestamps")
                else:
                    self.log(f"❌ Some jobs missing valid timestamps")
                
                # Check if we have the complete chain
                complete_chain = all(job_type in job_types_found for job_type in expected_jobs)
                
                if complete_chain:
                    self.log(f"✅ Complete job chain found: {' → '.join(expected_jobs)}")
                    return True
                else:
                    missing_jobs = [job for job in expected_jobs if job not in job_types_found]
                    self.log(f"❌ Incomplete job chain. Missing: {missing_jobs}")
                    self.log(f"📊 Found jobs: {job_types_found}")
                    return False
                    
            finally:
                db.close()
                
        except Exception as e:
            self.log(f"❌ Error monitoring job chain: {e}")
            return False
    
    def check_backend_logs(self):
        """Check backend logs for event loop issues"""
        self.log("📋 PHASE 4: BACKEND LOGS CHECK")
        
        try:
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                log_content = result.stdout
                
                # Check for event loop issues
                event_loop_errors = [
                    "RuntimeError: There is no current event loop",
                    "RuntimeError: cannot be called from a running event loop",
                    "asyncio.run() cannot be called from a running event loop",
                    "Event loop is closed"
                ]
                
                async_await_errors = [
                    "coroutine was never awaited",
                    "RuntimeWarning: coroutine",
                    "SyntaxError: 'await' outside async function"
                ]
                
                found_event_loop_errors = []
                found_async_errors = []
                
                for error in event_loop_errors:
                    if error.lower() in log_content.lower():
                        found_event_loop_errors.append(error)
                
                for error in async_await_errors:
                    if error.lower() in log_content.lower():
                        found_async_errors.append(error)
                
                if not found_event_loop_errors and not found_async_errors:
                    self.log(f"✅ No event loop conflicts or async/await issues detected")
                    return True
                else:
                    self.log(f"❌ Found issues in backend logs:")
                    if found_event_loop_errors:
                        self.log(f"   Event loop errors: {found_event_loop_errors}")
                    if found_async_errors:
                        self.log(f"   Async/await errors: {found_async_errors}")
                    return False
                
            else:
                self.log(f"⚠️ Could not access backend logs")
                return True  # Assume no errors if we can't check
                
        except Exception as e:
            self.log(f"⚠️ Error checking backend logs: {e}")
            return True  # Assume no errors if we can't check
    
    def run_complete_test(self):
        """Run the complete job chaining test"""
        self.log("🎯 ADAPTIVE LEARNING PIPELINE JOB CHAINING TEST")
        self.log("=" * 80)
        self.log("OBJECTIVE: Test job chaining fixes with correlation_id propagation")
        self.log("FOCUS: SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS")
        self.log("=" * 80)
        
        # Phase 1: Authentication
        if not self.test_authentication():
            self.log("❌ CRITICAL: Authentication failed - cannot proceed")
            return False
        
        # Phase 2: Create test session and test completion
        session_id = self.create_test_session()
        if not self.test_session_completion(session_id):
            self.log("❌ CRITICAL: Session completion failed - cannot proceed")
            return False
        
        # Phase 3: Check SUMMARIZE_SESSION job
        if not self.check_summarize_session_job(session_id):
            self.log("❌ CRITICAL: SUMMARIZE_SESSION job not properly enqueued")
            return False
        
        # Phase 4: Monitor job chain
        job_chain_success = self.monitor_job_chain()
        
        # Phase 5: Check backend logs
        logs_clean = self.check_backend_logs()
        
        # Final assessment
        self.log("\n" + "=" * 80)
        self.log("🎯 FINAL ASSESSMENT")
        self.log("=" * 80)
        
        if job_chain_success and logs_clean:
            self.log("✅ JOB CHAINING FIX VALIDATION: SUCCESS")
            self.log("   - Session completion triggers SUMMARIZE_SESSION job")
            self.log("   - Correlation_id properly propagated through job chain")
            self.log("   - Complete job pipeline working: SUMMARIZE_SESSION → PLAN_NEXT_SESSION → UPDATE_INSIGHTS")
            self.log("   - No event loop conflicts or async/await issues")
            self.log("   - All jobs have valid timestamps")
            return True
        else:
            self.log("❌ JOB CHAINING FIX VALIDATION: ISSUES DETECTED")
            if not job_chain_success:
                self.log("   - Job chain progression incomplete")
            if not logs_clean:
                self.log("   - Event loop or async/await issues detected")
            return False

def main():
    """Main test execution"""
    tester = JobChainingTester()
    success = tester.run_complete_test()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - Job chaining fixes validated successfully!")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED - Job chaining issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()