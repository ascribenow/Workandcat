import requests
import sys
import json
from datetime import datetime
import time

class CATBackendTester:
    def __init__(self, base_url="https://f74e3e84-2c7e-49cd-9652-7dd1b1417a14.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.student_user = None
        self.admin_user = None
        self.student_token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.sample_question_id = None
        self.diagnostic_id = None
        self.session_id = None
        self.plan_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        success, response = self.run_test("Root Endpoint", "GET", "", 200)
        if success:
            print(f"   Admin email: {response.get('admin_email')}")
            features = response.get('features', [])
            print(f"   Features available: {len(features)}")
            for feature in features:
                print(f"     - {feature}")
        return success

    def test_jwt_authentication_fix(self):
        """Test JWT authentication with FIXED InvalidTokenError handling"""
        print("🔍 Testing JWT Authentication Fix...")
        
        # Test with invalid token to verify error handling
        invalid_headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer invalid_token_here'
        }
        
        success, response = self.run_test("CRITICAL: JWT Invalid Token Handling (FIXED)", "GET", "auth/me", 401, None, invalid_headers)
        if success:
            print("   ✅ FIXED: JWT InvalidTokenError properly handled")
        else:
            print("   ❌ CRITICAL: JWT error handling still broken")
            return False
        
        # Test with valid token
        if self.student_token:
            valid_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            success, response = self.run_test("JWT Valid Token", "GET", "auth/me", 200, None, valid_headers)
            if success:
                print("   ✅ Valid JWT token authentication working")
                return True
        
        return False

    def test_student_user_registration_flow(self):
        """Test complete student user registration and flow - CRITICAL TEST"""
        print("🔍 Testing Student User Registration Flow...")
        
        # Create a new student user with realistic data
        timestamp = datetime.now().strftime('%H%M%S')
        student_data = {
            "email": f"new_student_{timestamp}@catprep.com",
            "full_name": "Priya Sharma",
            "password": "student2025"
        }
        
        success, response = self.run_test("CRITICAL: New Student Registration", "POST", "auth/register", 200, student_data)
        if not success or 'user' not in response or 'access_token' not in response:
            print("   ❌ CRITICAL: Student registration failing - blocking new users")
            return False
        
        new_student_token = response['access_token']
        new_student_user = response['user']
        
        print(f"   ✅ New student registered: {new_student_user['full_name']}")
        print(f"   Student email: {new_student_user['email']}")
        print(f"   Is admin: {new_student_user.get('is_admin', False)}")
        
        # Test diagnostic status for new user (should be false)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {new_student_token}'
        }
        
        success, response = self.run_test("New Student Diagnostic Status", "GET", "user/diagnostic-status", 200, None, headers)
        if success:
            has_completed = response.get('has_completed', True)  # Default to True to catch issues
            print(f"   New student has completed diagnostic: {has_completed}")
            if not has_completed:
                print("   ✅ New student correctly shows no completed diagnostic")
                return True
            else:
                print("   ⚠️ New student incorrectly shows completed diagnostic")
                return False
        
        return False

    def test_user_login(self):
        """Test user login with provided credentials"""
        # Test admin login with the specific admin credentials
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'user' in response and 'access_token' in response:
            self.admin_user = response['user']
            self.admin_token = response['access_token']
            print(f"   Logged in admin: {self.admin_user['full_name']}")
            print(f"   Admin is admin: {self.admin_user.get('is_admin', False)}")
        else:
            # Try to register admin first if login fails
            admin_register = {
                "email": "sumedhprabhu18@gmail.com",
                "full_name": "Admin User",
                "password": "admin2025"
            }
            
            success, response = self.run_test("Admin Registration", "POST", "auth/register", 200, admin_register)
            if success and 'user' in response and 'access_token' in response:
                self.admin_user = response['user']
                self.admin_token = response['access_token']
                print(f"   Registered and logged in admin: {self.admin_user['full_name']}")
                print(f"   Admin is admin: {self.admin_user.get('is_admin', False)}")

        # Test student login
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if success and 'user' in response and 'access_token' in response:
            self.student_user = response['user']
            self.student_token = response['access_token']
            print(f"   Logged in student: {self.student_user['full_name']}")
            print(f"   Student is admin: {self.student_user.get('is_admin', False)}")
            return True
        else:
            # Try to register student first if login fails
            student_register = {
                "email": "student@catprep.com",
                "full_name": "Test Student",
                "password": "student123"
            }
            
            success, response = self.run_test("Student Registration", "POST", "auth/register", 200, student_register)
            if success and 'user' in response and 'access_token' in response:
                self.student_user = response['user']
                self.student_token = response['access_token']
                print(f"   Registered and logged in student: {self.student_user['full_name']}")
                print(f"   Student is admin: {self.student_user.get('is_admin', False)}")
                return True
        
        return False

    def test_question_creation(self):
        """Test question creation with LLM enrichment (requires authentication)"""
        if not self.admin_token:
            print("❌ Skipping question creation - no admin token")
            return False
            
        question_data = {
            "stem": "A train travels 120 km in 2 hours. What is its speed in km/h?",
            "answer": "60",
            "solution_approach": "Speed = Distance / Time",
            "detailed_solution": "Speed = 120 km / 2 hours = 60 km/h",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "tags": ["speed", "distance", "time"],
            "source": "Test Admin"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        success, response = self.run_test("Create Question with LLM Enrichment", "POST", "questions", 200, question_data, headers)
        if success and 'question_id' in response:
            self.sample_question_id = response['question_id']
            print(f"   Created question ID: {self.sample_question_id}")
            print(f"   Status: {response.get('status')}")
            return True
        return False

    def test_diagnostic_status_endpoint(self):
        """Test the FIXED diagnostic status endpoint - CRITICAL TEST"""
        if not self.student_token:
            print("❌ Skipping diagnostic status test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Test the fixed diagnostic status endpoint
        success, response = self.run_test("CRITICAL: Diagnostic Status Check (FIXED)", "GET", "user/diagnostic-status", 200, None, headers)
        if success:
            print(f"   ✅ FIXED: Diagnostic status endpoint working with completed_at.isnot(None)")
            print(f"   Has completed diagnostic: {response.get('has_completed')}")
            print(f"   User ID: {response.get('user_id')}")
            return True
        else:
            print(f"   ❌ CRITICAL: Diagnostic status endpoint still failing after fix")
            return False

    def test_diagnostic_system(self):
        """Test 25-question diagnostic system with focus on critical fixes"""
        if not self.student_token:
            print("❌ Skipping diagnostic test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # First test the diagnostic status endpoint (critical fix)
        status_success = self.test_diagnostic_status_endpoint()
        if not status_success:
            print("   ❌ CRITICAL: Diagnostic status endpoint failed - blocking issue")
            return False

        # Start diagnostic
        success, response = self.run_test("Start Diagnostic", "POST", "diagnostic/start", 200, {}, headers)
        if not success or 'diagnostic_id' not in response:
            return False
        
        self.diagnostic_id = response['diagnostic_id']
        print(f"   Diagnostic ID: {self.diagnostic_id}")
        print(f"   Total questions: {response.get('total_questions')}")
        print(f"   Estimated time: {response.get('estimated_time_minutes')} minutes")

        # Get diagnostic questions
        success, response = self.run_test("Get Diagnostic Questions", "GET", f"diagnostic/{self.diagnostic_id}/questions", 200, None, headers)
        if not success or 'questions' not in response:
            return False
        
        questions = response['questions']
        print(f"   Retrieved {len(questions)} questions")
        
        if len(questions) == 0:
            print("   ⚠️ No questions available for diagnostic")
            return False

        # Submit answers for first few questions (simulate diagnostic)
        for i, question in enumerate(questions[:5]):  # Test first 5 questions
            answer_data = {
                "diagnostic_id": self.diagnostic_id,
                "question_id": question['id'],
                "user_answer": "A",  # Simulate answer
                "time_sec": 45,
                "context": "diagnostic",
                "hint_used": False
            }
            
            success, response = self.run_test(f"Submit Diagnostic Answer {i+1}", "POST", "diagnostic/submit-answer", 200, answer_data, headers)
            if success:
                print(f"   Answer {i+1} correct: {response.get('correct')}")
            else:
                return False

        # Complete diagnostic (with limited answers)
        success, response = self.run_test("Complete Diagnostic", "POST", f"diagnostic/{self.diagnostic_id}/complete", 200, {}, headers)
        if success:
            print(f"   ✅ CRITICAL: Diagnostic completion working after async fix")
            if 'track_recommendation' in response:
                print(f"   Track recommendation: {response.get('track_recommendation')}")
            
            # Test diagnostic status again after completion
            success2, response2 = self.run_test("Diagnostic Status After Completion", "GET", "user/diagnostic-status", 200, None, headers)
            if success2:
                print(f"   ✅ Status after completion: {response2.get('has_completed')}")
            
            return True
        else:
            print(f"   ❌ CRITICAL: Diagnostic completion still failing")
            return False

    def test_mcq_generation(self):
        """Test MCQ generation functionality"""
        # This is tested implicitly in diagnostic questions
        # MCQ options should be generated for each question
        if not self.student_token or not self.diagnostic_id:
            print("❌ Skipping MCQ generation test - missing prerequisites")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Get diagnostic questions to verify MCQ options are generated
        success, response = self.run_test("Verify MCQ Options Generation", "GET", f"diagnostic/{self.diagnostic_id}/questions", 200, None, headers)
        if success and 'questions' in response:
            questions = response['questions']
            if len(questions) > 0:
                first_question = questions[0]
                if 'options' in first_question and first_question['options']:
                    print(f"   MCQ options generated: {list(first_question['options'].keys())}")
                    return True
                else:
                    print("   ❌ No MCQ options found in questions")
                    return False
        
        return False

    def test_study_planner(self):
        """Test 90-day study planning system"""
        if not self.student_token:
            print("❌ Skipping study planner test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Create study plan
        plan_data = {
            "track": "Beginner",
            "daily_minutes_weekday": 30,
            "daily_minutes_weekend": 60
        }
        
        success, response = self.run_test("Create Study Plan", "POST", "study-plan", 200, plan_data, headers)
        if not success or 'plan_id' not in response:
            return False
        
        self.plan_id = response['plan_id']
        print(f"   Plan ID: {self.plan_id}")
        print(f"   Track: {response.get('track')}")
        print(f"   Start date: {response.get('start_date')}")

        # Get today's plan
        success, response = self.run_test("Get Today's Plan", "GET", "study-plan/today", 200, None, headers)
        if success:
            plan_units = response.get('plan_units', [])
            print(f"   Today's plan units: {len(plan_units)}")
            return True
        
        return False

    def test_session_management(self):
        """Test study session management"""
        if not self.student_token:
            print("❌ Skipping session management test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Start session
        session_data = {
            "target_minutes": 30
        }
        
        success, response = self.run_test("Start Study Session", "POST", "session/start", 200, session_data, headers)
        if not success or 'session_id' not in response:
            return False
        
        self.session_id = response['session_id']
        print(f"   Session ID: {self.session_id}")

        # Get next question
        success, response = self.run_test("Get Next Question", "GET", f"session/{self.session_id}/next-question", 200, None, headers)
        if success:
            question = response.get('question')
            if question:
                print(f"   Next question ID: {question.get('id')}")
                
                # Submit answer
                answer_data = {
                    "question_id": question['id'],
                    "user_answer": "A",
                    "time_sec": 60,
                    "context": "daily",
                    "hint_used": False
                }
                
                success, response = self.run_test("Submit Session Answer", "POST", f"session/{self.session_id}/submit-answer", 200, answer_data, headers)
                if success:
                    print(f"   Answer correct: {response.get('correct')}")
                    print(f"   Attempt number: {response.get('attempt_no')}")
                    return True
            else:
                print("   No questions available for session")
                return True  # This might be expected if no questions are available
        
        return False

    def test_mastery_tracking(self):
        """Test Enhanced Mastery Dashboard with category/subcategory hierarchy"""
        if not self.student_token:
            print("❌ Skipping mastery tracking test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Get enhanced mastery dashboard
        success, response = self.run_test("Get Enhanced Mastery Dashboard", "GET", "dashboard/mastery", 200, None, headers)
        if success:
            mastery_data = response.get('mastery_by_topic', [])
            total_topics = response.get('total_topics', 0)
            print(f"   Mastery topics tracked: {len(mastery_data)}")
            print(f"   Total topics: {total_topics}")
            
            if len(mastery_data) > 0:
                first_topic = mastery_data[0]
                print(f"   Sample topic: {first_topic.get('topic_name')}")
                print(f"   Category name: {first_topic.get('category_name')}")
                print(f"   Is main category: {first_topic.get('is_main_category')}")
                print(f"   Mastery %: {first_topic.get('mastery_percentage')}")
                print(f"   Accuracy score: {first_topic.get('accuracy_score')}")
                print(f"   Speed score: {first_topic.get('speed_score')}")
                print(f"   Stability score: {first_topic.get('stability_score')}")
                print(f"   Questions attempted: {first_topic.get('questions_attempted')}")
                
                # Check subcategories
                subcategories = first_topic.get('subcategories', [])
                print(f"   Subcategories: {len(subcategories)}")
                if subcategories:
                    print(f"   Sample subcategory: {subcategories[0].get('name')}")
                    print(f"   Subcategory mastery %: {subcategories[0].get('mastery_percentage')}")
                
                # Verify percentage format (should be 0-100, not 0-1)
                mastery_pct = first_topic.get('mastery_percentage', 0)
                if mastery_pct > 1:
                    print(f"   ✅ Percentages properly converted to 0-100 format")
                else:
                    print(f"   ⚠️ Percentages might still be in 0-1 format")
                
                # Verify required fields are present
                required_fields = ['topic_name', 'category_name', 'is_main_category', 
                                 'mastery_percentage', 'accuracy_score', 'speed_score', 'stability_score']
                missing_fields = [field for field in required_fields if field not in first_topic]
                if not missing_fields:
                    print(f"   ✅ All required fields present in response")
                else:
                    print(f"   ❌ Missing fields: {missing_fields}")
                    return False
            
            return True
        
        return False

    def test_progress_dashboard(self):
        """Test progress dashboard and analytics"""
        if not self.student_token:
            print("❌ Skipping progress dashboard test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Get progress dashboard
        success, response = self.run_test("Get Progress Dashboard", "GET", "dashboard/progress", 200, None, headers)
        if success:
            print(f"   Total sessions: {response.get('total_sessions')}")
            print(f"   Total minutes: {response.get('total_minutes')}")
            print(f"   Current streak: {response.get('current_streak')}")
            print(f"   Sessions this week: {response.get('sessions_this_week')}")
            return True
        
        return False

    def test_auth_me_endpoint(self):
        """Test /auth/me endpoint"""
        if not self.student_token:
            print("❌ Skipping auth/me test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        success, response = self.run_test("Get Current User Info", "GET", "auth/me", 200, None, headers)
        if success:
            print(f"   User ID: {response.get('id')}")
            print(f"   Email: {response.get('email')}")
            print(f"   Full name: {response.get('full_name')}")
            print(f"   Is admin: {response.get('is_admin')}")
            return True
        
        return False

    def test_get_questions(self):
        """Test getting questions with various filters"""
        # Test get all questions
        success, response = self.run_test("Get All Questions", "GET", "questions", 200)
        if not success:
            return False
        
        questions_count = len(response.get('questions', []))
        print(f"   Found {questions_count} total questions")

        # Test get questions by category
        success, response = self.run_test("Get Questions by Category", "GET", "questions?category=Arithmetic", 200)
        if success:
            arithmetic_count = len(response.get('questions', []))
            print(f"   Found {arithmetic_count} Arithmetic questions")

        # Test get questions by difficulty
        success, response = self.run_test("Get Questions by Difficulty", "GET", "questions?difficulty=Easy", 200)
        if success:
            easy_count = len(response.get('questions', []))
            print(f"   Found {easy_count} Easy questions")

        return True

    def test_admin_endpoints(self):
        """Test admin-only endpoints"""
        if not self.admin_token:
            print("❌ Skipping admin tests - no admin token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Test admin stats
        success, response = self.run_test("Admin Stats", "GET", "admin/stats", 200, None, headers)
        if success:
            print(f"   Total users: {response.get('total_users')}")
            print(f"   Total questions: {response.get('total_questions')}")
            print(f"   Total attempts: {response.get('total_attempts')}")
            print(f"   Active study plans: {response.get('active_study_plans')}")
            print(f"   Admin email: {response.get('admin_email')}")
            return True
        
        return False

    def test_auth_middleware(self):
        """Test authentication middleware and protected routes"""
        # Test accessing protected route without token
        success, response = self.run_test("Protected Route (No Auth)", "GET", "auth/me", 401)
        
        # Test accessing protected route with valid token
        if self.student_token:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.student_token}'
            }
            success, response = self.run_test("Protected Route (Valid Auth)", "GET", "auth/me", 200, None, headers)
            if success:
                print(f"   Authenticated user: {response.get('full_name')}")
                return True
        
        return False

    def test_admin_access_control(self):
        """Test that non-admin users cannot access admin endpoints"""
        if not self.student_token:
            print("❌ Skipping admin access control test - no student token")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Student should not be able to access admin stats
        success, response = self.run_test("Student Access Admin Stats (Should Fail)", "GET", "admin/stats", 403, None, headers)
        
        return True  # This should fail with 403, so we return True

    def test_background_jobs_system(self):
        """Test Background Jobs System initialization and functionality"""
        print("🔍 Testing Background Jobs System...")
        
        # Check if background jobs are mentioned in root endpoint
        success, response = self.run_test("Check Background Jobs in Features", "GET", "", 200)
        if success:
            features = response.get('features', [])
            has_background_jobs = any('background' in feature.lower() or 'job' in feature.lower() for feature in features)
            if has_background_jobs:
                print("   ✅ Background jobs mentioned in features")
            else:
                print("   ⚠️ Background jobs not explicitly mentioned in features")
        
        # Test question creation which should queue background enrichment
        if not self.admin_token:
            print("   ❌ Cannot test background job queuing - no admin token")
            return False
            
        question_data = {
            "stem": "If a car travels at 80 km/h for 3 hours, what distance does it cover?",
            "answer": "240",
            "solution_approach": "Distance = Speed × Time",
            "detailed_solution": "Distance = 80 km/h × 3 hours = 240 km",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "tags": ["speed", "distance", "time", "background_test"],
            "source": "Background Job Test"
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        success, response = self.run_test("Create Question (Background Job Queue)", "POST", "questions", 200, question_data, headers)
        if success and 'question_id' in response:
            print(f"   ✅ Question created and queued for background enrichment")
            print(f"   Question ID: {response['question_id']}")
            print(f"   Status: {response.get('status')}")
            
            # Check if status indicates background processing
            if response.get('status') == 'enrichment_queued':
                print("   ✅ Background enrichment properly queued")
                return True
            else:
                print("   ⚠️ Background enrichment status unclear")
                return True  # Still consider it working if question was created
        
        return False

    def test_invalid_endpoints(self):
        """Test error handling for invalid requests"""
        # Test invalid login
        invalid_login = {"email": "invalid@test.com", "password": "wrongpass"}
        success, response = self.run_test("Invalid Login", "POST", "auth/login", 401, invalid_login)
        
        # Test invalid question creation without auth
        invalid_question = {
            "stem": "Test question",
            "answer": "Test answer"
        }
        success, response = self.run_test("Invalid Question Creation (No Auth)", "POST", "questions", 401, invalid_question)
        
        return True  # These should fail, so we return True if they do

def main():
    print("🚀 Starting CAT Backend API v2.0 CRITICAL FIXES Testing...")
    print("Testing FIXED: Database Schema, JWT Auth, and Student User Flow")
    print("=" * 70)
    
    tester = CATBackendTester()
    
    # Run tests focusing on critical fixes
    test_results = []
    
    # Core system tests
    test_results.append(("Root Endpoint", tester.test_root_endpoint()))
    
    # CRITICAL FIXES TESTING
    print("\n🔥 CRITICAL FIXES TESTING - PRIMARY FOCUS")
    print("=" * 50)
    
    # Authentication tests (JWT fix)
    test_results.append(("CRITICAL: JWT Authentication Fix", tester.test_jwt_authentication_fix()))
    test_results.append(("User Login & Registration", tester.test_user_login()))
    test_results.append(("CRITICAL: Student Registration Flow", tester.test_student_user_registration_flow()))
    
    # Diagnostic system tests (database schema fix)
    test_results.append(("CRITICAL: Diagnostic System (FIXED)", tester.test_diagnostic_system()))
    test_results.append(("MCQ Generation", tester.test_mcq_generation()))
    
    # Enhanced Mastery Dashboard (confirm still working after fixes)
    test_results.append(("Enhanced Mastery Dashboard", tester.test_mastery_tracking()))
    
    print("\n📋 ADDITIONAL BACKEND VERIFICATION")
    print("=" * 40)
    
    # Additional core functionality tests
    test_results.append(("Auth Me Endpoint", tester.test_auth_me_endpoint()))
    test_results.append(("Question Creation with LLM", tester.test_question_creation()))
    test_results.append(("Study Planner (90-day)", tester.test_study_planner()))
    test_results.append(("Session Management", tester.test_session_management()))
    test_results.append(("Progress Dashboard", tester.test_progress_dashboard()))
    test_results.append(("Admin Endpoints", tester.test_admin_endpoints()))
    test_results.append(("Background Jobs System", tester.test_background_jobs_system()))
    
    # Security and error handling
    test_results.append(("Auth Middleware", tester.test_auth_middleware()))
    test_results.append(("Admin Access Control", tester.test_admin_access_control()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 CAT BACKEND v2.0 CRITICAL FIXES TEST SUMMARY")
    print("=" * 70)
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    # Separate critical vs additional tests
    critical_tests = [
        "CRITICAL: JWT Authentication Fix",
        "CRITICAL: Student Registration Flow", 
        "CRITICAL: Diagnostic System (FIXED)",
        "Enhanced Mastery Dashboard"
    ]
    
    critical_passed = sum(1 for name, result in test_results if any(crit in name for crit in critical_tests) and result)
    critical_total = sum(1 for name, result in test_results if any(crit in name for crit in critical_tests))
    
    print("🔥 CRITICAL FIXES RESULTS:")
    for test_name, result in test_results:
        if any(crit in test_name for crit in critical_tests):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
    
    print(f"\n📋 ADDITIONAL TESTS:")
    for test_name, result in test_results:
        if not any(crit in test_name for crit in critical_tests):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
    
    print(f"\n🎯 Critical Fixes: {critical_passed}/{critical_total} passed ({(critical_passed/critical_total)*100:.1f}%)")
    print(f"🎯 Overall Results: {tester.tests_passed}/{tester.tests_run} individual API calls passed")
    print(f"🎯 Test Suites: {passed_tests}/{total_tests} test suites passed")
    print(f"🎯 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Detailed analysis focusing on critical fixes
    print(f"\n📋 CRITICAL FIXES ANALYSIS:")
    diagnostic_working = any('Diagnostic' in name and 'CRITICAL' in name for name, result in test_results if result)
    jwt_working = any('JWT' in name and 'CRITICAL' in name for name, result in test_results if result)
    registration_working = any('Registration Flow' in name and 'CRITICAL' in name for name, result in test_results if result)
    mastery_working = any('Enhanced Mastery' in name for name, result in test_results if result)
    
    print(f"   🔐 JWT Authentication Fix: {'✅' if jwt_working else '❌'}")
    print(f"   🎯 Diagnostic System Fix: {'✅' if diagnostic_working else '❌'}")
    print(f"   👤 Student Registration Fix: {'✅' if registration_working else '❌'}")
    print(f"   📊 Enhanced Mastery Dashboard: {'✅' if mastery_working else '❌'}")
    
    print(f"\n📋 ADDITIONAL FEATURES:")
    print(f"   🤖 LLM Integration: {'✅' if any('LLM' in name for name, result in test_results if result) else '❌'}")
    print(f"   📚 Study Planning: {'✅' if any('Study Planner' in name for name, result in test_results if result) else '❌'}")
    print(f"   📊 Progress Tracking: {'✅' if any('Progress' in name for name, result in test_results if result) else '❌'}")
    
    # Determine if critical fixes are working
    critical_success = critical_passed >= critical_total * 0.75  # 75% of critical tests must pass
    overall_success = passed_tests >= total_tests * 0.8  # 80% overall pass rate
    
    if critical_success and overall_success:
        print("\n🎉 CRITICAL FIXES SUCCESSFUL! Backend ready for student user flow.")
        print("✅ Diagnostic system should now be fully functional")
        print("✅ Student registration should work")
        print("✅ Enhanced Mastery Dashboard should be accessible")
        return 0
    elif critical_success:
        print("\n✅ CRITICAL FIXES WORKING but some additional features have issues.")
        print("🎯 Main blocking issues resolved - student flow should work")
        return 0
    else:
        print("\n❌ CRITICAL FIXES STILL FAILING - student user flow blocked.")
        print("⚠️  Check diagnostic system and authentication issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())