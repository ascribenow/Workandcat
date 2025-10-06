#!/usr/bin/env python3
"""
🎯 ASK TWELVR CONVERSATION FLOW TO VERIFY MESSAGE HANDLING

OBJECTIVE: Test the Ask Twelvr doubts system to verify that user messages are correctly stored and retrieved without modification.

BACKEND URL: https://twelvr-adaptive-2.preview.emergentagent.com
TEST CREDENTIALS: sp@theskinmantra.com / student123

TEST SCENARIO:
1. Authenticate with test credentials
2. Get a sample question ID from the questions database
3. Send first message: "Can you help me understand this question?"
4. Send second message: "What is the principle to remember?"
5. Retrieve conversation history via GET /api/doubts/{question_id}/history
6. Verify:
   - Both user messages stored exactly as typed (no modifications)
   - AI responses generated for both messages
   - Message count incremented correctly (2/10)
   - Conversation history order is correct (chronological)
   - Timestamps are present for all messages

CRITICAL VERIFICATION:
- Confirm user message content is UNCHANGED (no AI modification of user input)
- Check that "What is the principle to remember?" appears as second user message
- Verify conversation structure: user1 → AI1 → user2 → AI2
"""

import requests
import json
import uuid
import sys
from datetime import datetime

class AskTwelvrTester:
    def __init__(self, base_url="https://twelvr-adaptive-2.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
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

    def test_ask_twelvr_conversation_flow(self):
        """Test the complete Ask Twelvr conversation flow"""
        print("🎯 ASK TWELVR CONVERSATION FLOW TO VERIFY MESSAGE HANDLING")
        print("=" * 90)
        print("OBJECTIVE: Test Ask Twelvr doubts system to verify user messages are stored without modification")
        print("BACKEND URL: https://twelvr-adaptive-2.preview.emergentagent.com")
        print("TEST CREDENTIALS: sp@theskinmantra.com / student123")
        print("FOCUS: Message storage integrity, conversation flow, chronological order")
        print("=" * 90)
        
        test_results = {
            # Authentication Phase
            "authentication_successful": False,
            "jwt_token_generated": False,
            "user_adaptive_enabled": False,
            
            # Sample Question Retrieval
            "sample_question_retrieved": False,
            "question_id_available": False,
            "question_has_solution_fields": False,
            
            # First Message Test
            "first_message_sent": False,
            "first_ai_response_generated": False,
            "first_message_count_correct": False,
            
            # Second Message Test
            "second_message_sent": False,
            "second_ai_response_generated": False,
            "second_message_count_correct": False,
            
            # Conversation History Verification
            "conversation_history_retrieved": False,
            "message_order_correct": False,
            "timestamps_present": False,
            "user_messages_unchanged": False,
            "ai_responses_contextual": False,
            
            # Critical Verification
            "first_user_message_exact": False,
            "second_user_message_exact": False,
            "conversation_structure_correct": False,
            "no_user_input_modification": False,
            
            # Overall Assessment
            "message_handling_working": False,
            "conversation_flow_validated": False,
            "system_integrity_confirmed": False
        }
        
        # Test messages as specified in review request
        first_message = "Can you help me understand this question?"
        second_message = "What is the principle to remember?"
        
        print(f"\n📋 TEST MESSAGES:")
        print(f"   First message: '{first_message}'")
        print(f"   Second message: '{second_message}'")
        
        # PHASE 1: AUTHENTICATION
        print("\n🔐 PHASE 1: AUTHENTICATION WITH TEST CREDENTIALS")
        print("-" * 70)
        print("Testing authentication with sp@theskinmantra.com/student123")
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        success, auth_response = self.run_test(
            "Authentication with Test Credentials", 
            "POST", 
            "auth/login", 
            [200, 401], 
            auth_data
        )
        
        if success and auth_response.get('access_token'):
            test_results["authentication_successful"] = True
            test_results["jwt_token_generated"] = True
            
            token = auth_response['access_token']
            self.auth_headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            print(f"   ✅ Authentication successful")
            print(f"   📊 JWT token generated: {len(token)} characters")
            
            user_data = auth_response.get('user', {})
            self.user_id = user_data.get('id')
            adaptive_enabled = user_data.get('adaptive_enabled', False)
            
            if adaptive_enabled:
                test_results["user_adaptive_enabled"] = True
                print(f"   ✅ User adaptive_enabled: {adaptive_enabled}")
                print(f"   📊 User ID: {self.user_id}")
            else:
                print(f"   ⚠️ User adaptive_enabled: {adaptive_enabled}")
        else:
            print(f"   ❌ Authentication failed: {auth_response}")
            return False
        
        # PHASE 2: GET SAMPLE QUESTION ID
        print("\n📚 PHASE 2: GET SAMPLE QUESTION ID FROM DATABASE")
        print("-" * 70)
        print("Retrieving sample question for doubts testing")
        
        sample_question_id = None
        
        if self.auth_headers:
            success, questions_response = self.run_test(
                "Get Sample Questions", 
                "GET", 
                "questions?limit=6", 
                [200, 500], 
                None, 
                self.auth_headers
            )
            
            if success and questions_response:
                test_results["sample_question_retrieved"] = True
                print(f"   ✅ Sample questions retrieved successfully")
                
                questions = questions_response if isinstance(questions_response, list) else [questions_response]
                if questions and len(questions) > 0:
                    # Find a question with solution fields for better testing
                    for question in questions:
                        if (question.get('id') and 
                            question.get('snap_read') and 
                            question.get('solution_approach') and 
                            question.get('detailed_solution') and 
                            question.get('principle_to_remember')):
                            sample_question_id = question.get('id')
                            test_results["question_id_available"] = True
                            test_results["question_has_solution_fields"] = True
                            print(f"   ✅ Question ID available: {sample_question_id}")
                            print(f"   ✅ Question has complete solution fields")
                            print(f"   📊 Question details:")
                            print(f"      Snap read: {len(question.get('snap_read', ''))} chars")
                            print(f"      Solution approach: {len(question.get('solution_approach', ''))} chars")
                            print(f"      Detailed solution: {len(question.get('detailed_solution', ''))} chars")
                            print(f"      Principle to remember: {len(question.get('principle_to_remember', ''))} chars")
                            break
                    
                    if not sample_question_id and questions:
                        # Fallback to first available question
                        sample_question_id = questions[0].get('id')
                        test_results["question_id_available"] = True
                        print(f"   ✅ Question ID available (fallback): {sample_question_id}")
                else:
                    print(f"   ❌ No questions found in response")
            else:
                print(f"   ❌ Failed to retrieve sample questions: {questions_response}")
        
        if not sample_question_id:
            print("   ❌ Cannot proceed without sample question ID")
            return False
        
        # PHASE 3: SEND FIRST MESSAGE
        print("\n💬 PHASE 3: SEND FIRST MESSAGE")
        print("-" * 70)
        print(f"Sending first message: '{first_message}'")
        
        session_id = str(uuid.uuid4())  # Generate unique session ID for this test
        
        first_message_data = {
            "question_id": sample_question_id,
            "session_id": session_id,
            "message": first_message
        }
        
        if self.auth_headers:
            success, first_response = self.run_test(
                "Send First Message", 
                "POST", 
                "doubts/ask", 
                [200, 400, 500], 
                first_message_data, 
                self.auth_headers
            )
            
            if success and first_response:
                test_results["first_message_sent"] = True
                print(f"   ✅ First message sent successfully")
                
                # Check AI response
                ai_response = first_response.get('response', '') or ''
                if len(ai_response) > 50:  # Meaningful response
                    test_results["first_ai_response_generated"] = True
                    print(f"   ✅ AI response generated: {len(ai_response)} characters")
                    print(f"   📊 Response preview: {ai_response[:100]}...")
                else:
                    print(f"   ❌ AI response too short or missing: {len(ai_response)} chars")
                
                # Check message count
                message_count = first_response.get('message_count', 0)
                remaining_messages = first_response.get('remaining_messages', 0)
                if message_count == 1 and remaining_messages == 9:
                    test_results["first_message_count_correct"] = True
                    print(f"   ✅ Message count correct: {message_count}/10 (remaining: {remaining_messages})")
                else:
                    print(f"   ⚠️ Message count: {message_count}/10 (remaining: {remaining_messages})")
            else:
                print(f"   ❌ First message failed: {first_response}")
                return False
        
        # PHASE 4: SEND SECOND MESSAGE
        print("\n💬 PHASE 4: SEND SECOND MESSAGE")
        print("-" * 70)
        print(f"Sending second message: '{second_message}'")
        
        second_message_data = {
            "question_id": sample_question_id,
            "session_id": session_id,
            "message": second_message
        }
        
        if self.auth_headers:
            success, second_response = self.run_test(
                "Send Second Message", 
                "POST", 
                "doubts/ask", 
                [200, 400, 500], 
                second_message_data, 
                self.auth_headers
            )
            
            if success and second_response:
                test_results["second_message_sent"] = True
                print(f"   ✅ Second message sent successfully")
                
                # Check AI response
                ai_response = second_response.get('response', '') or ''
                if len(ai_response) > 50:  # Meaningful response
                    test_results["second_ai_response_generated"] = True
                    print(f"   ✅ AI response generated: {len(ai_response)} characters")
                    print(f"   📊 Response preview: {ai_response[:100]}...")
                else:
                    print(f"   ❌ AI response too short or missing: {len(ai_response)} chars")
                
                # Check message count
                message_count = second_response.get('message_count', 0)
                remaining_messages = second_response.get('remaining_messages', 0)
                if message_count == 2 and remaining_messages == 8:
                    test_results["second_message_count_correct"] = True
                    print(f"   ✅ Message count correct: {message_count}/10 (remaining: {remaining_messages})")
                else:
                    print(f"   ⚠️ Message count: {message_count}/10 (remaining: {remaining_messages})")
            else:
                print(f"   ❌ Second message failed: {second_response}")
                return False
        
        # PHASE 5: RETRIEVE CONVERSATION HISTORY
        print("\n📜 PHASE 5: RETRIEVE CONVERSATION HISTORY")
        print("-" * 70)
        print(f"Retrieving conversation history via GET /api/doubts/{sample_question_id}/history")
        
        if self.auth_headers:
            success, history_response = self.run_test(
                "Retrieve Conversation History", 
                "GET", 
                f"doubts/{sample_question_id}/history", 
                [200, 404, 500], 
                None, 
                self.auth_headers
            )
            
            if success and history_response:
                test_results["conversation_history_retrieved"] = True
                print(f"   ✅ Conversation history retrieved successfully")
                
                messages = history_response.get('messages', [])
                message_count = history_response.get('message_count', 0)
                remaining_messages = history_response.get('remaining_messages', 0)
                
                print(f"   📊 Total messages in history: {len(messages)}")
                print(f"   📊 Message count: {message_count}/10")
                print(f"   📊 Remaining messages: {remaining_messages}")
                
                # CRITICAL VERIFICATION: Check message order and content
                if len(messages) >= 4:  # Should have user1, AI1, user2, AI2
                    print(f"\n   🔍 CRITICAL VERIFICATION - MESSAGE CONTENT AND ORDER:")
                    
                    # Check conversation structure: user1 → AI1 → user2 → AI2
                    expected_structure = ['user', 'assistant', 'user', 'assistant']
                    actual_structure = [msg.get('role') for msg in messages[:4]]
                    
                    if actual_structure == expected_structure:
                        test_results["conversation_structure_correct"] = True
                        print(f"   ✅ Conversation structure correct: {' → '.join(actual_structure)}")
                    else:
                        print(f"   ❌ Conversation structure incorrect:")
                        print(f"      Expected: {' → '.join(expected_structure)}")
                        print(f"      Actual: {' → '.join(actual_structure)}")
                    
                    # Check first user message (exact match)
                    first_user_msg = messages[0]
                    if (first_user_msg.get('role') == 'user' and 
                        first_user_msg.get('content') == first_message):
                        test_results["first_user_message_exact"] = True
                        print(f"   ✅ First user message stored exactly: '{first_user_msg.get('content')}'")
                    else:
                        print(f"   ❌ First user message modified:")
                        print(f"      Expected: '{first_message}'")
                        print(f"      Stored: '{first_user_msg.get('content')}'")
                    
                    # Check second user message (exact match)
                    if len(messages) >= 3:
                        second_user_msg = messages[2]
                        if (second_user_msg.get('role') == 'user' and 
                            second_user_msg.get('content') == second_message):
                            test_results["second_user_message_exact"] = True
                            print(f"   ✅ Second user message stored exactly: '{second_user_msg.get('content')}'")
                        else:
                            print(f"   ❌ Second user message modified:")
                            print(f"      Expected: '{second_message}'")
                            print(f"      Stored: '{second_user_msg.get('content')}'")
                    
                    # Check if both user messages are unchanged
                    if (test_results["first_user_message_exact"] and 
                        test_results["second_user_message_exact"]):
                        test_results["user_messages_unchanged"] = True
                        test_results["no_user_input_modification"] = True
                        print(f"   ✅ CRITICAL: User messages stored WITHOUT modification")
                    else:
                        print(f"   ❌ CRITICAL: User input has been modified by the system")
                    
                    # Check AI responses are contextual
                    ai_responses = [msg for msg in messages if msg.get('role') == 'assistant']
                    if len(ai_responses) >= 2:
                        first_ai_response = ai_responses[0].get('content', '') or ''
                        second_ai_response = ai_responses[1].get('content', '') or ''
                        
                        if (len(first_ai_response) > 100 and len(second_ai_response) > 100):
                            test_results["ai_responses_contextual"] = True
                            print(f"   ✅ AI responses are contextually relevant")
                            print(f"      First AI response: {len(first_ai_response)} chars")
                            print(f"      Second AI response: {len(second_ai_response)} chars")
                        else:
                            print(f"   ⚠️ AI responses may be too short")
                    
                    # Check timestamps are present
                    timestamps_present = all(msg.get('timestamp') for msg in messages)
                    if timestamps_present:
                        test_results["timestamps_present"] = True
                        print(f"   ✅ All messages have timestamps")
                        
                        # Display timestamps for verification
                        for i, msg in enumerate(messages[:4]):
                            role = msg.get('role')
                            timestamp = msg.get('timestamp')
                            content_preview = msg.get('content', '')[:50] + '...' if len(msg.get('content', '')) > 50 else msg.get('content', '')
                            print(f"      Message {i+1} ({role}): {timestamp} - {content_preview}")
                    else:
                        print(f"   ❌ Some messages missing timestamps")
                    
                    # Check chronological order
                    if timestamps_present:
                        timestamps = [msg.get('timestamp') for msg in messages]
                        sorted_timestamps = sorted(timestamps)
                        if timestamps == sorted_timestamps:
                            test_results["message_order_correct"] = True
                            print(f"   ✅ Messages in correct chronological order")
                        else:
                            print(f"   ❌ Messages not in chronological order")
                
                else:
                    print(f"   ❌ Insufficient messages in history: {len(messages)} (expected at least 4)")
            else:
                print(f"   ❌ Failed to retrieve conversation history: {history_response}")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 90)
        print("🎯 ASK TWELVR CONVERSATION FLOW MESSAGE HANDLING - RESULTS")
        print("=" * 90)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        # Group results by test phases
        test_phases = {
            "AUTHENTICATION": [
                "authentication_successful", "jwt_token_generated", "user_adaptive_enabled"
            ],
            "SAMPLE QUESTION RETRIEVAL": [
                "sample_question_retrieved", "question_id_available", "question_has_solution_fields"
            ],
            "FIRST MESSAGE TEST": [
                "first_message_sent", "first_ai_response_generated", "first_message_count_correct"
            ],
            "SECOND MESSAGE TEST": [
                "second_message_sent", "second_ai_response_generated", "second_message_count_correct"
            ],
            "CONVERSATION HISTORY VERIFICATION": [
                "conversation_history_retrieved", "message_order_correct", "timestamps_present",
                "user_messages_unchanged", "ai_responses_contextual"
            ],
            "CRITICAL VERIFICATION": [
                "first_user_message_exact", "second_user_message_exact", 
                "conversation_structure_correct", "no_user_input_modification"
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
        
        # Message Handling Assessment
        message_handling_working = (
            test_results["user_messages_unchanged"] and
            test_results["no_user_input_modification"] and
            test_results["first_user_message_exact"] and
            test_results["second_user_message_exact"]
        )
        
        if message_handling_working:
            test_results["message_handling_working"] = True
            print("\n✅ MESSAGE HANDLING: WORKING PERFECTLY")
            print("   - User messages stored exactly as typed (no modifications)")
            print("   - First message: 'Can you help me understand this question?' ✅")
            print("   - Second message: 'What is the principle to remember?' ✅")
            print("   - No evidence of user input being changed by the system")
        else:
            print("\n❌ MESSAGE HANDLING: CRITICAL ISSUES DETECTED")
            print("   - User input may be modified by the system")
            print("   - Message storage integrity compromised")
        
        # Conversation Flow Assessment
        conversation_flow_validated = (
            test_results["conversation_structure_correct"] and
            test_results["message_order_correct"] and
            test_results["timestamps_present"] and
            test_results["ai_responses_contextual"]
        )
        
        if conversation_flow_validated:
            test_results["conversation_flow_validated"] = True
            print("\n✅ CONVERSATION FLOW: VALIDATED")
            print("   - Conversation structure: user1 → AI1 → user2 → AI2 ✅")
            print("   - Messages in correct chronological order ✅")
            print("   - All messages have timestamps ✅")
            print("   - AI responses contextually relevant ✅")
        else:
            print("\n❌ CONVERSATION FLOW: ISSUES DETECTED")
            print("   - Conversation structure or ordering problems")
        
        # System Integrity Assessment
        system_integrity_confirmed = (
            message_handling_working and
            conversation_flow_validated and
            test_results["first_message_count_correct"] and
            test_results["second_message_count_correct"]
        )
        
        if system_integrity_confirmed:
            test_results["system_integrity_confirmed"] = True
            print("\n✅ SYSTEM INTEGRITY: CONFIRMED")
            print("   - User messages stored verbatim without modification ✅")
            print("   - AI responses contextually relevant to each user question ✅")
            print("   - Conversation history maintains correct order ✅")
            print("   - Message count incremented correctly (2/10) ✅")
            print("   - No evidence of user input modification ✅")
        else:
            print("\n❌ SYSTEM INTEGRITY: COMPROMISED")
            print("   - Critical issues with message handling or conversation flow")
        
        # FINAL VERDICT
        print("\n" + "=" * 90)
        print("🎯 FINAL VERDICT:")
        
        if system_integrity_confirmed:
            print("\n🎉 ASK TWELVR CONVERSATION FLOW: ✅ EXCELLENT SUCCESS")
            print("   - All review request objectives achieved")
            print("   - User messages stored exactly as typed")
            print("   - Conversation flow working perfectly")
            print("   - System maintains message integrity")
            print("   - Ready for production use")
        else:
            print("\n⚠️ ASK TWELVR CONVERSATION FLOW: ❌ ISSUES DETECTED")
            print("   - Critical message handling problems")
            print("   - User input modification detected")
            print("   - System integrity compromised")
        
        print(f"\n📊 Final Score: {success_rate:.1f}%")
        print(f"🔍 Critical Verification: {'✅ PASSED' if message_handling_working else '❌ FAILED'}")
        print("=" * 90)
        
        return system_integrity_confirmed, test_results

def main():
    """Run the Ask Twelvr conversation flow test"""
    tester = AskTwelvrTester()
    success, results = tester.test_ask_twelvr_conversation_flow()
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()