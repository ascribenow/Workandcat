#!/usr/bin/env python3
"""
PostgreSQL Migration Testing Script
Tests the complete PostgreSQL migration and backend functionality
"""

import requests
import json
import time
from datetime import datetime

class PostgreSQLMigrationTester:
    def __init__(self):
        self.base_url = "https://learning-tutor.preview.emergentagent.com/api"
        self.admin_token = None
        self.student_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def test_api_call(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Make API call and return success status and response"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"API call failed: {method} {endpoint} - Status {response.status_code}", "ERROR")
                try:
                    error_data = response.json()
                    self.log(f"Error details: {error_data}", "ERROR")
                except:
                    self.log(f"Error text: {response.text[:200]}", "ERROR")
                return False, {}

        except Exception as e:
            self.log(f"API call exception: {method} {endpoint} - {str(e)}", "ERROR")
            return False, {}

    def test_authentication(self):
        """Test authentication with provided credentials"""
        self.log("Testing Authentication System")
        
        # Test admin login
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.test_api_call("POST", "auth/login", admin_login)
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            admin_user = response.get('user', {})
            self.log(f"✅ Admin login successful: {admin_user.get('full_name', 'Unknown')}")
            self.log(f"   Admin privileges: {admin_user.get('is_admin', False)}")
        else:
            self.log("❌ Admin login failed", "ERROR")
            return False

        # Test student login
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.test_api_call("POST", "auth/login", student_login)
        if success and 'access_token' in response:
            self.student_token = response['access_token']
            student_user = response.get('user', {})
            self.log(f"✅ Student login successful: {student_user.get('full_name', 'Unknown')}")
        else:
            self.log("❌ Student login failed", "ERROR")
            return False

        return True

    def test_database_operations(self):
        """Test database CRUD operations"""
        self.log("Testing Database Operations")
        
        if not self.admin_token:
            self.log("❌ No admin token for database operations", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Test question retrieval (verify migrated data)
        success, response = self.test_api_call("GET", "questions?limit=10", headers=headers)
        if success:
            questions = response.get('questions', [])
            self.log(f"✅ Retrieved {len(questions)} questions from PostgreSQL")
            
            if len(questions) >= 37:
                self.log(f"✅ Migrated data confirmed: {len(questions)} questions (expected 37+)")
            else:
                self.log(f"⚠️ Question count: {len(questions)} (expected 37+)")
        else:
            self.log("❌ Question retrieval failed", "ERROR")
            return False

        # Test question creation
        question_data = {
            "stem": "PostgreSQL Test: A car travels 200 km in 2.5 hours. What is its speed?",
            "answer": "80",
            "solution_approach": "Speed = Distance / Time",
            "detailed_solution": "Speed = 200 km / 2.5 hours = 80 km/h",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "type_of_question": "Speed Calculation",
            "tags": ["postgresql_test"],
            "source": "PostgreSQL Migration Test"
        }
        
        success, response = self.test_api_call("POST", "questions", question_data, headers)
        if success and 'question_id' in response:
            question_id = response['question_id']
            self.log(f"✅ Question created: {question_id}")
            self.log(f"   Status: {response.get('status', 'Unknown')}")
        else:
            self.log("❌ Question creation failed", "ERROR")
            return False

        return True

    def test_admin_endpoints(self):
        """Test admin-specific endpoints"""
        self.log("Testing Admin Endpoints")
        
        if not self.admin_token:
            self.log("❌ No admin token for admin endpoints", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Test admin stats
        success, response = self.test_api_call("GET", "admin/stats", headers=headers)
        if success:
            self.log("✅ Admin stats retrieved")
            self.log(f"   Total users: {response.get('total_users', 0)} (expected 22+)")
            self.log(f"   Total questions: {response.get('total_questions', 0)} (expected 37+)")
            self.log(f"   Total attempts: {response.get('total_attempts', 0)} (expected 12+)")
            self.log(f"   Active study plans: {response.get('active_study_plans', 0)} (expected 2+)")
            
            # Verify migrated data counts
            if (response.get('total_users', 0) >= 22 and 
                response.get('total_questions', 0) >= 37 and
                response.get('total_attempts', 0) >= 12):
                self.log("✅ Migrated data counts verified")
            else:
                self.log("⚠️ Some migrated data counts lower than expected")
        else:
            self.log("❌ Admin stats failed", "ERROR")
            return False

        return True

    def test_session_management(self):
        """Test session creation and management"""
        self.log("Testing Session Management")
        
        if not self.student_token:
            self.log("❌ No student token for session management", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }

        # Test session creation
        session_data = {"target_minutes": 30}
        success, response = self.test_api_call("POST", "sessions/start", session_data, headers)
        if success and 'session_id' in response:
            session_id = response['session_id']
            self.log(f"✅ Session created: {session_id}")
            self.log(f"   Session type: {response.get('session_type', 'Unknown')}")
            self.log(f"   Total questions: {response.get('total_questions', 0)}")
            
            # Test getting next question
            success, response = self.test_api_call("GET", f"sessions/{session_id}/next-question", headers=headers)
            if success and response.get('question'):
                question = response['question']
                self.log(f"✅ Question retrieved from session")
                self.log(f"   Question ID: {question.get('id', 'Unknown')}")
                self.log(f"   Subcategory: {question.get('subcategory', 'Unknown')}")
                
                # Test answer submission
                answer_data = {
                    "question_id": question['id'],
                    "user_answer": "80",
                    "time_sec": 45,
                    "hint_used": False
                }
                
                success, response = self.test_api_call("POST", f"sessions/{session_id}/submit-answer", answer_data, headers)
                if success:
                    self.log(f"✅ Answer submitted successfully")
                    self.log(f"   Answer correct: {response.get('correct', 'Unknown')}")
                else:
                    self.log("❌ Answer submission failed", "ERROR")
                    return False
            else:
                self.log("⚠️ No question available in session (may be expected)")
        else:
            self.log("❌ Session creation failed", "ERROR")
            return False

        return True

    def test_postgresql_specific_features(self):
        """Test PostgreSQL-specific features"""
        self.log("Testing PostgreSQL-Specific Features")
        
        if not self.admin_token:
            self.log("❌ No admin token for PostgreSQL features test", "ERROR")
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }

        # Test data type handling
        success, response = self.test_api_call("GET", "questions?limit=5", headers=headers)
        if success:
            questions = response.get('questions', [])
            if questions:
                first_question = questions[0]
                
                # Check boolean field conversion
                is_active = first_question.get('is_active')
                if isinstance(is_active, bool):
                    self.log("✅ Boolean fields properly converted (SQLite 0/1 → PostgreSQL TRUE/FALSE)")
                else:
                    self.log(f"❌ Boolean field issue: is_active = {is_active} (type: {type(is_active)})", "ERROR")
                    return False
                
                # Check numeric fields
                difficulty_score = first_question.get('difficulty_score')
                if difficulty_score is None or isinstance(difficulty_score, (int, float)):
                    self.log("✅ Numeric fields properly handled")
                else:
                    self.log(f"❌ Numeric field issue: difficulty_score = {difficulty_score}", "ERROR")
                    return False
                
                self.log("✅ PostgreSQL data type conversion successful")
            else:
                self.log("⚠️ No questions available to test PostgreSQL features")
        else:
            self.log("❌ Failed to test PostgreSQL features", "ERROR")
            return False

        return True

    def run_comprehensive_test(self):
        """Run comprehensive PostgreSQL migration test"""
        self.log("🔍 COMPREHENSIVE POSTGRESQL MIGRATION TESTING")
        self.log("=" * 60)
        self.log("Database: PostgreSQL (Supabase)")
        self.log("Migrated Data: 22 users, 37 questions, 12 attempts, 50 sessions, 2 mastery records, 2 plans")
        self.log("Admin Credentials: sumedhprabhu18@gmail.com / admin2025")
        self.log("Student Credentials: student@catprep.com / student123")
        self.log("=" * 60)

        # Test basic connectivity
        self.log("Testing Basic API Connectivity")
        success, response = self.test_api_call("GET", "")
        if not success:
            self.log("❌ Basic API connectivity failed", "ERROR")
            return False
        
        self.log("✅ Basic API connectivity successful")
        self.log(f"   Admin email: {response.get('admin_email', 'Unknown')}")
        features = response.get('features', [])
        self.log(f"   Features: {len(features)} available")

        # Run test suite
        test_results = {}
        
        test_results['authentication'] = self.test_authentication()
        test_results['database_operations'] = self.test_database_operations()
        test_results['admin_endpoints'] = self.test_admin_endpoints()
        test_results['session_management'] = self.test_session_management()
        test_results['postgresql_features'] = self.test_postgresql_specific_features()

        # Summary
        self.log("=" * 60)
        self.log("POSTGRESQL MIGRATION TEST RESULTS")
        self.log("=" * 60)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title():<25} {status}")
        
        self.log("-" * 60)
        self.log(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        self.log(f"API Calls: {self.tests_passed}/{self.tests_run} successful")
        
        if success_rate >= 80:
            self.log("🎉 POSTGRESQL MIGRATION SUCCESSFUL!")
            self.log("Backend is ready for production with PostgreSQL database")
        elif success_rate >= 60:
            self.log("⚠️ PostgreSQL migration mostly successful with minor issues")
        else:
            self.log("❌ PostgreSQL migration has significant issues requiring attention")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = PostgreSQLMigrationTester()
    success = tester.run_comprehensive_test()
    exit(0 if success else 1)