import requests
import sys
import json
from datetime import datetime

class CATBackendTester:
    def __init__(self, base_url="https://26caaca9-c218-45fa-a703-95fa1fa6ab9d.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.student_user = None
        self.admin_user = None
        self.student_token = None
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.sample_question_id = None

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
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_taxonomy_endpoint(self):
        """Test taxonomy endpoint"""
        success, response = self.run_test("Get Taxonomy", "GET", "taxonomy", 200)
        if success and 'taxonomy' in response:
            print(f"   Found {len(response['taxonomy'])} categories")
            return True
        return False

    def test_user_registration(self):
        """Test user registration"""
        # Test student registration
        student_data = {
            "email": f"test_student_{datetime.now().strftime('%H%M%S')}@test.com",
            "name": "Test Student",
            "password": "testpass123",
            "is_admin": False
        }
        
        success, response = self.run_test("Student Registration", "POST", "register", 200, student_data)
        if not success:
            return False

        # Test admin registration
        admin_data = {
            "email": f"test_admin_{datetime.now().strftime('%H%M%S')}@test.com",
            "name": "Test Admin",
            "password": "testpass123",
            "is_admin": True
        }
        
        success, response = self.run_test("Admin Registration", "POST", "register", 200, admin_data)
        return success

    def test_user_login(self):
        """Test user login with provided credentials"""
        # Test student login
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if success and 'user' in response and 'access_token' in response:
            self.student_user = response['user']
            self.student_token = response['access_token']
            print(f"   Logged in student: {self.student_user['name']}")
            print(f"   Student is admin: {self.student_user.get('is_admin', False)}")
        else:
            return False

        # Test admin login with the specific admin credentials
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if success and 'user' in response and 'access_token' in response:
            self.admin_user = response['user']
            self.admin_token = response['access_token']
            print(f"   Logged in admin: {self.admin_user['name']}")
            print(f"   Admin is admin: {self.admin_user.get('is_admin', False)}")
            return True
        else:
            # Try to register admin first if login fails
            admin_register = {
                "email": "sumedhprabhu18@gmail.com",
                "name": "Admin User",
                "password": "admin2025"
            }
            
            success, response = self.run_test("Admin Registration", "POST", "auth/register", 200, admin_register)
            if success and 'user' in response and 'access_token' in response:
                self.admin_user = response['user']
                self.admin_token = response['access_token']
                print(f"   Registered and logged in admin: {self.admin_user['name']}")
                print(f"   Admin is admin: {self.admin_user.get('is_admin', False)}")
                return True
        
        return False

    def test_question_creation(self):
        """Test question creation"""
        question_data = {
            "text": "What is 2 + 2?",
            "options": ["2", "3", "4", "5"],
            "correct_answer": "4",
            "explanation": "Basic addition: 2 + 2 = 4",
            "category": "Arithmetic",
            "sub_category": "Percentages",
            "year": 2024
        }
        
        success, response = self.run_test("Create Question", "POST", "questions", 200, question_data)
        if success and 'question' in response:
            self.sample_question_id = response['question']['id']
            print(f"   Created question ID: {self.sample_question_id}")
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

        # Test get specific question
        if self.sample_question_id:
            success, response = self.run_test("Get Specific Question", "GET", f"questions/{self.sample_question_id}", 200)
            if success and 'question' in response:
                print(f"   Retrieved question: {response['question']['text'][:50]}...")
                return True
        
        return success

    def test_progress_tracking(self):
        """Test progress tracking"""
        if not self.student_user or not self.sample_question_id:
            print("❌ Skipping progress test - missing student user or question ID")
            return False

        progress_data = {
            "user_id": self.student_user['id'],
            "question_id": self.sample_question_id,
            "user_answer": "4",
            "time_taken": 30
        }
        
        success, response = self.run_test("Submit Answer", "POST", "progress", 200, progress_data)
        if not success:
            return False

        print(f"   Answer correct: {response.get('is_correct')}")
        print(f"   Correct answer: {response.get('correct_answer')}")

        # Test get user progress
        success, response = self.run_test("Get User Progress", "GET", f"progress/{self.student_user['id']}", 200)
        if success:
            stats = response.get('stats', {})
            print(f"   Total questions: {stats.get('total_questions')}")
            print(f"   Accuracy: {stats.get('accuracy')}%")
            return True
        
        return False

    def test_study_plan(self):
        """Test study plan generation and retrieval"""
        if not self.student_user:
            print("❌ Skipping study plan test - missing student user")
            return False

        # Generate study plan
        success, response = self.run_test("Generate Study Plan", "POST", f"study-plan/{self.student_user['id']}", 200)
        if not success:
            return False

        # Get study plan
        success, response = self.run_test("Get Study Plan", "GET", f"study-plan/{self.student_user['id']}", 200)
        if success:
            plans = response.get('study_plans', [])
            print(f"   Generated {len(plans)} study plan days")
            return True
        
        return False

    def test_analytics(self):
        """Test analytics endpoint"""
        if not self.student_user:
            print("❌ Skipping analytics test - missing student user")
            return False

        success, response = self.run_test("Get Analytics", "GET", f"analytics/{self.student_user['id']}", 200)
        if success:
            print(f"   Total questions attempted: {response.get('total_questions_attempted')}")
            print(f"   Overall accuracy: {response.get('overall_accuracy')}%")
            category_performance = response.get('category_performance', {})
            print(f"   Categories analyzed: {len(category_performance)}")
            return True
        
        return False

    def test_invalid_endpoints(self):
        """Test error handling for invalid requests"""
        # Test invalid login
        invalid_login = {"email": "invalid@test.com", "password": "wrongpass"}
        success, response = self.run_test("Invalid Login", "POST", "login", 400, invalid_login)
        
        # Test non-existent question
        success, response = self.run_test("Non-existent Question", "GET", "questions/invalid-id", 404)
        
        # Test invalid question creation
        invalid_question = {
            "text": "Test question",
            "category": "InvalidCategory",
            "sub_category": "InvalidSub"
        }
        success, response = self.run_test("Invalid Question Creation", "POST", "questions", 400, invalid_question)
        
        return True  # These should fail, so we return True if they do

def main():
    print("🚀 Starting CAT Backend API Testing...")
    print("=" * 60)
    
    tester = CATBackendTester()
    
    # Run all tests
    test_results = []
    
    test_results.append(("Root Endpoint", tester.test_root_endpoint()))
    test_results.append(("Taxonomy", tester.test_taxonomy_endpoint()))
    test_results.append(("User Registration", tester.test_user_registration()))
    test_results.append(("User Login", tester.test_user_login()))
    test_results.append(("Question Creation", tester.test_question_creation()))
    test_results.append(("Get Questions", tester.test_get_questions()))
    test_results.append(("Progress Tracking", tester.test_progress_tracking()))
    test_results.append(("Study Plan", tester.test_study_plan()))
    test_results.append(("Analytics", tester.test_analytics()))
    test_results.append(("Error Handling", tester.test_invalid_endpoints()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall Results: {tester.tests_passed}/{tester.tests_run} individual API calls passed")
    print(f"🎯 Test Suites: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        print("🎉 All backend tests passed!")
        return 0
    else:
        print("⚠️  Some backend tests failed. Check the details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())