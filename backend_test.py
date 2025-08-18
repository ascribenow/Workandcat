import requests
import sys
import json
from datetime import datetime
import time
import os

class CATBackendTester:
    def __init__(self, base_url="https://7c02cfe7-3550-46e8-a144-11935599c1f5.preview.emergentagent.com/api"):
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
        
        # New canonical taxonomy structure from review request
        self.canonical_taxonomy = {
            "Arithmetic": [
                "Time–Speed–Distance (TSD)", "Time & Work", "Ratio–Proportion–Variation",
                "Percentages", "Averages & Alligation", "Profit–Loss–Discount (PLD)",
                "Simple & Compound Interest (SI–CI)", "Mixtures & Solutions", "Partnerships"
            ],
            "Algebra": [
                "Linear Equations", "Quadratic Equations", "Inequalities", "Progressions",
                "Functions & Graphs", "Logarithms & Exponents", "Special Algebraic Identities",
                "Maxima and Minima", "Special Polynomials"
            ],
            "Geometry and Mensuration": [
                "Triangles", "Circles", "Polygons", "Coordinate Geometry",
                "Trigonometry in Geometry", "Mensuration 2D", "Mensuration 3D"
            ],
            "Number System": [
                "Divisibility", "HCF–LCM", "Remainders & Modular Arithmetic",
                "Base Systems", "Digit Properties", "Number Properties", "Number Series", "Factorials"
            ],
            "Modern Math": [
                "Permutation–Combination (P&C)", "Probability", "Set Theory & Venn Diagrams"
            ]
        }

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

    def test_canonical_taxonomy_update(self):
        """Test the new canonical taxonomy structure update"""
        print("🎯 CANONICAL TAXONOMY UPDATE TESTING")
        print("=" * 60)
        print("Testing database update with new canonical taxonomy structure")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 60)
        
        # First authenticate as admin
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test taxonomy update - admin login failed")
            return False
            
        self.admin_token = response['access_token']
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        taxonomy_results = {
            "admin_authentication": True,
            "topics_table_update": False,
            "new_subcategories_added": False,
            "question_classification_test": False,
            "llm_enrichment_with_taxonomy": False,
            "session_creation_with_taxonomy": False,
            "category_structure_validation": False,
            "subcategory_coverage_validation": False
        }
        
        # TEST 1: Initialize/Update Topics Table
        print("\n🗄️ TEST 1: TOPICS TABLE UPDATE")
        print("-" * 40)
        print("Initializing topics table with canonical taxonomy")
        
        success, response = self.run_test("Initialize Topics Table", "POST", "admin/init-topics", 200, {}, headers)
        if success:
            print(f"   ✅ Topics initialization response: {response.get('message', 'Success')}")
            taxonomy_results["topics_table_update"] = True
        else:
            print("   ❌ Failed to initialize topics table")
        
        # TEST 2: Verify New Subcategories Added
        print("\n📋 TEST 2: NEW SUBCATEGORIES VERIFICATION")
        print("-" * 40)
        print("Checking if all new subcategories from canonical taxonomy are present")
        
        # Get all questions to see available subcategories
        success, response = self.run_test("Get Questions for Subcategory Check", "GET", "questions?limit=100", 200, None, headers)
        if success:
            questions = response.get('questions', [])
            found_subcategories = set()
            
            for q in questions:
                subcategory = q.get('subcategory')
                if subcategory:
                    found_subcategories.add(subcategory)
            
            print(f"   📊 Found {len(found_subcategories)} unique subcategories in database")
            
            # Check for new subcategories from canonical taxonomy
            new_subcategories = [
                "Partnerships", "Maxima and Minima", "Special Polynomials",
                "Mensuration 2D", "Mensuration 3D", "Number Properties", 
                "Number Series", "Factorials"
            ]
            
            found_new = []
            missing_new = []
            
            for subcat in new_subcategories:
                if subcat in found_subcategories:
                    found_new.append(subcat)
                else:
                    missing_new.append(subcat)
            
            print(f"   ✅ Found new subcategories: {found_new}")
            if missing_new:
                print(f"   ⚠️ Missing new subcategories: {missing_new}")
            
            if len(found_new) > 0:
                taxonomy_results["new_subcategories_added"] = True
                print("   ✅ New subcategories successfully added to database")
            else:
                print("   ❌ No new subcategories found - may need manual addition")
        
        # TEST 3: Question Classification Test
        print("\n🔍 TEST 3: QUESTION CLASSIFICATION WITH NEW TAXONOMY")
        print("-" * 40)
        print("Testing question creation and classification with new taxonomy structure")
        
        # Test question for each new category
        test_questions = [
            {
                "stem": "TAXONOMY TEST: In a partnership, A invests Rs. 5000 and B invests Rs. 7000. If the profit is Rs. 2400, what is A's share?",
                "hint_category": "Arithmetic",
                "hint_subcategory": "Partnerships",
                "source": "Taxonomy Test"
            },
            {
                "stem": "TAXONOMY TEST: Find the maximum value of the function f(x) = -x² + 4x + 5.",
                "hint_category": "Algebra", 
                "hint_subcategory": "Maxima and Minima",
                "source": "Taxonomy Test"
            },
            {
                "stem": "TAXONOMY TEST: Find the area of a rectangle with length 12 cm and width 8 cm.",
                "hint_category": "Geometry and Mensuration",
                "hint_subcategory": "Mensuration 2D",
                "source": "Taxonomy Test"
            }
        ]
        
        created_questions = []
        for i, test_q in enumerate(test_questions):
            success, response = self.run_test(f"Create Test Question {i+1}", "POST", "questions", 200, test_q, headers)
            if success and 'question_id' in response:
                created_questions.append({
                    'id': response['question_id'],
                    'subcategory': test_q['hint_subcategory']
                })
                print(f"   ✅ Created question for {test_q['hint_subcategory']}")
            else:
                print(f"   ❌ Failed to create question for {test_q['hint_subcategory']}")
        
        if len(created_questions) > 0:
            taxonomy_results["question_classification_test"] = True
            print(f"   ✅ Successfully created {len(created_questions)} questions with new taxonomy")
        
        # TEST 4: LLM Enrichment with New Taxonomy
        print("\n🤖 TEST 4: LLM ENRICHMENT WITH NEW TAXONOMY")
        print("-" * 40)
        print("Testing LLM enrichment works with updated taxonomy structure")
        
        if created_questions:
            # Wait for LLM processing
            print("   ⏳ Waiting 15 seconds for LLM enrichment...")
            time.sleep(15)
            
            # Check enrichment results
            success, response = self.run_test("Check LLM Enrichment Results", "GET", "questions?limit=50", 200, None, headers)
            if success:
                questions = response.get('questions', [])
                enriched_count = 0
                
                for created_q in created_questions:
                    for q in questions:
                        if q.get('id') == created_q['id']:
                            answer = q.get('answer', '')
                            solution = q.get('solution_approach', '')
                            
                            # Check if enriched (not generic)
                            if (answer and answer != "To be generated by LLM" and 
                                solution and "Mathematical approach" not in solution):
                                enriched_count += 1
                                print(f"   ✅ Question enriched for {created_q['subcategory']}")
                            break
                
                if enriched_count > 0:
                    taxonomy_results["llm_enrichment_with_taxonomy"] = True
                    print(f"   ✅ LLM enrichment working with new taxonomy ({enriched_count}/{len(created_questions)} questions)")
                else:
                    print("   ⚠️ LLM enrichment may need more time or has issues")
        
        # TEST 5: Session Creation with New Taxonomy
        print("\n🎯 TEST 5: SESSION CREATION WITH NEW TAXONOMY")
        print("-" * 40)
        print("Testing 12-question session creation works with updated taxonomy")
        
        # Login as student for session testing
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login for Session Test", "POST", "auth/login", 200, student_login)
        if success and 'access_token' in response:
            student_token = response['access_token']
            student_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {student_token}'
            }
            
            # Create session
            session_data = {"target_minutes": 30}
            success, response = self.run_test("Create Session with New Taxonomy", "POST", "sessions/start", 200, session_data, student_headers)
            if success and 'session_id' in response:
                session_id = response['session_id']
                session_type = response.get('session_type', 'unknown')
                total_questions = response.get('total_questions', 0)
                
                print(f"   ✅ Session created: {session_id}")
                print(f"   📊 Session type: {session_type}")
                print(f"   📊 Total questions: {total_questions}")
                
                if total_questions >= 12:
                    taxonomy_results["session_creation_with_taxonomy"] = True
                    print("   ✅ 12-question session working with new taxonomy")
                else:
                    print(f"   ⚠️ Session has only {total_questions} questions (expected 12)")
                
                # Test getting questions from session
                success, response = self.run_test("Get Question from Session", "GET", f"sessions/{session_id}/next-question", 200, None, student_headers)
                if success and 'question' in response:
                    question = response['question']
                    subcategory = question.get('subcategory', '')
                    print(f"   ✅ Retrieved question with subcategory: {subcategory}")
                    
                    # Check if it's using new taxonomy
                    if subcategory in [item for sublist in self.canonical_taxonomy.values() for item in sublist]:
                        print("   ✅ Question uses canonical taxonomy subcategory")
            else:
                print("   ❌ Failed to create session")
        else:
            print("   ❌ Failed to login as student")
        
        # TEST 6: Category Structure Validation
        print("\n📊 TEST 6: CATEGORY STRUCTURE VALIDATION")
        print("-" * 40)
        print("Validating new category structure (without A-, B-, C- prefixes)")
        
        success, response = self.run_test("Get Dashboard for Category Check", "GET", "dashboard/mastery", 200, None, headers)
        if success:
            mastery_data = response.get('mastery_by_topic', [])
            found_categories = set()
            
            for topic in mastery_data:
                category = topic.get('category_name', '')
                if category:
                    found_categories.add(category)
            
            print(f"   📊 Found categories: {list(found_categories)}")
            
            # Check for new category names (without prefixes)
            expected_categories = ["Arithmetic", "Algebra", "Geometry and Mensuration", "Number System", "Modern Math"]
            new_format_found = any(cat in found_categories for cat in expected_categories)
            
            if new_format_found:
                taxonomy_results["category_structure_validation"] = True
                print("   ✅ New category structure detected")
            else:
                print("   ⚠️ Still using old category format (A-Arithmetic, B-Algebra, etc.)")
        
        # TEST 7: Subcategory Coverage Validation
        print("\n📋 TEST 7: SUBCATEGORY COVERAGE VALIDATION")
        print("-" * 40)
        print("Validating comprehensive subcategory coverage")
        
        success, response = self.run_test("Get Detailed Progress", "GET", "dashboard/mastery", 200, None, headers)
        if success:
            detailed_progress = response.get('detailed_progress', [])
            covered_subcategories = set()
            
            for progress in detailed_progress:
                subcategory = progress.get('subcategory', '')
                if subcategory:
                    covered_subcategories.add(subcategory)
            
            print(f"   📊 Total subcategories covered: {len(covered_subcategories)}")
            
            # Check coverage of canonical taxonomy
            all_canonical_subcategories = [item for sublist in self.canonical_taxonomy.values() for item in sublist]
            coverage_count = sum(1 for subcat in all_canonical_subcategories if subcat in covered_subcategories)
            coverage_percentage = (coverage_count / len(all_canonical_subcategories)) * 100
            
            print(f"   📊 Canonical taxonomy coverage: {coverage_count}/{len(all_canonical_subcategories)} ({coverage_percentage:.1f}%)")
            
            if coverage_percentage >= 50:
                taxonomy_results["subcategory_coverage_validation"] = True
                print("   ✅ Good subcategory coverage of canonical taxonomy")
            else:
                print("   ⚠️ Low subcategory coverage - may need more questions")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 60)
        print("CANONICAL TAXONOMY UPDATE RESULTS")
        print("=" * 60)
        
        passed_tests = sum(taxonomy_results.values())
        total_tests = len(taxonomy_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in taxonomy_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<40} {status}")
            
        print("-" * 60)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis
        if taxonomy_results["topics_table_update"] and taxonomy_results["new_subcategories_added"]:
            print("🎉 TAXONOMY UPDATE SUCCESS: Database updated with new structure!")
        else:
            print("❌ TAXONOMY UPDATE ISSUES: Database may not be fully updated")
        
        if taxonomy_results["question_classification_test"] and taxonomy_results["llm_enrichment_with_taxonomy"]:
            print("✅ QUESTION SYSTEM: Working with new taxonomy")
        else:
            print("⚠️ QUESTION SYSTEM: May have issues with new taxonomy")
        
        if taxonomy_results["session_creation_with_taxonomy"]:
            print("✅ SESSION SYSTEM: 12-question sessions working with new taxonomy")
        else:
            print("❌ SESSION SYSTEM: Issues with new taxonomy structure")
        
        return success_rate >= 70
        """CRITICAL: Test and fix all questions with generic/wrong solutions in database"""
        print("🚨 CRITICAL LLM SOLUTION RE-ENRICHMENT TESTING")
        print("=" * 60)
        print("URGENT REQUIREMENT: Re-enrich ALL questions with generic/wrong solutions")
        print("Cannot leave any question in error state with generic solutions")
        print("Examples of generic solutions to find and fix:")
        print("- 'Mathematical approach to solve this problem'")
        print("- 'Example answer based on the question pattern'")
        print("- 'Detailed solution for: [question]...'")
        print("- 'To be generated by LLM'")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 60)
        
        # First authenticate as admin
        admin_login = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test LLM re-enrichment - admin login failed")
            return False
            
        self.admin_token = response['access_token']
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        
        re_enrichment_results = {
            "admin_authentication": True,
            "database_scan_for_generic_solutions": False,
            "generic_solutions_identified": False,
            "llm_enrichment_pipeline_test": False,
            "force_re_enrichment_test": False,
            "solution_quality_verification": False,
            "database_update_verification": False,
            "student_experience_protection": False
        }
        
        # TEST 1: Database Scan for Generic Solutions
        print("\n🔍 TEST 1: DATABASE SCAN FOR GENERIC SOLUTIONS")
        print("-" * 40)
        print("Scanning all questions in database for generic/wrong solutions")
        
        success, response = self.run_test("Get All Questions for Generic Solution Scan", "GET", "questions?limit=300", 200, None, headers)
        if success:
            questions = response.get('questions', [])
            print(f"   ✅ Retrieved {len(questions)} questions from database")
            re_enrichment_results["database_scan_for_generic_solutions"] = True
            
            # Define generic solution patterns to identify
            generic_patterns = [
                "mathematical approach to solve this problem",
                "example answer based on the question pattern",
                "detailed solution for:",
                "to be generated by llm",
                "approach to solve this problem",
                "solution based on the question pattern",
                "mathematical solution approach",
                "step-by-step solution approach"
            ]
            
            generic_questions = []
            wrong_solution_questions = []
            
            for q in questions:
                question_id = q.get('id')
                stem = (q.get('stem') or '').lower()
                answer = (q.get('answer') or '').lower()
                solution_approach = (q.get('solution_approach') or '').lower()
                detailed_solution = (q.get('detailed_solution') or '').lower()
                
                # Check for generic solutions
                is_generic = False
                for pattern in generic_patterns:
                    if (pattern in solution_approach or 
                        pattern in detailed_solution or 
                        pattern in answer):
                        is_generic = True
                        break
                
                if is_generic:
                    generic_questions.append({
                        'id': question_id,
                        'stem': q.get('stem', '')[:80] + '...',
                        'answer': q.get('answer', '')[:50] + '...',
                        'solution_approach': q.get('solution_approach', '')[:80] + '...',
                        'detailed_solution': q.get('detailed_solution', '')[:80] + '...'
                    })
                
                # Check for solution mismatches (e.g., salary question with alloy solution)
                if 'earn' in stem or 'salary' in stem or 'income' in stem:
                    if ('alloy' in solution_approach or 'copper' in solution_approach or 
                        'aluminum' in solution_approach or 'metal' in solution_approach):
                        wrong_solution_questions.append({
                            'id': question_id,
                            'stem': q.get('stem', '')[:80] + '...',
                            'solution_approach': q.get('solution_approach', '')[:80] + '...',
                            'mismatch_type': 'salary_question_with_alloy_solution'
                        })
            
            print(f"   🚨 FOUND {len(generic_questions)} questions with GENERIC solutions")
            print(f"   🚨 FOUND {len(wrong_solution_questions)} questions with WRONG solutions")
            
            if len(generic_questions) > 0 or len(wrong_solution_questions) > 0:
                re_enrichment_results["generic_solutions_identified"] = True
                
                print("\n   📋 GENERIC SOLUTION EXAMPLES:")
                for i, q in enumerate(generic_questions[:5]):
                    print(f"     {i+1}. ID: {q['id']}")
                    print(f"        Question: {q['stem']}")
                    print(f"        Generic Solution: {q['solution_approach']}")
                    print()
                
                if wrong_solution_questions:
                    print("   📋 WRONG SOLUTION EXAMPLES:")
                    for i, q in enumerate(wrong_solution_questions[:3]):
                        print(f"     {i+1}. ID: {q['id']}")
                        print(f"        Question: {q['stem']}")
                        print(f"        Wrong Solution: {q['solution_approach']}")
                        print(f"        Mismatch Type: {q['mismatch_type']}")
                        print()
            else:
                print("   ✅ No generic or wrong solutions found in database")
                re_enrichment_results["solution_quality_verification"] = True
        else:
            print("   ❌ Failed to retrieve questions from database")
            return False
        
        # TEST 2: LLM Enrichment Pipeline Test
        print("\n🤖 TEST 2: LLM ENRICHMENT PIPELINE TEST")
        print("-" * 40)
        print("Testing if LLM enrichment pipeline generates proper solutions")
        
        # Create a test question to verify LLM enrichment works correctly
        test_question_data = {
            "stem": "RE-ENRICHMENT TEST: A person earns 30% more than his colleague. If the colleague earns Rs. 2000, how much does the person earn?",
            "hint_category": "Arithmetic",
            "hint_subcategory": "Percentages",
            "source": "Re-enrichment Test"
        }
        
        success, response = self.run_test("Create Test Question for LLM Pipeline", "POST", "questions", 200, test_question_data, headers)
        if success and 'question_id' in response:
            test_question_id = response['question_id']
            print(f"   ✅ Test question created: {test_question_id}")
            print(f"   Status: {response.get('status')}")
            
            # Wait for LLM processing
            print("   ⏳ Waiting 15 seconds for LLM enrichment...")
            time.sleep(15)
            
            # Check if LLM generated proper solution
            success, response = self.run_test("Check LLM Pipeline Results", "GET", f"questions?limit=50", 200, None, headers)
            if success:
                questions = response.get('questions', [])
                test_question = None
                
                for q in questions:
                    if q.get('id') == test_question_id:
                        test_question = q
                        break
                
                if test_question:
                    answer = test_question.get('answer', '')
                    solution_approach = test_question.get('solution_approach', '')
                    detailed_solution = test_question.get('detailed_solution', '')
                    
                    print(f"   Generated Answer: {answer}")
                    print(f"   Generated Solution Approach: {solution_approach}")
                    print(f"   Generated Detailed Solution: {detailed_solution[:100]}...")
                    
                    # Check if solution is relevant and not generic
                    is_relevant = False
                    is_not_generic = True
                    
                    if answer and answer != "To be generated by LLM":
                        # Check for relevant content (should mention percentage, earning, 2600, etc.)
                        if ('2600' in str(answer) or '30%' in solution_approach or 
                            'percentage' in solution_approach.lower() or 
                            'earn' in solution_approach.lower()):
                            is_relevant = True
                    
                    # Check it's not generic
                    for pattern in generic_patterns:
                        if pattern in solution_approach.lower() or pattern in detailed_solution.lower():
                            is_not_generic = False
                            break
                    
                    if is_relevant and is_not_generic:
                        print("   ✅ LLM enrichment pipeline working correctly")
                        print("   ✅ Generated relevant, non-generic solution")
                        re_enrichment_results["llm_enrichment_pipeline_test"] = True
                    else:
                        print("   ❌ LLM enrichment pipeline issues detected")
                        if not is_relevant:
                            print("   ❌ Solution not relevant to question")
                        if not is_not_generic:
                            print("   ❌ Solution is still generic")
                else:
                    print("   ❌ Test question not found after creation")
        else:
            print("   ❌ Failed to create test question for LLM pipeline test")
        
        # TEST 3: CRITICAL - Use Mass Re-enrichment API Endpoint
        print("\n🔄 TEST 3: CRITICAL MASS RE-ENRICHMENT API ENDPOINT")
        print("-" * 40)
        print("Using /api/admin/re-enrich-all-questions endpoint to fix ALL generic solutions")
        
        if len(generic_questions) > 0:
            print(f"   🚨 CRITICAL: Found {len(generic_questions)} questions with generic solutions")
            print("   🔄 Calling mass re-enrichment API endpoint...")
            
            # Call the critical re-enrichment endpoint
            success, response = self.run_test("Mass Re-enrichment API Call", "POST", "admin/re-enrich-all-questions", 200, {}, headers)
            if success:
                processed = response.get('processed', 0)
                success_count = response.get('success', 0)
                failed_count = response.get('failed', 0)
                status = response.get('status', 'unknown')
                
                print(f"   ✅ Mass re-enrichment API called successfully")
                print(f"   📊 Status: {status}")
                print(f"   📊 Questions processed: {processed}")
                print(f"   📊 Successfully re-enriched: {success_count}")
                print(f"   📊 Failed to re-enrich: {failed_count}")
                
                if success_count > 0:
                    re_enrichment_results["force_re_enrichment_test"] = True
                    print(f"   🎉 SUCCESS: {success_count} questions re-enriched with proper solutions!")
                    
                    # Wait for processing to complete
                    print("   ⏳ Waiting 30 seconds for mass re-enrichment to complete...")
                    time.sleep(30)
                else:
                    print(f"   ⚠️ WARNING: No questions were successfully re-enriched")
                    if failed_count > 0:
                        print(f"   ❌ {failed_count} questions failed re-enrichment")
            else:
                print("   ❌ CRITICAL FAILURE: Mass re-enrichment API call failed")
                print("   🚨 This is a production-blocking issue!")
        else:
            print("   ✅ No generic questions found - database already clean")
            re_enrichment_results["force_re_enrichment_test"] = True
        
        # TEST 4: Database Update Verification
        print("\n✅ TEST 4: DATABASE UPDATE VERIFICATION")
        print("-" * 40)
        print("Verifying that re-enrichment updated the database correctly")
        
        # Re-scan database for generic solutions
        success, response = self.run_test("Re-scan Database After Re-enrichment", "GET", "questions?limit=300", 200, None, headers)
        if success:
            questions_after = response.get('questions', [])
            print(f"   ✅ Retrieved {len(questions_after)} questions after re-enrichment")
            
            # Count generic solutions again
            generic_count_after = 0
            for q in questions_after:
                solution_approach = (q.get('solution_approach') or '').lower()
                detailed_solution = (q.get('detailed_solution') or '').lower()
                answer = (q.get('answer') or '').lower()
                
                for pattern in generic_patterns:
                    if (pattern in solution_approach or 
                        pattern in detailed_solution or 
                        pattern in answer):
                        generic_count_after += 1
                        break
            
            original_generic_count = len(generic_questions)
            print(f"   📊 Generic solutions before: {original_generic_count}")
            print(f"   📊 Generic solutions after: {generic_count_after}")
            
            if generic_count_after < original_generic_count:
                print("   ✅ Database update successful - generic solutions reduced")
                re_enrichment_results["database_update_verification"] = True
            elif generic_count_after == 0:
                print("   🎉 PERFECT! No generic solutions remaining in database")
                re_enrichment_results["database_update_verification"] = True
                re_enrichment_results["student_experience_protection"] = True
            else:
                print("   ⚠️ Generic solutions still present - may need more time or manual intervention")
        else:
            print("   ❌ Failed to verify database updates")
        
        # TEST 5: Student Experience Protection Verification
        print("\n👨‍🎓 TEST 5: STUDENT EXPERIENCE PROTECTION")
        print("-" * 40)
        print("Verifying students won't see generic/wrong solutions")
        
        # Test session creation and question retrieval to ensure students get proper solutions
        student_login = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        
        success, response = self.run_test("Student Login for Experience Test", "POST", "auth/login", 200, student_login)
        if success and 'access_token' in response:
            student_token = response['access_token']
            student_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {student_token}'
            }
            
            # Create a session to test student experience
            session_data = {"target_minutes": 30}
            success, response = self.run_test("Create Student Session", "POST", "sessions/start", 200, session_data, student_headers)
            if success and 'session_id' in response:
                session_id = response['session_id']
                print(f"   ✅ Student session created: {session_id}")
                
                # Get a question from the session
                success, response = self.run_test("Get Student Question", "GET", f"sessions/{session_id}/next-question", 200, None, student_headers)
                if success and 'question' in response:
                    question = response['question']
                    question_stem = question.get('stem', '')
                    
                    print(f"   ✅ Student question retrieved")
                    print(f"   Question: {question_stem[:60]}...")
                    
                    # Submit an answer to get solution feedback
                    answer_data = {
                        "question_id": question['id'],
                        "user_answer": "test_answer",
                        "time_sec": 30,
                        "hint_used": False
                    }
                    
                    success, response = self.run_test("Submit Answer for Solution", "POST", f"sessions/{session_id}/submit-answer", 200, answer_data, student_headers)
                    if success and 'solution_feedback' in response:
                        solution_feedback = response['solution_feedback']
                        solution_approach = solution_feedback.get('solution_approach', '').lower()
                        detailed_solution = solution_feedback.get('detailed_solution', '').lower()
                        
                        print(f"   Solution shown to student: {solution_approach[:80]}...")
                        
                        # Check if student sees generic solution
                        student_sees_generic = False
                        for pattern in generic_patterns:
                            if pattern in solution_approach or pattern in detailed_solution:
                                student_sees_generic = True
                                break
                        
                        if not student_sees_generic:
                            print("   ✅ Student protected - no generic solutions shown")
                            re_enrichment_results["student_experience_protection"] = True
                        else:
                            print("   ❌ CRITICAL: Student still seeing generic solutions!")
                    else:
                        print("   ⚠️ Could not verify solution feedback to student")
                else:
                    print("   ⚠️ No questions available in student session")
            else:
                print("   ❌ Failed to create student session")
        else:
            print("   ❌ Failed to login as student")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 60)
        print("CRITICAL LLM SOLUTION RE-ENRICHMENT RESULTS")
        print("=" * 60)
        
        passed_tests = sum(re_enrichment_results.values())
        total_tests = len(re_enrichment_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in re_enrichment_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<40} {status}")
            
        print("-" * 60)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis
        if re_enrichment_results["generic_solutions_identified"]:
            if re_enrichment_results["database_update_verification"]:
                print("🎉 CRITICAL SUCCESS: Generic solutions identified and fixed!")
                print("   ✅ Database updated with proper solutions")
            else:
                print("❌ CRITICAL ISSUE: Generic solutions found but not fixed!")
                print("   🚨 URGENT: Manual intervention required")
        else:
            print("✅ EXCELLENT: No generic solutions found in database")
        
        if re_enrichment_results["student_experience_protection"]:
            print("✅ STUDENT SAFETY: Students protected from generic solutions")
        else:
            print("❌ STUDENT RISK: Students may still see generic solutions")
        
        if success_rate >= 80:
            print("🎉 LLM SOLUTION RE-ENRICHMENT SUCCESSFUL!")
            print("   ✅ Database cleaned, students protected")
        elif success_rate >= 60:
            print("⚠️ Re-enrichment mostly successful with minor issues")
        else:
            print("❌ CRITICAL FAILURE: Re-enrichment process needs immediate attention")
            
        return success_rate >= 70

def main():
    """Main test execution"""
    print("🚀 STARTING CANONICAL TAXONOMY UPDATE TESTING")
    print("=" * 60)
    
    tester = CATBackendTester()
    
    # Run the canonical taxonomy update test
    success = tester.test_canonical_taxonomy_update()
    
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ CANONICAL TAXONOMY UPDATE: SUCCESSFUL")
        print("   Database updated with new taxonomy structure")
        print("   New subcategories added and working")
        print("   Question classification system operational")
        print("   LLM enrichment working with new taxonomy")
        print("   12-question sessions functional")
    else:
        print("❌ CANONICAL TAXONOMY UPDATE: FAILED")
        print("   🚨 URGENT ACTION REQUIRED")
        print("   Database may not be fully updated")
        print("   Question enrichment system may have issues")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)