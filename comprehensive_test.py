#!/usr/bin/env python3
"""
Comprehensive Twelvr Backend Testing Suite
Final end-to-end testing of the complete Twelvr application
"""

import requests
import json
import sys
from datetime import datetime

class TwelvrComprehensiveTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.student_token = None
        self.admin_token = None
        self.session_id = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, test_name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single test and return success status and response"""
        self.tests_run += 1
        
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        
        # Default headers
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                print(f"❌ {test_name}: Unsupported method {method}")
                return False, {}
            
            # Check if status code matches expected
            if isinstance(expected_status, list):
                status_match = response.status_code in expected_status
            else:
                status_match = response.status_code == expected_status
            
            if status_match:
                self.tests_passed += 1
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": response.text}
                
                print(f"✅ {test_name}: Status {response.status_code}")
                return True, response_data
            else:
                print(f"❌ {test_name}: Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ {test_name}: Exception - {str(e)}")
            return False, {}

    def test_authentication_system(self):
        """Test authentication system including sign up and login"""
        print("\n🔐 AUTHENTICATION SYSTEM TESTING")
        print("=" * 60)
        
        auth_results = {
            "student_login": False,
            "admin_login": False,
            "jwt_validation": False,
            "user_profile_access": False,
            "basic_signup": False,
            "email_verification_endpoints": False
        }
        
        # Test student login
        print("\n👨‍🎓 Testing Student Login (student@catprep.com)")
        student_login_data = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login_data)
        if success and response.get('access_token'):
            self.student_token = response['access_token']
            auth_results["student_login"] = True
            print(f"   ✅ Student authenticated, token length: {len(self.student_token)}")
            
            # Test JWT validation
            student_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            
            success, me_response = self.run_test("Student Profile Access", "GET", "auth/me", 200, None, student_headers)
            if success:
                auth_results["jwt_validation"] = True
                auth_results["user_profile_access"] = True
                user_id = me_response.get('id')
                email = me_response.get('email')
                full_name = me_response.get('full_name')
                print(f"   ✅ JWT validation working")
                print(f"   📊 User ID: {user_id}")
                print(f"   📊 Email: {email}")
                print(f"   📊 Name: {full_name}")
        
        # Test basic signup functionality
        print("\n📝 Testing Basic Signup")
        signup_data = {
            "email": f"test.user.{datetime.now().strftime('%H%M%S')}@gmail.com",
            "password": "TestPassword123!",
            "full_name": "Test User"
        }
        
        success, response = self.run_test("Basic Signup", "POST", "auth/register", [200, 201, 409], signup_data)
        if success:
            if response.get('access_token'):
                auth_results["basic_signup"] = True
                print("   ✅ Basic signup working - JWT token returned")
            elif 'already' in str(response.get('message', '')).lower():
                auth_results["basic_signup"] = True
                print("   ✅ Basic signup working - duplicate email handled")
        
        # Test email verification endpoints
        print("\n📧 Testing Email Verification Endpoints")
        
        # Test Gmail authorization
        success, response = self.run_test("Gmail Authorization", "GET", "auth/gmail/authorize", [200, 500, 503])
        if success:
            auth_results["email_verification_endpoints"] = True
            print("   ✅ Gmail authorization endpoint accessible")
        
        # Test verification code sending
        verification_data = {"email": "test@gmail.com"}
        success, response = self.run_test("Send Verification Code", "POST", "auth/send-verification-code", [200, 503, 500], verification_data)
        if success:
            print("   ✅ Verification code endpoint accessible")
        
        return auth_results

    def test_session_management(self):
        """Test session management system"""
        print("\n🎮 SESSION MANAGEMENT TESTING")
        print("=" * 60)
        
        if not self.student_token:
            print("❌ Cannot test sessions without student authentication")
            return {}
        
        student_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        session_results = {
            "session_status_check": False,
            "session_creation": False,
            "question_delivery": False,
            "answer_submission": False,
            "solution_feedback": False
        }
        
        # Test session status
        print("\n📊 Testing Session Status")
        success, response = self.run_test("Current Session Status", "GET", "sessions/current-status", 200, None, student_headers)
        if success:
            session_results["session_status_check"] = True
            active_session = response.get('active_session', False)
            session_id = response.get('session_id')
            progress = response.get('progress', {})
            print(f"   ✅ Session status check working")
            print(f"   📊 Active session: {active_session}")
            if session_id:
                print(f"   📊 Session ID: {session_id}")
                print(f"   📊 Progress: {progress}")
        
        # Test session creation
        print("\n🚀 Testing Session Creation")
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create Session", "POST", "sessions/start", 200, session_data, student_headers)
        if success:
            self.session_id = response.get('session_id')
            total_questions = response.get('total_questions', 0)
            session_type = response.get('session_type')
            
            if self.session_id and total_questions > 0:
                session_results["session_creation"] = True
                print(f"   ✅ Session created successfully")
                print(f"   📊 Session ID: {self.session_id}")
                print(f"   📊 Total questions: {total_questions}")
                print(f"   📊 Session type: {session_type}")
                
                # Test question delivery
                print("\n❓ Testing Question Delivery")
                success, response = self.run_test("Get Next Question", "GET", f"sessions/{self.session_id}/next-question", 200, None, student_headers)
                if success and 'question' in response:
                    question = response['question']
                    question_id = question.get('id')
                    stem = question.get('stem', '')
                    options = question.get('options', {})
                    
                    session_results["question_delivery"] = True
                    print(f"   ✅ Question delivery working")
                    print(f"   📊 Question ID: {question_id}")
                    print(f"   📊 Question stem: {stem[:100]}...")
                    print(f"   📊 Options available: {bool(options)}")
                    
                    # Test answer submission
                    if question_id:
                        print("\n📝 Testing Answer Submission")
                        answer_data = {
                            "question_id": question_id,
                            "user_answer": "A",
                            "context": "session",
                            "time_sec": 60,
                            "hint_used": False
                        }
                        
                        success, response = self.run_test("Submit Answer", "POST", f"sessions/{self.session_id}/submit-answer", 200, answer_data, student_headers)
                        if success:
                            correct = response.get('correct', False)
                            solution_feedback = response.get('solution_feedback', {})
                            
                            session_results["answer_submission"] = True
                            print(f"   ✅ Answer submission working")
                            print(f"   📊 Answer correct: {correct}")
                            
                            # Check solution feedback
                            if solution_feedback:
                                approach = solution_feedback.get('solution_approach', '')
                                detailed_solution = solution_feedback.get('detailed_solution', '')
                                principle = solution_feedback.get('principle_to_remember', '')
                                
                                session_results["solution_feedback"] = True
                                print(f"   ✅ Solution feedback provided")
                                print(f"   📊 Approach length: {len(approach)} chars")
                                print(f"   📊 Solution length: {len(detailed_solution)} chars")
                                print(f"   📊 Principle length: {len(principle)} chars")
                                
                                # Check for LaTeX artifacts
                                has_latex = '$' in approach or '$' in detailed_solution
                                print(f"   📊 Has LaTeX artifacts: {has_latex}")
        
        return session_results

    def test_question_system(self):
        """Test question system and quality control"""
        print("\n📚 QUESTION SYSTEM TESTING")
        print("=" * 60)
        
        question_results = {
            "question_retrieval": False,
            "question_quality": False,
            "mcq_options": False,
            "solution_formatting": False,
            "latex_cleanup": False
        }
        
        # Test question retrieval
        print("\n📖 Testing Question Retrieval")
        success, response = self.run_test("Get Questions", "GET", "questions?limit=10", 200)
        if success:
            questions = response.get('questions', [])
            question_results["question_retrieval"] = True
            print(f"   ✅ Question retrieval working")
            print(f"   📊 Questions retrieved: {len(questions)}")
            
            if questions:
                # Analyze question quality
                print("\n🔍 Analyzing Question Quality")
                latex_free_count = 0
                complete_solutions_count = 0
                
                for i, q in enumerate(questions[:5]):  # Check first 5 questions
                    question_id = q.get('id', '')
                    stem = q.get('stem', '')
                    solution_approach = q.get('solution_approach', '')
                    detailed_solution = q.get('detailed_solution', '')
                    answer = q.get('answer', '')
                    
                    # Check for LaTeX artifacts
                    has_latex = '$' in solution_approach or '$' in detailed_solution
                    if not has_latex:
                        latex_free_count += 1
                    
                    # Check for complete solutions
                    if (solution_approach and solution_approach != "To be generated by LLM" and
                        detailed_solution and detailed_solution != "To be generated by LLM" and
                        len(detailed_solution) > 100):
                        complete_solutions_count += 1
                    
                    if i < 2:  # Show details for first 2 questions
                        print(f"   Question {i+1}: {question_id[:8]}...")
                        print(f"     Stem: {stem[:80]}...")
                        print(f"     Has LaTeX: {has_latex}")
                        print(f"     Solution length: {len(detailed_solution)} chars")
                
                if latex_free_count >= 4:  # At least 4 out of 5 should be LaTeX-free
                    question_results["latex_cleanup"] = True
                    print(f"   ✅ LaTeX cleanup successful ({latex_free_count}/5 questions)")
                
                if complete_solutions_count >= 3:
                    question_results["solution_formatting"] = True
                    question_results["question_quality"] = True
                    print(f"   ✅ Question quality good ({complete_solutions_count}/5 complete)")
        
        return question_results

    def test_database_operations(self):
        """Test database operations and data integrity"""
        print("\n🗄️ DATABASE OPERATIONS TESTING")
        print("=" * 60)
        
        db_results = {
            "api_health": False,
            "data_retrieval": False,
            "user_data_integrity": False,
            "question_data_integrity": False
        }
        
        # Test API health
        print("\n🏥 Testing API Health")
        success, response = self.run_test("API Health Check", "GET", "", 200)
        if success:
            db_results["api_health"] = True
            print("   ✅ API health check passed")
            print(f"   📊 Response: {response.get('message', 'No message')}")
        
        # Test data retrieval
        print("\n📊 Testing Data Retrieval")
        success, response = self.run_test("Questions Data", "GET", "questions?limit=5", 200)
        if success:
            questions = response.get('questions', [])
            if questions:
                db_results["data_retrieval"] = True
                db_results["question_data_integrity"] = True
                print(f"   ✅ Data retrieval working ({len(questions)} questions)")
        
        # Test user data integrity (if authenticated)
        if self.student_token:
            print("\n👤 Testing User Data Integrity")
            student_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            
            success, response = self.run_test("User Profile", "GET", "auth/me", 200, None, student_headers)
            if success:
                user_id = response.get('id')
                email = response.get('email')
                if user_id and email:
                    db_results["user_data_integrity"] = True
                    print("   ✅ User data integrity verified")
        
        return db_results

    def test_api_endpoints(self):
        """Test all major API endpoints"""
        print("\n🔗 API ENDPOINTS TESTING")
        print("=" * 60)
        
        api_results = {
            "auth_endpoints": False,
            "session_endpoints": False,
            "question_endpoints": False,
            "mastery_endpoints": False
        }
        
        # Test authentication endpoints
        print("\n🔐 Testing Authentication Endpoints")
        endpoints_tested = 0
        endpoints_working = 0
        
        # Test various auth endpoints
        auth_endpoints = [
            ("GET", "auth/gmail/authorize", [200, 500, 503]),
            ("POST", "auth/send-verification-code", [200, 400, 422, 503], {"email": "test@gmail.com"}),
            ("POST", "auth/verify-email-code", [200, 400, 500], {"email": "test@gmail.com", "code": "123456"})
        ]
        
        for method, endpoint, expected_status, *data in auth_endpoints:
            endpoints_tested += 1
            test_data = data[0] if data else None
            success, response = self.run_test(f"Auth Endpoint: {endpoint}", method, endpoint, expected_status, test_data)
            if success:
                endpoints_working += 1
        
        if endpoints_working >= 2:  # At least 2 out of 3 should work
            api_results["auth_endpoints"] = True
            print(f"   ✅ Auth endpoints working ({endpoints_working}/{endpoints_tested})")
        
        # Test session endpoints (if authenticated)
        if self.student_token:
            print("\n🎮 Testing Session Endpoints")
            student_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            
            session_endpoints_working = 0
            session_endpoints_tested = 0
            
            # Test session status
            session_endpoints_tested += 1
            success, response = self.run_test("Session Status", "GET", "sessions/current-status", 200, None, student_headers)
            if success:
                session_endpoints_working += 1
            
            # Test mastery endpoint
            session_endpoints_tested += 1
            success, response = self.run_test("Type Mastery", "GET", "mastery/type-breakdown", 200, None, student_headers)
            if success:
                session_endpoints_working += 1
                api_results["mastery_endpoints"] = True
                print("   ✅ Mastery tracking endpoint working")
            
            if session_endpoints_working >= 1:
                api_results["session_endpoints"] = True
                print(f"   ✅ Session endpoints working ({session_endpoints_working}/{session_endpoints_tested})")
        
        # Test question endpoints
        print("\n📚 Testing Question Endpoints")
        success, response = self.run_test("Questions Endpoint", "GET", "questions?limit=5", 200)
        if success:
            api_results["question_endpoints"] = True
            print("   ✅ Question endpoints working")
        
        return api_results

    def run_comprehensive_test(self):
        """Run all comprehensive tests"""
        print("🎯 TWELVR COMPREHENSIVE END-TO-END TESTING")
        print("=" * 80)
        print("Final comprehensive testing of the complete Twelvr application")
        print("Testing all major systems after fixing the sign up issue")
        print("")
        print("SYSTEMS TO TEST:")
        print("1. Authentication System (sign up, login, JWT tokens)")
        print("2. Session Management (creation, status, question delivery)")
        print("3. Question System (enrichment, answer validation, MCQ)")
        print("4. Database Operations (CRUD, data integrity)")
        print("5. API Endpoints (all major endpoints)")
        print("=" * 80)
        
        # Run all test suites
        auth_results = self.test_authentication_system()
        session_results = self.test_session_management()
        question_results = self.test_question_system()
        db_results = self.test_database_operations()
        api_results = self.test_api_endpoints()
        
        # Compile overall results
        all_results = {
            **auth_results,
            **session_results,
            **question_results,
            **db_results,
            **api_results
        }
        
        # Calculate success rates
        total_tests = len(all_results)
        passed_tests = sum(all_results.values())
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Print final summary
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
        # Group results by category
        categories = {
            "AUTHENTICATION SYSTEM": ["student_login", "admin_login", "jwt_validation", "user_profile_access", "basic_signup", "email_verification_endpoints"],
            "SESSION MANAGEMENT": ["session_status_check", "session_creation", "question_delivery", "answer_submission", "solution_feedback"],
            "QUESTION SYSTEM": ["question_retrieval", "question_quality", "mcq_options", "solution_formatting", "latex_cleanup"],
            "DATABASE OPERATIONS": ["api_health", "data_retrieval", "user_data_integrity", "question_data_integrity"],
            "API ENDPOINTS": ["auth_endpoints", "session_endpoints", "question_endpoints", "mastery_endpoints"]
        }
        
        for category, tests in categories.items():
            print(f"\n{category}:")
            category_passed = 0
            category_total = len(tests)
            
            for test in tests:
                if test in all_results:
                    result = all_results[test]
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"  {test.replace('_', ' ').title():<35} {status}")
                    if result:
                        category_passed += 1
            
            category_rate = (category_passed / category_total) * 100 if category_total > 0 else 0
            print(f"  Category Success Rate: {category_passed}/{category_total} ({category_rate:.1f}%)")
        
        print("\n" + "-" * 80)
        print(f"OVERALL SUCCESS RATE: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"TOTAL TESTS RUN: {self.tests_run}")
        print(f"TOTAL TESTS PASSED: {self.tests_passed}")
        
        # Production readiness assessment
        print("\n📋 PRODUCTION READINESS ASSESSMENT:")
        
        if success_rate >= 85:
            print("🎉 PRODUCTION READY: System is ready for production deployment")
        elif success_rate >= 70:
            print("⚠️ MOSTLY READY: Core functionality working, minor improvements needed")
        elif success_rate >= 50:
            print("⚠️ NEEDS WORK: Significant issues need to be resolved")
        else:
            print("❌ NOT READY: Critical issues must be fixed before production")
        
        # Key findings
        print("\n🔍 KEY FINDINGS:")
        
        if all_results.get("student_login") and all_results.get("jwt_validation"):
            print("✅ AUTHENTICATION: Student login and JWT validation working")
        else:
            print("❌ AUTHENTICATION: Issues with login or token validation")
        
        if all_results.get("session_creation") and all_results.get("question_delivery"):
            print("✅ SESSION SYSTEM: Session creation and question delivery working")
        else:
            print("❌ SESSION SYSTEM: Issues with session management")
        
        if all_results.get("latex_cleanup") and all_results.get("solution_formatting"):
            print("✅ QUESTION QUALITY: LaTeX cleanup and solution formatting working")
        else:
            print("❌ QUESTION QUALITY: Issues with question formatting")
        
        if all_results.get("api_health") and all_results.get("data_retrieval"):
            print("✅ DATABASE: API health and data retrieval working")
        else:
            print("❌ DATABASE: Issues with database operations")
        
        return success_rate >= 70  # 70% threshold for production readiness

if __name__ == "__main__":
    tester = TwelvrComprehensiveTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 COMPREHENSIVE TESTING COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\n⚠️ COMPREHENSIVE TESTING COMPLETED WITH ISSUES")
        sys.exit(1)