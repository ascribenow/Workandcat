#!/usr/bin/env python3

import requests
import json
import uuid
import sys
from datetime import datetime
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DoubtsSystemTester:
    def __init__(self):
        self.base_url = "https://llm-prompt-repair.preview.emergentagent.com/api"
        self.auth_headers = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate with the test user"""
        print("🔐 AUTHENTICATING...")
        
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
                self.user_id = data.get('user', {}).get('id')
                
                self.auth_headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                print(f"✅ Authentication successful")
                print(f"📊 User ID: {self.user_id}")
                print(f"📊 Token length: {len(token)} chars")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_sample_question(self):
        """Get a sample question for testing"""
        print("\n📚 GETTING SAMPLE QUESTION...")
        
        try:
            response = requests.get(
                f"{self.base_url}/questions?limit=1",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                questions = response.json()
                if questions and len(questions) > 0:
                    question = questions[0]
                    question_id = question.get('id')
                    stem = question.get('stem', '')
                    
                    print(f"✅ Sample question retrieved")
                    print(f"📊 Question ID: {question_id}")
                    print(f"📊 Question preview: {stem[:100]}...")
                    return question_id, question
                else:
                    print("❌ No questions returned")
                    return None, None
            else:
                print(f"❌ Failed to get questions: {response.status_code}")
                print(f"Response: {response.text}")
                return None, None
                
        except Exception as e:
            print(f"❌ Error getting questions: {e}")
            return None, None
    
    def test_doubts_api(self, question_id):
        """Test the doubts API with a real question"""
        print(f"\n🤔 TESTING DOUBTS API...")
        
        session_id = str(uuid.uuid4())
        doubt_message = "Can you explain this solution step by step? I'm having trouble understanding the approach."
        
        doubt_data = {
            "question_id": question_id,
            "session_id": session_id,
            "message": doubt_message
        }
        
        print(f"📊 Request data:")
        print(f"   Question ID: {question_id}")
        print(f"   Session ID: {session_id}")
        print(f"   Message: {doubt_message}")
        
        try:
            response = requests.post(
                f"{self.base_url}/doubts/ask",
                json=doubt_data,
                headers=self.auth_headers,
                timeout=60,
                verify=False
            )
            
            print(f"\n📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ API returned 200 OK")
                    print(f"📊 Response structure:")
                    
                    for key, value in data.items():
                        if key == 'response' and value:
                            print(f"   {key}: {len(str(value))} chars - '{str(value)[:100]}...'")
                        else:
                            print(f"   {key}: {value}")
                    
                    # Check critical fields
                    success = data.get('success', False)
                    ai_response = data.get('response')
                    error = data.get('error')
                    
                    if success and ai_response and len(str(ai_response).strip()) > 0:
                        print(f"\n🎉 SUCCESS: Doubts API working correctly!")
                        print(f"✅ API returns success=True")
                        print(f"✅ Response field populated with {len(str(ai_response))} characters")
                        print(f"✅ AI generated contextual response")
                        return True, data
                    elif error:
                        print(f"\n❌ ERROR: {error}")
                        if "AI service temporarily unavailable" in str(error):
                            print(f"🚨 CRITICAL: AI service unavailable!")
                        return False, data
                    else:
                        print(f"\n❌ ISSUE: Response field empty or missing")
                        print(f"📊 Success: {success}")
                        print(f"📊 Response: {repr(ai_response)}")
                        return False, data
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"Raw response: {response.text}")
                    return False, None
            else:
                print(f"❌ API returned {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Raw error: {response.text}")
                return False, None
                
        except Exception as e:
            print(f"❌ Request error: {e}")
            return False, None
    
    def test_conversation_history(self, question_id):
        """Test conversation history endpoint"""
        print(f"\n💬 TESTING CONVERSATION HISTORY...")
        
        try:
            response = requests.get(
                f"{self.base_url}/doubts/{question_id}/history",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 History response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])
                message_count = data.get('message_count', 0)
                
                print(f"✅ History endpoint working")
                print(f"📊 Messages in history: {len(messages)}")
                print(f"📊 Message count: {message_count}")
                
                if messages:
                    print(f"📊 Message types:")
                    for i, msg in enumerate(messages):
                        role = msg.get('role', 'unknown')
                        content_len = len(str(msg.get('content', '')))
                        print(f"   {i+1}. {role}: {content_len} chars")
                
                return True, data
            else:
                print(f"❌ History failed: {response.status_code}")
                return False, None
                
        except Exception as e:
            print(f"❌ History error: {e}")
            return False, None
    
    def test_admin_endpoint(self):
        """Test admin conversations endpoint"""
        print(f"\n👨‍💼 TESTING ADMIN ENDPOINT...")
        
        try:
            response = requests.get(
                f"{self.base_url}/doubts/admin/conversations",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Admin response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('statistics', {})
                
                print(f"✅ Admin endpoint working")
                print(f"📊 Statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                
                return True, data
            else:
                print(f"❌ Admin endpoint failed: {response.status_code}")
                return False, None
                
        except Exception as e:
            print(f"❌ Admin endpoint error: {e}")
            return False, None
    
    def run_comprehensive_test(self):
        """Run comprehensive doubts system test"""
        print("🎯 COMPREHENSIVE DOUBTS/CHAT SYSTEM TEST")
        print("=" * 80)
        print("OBJECTIVE: Test complete doubts system end-to-end")
        print("USER: sp@theskinmantra.com (reported 'Ask Twelvr not working')")
        print("=" * 80)
        
        results = {
            "authentication": False,
            "question_retrieval": False,
            "doubts_api": False,
            "conversation_history": False,
            "admin_endpoint": False,
            "overall_success": False
        }
        
        # Step 1: Authenticate
        if not self.authenticate():
            print("\n❌ CRITICAL: Authentication failed - cannot proceed")
            return results
        results["authentication"] = True
        
        # Step 2: Get sample question
        question_id, question_data = self.get_sample_question()
        if not question_id:
            print("\n❌ CRITICAL: Cannot get sample question - cannot proceed")
            return results
        results["question_retrieval"] = True
        
        # Step 3: Test doubts API
        doubts_success, doubts_data = self.test_doubts_api(question_id)
        results["doubts_api"] = doubts_success
        
        # Step 4: Test conversation history
        history_success, history_data = self.test_conversation_history(question_id)
        results["conversation_history"] = history_success
        
        # Step 5: Test admin endpoint
        admin_success, admin_data = self.test_admin_endpoint()
        results["admin_endpoint"] = admin_success
        
        # Overall assessment
        core_working = results["authentication"] and results["doubts_api"]
        results["overall_success"] = core_working
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        success_count = sum(results.values())
        total_tests = len(results)
        success_rate = (success_count / total_tests) * 100
        
        print(f"\nOverall Success Rate: {success_count}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical assessment
        if results["doubts_api"]:
            print(f"\n🎉 DOUBTS SYSTEM: WORKING")
            print(f"   ✅ API accessible and returns responses")
            print(f"   ✅ LLM integration functional")
            print(f"   ✅ Response content populated")
            print(f"   ✅ System ready for frontend use")
        else:
            print(f"\n❌ DOUBTS SYSTEM: BROKEN")
            print(f"   🚨 API not returning proper responses")
            print(f"   🚨 User's 'Ask Twelvr not working' report confirmed")
            
            if doubts_data and doubts_data.get('error'):
                error = doubts_data.get('error')
                print(f"   🔍 Error detected: {error}")
                
                if "AI service temporarily unavailable" in str(error):
                    print(f"   🔧 LIKELY CAUSE: Gemini API issues")
                    print(f"   🔧 CHECK: API key, model name, rate limits")
        
        return results

def main():
    tester = DoubtsSystemTester()
    results = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    if results["overall_success"]:
        print(f"\n✅ Test completed successfully")
        sys.exit(0)
    else:
        print(f"\n❌ Test failed - issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()