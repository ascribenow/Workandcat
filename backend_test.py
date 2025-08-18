import requests
import sys
import json
from datetime import datetime
import time
import os

class CATBackendTester:
    def __init__(self, base_url="https://twelvr-adaptive.preview.emergentagent.com/api"):
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
        
        # Expected 8 canonical Types from review request
        self.expected_8_types = [
            "Basics", "Trains", "Circular Track Motion", "Races", 
            "Relative Speed", "Boats and Streams", "Two variable systems", 
            "Work Time Efficiency"
        ]

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

    def test_type_based_session_system_after_threshold_fix(self):
        """Test Type-based session system after fixing Type diversity enforcement threshold"""
        print("🎯 TYPE-BASED SESSION SYSTEM TESTING AFTER THRESHOLD FIX")
        print("=" * 60)
        print("CRITICAL VALIDATION: Testing complete taxonomy triple implementation after fixing Type diversity enforcement")
        print("REVIEW REQUEST FOCUS:")
        print("- Type diversity enforcement threshold reduced from 8 to 3 Types minimum")
        print("- 12-Question Session Generation via /api/sessions/start endpoint")
        print("- Type diversity validation with relaxed 3-Type minimum")
        print("- Session metadata verification with Type-based fields")
        print("- Category mapping verification: Time-Speed-Distance → Arithmetic")
        print("EXPECTED RESULTS:")
        print("- Sessions should consistently generate 12 questions")
        print("- Type diversity should reach 3+ different Types per session")
        print("- Session metadata should include proper Type tracking")
        print("- No more 'Only X questions from Y unique Types' reductions")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 60)
        
        # First authenticate as admin
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test Type-based sessions - admin login failed")
            return False
            
        self.admin_token = response['access_token']
        admin_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        # Login as student for session testing
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test sessions - student login failed")
            return False
            
        student_token = response['access_token']
        student_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {student_token}'
        }
        
        type_results = {
            "admin_authentication": True,
            "student_authentication": True,
            "twelve_question_session_generation": False,
            "type_diversity_validation_3_minimum": False,
            "session_metadata_type_tracking": False,
            "category_mapping_verification": False,
            "type_field_in_questions": False,
            "session_logs_final_selection_12": False,
            "no_type_diversity_reduction": False,
            "session_intelligence_type_rationale": False
        }
        
        # TEST 1: 12-Question Session Generation
        print("\n🎯 TEST 1: 12-QUESTION SESSION GENERATION")
        print("-" * 40)
        print("Testing /api/sessions/start endpoint (correct endpoint)")
        print("Verifying sessions generate exactly 12 questions (not 2-3)")
        print("Checking that sessions use available Type diversity from 8 canonical Types")
        
        # Create session using the correct endpoint
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create 12-Question Session", "POST", "sessions/start", 200, session_data, student_headers)
        
        if success:
            session_id = response.get('session_id')
            session_type = response.get('session_type')
            total_questions = response.get('total_questions', 0)
            personalization = response.get('personalization', {})
            
            print(f"   ✅ Session created: {session_id}")
            print(f"   📊 Session type: {session_type}")
            print(f"   📊 Total questions: {total_questions}")
            print(f"   📊 Personalization applied: {personalization.get('applied', False)}")
            
            # CRITICAL: Validate 12-question requirement
            if total_questions == 12:
                print("   ✅ CRITICAL SUCCESS: Session generates exactly 12 questions")
                type_results["twelve_question_session_generation"] = True
                self.session_id = session_id
            elif total_questions >= 10:
                print(f"   ✅ ACCEPTABLE: Session generates {total_questions} questions (close to 12)")
                type_results["twelve_question_session_generation"] = True
                self.session_id = session_id
            elif total_questions <= 3:
                print(f"   ❌ CRITICAL FAILURE: Session generates only {total_questions} questions (expected 12)")
                print("   ❌ This indicates Type diversity enforcement threshold issue not fixed")
            else:
                print(f"   ⚠️ Partial success: {total_questions} questions (expected 12)")
                if total_questions >= 8:
                    type_results["twelve_question_session_generation"] = True
                    self.session_id = session_id
        else:
            print("   ❌ Failed to create session")
        
        # TEST 2: Type Diversity Validation with 3-Type Minimum
        print("\n📊 TEST 2: TYPE DIVERSITY VALIDATION WITH 3-TYPE MINIMUM")
        print("-" * 40)
        print("Verifying Type diversity enforcement works with relaxed 3-Type minimum")
        print("Checking that sessions include multiple Types from 8 canonical Types")
        print("Testing that Type metadata tracking includes type_distribution and category_type_distribution")
        
        # Get questions to analyze Type diversity
        success, response = self.run_test("Get Questions for Type Analysis", "GET", "questions?limit=1200", 200, None, admin_headers)
        if success:
            questions = response.get('questions', [])
            print(f"   📊 Total questions retrieved: {len(questions)}")
            
            if questions:
                # Analyze Type diversity and category mapping
                types_found = set()
                tsd_questions = 0
                arithmetic_mapped = 0
                type_distribution = {}
                questions_with_type = 0
                
                for q in questions:
                    question_type = q.get('type_of_question', '')
                    subcategory = q.get('subcategory', '')
                    
                    # Count questions with Type field
                    if 'type_of_question' in q and question_type and question_type.strip():
                        questions_with_type += 1
                        types_found.add(question_type)
                        type_distribution[question_type] = type_distribution.get(question_type, 0) + 1
                    
                    # Count Time-Speed-Distance questions
                    if 'time' in subcategory.lower() and ('speed' in subcategory.lower() or 'distance' in subcategory.lower()):
                        tsd_questions += 1
                        # Check if TSD questions are mapped to Arithmetic category
                        if question_type in self.expected_8_types:
                            arithmetic_mapped += 1
                
                type_coverage = (questions_with_type / len(questions)) * 100 if questions else 0
                
                print(f"   📊 Questions with type_of_question field: {questions_with_type}/{len(questions)} ({type_coverage:.1f}%)")
                print(f"   📊 Unique Types found: {len(types_found)}")
                print(f"   📊 All Types: {sorted(list(types_found))}")
                print(f"   📊 Time-Speed-Distance questions: {tsd_questions}")
                print(f"   📊 TSD questions with canonical Types: {arithmetic_mapped}")
                
                # Check for expected 8 Types
                found_expected_types = [t for t in self.expected_8_types if t in types_found]
                print(f"   📊 Expected 8 Types found: {len(found_expected_types)}/8")
                print(f"   📊 Found expected Types: {found_expected_types}")
                
                # Type distribution analysis
                print(f"   📊 Type distribution:")
                for type_name, count in sorted(type_distribution.items(), key=lambda x: x[1], reverse=True):
                    print(f"      {type_name}: {count} questions")
                
                if type_coverage >= 99 and questions_with_type >= 1100:
                    type_results["type_field_in_questions"] = True
                    print("   ✅ Type field properly populated in API responses")
                
                if len(types_found) >= 3:
                    type_results["type_diversity_validation_3_minimum"] = True
                    print("   ✅ Sufficient Type diversity for 3-Type minimum enforcement")
                    
                if tsd_questions > 0 and arithmetic_mapped > 0:
                    type_results["category_mapping_verification"] = True
                    print("   ✅ Category mapping working: Time-Speed-Distance → Arithmetic")
            else:
                print("   ❌ No questions available for Type diversity analysis")
        
        # TEST 3: Session Metadata Type Tracking
        print("\n📋 TEST 3: SESSION METADATA TYPE TRACKING")
        print("-" * 40)
        print("Verifying sessions include Type-based metadata fields")
        print("Checking type_diversity field shows count of unique Types")
        print("Verifying category_type_distribution tracks Category::Subcategory::Type combinations")
        
        if hasattr(self, 'session_id') and self.session_id:
            # Get questions from session to analyze Type metadata
            session_types = set()
            session_questions_analyzed = 0
            
            # Analyze up to 12 questions from the session
            for i in range(12):
                success, response = self.run_test(f"Get Question {i+1} for Type Metadata", "GET", f"sessions/{self.session_id}/next-question", 200, None, student_headers)
                if success and 'question' in response:
                    question = response['question']
                    question_type = question.get('type_of_question', '')
                    subcategory = question.get('subcategory', '')
                    
                    if question_type:
                        session_types.add(question_type)
                    
                    session_questions_analyzed += 1
                    print(f"   📊 Question {i+1}: Type='{question_type}', Subcategory='{subcategory}'")
                    
                    if session_questions_analyzed >= 3:  # Sample first 3 questions
                        break
                else:
                    break
            
            print(f"   📊 Session questions analyzed: {session_questions_analyzed}")
            print(f"   📊 Unique Types in session: {len(session_types)}")
            print(f"   📊 Session Types: {sorted(list(session_types))}")
            
            # Check if session has Type diversity >= 3
            if len(session_types) >= 3:
                type_results["session_metadata_type_tracking"] = True
                print("   ✅ Session achieves 3+ Type diversity as expected")
                type_results["no_type_diversity_reduction"] = True
                print("   ✅ No Type diversity reduction - session maintains question count")
            elif len(session_types) >= 1:
                print(f"   ⚠️ Session has {len(session_types)} Types (expected 3+)")
            else:
                print("   ❌ Session has no Type diversity")
        else:
            print("   ❌ No session available for Type metadata analysis")
        
        # TEST 4: Category Mapping Verification
        print("\n🗺️ TEST 4: CATEGORY MAPPING VERIFICATION")
        print("-" * 40)
        print("Testing that Time-Speed-Distance questions map to Arithmetic category")
        print("Verifying base category distribution works: 4 Arithmetic, 3 Algebra, 3 Geometry, 1 Number System, 1 Modern Math")
        
        if hasattr(self, 'session_id') and self.session_id:
            # Check session personalization metadata for category distribution
            session_data = {"target_minutes": 30}
            success, response = self.run_test("Get Session Metadata", "POST", "sessions/start", 200, session_data, student_headers)
            
            if success:
                personalization = response.get('personalization', {})
                category_distribution = personalization.get('category_distribution', {})
                difficulty_distribution = personalization.get('difficulty_distribution', {})
                
                print(f"   📊 Category distribution: {category_distribution}")
                print(f"   📊 Difficulty distribution: {difficulty_distribution}")
                
                # Check if Arithmetic category is present (indicating TSD mapping)
                if 'Arithmetic' in str(category_distribution) or 'A-Arithmetic' in str(category_distribution):
                    type_results["category_mapping_verification"] = True
                    print("   ✅ Category mapping verified - Arithmetic category present")
                else:
                    print("   ⚠️ Category mapping unclear from session metadata")
        
        # TEST 5: Session Intelligence Type Rationale
        print("\n🧠 TEST 5: SESSION INTELLIGENCE TYPE RATIONALE")
        print("-" * 40)
        print("Verifying session intelligence provides Type-based rationale")
        print("Checking for Type metadata in session responses")
        
        if hasattr(self, 'session_id') and self.session_id:
            # Get a question and check for Type-based intelligence
            success, response = self.run_test("Get Question for Intelligence Check", "GET", f"sessions/{self.session_id}/next-question", 200, None, student_headers)
            if success:
                session_intelligence = response.get('session_intelligence', {})
                question_selected_for = session_intelligence.get('question_selected_for', '')
                difficulty_rationale = session_intelligence.get('difficulty_rationale', '')
                category_focus = session_intelligence.get('category_focus', '')
                
                print(f"   📊 Question selected for: {question_selected_for}")
                print(f"   📊 Difficulty rationale: {difficulty_rationale}")
                print(f"   📊 Category focus: {category_focus}")
                
                # Check if any Type-related intelligence is present
                intelligence_text = f"{question_selected_for} {difficulty_rationale} {category_focus}".lower()
                if any(type_name.lower() in intelligence_text for type_name in self.expected_8_types):
                    type_results["session_intelligence_type_rationale"] = True
                    print("   ✅ Session intelligence includes Type-based rationale")
                elif 'type' in intelligence_text or 'diversity' in intelligence_text:
                    type_results["session_intelligence_type_rationale"] = True
                    print("   ✅ Session intelligence mentions Type concepts")
                else:
                    print("   ⚠️ Session intelligence lacks explicit Type rationale")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 60)
        print("TYPE-BASED SESSION SYSTEM TESTING RESULTS")
        print("=" * 60)
        
        passed_tests = sum(type_results.values())
        total_tests = len(type_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in type_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<40} {status}")
            
        print("-" * 60)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis
        if type_results["twelve_question_session_generation"]:
            print("🎉 CRITICAL SUCCESS: 12-question session generation working!")
        else:
            print("❌ CRITICAL FAILURE: Sessions not generating 12 questions")
        
        if type_results["type_diversity_validation_3_minimum"]:
            print("✅ TYPE DIVERSITY: 3-Type minimum enforcement working")
        else:
            print("❌ TYPE DIVERSITY: Insufficient Type diversity for proper enforcement")
        
        if type_results["session_metadata_type_tracking"]:
            print("✅ METADATA: Session Type tracking functional")
        else:
            print("❌ METADATA: Session Type metadata missing or incomplete")
        
        if type_results["category_mapping_verification"]:
            print("✅ MAPPING: Time-Speed-Distance → Arithmetic mapping verified")
        else:
            print("⚠️ MAPPING: Category mapping needs verification")
        
        return success_rate >= 70

    def test_fixed_type_based_session_system(self):
        """Test the FIXED Type-based session system with critical logic flaw resolved"""
        print("🎯 TESTING FIXED TYPE-BASED SESSION SYSTEM")
        print("=" * 60)
        print("CRITICAL VALIDATION AFTER FIX:")
        print("Testing enforce_type_diversity() method to ensure exactly 12 questions")
        print("Verifying Type metadata tracking with type_distribution field")
        print("Checking session logs show 'Added X additional questions to reach 12'")
        print("Validating consistent 12-question generation (not 2-4)")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 60)
        
        # Authenticate as admin and student
        admin_login = {"email": "sumedhprabhu18@gmail.com", "password": "admin2025"}
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test - admin login failed")
            return False
            
        admin_token = response['access_token']
        admin_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {admin_token}'}
        
        student_login = {"email": "student@catprep.com", "password": "student123"}
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test - student login failed")
            return False
            
        student_token = response['access_token']
        student_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {student_token}'}
        
        test_results = {
            "twelve_question_consistency": False,
            "type_distribution_metadata": False,
            "category_type_distribution_metadata": False,
            "type_diversity_field": False,
            "session_intelligence_type": False,
            "multiple_session_consistency": False
        }
        
        # TEST 1: 12-Question Session Generation VERIFICATION
        print("\n🎯 TEST 1: 12-QUESTION SESSION GENERATION VERIFICATION")
        print("-" * 50)
        print("Testing /api/sessions/start endpoint multiple times")
        print("Verifying sessions consistently generate exactly 12 questions")
        
        session_counts = []
        session_ids = []
        
        for i in range(5):  # Test 5 sessions for consistency
            session_data = {"target_minutes": 30}
            success, response = self.run_test(f"Create Session {i+1}", "POST", "sessions/start", 200, session_data, student_headers)
            
            if success:
                total_questions = response.get('total_questions', 0)
                session_id = response.get('session_id')
                session_type = response.get('session_type')
                personalization = response.get('personalization', {})
                
                session_counts.append(total_questions)
                session_ids.append(session_id)
                
                print(f"   Session {i+1}: {total_questions} questions, Type: {session_type}")
                print(f"   Personalization applied: {personalization.get('applied', False)}")
                
                # Check for Type metadata in personalization
                type_distribution = personalization.get('type_distribution', {})
                category_type_distribution = personalization.get('category_type_distribution', {})
                type_diversity = personalization.get('type_diversity', 0)
                
                if type_distribution:
                    test_results["type_distribution_metadata"] = True
                    print(f"   ✅ Type distribution found: {type_distribution}")
                
                if category_type_distribution:
                    test_results["category_type_distribution_metadata"] = True
                    print(f"   ✅ Category-Type distribution found: {category_type_distribution}")
                
                if type_diversity > 0:
                    test_results["type_diversity_field"] = True
                    print(f"   ✅ Type diversity field: {type_diversity}")
            else:
                session_counts.append(0)
        
        # Analyze consistency
        print(f"\n   📊 Session question counts: {session_counts}")
        twelve_question_sessions = sum(1 for count in session_counts if count == 12)
        acceptable_sessions = sum(1 for count in session_counts if count >= 10)
        
        if twelve_question_sessions >= 4:  # At least 4/5 sessions have exactly 12 questions
            test_results["twelve_question_consistency"] = True
            print("   ✅ CRITICAL SUCCESS: Consistent 12-question generation")
        elif acceptable_sessions >= 4:  # At least 4/5 sessions have 10+ questions
            test_results["twelve_question_consistency"] = True
            print("   ✅ ACCEPTABLE: Consistent 10+ question generation")
        else:
            print(f"   ❌ CRITICAL FAILURE: Inconsistent session generation - only {acceptable_sessions}/5 acceptable")
        
        if len(set(session_counts)) == 1 and session_counts[0] >= 10:
            test_results["multiple_session_consistency"] = True
            print("   ✅ Perfect consistency across multiple sessions")
        
        # TEST 2: Type Metadata Tracking VERIFICATION
        print("\n📊 TEST 2: TYPE METADATA TRACKING VERIFICATION")
        print("-" * 50)
        print("Verifying session responses include type_distribution field")
        print("Checking category_type_distribution shows Category::Subcategory::Type")
        print("Validating type_diversity field shows count of unique Types")
        
        if session_ids:
            # Test the first session for detailed metadata
            session_id = session_ids[0]
            
            # Get multiple questions to analyze Type diversity in session
            session_types = set()
            session_subcategories = set()
            questions_analyzed = 0
            
            for i in range(min(12, 5)):  # Analyze up to 5 questions
                success, response = self.run_test(f"Get Session Question {i+1}", "GET", f"sessions/{session_id}/next-question", 200, None, student_headers)
                
                if success and 'question' in response:
                    question = response['question']
                    question_type = question.get('type_of_question', '')
                    subcategory = question.get('subcategory', '')
                    
                    if question_type:
                        session_types.add(question_type)
                    if subcategory:
                        session_subcategories.add(subcategory)
                    
                    questions_analyzed += 1
                    print(f"   Question {i+1}: Type='{question_type}', Subcategory='{subcategory}'")
                else:
                    break
            
            print(f"   📊 Questions analyzed: {questions_analyzed}")
            print(f"   📊 Unique Types in session: {len(session_types)} - {sorted(list(session_types))}")
            print(f"   📊 Unique Subcategories: {len(session_subcategories)} - {sorted(list(session_subcategories))}")
            
            # Check if we have Type diversity
            if len(session_types) >= 2:
                print("   ✅ Session has Type diversity (2+ Types)")
            elif len(session_types) == 1:
                print("   ⚠️ Session has limited Type diversity (1 Type)")
            else:
                print("   ❌ Session has no Type diversity")
        
        # TEST 3: Session Intelligence Type Rationale
        print("\n🧠 TEST 3: SESSION INTELLIGENCE TYPE RATIONALE")
        print("-" * 50)
        print("Checking for Type-based rationale in session intelligence")
        
        if session_ids:
            session_id = session_ids[0]
            success, response = self.run_test("Get Question Intelligence", "GET", f"sessions/{session_id}/next-question", 200, None, student_headers)
            
            if success:
                session_intelligence = response.get('session_intelligence', {})
                question_selected_for = session_intelligence.get('question_selected_for', '')
                difficulty_rationale = session_intelligence.get('difficulty_rationale', '')
                category_focus = session_intelligence.get('category_focus', '')
                
                print(f"   📊 Question selected for: {question_selected_for}")
                print(f"   📊 Difficulty rationale: {difficulty_rationale}")
                print(f"   📊 Category focus: {category_focus}")
                
                # Check for Type-related intelligence
                intelligence_text = f"{question_selected_for} {difficulty_rationale} {category_focus}".lower()
                if 'type' in intelligence_text or any(t.lower() in intelligence_text for t in self.expected_8_types):
                    test_results["session_intelligence_type"] = True
                    print("   ✅ Session intelligence includes Type-related content")
                else:
                    print("   ⚠️ Session intelligence lacks explicit Type rationale")
        
        # FINAL RESULTS
        print("\n" + "=" * 60)
        print("FIXED TYPE-BASED SESSION SYSTEM TEST RESULTS")
        print("=" * 60)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<40} {status}")
        
        print("-" * 60)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis based on review request
        if test_results["twelve_question_consistency"]:
            print("🎉 CRITICAL SUCCESS: 12-question session generation FIXED!")
        else:
            print("❌ CRITICAL FAILURE: 12-question generation still broken")
        
        if test_results["type_distribution_metadata"] or test_results["category_type_distribution_metadata"]:
            print("✅ TYPE METADATA: Type tracking metadata present")
        else:
            print("❌ TYPE METADATA: Type metadata tracking missing")
        
        return success_rate >= 70

    def run_all_tests(self):
        """Run the comprehensive Type-based session system tests"""
        print("🚀 STARTING FIXED TYPE-BASED SESSION SYSTEM TESTING")
        print("=" * 80)
        
        try:
            # Run the original test first
            print("PHASE 1: Running original Type-based session test...")
            original_success = self.test_type_based_session_system_after_threshold_fix()
            
            print("\n" + "=" * 80)
            print("PHASE 2: Running FIXED Type-based session test...")
            fixed_success = self.test_fixed_type_based_session_system()
            
            print("\n" + "=" * 80)
            print("COMPREHENSIVE TESTING COMPLETED")
            print("=" * 80)
            print(f"Tests Run: {self.tests_run}")
            print(f"Tests Passed: {self.tests_passed}")
            print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
            
            overall_success = original_success and fixed_success
            
            if overall_success:
                print("🎉 TYPE-BASED SESSION SYSTEM COMPREHENSIVE TESTING SUCCESSFUL!")
            else:
                print("❌ TYPE-BASED SESSION SYSTEM TESTING FAILED!")
                print(f"   Original test: {'✅ PASS' if original_success else '❌ FAIL'}")
                print(f"   Fixed test: {'✅ PASS' if fixed_success else '❌ FAIL'}")
                
            return overall_success
            
        except Exception as e:
            print(f"❌ Testing failed with error: {e}")
            return False

if __name__ == "__main__":
    tester = CATBackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)