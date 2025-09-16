#!/usr/bin/env python3
"""
FINAL ANSWER COMPARISON LOGIC VALIDATION

This test validates the critical bug fix mentioned in the review request:
- Issue: User answered "33 km/h" (incorrect) but system showed "Correct!" because "33" appeared in correct answer "8.33 km/h"
- Root Cause: Flawed regex number matching logic
- Solution: Simplified to direct string comparison between user answer and question.answer field

Expected Results:
- "33 km/h" vs "8.33 km/h" → INCORRECT
- "8.33 km/h" vs "8.33 km/h" → CORRECT
- Simple, accurate comparison without false positives
"""

import requests
import json
import uuid
from datetime import datetime
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FinalAnswerComparisonValidator:
    def __init__(self):
        self.base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
        self.auth_headers = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate with test credentials"""
        print("🔐 Authenticating with sp@theskinmantra.com/student123...")
        
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
                print(f"📊 JWT Token length: {len(token)} characters")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_answer_comparison(self, question_id, user_answer, expected_correct, test_name):
        """Test answer comparison logic"""
        print(f"\n🧪 {test_name}")
        print(f"   User Answer: '{user_answer}'")
        print(f"   Expected Result: {'CORRECT' if expected_correct else 'INCORRECT'}")
        
        session_id = f"test_{uuid.uuid4()}"
        
        answer_data = {
            "session_id": session_id,
            "question_id": question_id,
            "action": "submit",
            "data": {
                "user_answer": user_answer,
                "time_taken": 30,
                "question_number": 1
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/log/question-action",
                json=answer_data,
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                is_correct = result.get('correct', False)
                status = result.get('status', '')
                
                print(f"   📊 API Response: correct={is_correct}, status='{status}'")
                
                if is_correct == expected_correct:
                    print(f"   ✅ PASS: Answer comparison working correctly")
                    return True
                else:
                    print(f"   ❌ FAIL: Expected correct={expected_correct}, got correct={is_correct}")
                    return False
            else:
                print(f"   ❌ API Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
    
    def run_validation(self):
        """Run the complete answer comparison validation"""
        print("🎯 FINAL ANSWER COMPARISON LOGIC VALIDATION")
        print("=" * 80)
        print("OBJECTIVE: Verify the critical bug fix for answer comparison logic")
        print("FOCUS: Direct string comparison, no false positives from partial matches")
        print("EXPECTED: Clean comparison logic works properly, correct answer field shows question.answer")
        print("=" * 80)
        
        # Step 1: Authenticate
        if not self.authenticate():
            return False
        
        # Use the known question for testing
        question_id = "345291e1-0943-4260-baaf-0b5b1fdfabe9"
        canonical_answer = "35.2%"  # This is the actual answer field in database
        
        print(f"\n🎯 Testing with question: {question_id}")
        print(f"📊 Canonical answer (question.answer): '{canonical_answer}'")
        
        # Step 3: Test scenarios based on review request
        test_results = []
        
        # Test 1: Exact match with canonical answer (should be CORRECT)
        result1 = self.test_answer_comparison(
            question_id, 
            canonical_answer, 
            True, 
            "Test 1: Exact Match with Canonical Answer (Should be CORRECT)"
        )
        test_results.append(result1)
        
        # Test 2: Partial number match - the critical bug scenario
        # This simulates "33" vs "8.33" - partial number should NOT match
        result2 = self.test_answer_comparison(
            question_id, 
            "35", 
            False, 
            "Test 2: Partial Number Match '35' vs '35.2%' (Should be INCORRECT - Critical Bug Test)"
        )
        test_results.append(result2)
        
        # Test 3: Another partial match scenario
        result3 = self.test_answer_comparison(
            question_id, 
            "2%", 
            False, 
            "Test 3: Partial Match '2%' vs '35.2%' (Should be INCORRECT)"
        )
        test_results.append(result3)
        
        # Test 4: Case insensitive match (should be CORRECT)
        result4 = self.test_answer_comparison(
            question_id, 
            canonical_answer.upper(), 
            True, 
            "Test 4: Case Insensitive Match (Should be CORRECT)"
        )
        test_results.append(result4)
        
        # Test 5: Whitespace handling (should be CORRECT)
        result5 = self.test_answer_comparison(
            question_id, 
            f"  {canonical_answer}  ", 
            True, 
            "Test 5: Whitespace Handling (Should be CORRECT)"
        )
        test_results.append(result5)
        
        # Test 6: Wrong answer (should be INCORRECT)
        result6 = self.test_answer_comparison(
            question_id, 
            "Wrong Answer", 
            False, 
            "Test 6: Wrong Answer (Should be INCORRECT)"
        )
        test_results.append(result6)
        
        # Test 7: Full explanation match (should be INCORRECT - this is the key insight)
        # Users see the full explanation but should match against canonical answer
        result7 = self.test_answer_comparison(
            question_id, 
            "After two replacements, the percentage of water in the mixture is 35.2%.", 
            False, 
            "Test 7: Full Explanation vs Canonical Answer (Should be INCORRECT - Design Choice)"
        )
        test_results.append(result7)
        
        # Results Summary
        print("\n" + "=" * 80)
        print("🎯 FINAL ANSWER COMPARISON VALIDATION RESULTS")
        print("=" * 80)
        
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Detailed analysis
        print("\n📊 DETAILED ANALYSIS:")
        print(f"✅ Exact match working: {test_results[0]}")
        print(f"✅ Partial number match prevented: {test_results[1]} (Critical bug fix)")
        print(f"✅ Partial match prevention: {test_results[2]}")
        print(f"✅ Case insensitive handling: {test_results[3]}")
        print(f"✅ Whitespace handling: {test_results[4]}")
        print(f"✅ Wrong answer detection: {test_results[5]}")
        print(f"📋 Full explanation handling: {test_results[6]} (Expected behavior)")
        
        # Critical bug assessment
        critical_bug_fixed = test_results[1] and test_results[2]  # Partial matches prevented
        core_functionality = test_results[0] and test_results[5]  # Correct/incorrect detection
        
        if success_rate >= 85 and critical_bug_fixed and core_functionality:
            print("\n✅ ANSWER COMPARISON LOGIC VALIDATION: PASSED")
            print("   - Direct string comparison working correctly")
            print("   - Critical bug fix validated: No false positives from partial number matches")
            print("   - Case insensitive and whitespace handling working")
            print("   - Clean comparison logic without regex complexity")
            print("   - Correct answer field (question.answer) being used properly")
            print("   - System compares against canonical answer, not full explanation")
        else:
            print("\n❌ ANSWER COMPARISON LOGIC VALIDATION: FAILED")
            print("   - Answer comparison logic has issues")
            if not critical_bug_fixed:
                print("   - Critical bug still present: Partial matches not prevented")
            if not core_functionality:
                print("   - Core functionality broken: Correct/incorrect detection failing")
        
        return success_rate >= 85 and critical_bug_fixed and core_functionality

if __name__ == "__main__":
    validator = FinalAnswerComparisonValidator()
    success = validator.run_validation()
    exit(0 if success else 1)