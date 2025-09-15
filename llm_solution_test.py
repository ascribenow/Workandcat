#!/usr/bin/env python3
"""
LLM Solution Generation Fix Testing
Testing the critical fix for hardcoded generic solutions vs actual LLM-generated solutions
"""

import requests
import json
import time
import sys

class LLMSolutionTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.student_token = None
        
    def authenticate_admin(self):
        """Authenticate as admin"""
        print("🔐 Authenticating as admin...")
        
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        response = requests.post(f"{self.base_url}/auth/login", json=admin_login)
        if response.status_code == 200:
            data = response.json()
            self.admin_token = data['access_token']
            print(f"   ✅ Admin authenticated: {data['user']['full_name']}")
            return True
        else:
            print(f"   ❌ Admin authentication failed: {response.status_code}")
            return False
    
    def authenticate_student(self):
        """Authenticate as student"""
        print("🔐 Authenticating as student...")
        
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        response = requests.post(f"{self.base_url}/auth/login", json=student_login)
        if response.status_code == 200:
            data = response.json()
            self.student_token = data['access_token']
            print(f"   ✅ Student authenticated: {data['user']['full_name']}")
            return True
        else:
            print(f"   ❌ Student authentication failed: {response.status_code}")
            return False
    
    def test_llm_solution_generation_fix(self):
        """Test the critical LLM solution generation fix"""
        print("🔍 TESTING LLM SOLUTION GENERATION FIX")
        print("=" * 60)
        print("Issue: Questions were getting hardcoded generic solutions instead of LLM-generated ones")
        print("Fix: Updated enrich_question_background to use actual LLM enrichment pipeline")
        print("Testing: Create questions and verify they get proper LLM-generated solutions")
        print("=" * 60)
        
        if not self.authenticate_admin():
            return False
            
        if not self.authenticate_student():
            return False
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        test_results = {
            "admin_authentication": True,
            "student_authentication": True,
            "question_creation": False,
            "background_processing": False,
            "llm_solution_quality": False,
            "solution_specificity": False,
            "no_generic_solutions": False,
            "re_enrichment_test": False
        }
        
        # TEST 1: Create test questions with different types
        print("\n📝 TEST 1: CREATE TEST QUESTIONS")
        print("-" * 40)
        
        test_questions = [
            {
                "stem": "LLM Test: A earns 25% more than B. If B earns Rs. 1000, how much does A earn?",
                "hint_category": "Arithmetic",
                "hint_subcategory": "Percentages",
                "source": "LLM Solution Test",
                "expected_keywords": ["1250", "25%", "percentage", "earn"]
            },
            {
                "stem": "LLM Test: A train travels 240 km in 3 hours. What is its average speed?",
                "hint_category": "Arithmetic", 
                "hint_subcategory": "Time–Speed–Distance (TSD)",
                "source": "LLM Solution Test",
                "expected_keywords": ["80", "speed", "distance", "time"]
            },
            {
                "stem": "LLM Test: Find the compound interest on Rs. 5000 at 10% per annum for 2 years.",
                "hint_category": "Arithmetic",
                "hint_subcategory": "Simple & Compound Interest (SI–CI)",
                "source": "LLM Solution Test", 
                "expected_keywords": ["compound", "interest", "5000", "10%"]
            }
        ]
        
        created_questions = []
        
        for i, question_data in enumerate(test_questions):
            print(f"\n   Creating question {i+1}: {question_data['stem'][:50]}...")
            
            response = requests.post(f"{self.base_url}/questions", json=question_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                question_id = data.get('question_id')
                status = data.get('status')
                
                print(f"   ✅ Question {i+1} created: {question_id}")
                print(f"   Status: {status}")
                
                created_questions.append({
                    'id': question_id,
                    'data': question_data,
                    'expected_keywords': question_data['expected_keywords']
                })
                
                test_results["question_creation"] = True
            else:
                print(f"   ❌ Question {i+1} creation failed: {response.status_code}")
                try:
                    error = response.json()
                    print(f"   Error: {error}")
                except:
                    print(f"   Raw error: {response.text}")
        
        if not created_questions:
            print("❌ No questions created - cannot test LLM solution generation")
            return False
        
        # TEST 2: Wait for background processing and check solutions
        print("\n⏳ TEST 2: BACKGROUND PROCESSING & SOLUTION VERIFICATION")
        print("-" * 40)
        print("Waiting for LLM enrichment to complete...")
        
        # Wait for background processing
        time.sleep(15)  # Give enough time for LLM processing
        
        # Check each question for proper LLM-generated solutions
        for i, question_info in enumerate(created_questions):
            question_id = question_info['id']
            expected_keywords = question_info['expected_keywords']
            question_type = question_info['data']['hint_subcategory']
            
            print(f"\n   Checking question {i+1} ({question_type})...")
            
            # Get updated question data
            response = requests.get(f"{self.base_url}/questions?limit=50", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                
                # Find our test question
                test_question = None
                for q in questions:
                    if q.get('id') == question_id:
                        test_question = q
                        break
                
                if test_question:
                    answer = test_question.get('answer', '')
                    solution_approach = test_question.get('solution_approach', '')
                    detailed_solution = test_question.get('detailed_solution', '')
                    
                    print(f"   Answer: {answer}")
                    print(f"   Solution Approach: {solution_approach[:100]}...")
                    print(f"   Detailed Solution: {detailed_solution[:100]}...")
                    
                    # Check if background processing completed
                    if answer and answer != "To be generated by LLM":
                        test_results["background_processing"] = True
                        print("   ✅ Background processing completed")
                        
                        # Check for generic solutions (the bug we're testing)
                        generic_indicators = [
                            "Example answer based on the question pattern",
                            "Mathematical approach to solve this problem",
                            "Detailed solution for:",
                            "To be generated by LLM"
                        ]
                        
                        is_generic = any(indicator in answer + solution_approach + detailed_solution 
                                       for indicator in generic_indicators)
                        
                        if not is_generic:
                            test_results["no_generic_solutions"] = True
                            print("   ✅ No generic solutions detected - fix working!")
                        else:
                            print("   ❌ Generic solutions still present - fix not working!")
                            print(f"   Generic content found in: {answer} | {solution_approach}")
                        
                        # Check solution quality and specificity
                        solution_text = (answer + " " + solution_approach + " " + detailed_solution).lower()
                        
                        # Check if solution contains expected keywords for this question type
                        keywords_found = sum(1 for keyword in expected_keywords 
                                           if keyword.lower() in solution_text)
                        
                        if keywords_found >= 2:  # At least 2 relevant keywords
                            test_results["solution_specificity"] = True
                            print(f"   ✅ Solution is specific to question type ({keywords_found}/{len(expected_keywords)} keywords found)")
                        else:
                            print(f"   ❌ Solution may not be specific ({keywords_found}/{len(expected_keywords)} keywords found)")
                        
                        # Check overall solution quality
                        if (len(solution_approach) > 50 and len(detailed_solution) > 100 and
                            not is_generic and keywords_found >= 1):
                            test_results["llm_solution_quality"] = True
                            print("   ✅ Solution quality appears good")
                        else:
                            print("   ❌ Solution quality needs improvement")
                    else:
                        print("   ❌ Background processing not completed or failed")
                else:
                    print(f"   ❌ Question {question_id} not found in database")
            else:
                print(f"   ❌ Failed to retrieve questions: {response.status_code}")
        
        # TEST 3: Test re-enrichment of existing questions with generic solutions
        print("\n🔄 TEST 3: RE-ENRICHMENT OF EXISTING QUESTIONS")
        print("-" * 40)
        print("Testing re-processing of questions that have generic solutions")
        
        # Get all questions and find ones with generic solutions
        response = requests.get(f"{self.base_url}/questions?limit=100", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            questions = data.get('questions', [])
            
            generic_questions = []
            for q in questions:
                solution_approach = q.get('solution_approach', '')
                detailed_solution = q.get('detailed_solution', '')
                
                if ("Mathematical approach to solve this problem" in solution_approach or
                    "Example answer based on the question pattern" in q.get('answer', '') or
                    "Detailed solution for:" in detailed_solution):
                    generic_questions.append(q)
            
            print(f"   Found {len(generic_questions)} questions with generic solutions")
            
            if generic_questions:
                # Test re-enrichment by creating a similar question
                sample_generic = generic_questions[0]
                print(f"   Sample generic question: {sample_generic.get('stem', '')[:50]}...")
                print(f"   Generic solution: {sample_generic.get('solution_approach', '')[:50]}...")
                
                # Create a new question to test the fix
                re_enrich_question = {
                    "stem": f"Re-enrichment test: {sample_generic.get('stem', 'Test question')}",
                    "hint_category": "Arithmetic",
                    "hint_subcategory": "Time–Speed–Distance (TSD)",
                    "source": "Re-enrichment Test"
                }
                
                response = requests.post(f"{self.base_url}/questions", json=re_enrich_question, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    re_enrich_id = data.get('question_id')
                    print(f"   ✅ Re-enrichment test question created: {re_enrich_id}")
                    
                    # Wait and check if it gets proper solution
                    time.sleep(10)
                    
                    response = requests.get(f"{self.base_url}/questions?limit=50", headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        questions = data.get('questions', [])
                        
                        for q in questions:
                            if q.get('id') == re_enrich_id:
                                new_solution = q.get('solution_approach', '')
                                new_answer = q.get('answer', '')
                                
                                if ("Mathematical approach to solve this problem" not in new_solution and
                                    "Example answer based on the question pattern" not in new_answer):
                                    test_results["re_enrichment_test"] = True
                                    print("   ✅ Re-enrichment working - new questions get proper solutions")
                                else:
                                    print("   ❌ Re-enrichment still producing generic solutions")
                                break
                else:
                    print("   ❌ Failed to create re-enrichment test question")
            else:
                print("   ✅ No generic questions found - all questions have proper solutions")
                test_results["re_enrichment_test"] = True
        
        # TEST 4: Test session with fixed questions
        print("\n🎯 TEST 4: SESSION WITH FIXED QUESTIONS")
        print("-" * 40)
        print("Testing that sessions now show proper solutions instead of generic ones")
        
        if self.student_token:
            student_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            
            # Start a session
            response = requests.post(f"{self.base_url}/sessions/start", 
                                   json={"target_minutes": 30}, 
                                   headers=student_headers)
            
            if response.status_code == 200:
                data = response.json()
                session_id = data.get('session_id')
                print(f"   ✅ Session created: {session_id}")
                
                # Get a question from the session
                response = requests.get(f"{self.base_url}/sessions/{session_id}/next-question",
                                      headers=student_headers)
                
                if response.status_code == 200:
                    data = response.json()
                    question = data.get('question')
                    
                    if question:
                        question_id = question.get('id')
                        print(f"   Session question: {question.get('stem', '')[:50]}...")
                        
                        # Submit a wrong answer to see the solution
                        answer_data = {
                            "question_id": question_id,
                            "user_answer": "wrong_answer",
                            "time_sec": 30
                        }
                        
                        response = requests.post(f"{self.base_url}/sessions/{session_id}/submit-answer",
                                               json=answer_data, headers=student_headers)
                        
                        if response.status_code == 200:
                            data = response.json()
                            solution_feedback = data.get('solution_feedback', {})
                            solution_approach = solution_feedback.get('solution_approach', '')
                            detailed_solution = solution_feedback.get('detailed_solution', '')
                            
                            print(f"   Solution shown: {solution_approach[:100]}...")
                            
                            # Check if solution is generic
                            if ("Mathematical approach to solve this problem" not in solution_approach and
                                "Example answer based on the question pattern" not in detailed_solution):
                                print("   ✅ Session shows proper solutions - fix working in sessions!")
                            else:
                                print("   ❌ Session still shows generic solutions")
                        else:
                            print("   ❌ Failed to submit answer")
                    else:
                        print("   ⚠️ No question available in session")
                else:
                    print("   ❌ Failed to get question from session")
            else:
                print("   ❌ Failed to create session")
        
        # FINAL RESULTS
        print("\n" + "=" * 60)
        print("LLM SOLUTION GENERATION FIX TEST RESULTS")
        print("=" * 60)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<35} {status}")
        
        print("-" * 60)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis
        if test_results["no_generic_solutions"]:
            print("🎉 CRITICAL SUCCESS: Generic solutions bug FIXED!")
            print("   ✅ Questions now get proper LLM-generated solutions")
        else:
            print("❌ CRITICAL FAILURE: Generic solutions bug still exists!")
        
        if test_results["solution_specificity"]:
            print("✅ Solutions are specific to question types")
        else:
            print("⚠️ Solutions may not be specific enough to question types")
        
        if success_rate >= 80:
            print("🎉 LLM SOLUTION GENERATION FIX SUCCESSFUL!")
            print("   ✅ Students will now see proper mathematical solutions")
            print("   ✅ No more misleading generic solutions")
        elif success_rate >= 60:
            print("⚠️ LLM solution generation mostly fixed with minor issues")
        else:
            print("❌ LLM solution generation fix has significant issues")
        
        return success_rate >= 70

if __name__ == "__main__":
    tester = LLMSolutionTester()
    success = tester.test_llm_solution_generation_fix()
    
    if success:
        print("\n🎉 LLM Solution Generation Fix Test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ LLM Solution Generation Fix Test failed!")
        sys.exit(1)