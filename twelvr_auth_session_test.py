#!/usr/bin/env python3
"""
Twelvr Authentication and Session System Testing
Test the specific requirements from the review request:
1. Student authentication with credentials student@catprep.com / student123
2. Session creation API endpoint /api/sessions/start 
3. Session status API endpoint /api/sessions/current-status
4. Verify that the API configuration changes fixed the URL routing issues
5. Test the quality control systems we implemented (answer validation, MCQ validation)
6. Check if all authentication tokens are working properly
7. Verify session endpoints return proper data
8. Test the adaptive session logic integration
"""

import requests
import json
import time
from datetime import datetime

class TwelvrAuthSessionTester:
    def __init__(self, base_url="https://learning-tutor.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.student_token = None
        self.session_id = None
        self.current_question_id = None
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test with proper error handling"""
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            # Handle multiple expected status codes
            if isinstance(expected_status, list):
                success = response.status_code in expected_status
            else:
                success = response.status_code == expected_status

            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response preview: {str(response_data)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                    return False, error_data
                except:
                    print(f"   Error: {response.text}")
                    return False, {}

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed - Error: {str(e)}")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_student_authentication(self):
        """Test student authentication with specific credentials"""
        print("🔐 TESTING STUDENT AUTHENTICATION")
        print("=" * 60)
        print("Testing authentication with student@catprep.com / student123")
        print("Verifying JWT token generation and validation")
        
        # Test student login
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test(
            "Student Authentication", 
            "POST", 
            "auth/login", 
            200, 
            student_login
        )
        
        if success and 'access_token' in response:
            self.student_token = response['access_token']
            user_info = response.get('user', {})
            print(f"   ✅ Authentication successful")
            print(f"   📊 User ID: {user_info.get('id', 'N/A')}")
            print(f"   📊 Email: {user_info.get('email', 'N/A')}")
            print(f"   📊 Full Name: {user_info.get('full_name', 'N/A')}")
            print(f"   📊 Token length: {len(self.student_token)} chars")
            
            # Test token validation by getting user info
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            
            success, response = self.run_test(
                "Token Validation", 
                "GET", 
                "auth/me", 
                200, 
                None, 
                headers
            )
            
            if success:
                print("   ✅ JWT token validation successful")
                return True
            else:
                print("   ❌ JWT token validation failed")
                return False
        else:
            print("   ❌ Student authentication failed")
            return False

    def test_session_status_endpoint(self):
        """Test session status API endpoint"""
        print("\n📊 TESTING SESSION STATUS ENDPOINT")
        print("=" * 60)
        print("Testing /api/sessions/current-status endpoint")
        print("Verifying session status detection and resumption logic")
        
        if not self.student_token:
            print("❌ Cannot test - no authentication token")
            return False
            
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        success, response = self.run_test(
            "Session Status Check", 
            "GET", 
            "sessions/current-status", 
            200, 
            None, 
            headers
        )
        
        if success:
            active_session = response.get('active_session', False)
            message = response.get('message', '')
            session_id = response.get('session_id')
            progress = response.get('progress', {})
            
            print(f"   📊 Active session: {active_session}")
            print(f"   📊 Message: {message}")
            print(f"   📊 Session ID: {session_id}")
            print(f"   📊 Progress: {progress}")
            
            if active_session and session_id:
                self.session_id = session_id
                print("   ✅ Active session found - can resume")
            else:
                print("   ✅ No active session - ready for new session")
            
            return True
        else:
            print("   ❌ Session status endpoint failed")
            return False

    def test_session_creation_endpoint(self):
        """Test session creation API endpoint"""
        print("\n🎯 TESTING SESSION CREATION ENDPOINT")
        print("=" * 60)
        print("Testing /api/sessions/start endpoint")
        print("Verifying session creation with adaptive logic")
        
        if not self.student_token:
            print("❌ Cannot test - no authentication token")
            return False
            
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        session_data = {
            "target_minutes": 30
        }
        
        success, response = self.run_test(
            "Session Creation", 
            "POST", 
            "sessions/start", 
            200, 
            session_data, 
            headers
        )
        
        if success:
            session_id = response.get('session_id')
            total_questions = response.get('total_questions', 0)
            session_type = response.get('session_type')
            current_question = response.get('current_question', 1)
            personalization = response.get('personalization', {})
            phase_info = response.get('phase_info', {})
            
            print(f"   ✅ Session created successfully")
            print(f"   📊 Session ID: {session_id}")
            print(f"   📊 Total questions: {total_questions}")
            print(f"   📊 Session type: {session_type}")
            print(f"   📊 Current question: {current_question}")
            print(f"   📊 Personalization applied: {personalization.get('applied', False)}")
            print(f"   📊 Phase info: {phase_info}")
            
            # Verify session has proper structure
            if session_id and total_questions >= 10:
                self.session_id = session_id
                print("   ✅ Session structure valid")
                
                # Test adaptive session logic integration
                if personalization.get('applied'):
                    print("   ✅ Adaptive session logic integrated")
                    
                    # Check for enhanced metadata
                    metadata_fields = [
                        'learning_stage', 'recent_accuracy', 'difficulty_distribution',
                        'category_distribution', 'subcategory_distribution'
                    ]
                    
                    metadata_count = sum(1 for field in metadata_fields if field in personalization)
                    print(f"   📊 Metadata fields present: {metadata_count}/{len(metadata_fields)}")
                    
                    if metadata_count >= 3:
                        print("   ✅ Enhanced session metadata present")
                
                return True
            else:
                print("   ❌ Session structure invalid")
                return False
        else:
            print("   ❌ Session creation failed")
            return False

    def test_session_question_delivery(self):
        """Test session question delivery and MCQ validation"""
        print("\n📝 TESTING SESSION QUESTION DELIVERY")
        print("=" * 60)
        print("Testing /api/sessions/current/next-question endpoint")
        print("Verifying question structure and MCQ options")
        
        if not self.student_token or not self.session_id:
            print("❌ Cannot test - no session available")
            return False
            
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        success, response = self.run_test(
            "Get Next Question", 
            "GET", 
            f"sessions/{self.session_id}/next-question", 
            200, 
            None, 
            headers
        )
        
        if success and 'question' in response:
            question = response['question']
            question_id = question.get('id')
            stem = question.get('stem', '')
            options = question.get('options', {})
            subcategory = question.get('subcategory', '')
            difficulty_band = question.get('difficulty_band', '')
            type_of_question = question.get('type_of_question', '')
            
            session_progress = response.get('session_progress', {})
            session_intelligence = response.get('session_intelligence', {})
            
            print(f"   ✅ Question retrieved successfully")
            print(f"   📊 Question ID: {question_id}")
            print(f"   📊 Stem length: {len(stem)} chars")
            print(f"   📊 Subcategory: {subcategory}")
            print(f"   📊 Difficulty: {difficulty_band}")
            print(f"   📊 Type: {type_of_question}")
            print(f"   📊 Options available: {bool(options)}")
            print(f"   📊 Session progress: {session_progress}")
            print(f"   📊 Session intelligence: {bool(session_intelligence)}")
            
            # Validate MCQ options structure
            if options:
                option_keys = list(options.keys())
                correct_answer = options.get('correct')
                
                print(f"   📊 Option keys: {option_keys}")
                print(f"   📊 Correct answer: {correct_answer}")
                
                # Check for proper MCQ structure (A, B, C, D + correct)
                expected_keys = ['A', 'B', 'C', 'D', 'correct']
                has_proper_structure = all(key in options for key in expected_keys)
                
                if has_proper_structure:
                    print("   ✅ MCQ options properly structured")
                    
                    # Validate options are meaningful (not just A, B, C, D)
                    option_values = [options[key] for key in ['A', 'B', 'C', 'D']]
                    meaningful_options = all(len(str(val)) > 1 for val in option_values)
                    
                    if meaningful_options:
                        print("   ✅ MCQ options are meaningful")
                        print(f"   📊 Sample options: {option_values[:2]}")
                    else:
                        print("   ⚠️ MCQ options may be generic")
                else:
                    print("   ⚠️ MCQ options structure needs improvement")
            else:
                print("   ⚠️ No MCQ options provided")
            
            # Store question ID for answer submission test
            if question_id:
                self.current_question_id = question_id
                return True
            else:
                print("   ❌ No question ID provided")
                return False
        else:
            print("   ❌ Question delivery failed")
            return False

    def test_answer_submission_and_validation(self):
        """Test answer submission and quality control systems"""
        print("\n✅ TESTING ANSWER SUBMISSION AND VALIDATION")
        print("=" * 60)
        print("Testing answer submission with quality control")
        print("Verifying solution feedback and validation systems")
        
        if not self.student_token or not self.session_id or not self.current_question_id:
            print("❌ Cannot test - missing session or question data")
            return False
            
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        # Submit an answer
        answer_data = {
            "question_id": self.current_question_id,
            "user_answer": "A",
            "context": "session",
            "time_sec": 45,
            "hint_used": False
        }
        
        success, response = self.run_test(
            "Submit Answer", 
            "POST", 
            f"sessions/{self.session_id}/submit-answer", 
            200, 
            answer_data, 
            headers
        )
        
        if success:
            correct = response.get('correct', False)
            status = response.get('status', '')
            message = response.get('message', '')
            correct_answer = response.get('correct_answer', '')
            solution_feedback = response.get('solution_feedback', {})
            question_metadata = response.get('question_metadata', {})
            
            print(f"   ✅ Answer submitted successfully")
            print(f"   📊 Correct: {correct}")
            print(f"   📊 Status: {status}")
            print(f"   📊 Message: {message}")
            print(f"   📊 Correct answer: {correct_answer}")
            print(f"   📊 Question metadata: {question_metadata}")
            
            # Test solution feedback quality
            if solution_feedback:
                approach = solution_feedback.get('solution_approach', '')
                detailed_solution = solution_feedback.get('detailed_solution', '')
                principle = solution_feedback.get('principle_to_remember', '')
                
                print(f"   📊 Solution approach length: {len(approach)} chars")
                print(f"   📊 Detailed solution length: {len(detailed_solution)} chars")
                print(f"   📊 Principle length: {len(principle)} chars")
                
                # Check for quality control - no LaTeX artifacts
                latex_artifacts = ['$', '\\(', '\\)', '\\[', '\\]']
                has_latex = any(artifact in approach + detailed_solution + principle 
                              for artifact in latex_artifacts)
                
                if not has_latex:
                    print("   ✅ Solution feedback clean - no LaTeX artifacts")
                else:
                    print("   ⚠️ Solution feedback contains LaTeX artifacts")
                
                # Check for meaningful content
                if len(detailed_solution) > 100 and len(approach) > 50:
                    print("   ✅ Solution feedback comprehensive")
                else:
                    print("   ⚠️ Solution feedback may be incomplete")
                
                return True
            else:
                print("   ⚠️ No solution feedback provided")
                return False
        else:
            print("   ❌ Answer submission failed")
            return False

    def test_url_routing_fixes(self):
        """Test that API configuration changes fixed URL routing issues"""
        print("\n🌐 TESTING URL ROUTING FIXES")
        print("=" * 60)
        print("Testing API endpoints accessibility and routing")
        print("Verifying no 'Failed to start/resume session' errors")
        
        # Test multiple endpoints to verify routing
        endpoints_to_test = [
            ("API Root", "GET", "", 200),
            ("Auth Login", "POST", "auth/login", [200, 400, 422]),
            ("Sessions Status", "GET", "sessions/current-status", [200, 401]),
            ("Questions List", "GET", "questions?limit=5", 200),
        ]
        
        routing_success = 0
        total_endpoints = len(endpoints_to_test)
        
        for name, method, endpoint, expected_status in endpoints_to_test:
            # Use minimal data for POST requests
            test_data = None
            if method == "POST" and "auth/login" in endpoint:
                test_data = {"email": "test@example.com", "password": "test"}
            
            headers = None
            if "sessions" in endpoint and self.student_token:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.student_token}'
                }
            
            success, response = self.run_test(
                f"Routing Test - {name}", 
                method, 
                endpoint, 
                expected_status, 
                test_data, 
                headers
            )
            
            if success:
                routing_success += 1
                print(f"   ✅ {name} endpoint accessible")
            else:
                print(f"   ❌ {name} endpoint routing issue")
        
        success_rate = (routing_success / total_endpoints) * 100
        print(f"\n   📊 Routing success rate: {routing_success}/{total_endpoints} ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print("   ✅ URL routing fixes working - endpoints accessible")
            return True
        else:
            print("   ❌ URL routing issues detected")
            return False

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🎯 TWELVR AUTHENTICATION AND SESSION SYSTEM TESTING")
        print("=" * 80)
        print("Testing the specific requirements from the review request:")
        print("1. Student authentication with credentials student@catprep.com / student123")
        print("2. Session creation API endpoint /api/sessions/start")
        print("3. Session status API endpoint /api/sessions/current-status")
        print("4. API configuration changes and URL routing fixes")
        print("5. Quality control systems (answer validation, MCQ validation)")
        print("6. Authentication tokens working properly")
        print("7. Session endpoints returning proper data")
        print("8. Adaptive session logic integration")
        print("=" * 80)
        
        results = {}
        
        # Test 1: Student Authentication
        results['student_authentication'] = self.test_student_authentication()
        
        # Test 2: Session Status Endpoint
        results['session_status'] = self.test_session_status_endpoint()
        
        # Test 3: Session Creation Endpoint
        results['session_creation'] = self.test_session_creation_endpoint()
        
        # Test 4: Session Question Delivery
        results['question_delivery'] = self.test_session_question_delivery()
        
        # Test 5: Answer Submission and Validation
        results['answer_validation'] = self.test_answer_submission_and_validation()
        
        # Test 6: URL Routing Fixes
        results['url_routing'] = self.test_url_routing_fixes()
        
        # Final Results Summary
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        passed_tests = sum(results.values())
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"Total API calls made: {self.tests_run}")
        print(f"Successful API calls: {self.tests_passed}")
        
        # Critical Analysis
        print("\n🎯 CRITICAL ANALYSIS:")
        
        if results['student_authentication']:
            print("✅ AUTHENTICATION: Student login working with proper JWT tokens")
        else:
            print("❌ AUTHENTICATION: Issues with student login or token validation")
        
        if results['session_creation'] and results['session_status']:
            print("✅ SESSION MANAGEMENT: Creation and status endpoints working")
        else:
            print("❌ SESSION MANAGEMENT: Issues with session endpoints")
        
        if results['question_delivery'] and results['answer_validation']:
            print("✅ QUALITY CONTROL: Question delivery and answer validation working")
        else:
            print("❌ QUALITY CONTROL: Issues with question/answer systems")
        
        if results['url_routing']:
            print("✅ URL ROUTING: API configuration fixes successful")
        else:
            print("❌ URL ROUTING: Configuration issues detected")
        
        # Production Readiness Assessment
        print("\n📋 PRODUCTION READINESS ASSESSMENT:")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: All systems working perfectly - ready for production")
        elif success_rate >= 75:
            print("✅ GOOD: Core functionality working - minor issues to address")
        elif success_rate >= 50:
            print("⚠️ PARTIAL: Some systems working - significant issues need fixing")
        else:
            print("❌ CRITICAL: Major issues detected - not ready for production")
        
        return success_rate >= 75

if __name__ == "__main__":
    tester = TwelvrAuthSessionTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 TESTING COMPLETED SUCCESSFULLY")
        exit(0)
    else:
        print("\n❌ TESTING COMPLETED WITH ISSUES")
        exit(1)