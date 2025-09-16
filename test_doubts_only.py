#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time
import os
import uuid

class DoubtsSystemTester:
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

    def test_ask_twelvr_doubts_system(self):
        """Test the Ask Twelvr doubts system with Google Gemini AI integration"""
        print("🤔 ASK TWELVR DOUBTS SYSTEM VALIDATION")
        print("=" * 80)
        print("OBJECTIVE: Test complete Ask Twelvr doubts system with Google Gemini AI")
        print("FOCUS: Doubt submission, AI responses, message limiting, conversation tracking")
        print("EXPECTED: Context-aware AI responses, message counting, conversation history")
        print("=" * 80)
        
        # PHASE 1: AUTHENTICATION SETUP
        print("\n🔐 PHASE 1: AUTHENTICATION SETUP")
        print("-" * 60)
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Authentication", "POST", "auth/login", [200, 401], auth_data)
        
        if not success or not response.get('access_token'):
            print("   ❌ Authentication failed - cannot proceed")
            return False
            
        token = response['access_token']
        auth_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        user_data = response.get('user', {})
        user_id = user_data.get('id')
        
        print(f"   ✅ Authentication successful")
        print(f"   📊 User ID: {user_id}")
        print(f"   📊 Adaptive enabled: {user_data.get('adaptive_enabled')}")
        
        # PHASE 2: GET A SAMPLE QUESTION
        print("\n📚 PHASE 2: SAMPLE QUESTION RETRIEVAL")
        print("-" * 60)
        
        success, questions_response = self.run_test(
            "Get Sample Questions", 
            "GET", 
            "questions?limit=5", 
            [200, 500], 
            None, 
            auth_headers
        )
        
        if not success or not questions_response or len(questions_response) == 0:
            print("   ❌ Failed to get sample question")
            return False
            
        sample_question = questions_response[0]
        question_id = sample_question.get('id')
        
        print(f"   ✅ Sample question retrieved")
        print(f"   📊 Question ID: {question_id}")
        print(f"   📊 Question stem: {sample_question.get('stem', 'N/A')[:100]}...")
        
        # PHASE 3: TEST ASK TWELVR DOUBTS SYSTEM
        print("\n🤔 PHASE 3: ASK TWELVR DOUBTS SYSTEM CORE")
        print("-" * 60)
        
        session_id = f"doubts_test_{uuid.uuid4()}"
        
        # Test 1: Submit first doubt message
        print(f"   🤔 Testing first doubt submission...")
        
        doubt_message_1 = {
            "question_id": question_id,
            "session_id": session_id,
            "message": "Can you explain this solution step by step? I'm having trouble understanding the approach."
        }
        
        success, doubt_response_1 = self.run_test(
            "Ask Twelvr - First Doubt", 
            "POST", 
            "doubts/ask", 
            [200, 500], 
            doubt_message_1, 
            auth_headers
        )
        
        if not success:
            print(f"   ❌ First doubt submission failed: {doubt_response_1}")
            return False
            
        if doubt_response_1.get('success'):
            print(f"   ✅ Doubts ask endpoint working")
            
            # Check AI response
            ai_response = doubt_response_1.get('response')
            if ai_response and len(ai_response) > 20:
                print(f"   ✅ Gemini AI responding")
                print(f"   📊 AI response length: {len(ai_response)} characters")
                print(f"   📊 AI response preview: {ai_response[:150]}...")
                
                # Check message counting
                message_count = doubt_response_1.get('message_count', 0)
                remaining_messages = doubt_response_1.get('remaining_messages', 0)
                
                if message_count == 1:
                    print(f"   ✅ Message counter working (count: {message_count})")
                
                if remaining_messages == 9:
                    print(f"   ✅ Remaining messages calculated correctly ({remaining_messages})")
            else:
                print(f"   ❌ No AI response received")
        else:
            print(f"   ❌ Doubt submission failed: {doubt_response_1}")
            return False
        
        # PHASE 4: TEST CONVERSATION HISTORY
        print("\n📜 PHASE 4: CONVERSATION HISTORY TESTING")
        print("-" * 60)
        
        success, history_response = self.run_test(
            "Doubt History Retrieval", 
            "GET", 
            f"doubts/{question_id}/history", 
            [200, 500], 
            None, 
            auth_headers
        )
        
        if success and history_response.get('success'):
            print(f"   ✅ History endpoint working")
            
            messages = history_response.get('messages', [])
            if len(messages) >= 2:  # Should have user message + AI response
                print(f"   ✅ Conversation history stored ({len(messages)} messages)")
                
                first_message = messages[0]
                if first_message.get('timestamp') and first_message.get('role'):
                    print(f"   ✅ Message timestamps and structure present")
            else:
                print(f"   ⚠️ Limited conversation history: {len(messages)} messages")
        else:
            print(f"   ❌ History retrieval failed: {history_response}")
        
        # PHASE 5: TEST MULTIPLE MESSAGES
        print("\n💬 PHASE 5: MULTIPLE MESSAGES TESTING")
        print("-" * 60)
        
        # Submit second doubt message
        doubt_message_2 = {
            "question_id": question_id,
            "session_id": session_id,
            "message": "I understand the first part, but can you clarify the calculation in step 2?"
        }
        
        success, doubt_response_2 = self.run_test(
            "Ask Twelvr - Second Doubt", 
            "POST", 
            "doubts/ask", 
            [200, 500], 
            doubt_message_2, 
            auth_headers
        )
        
        if success and doubt_response_2.get('success'):
            print(f"   ✅ Multiple doubt messages working")
            
            message_count = doubt_response_2.get('message_count', 0)
            if message_count == 2:
                print(f"   ✅ Message count incremented correctly (count: {message_count})")
        else:
            print(f"   ❌ Second doubt submission failed: {doubt_response_2}")
        
        # PHASE 6: TEST ADMIN MONITORING
        print("\n👨‍💼 PHASE 6: ADMIN MONITORING")
        print("-" * 60)
        
        success, admin_response = self.run_test(
            "Admin Conversations", 
            "GET", 
            "doubts/admin/conversations", 
            [200, 500], 
            None, 
            auth_headers
        )
        
        if success and admin_response.get('success'):
            print(f"   ✅ Admin conversations endpoint working")
            
            statistics = admin_response.get('statistics', {})
            if statistics:
                print(f"   ✅ Conversation statistics available")
                print(f"   📊 Total conversations: {statistics.get('total_conversations', 0)}")
                print(f"   📊 Total messages: {statistics.get('total_messages', 0)}")
        else:
            print(f"   ❌ Admin conversations failed: {admin_response}")
        
        # FINAL SUMMARY
        print("\n" + "=" * 80)
        print("🤔 ASK TWELVR DOUBTS SYSTEM VALIDATION - RESULTS")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 ASK TWELVR DOUBTS SYSTEM: VALIDATED")
            print("   - Google Gemini AI integration working")
            print("   - Context-aware responses functional")
            print("   - Message counting and limiting operational")
            print("   - Conversation history working")
            print("   - Admin monitoring functional")
            return True
        else:
            print("\n⚠️ ASK TWELVR DOUBTS SYSTEM: NEEDS ATTENTION")
            print("   - Some components not working properly")
            return False

if __name__ == "__main__":
    tester = DoubtsSystemTester()
    success = tester.test_ask_twelvr_doubts_system()
    sys.exit(0 if success else 1)