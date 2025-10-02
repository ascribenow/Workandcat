#!/usr/bin/env python3
"""
Test script to investigate the "AI service temporarily unavailable" error
reported by the user in the chat interface.
"""

import requests
import json
import sys
import time
import uuid

class DoubtsIssueInvestigator:
    def __init__(self, base_url="https://smart-tutor-50.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def log(self, message, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method, endpoint, data=None, headers=None, expected_status=None):
        """Make HTTP request and return success status and response"""
        try:
            url = f"{self.base_url}/{endpoint}"
            
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30, verify=False)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30, verify=False)
            else:
                self.log(f"Unsupported method: {method}", "ERROR")
                return False, None
            
            # Check status
            if expected_status:
                if isinstance(expected_status, list):
                    status_ok = response.status_code in expected_status
                else:
                    status_ok = response.status_code == expected_status
            else:
                status_ok = 200 <= response.status_code < 300
            
            try:
                response_data = response.json()
            except:
                response_data = {"status_code": response.status_code, "text": response.text}
            
            return status_ok, response_data
            
        except Exception as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            return False, {"error": str(e)}
    
    def authenticate(self):
        """Authenticate with the test user"""
        self.log("🔐 Authenticating with sp@theskinmantra.com/student123")
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, response = self.make_request("POST", "auth/login", auth_data, expected_status=[200, 401])
        
        if success and response.get('access_token'):
            token = response['access_token']
            self.auth_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            user_data = response.get('user', {})
            self.user_id = user_data.get('id')
            adaptive_enabled = user_data.get('adaptive_enabled', False)
            
            self.log(f"✅ Authentication successful")
            self.log(f"📊 JWT Token length: {len(token)} characters")
            self.log(f"📊 User ID: {self.user_id}")
            self.log(f"📊 Adaptive enabled: {adaptive_enabled}")
            
            return True
        else:
            self.log(f"❌ Authentication failed: {response}", "ERROR")
            return False
    
    def get_sample_question(self):
        """Get a sample question for doubts testing"""
        self.log("📚 Getting sample question for doubts testing")
        
        success, response = self.make_request("GET", "questions?limit=1", headers=self.auth_headers)
        
        if success and isinstance(response, list) and len(response) > 0:
            question = response[0]
            question_id = question.get('id')
            stem = question.get('stem', '')[:100] + "..."
            
            self.log(f"✅ Sample question retrieved")
            self.log(f"📊 Question ID: {question_id}")
            self.log(f"📊 Question stem: {stem}")
            
            return question_id
        else:
            self.log(f"❌ Failed to get sample question: {response}", "ERROR")
            # Return a mock question ID for testing
            mock_id = "test-question-id-for-doubts"
            self.log(f"⚠️ Using mock question ID: {mock_id}")
            return mock_id
    
    def test_doubts_ask_endpoint(self, question_id):
        """Test the /api/doubts/ask endpoint that's causing the AI service error"""
        self.log("💬 Testing /api/doubts/ask endpoint")
        
        doubt_message = "Can you explain this solution step by step? I'm having trouble understanding the approach."
        
        doubt_data = {
            "question_id": question_id,
            "message": doubt_message
        }
        
        self.log(f"📝 Sending doubt message: '{doubt_message[:50]}...'")
        
        success, response = self.make_request(
            "POST", 
            "doubts/ask", 
            doubt_data, 
            headers=self.auth_headers,
            expected_status=[200, 400, 500, 503]
        )
        
        if success:
            self.log(f"✅ Doubts ask endpoint responded successfully")
            
            if response.get('response'):
                ai_response = response.get('response', '')
                response_length = len(ai_response)
                
                self.log(f"✅ AI response generated successfully")
                self.log(f"📊 AI response length: {response_length} characters")
                self.log(f"📊 AI response preview: {ai_response[:100]}...")
                
                return True, "SUCCESS"
            
            elif response.get('error'):
                error_message = response.get('error', '')
                self.log(f"❌ Doubts ask returned error: {error_message}", "ERROR")
                
                if 'AI service temporarily unavailable' in error_message:
                    self.log(f"🎯 REPRODUCED: 'AI service temporarily unavailable' error!", "CRITICAL")
                    return False, "AI_SERVICE_UNAVAILABLE"
                
                if 'api key' in error_message.lower():
                    self.log(f"🔍 API key issue detected", "CRITICAL")
                    return False, "API_KEY_ISSUE"
                
                if 'timeout' in error_message.lower():
                    self.log(f"🔍 Timeout issue detected", "CRITICAL")
                    return False, "TIMEOUT_ISSUE"
                
                return False, "OTHER_ERROR"
            
            else:
                self.log(f"⚠️ Unexpected response format: {response}")
                return False, "UNEXPECTED_RESPONSE"
        
        else:
            self.log(f"❌ Doubts ask endpoint failed: {response}", "ERROR")
            
            status_code = response.get('status_code')
            if status_code == 503:
                self.log(f"🎯 REPRODUCED: Service unavailable (503) - matches user report!", "CRITICAL")
                return False, "SERVICE_UNAVAILABLE_503"
            elif status_code == 500:
                self.log(f"🎯 REPRODUCED: Internal server error (500)", "CRITICAL")
                return False, "INTERNAL_SERVER_ERROR"
            
            return False, "REQUEST_FAILED"
    
    def test_session_completion(self):
        """Test session completion endpoint for 500 errors"""
        self.log("🎯 Testing session completion endpoint")
        
        # Get user sessions first
        success, response = self.make_request("GET", "session/list?limit=5", headers=self.auth_headers)
        
        if success and response.get('sessions'):
            sessions = response.get('sessions', [])
            self.log(f"📊 Found {len(sessions)} sessions for user")
            
            # Find a session to test
            test_session_id = None
            for session in sessions:
                session_id = session.get('session_id')
                status = session.get('status')
                answered = session.get('answered_count', 0)
                
                self.log(f"📋 Session {session_id[:8]}: status={status}, answered={answered}")
                
                if answered >= 8:  # Session with some answers
                    test_session_id = session_id
                    break
            
            if not test_session_id and sessions:
                test_session_id = sessions[0].get('session_id')
            
            if test_session_id:
                self.log(f"🎯 Testing completion with session: {test_session_id[:8]}")
                
                completion_data = {"session_id": test_session_id}
                
                success, response = self.make_request(
                    "POST", 
                    "session/complete", 
                    completion_data, 
                    headers=self.auth_headers,
                    expected_status=[200, 400, 404, 500]
                )
                
                if success:
                    self.log(f"✅ Session completion endpoint working")
                    
                    if response.get('adaptive_processing'):
                        self.log(f"📊 Adaptive processing: {response.get('adaptive_processing')}")
                    
                    return True, "SUCCESS"
                else:
                    status_code = response.get('status_code')
                    if status_code == 500:
                        self.log(f"🎯 REPRODUCED: 500 error in session completion!", "CRITICAL")
                        return False, "SESSION_COMPLETION_500"
                    else:
                        self.log(f"❌ Session completion failed: {response}", "ERROR")
                        return False, "SESSION_COMPLETION_FAILED"
            else:
                self.log(f"⚠️ No sessions available for testing")
                return False, "NO_SESSIONS"
        else:
            self.log(f"❌ Failed to get user sessions: {response}", "ERROR")
            return False, "SESSIONS_LIST_FAILED"
    
    def check_backend_logs(self):
        """Check backend logs for errors"""
        self.log("📋 Checking backend logs for errors")
        
        try:
            import subprocess
            result = subprocess.run(
                ["tail", "-n", "50", "/var/log/supervisor/backend.err.log"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.stdout:
                self.log("📋 Recent backend error logs:")
                for line in result.stdout.strip().split('\n')[-10:]:  # Last 10 lines
                    if line.strip():
                        self.log(f"   {line}")
            else:
                self.log("✅ No recent backend error logs")
                
        except Exception as e:
            self.log(f"⚠️ Could not check backend logs: {e}")
    
    def investigate_issue(self):
        """Main investigation method"""
        self.log("🔍 Starting investigation of 'AI service temporarily unavailable' error")
        self.log("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate():
            self.log("❌ Cannot proceed without authentication", "CRITICAL")
            return False
        
        # Step 2: Get sample question
        question_id = self.get_sample_question()
        if not question_id:
            self.log("❌ Cannot proceed without a question ID", "CRITICAL")
            return False
        
        # Step 3: Test doubts/ask endpoint
        self.log("\n" + "=" * 50)
        doubts_success, doubts_result = self.test_doubts_ask_endpoint(question_id)
        
        # Step 4: Test session completion
        self.log("\n" + "=" * 50)
        session_success, session_result = self.test_session_completion()
        
        # Step 5: Check backend logs
        self.log("\n" + "=" * 50)
        self.check_backend_logs()
        
        # Step 6: Summary and recommendations
        self.log("\n" + "=" * 80)
        self.log("🎯 INVESTIGATION SUMMARY")
        self.log("=" * 80)
        
        if doubts_result == "AI_SERVICE_UNAVAILABLE":
            self.log("🎯 ROOT CAUSE IDENTIFIED: 'AI service temporarily unavailable' error reproduced", "CRITICAL")
            self.log("💡 RECOMMENDATION: Check LLM API keys and service configuration")
            
        elif doubts_result == "API_KEY_ISSUE":
            self.log("🎯 ROOT CAUSE IDENTIFIED: API key configuration issue", "CRITICAL")
            self.log("💡 RECOMMENDATION: Verify OpenAI/Gemini API keys in environment")
            
        elif doubts_result == "TIMEOUT_ISSUE":
            self.log("🎯 ROOT CAUSE IDENTIFIED: LLM service timeout", "CRITICAL")
            self.log("💡 RECOMMENDATION: Check network connectivity and API rate limits")
            
        elif doubts_result == "SERVICE_UNAVAILABLE_503":
            self.log("🎯 ROOT CAUSE IDENTIFIED: Service unavailable (503)", "CRITICAL")
            self.log("💡 RECOMMENDATION: Check backend service health and dependencies")
            
        elif doubts_result == "SUCCESS":
            self.log("✅ DOUBTS SYSTEM: Working correctly")
            self.log("💡 The 'AI service temporarily unavailable' error may be intermittent")
            
        else:
            self.log(f"⚠️ DOUBTS SYSTEM: Issue detected - {doubts_result}")
        
        if session_result == "SESSION_COMPLETION_500":
            self.log("🎯 SESSION COMPLETION: 500 errors confirmed (matches logs)", "CRITICAL")
            self.log("💡 RECOMMENDATION: Check session completion logic and database queries")
            
        elif session_result == "SUCCESS":
            self.log("✅ SESSION COMPLETION: Working correctly")
            
        else:
            self.log(f"⚠️ SESSION COMPLETION: Issue detected - {session_result}")
        
        # Overall assessment
        if doubts_success and session_success:
            self.log("\n🎉 OVERALL ASSESSMENT: Systems appear to be working")
            self.log("💡 User issues may be resolved or intermittent")
            return True
        else:
            self.log("\n❌ OVERALL ASSESSMENT: Critical issues identified")
            self.log("💡 These issues explain the user's 'Twelvr is not working' report")
            return False

def main():
    print("🎯 Twelvr Chat Interface Issue Investigation")
    print("Investigating: 'AI service temporarily unavailable' error")
    print("=" * 80)
    
    investigator = DoubtsIssueInvestigator()
    success = investigator.investigate_issue()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ Investigation completed - systems appear functional")
    else:
        print("❌ Investigation completed - critical issues identified")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)