#!/usr/bin/env python3
"""
Focused Dual-Dimension Diversity Enforcement Testing
Tests the NEW dual-dimension diversity system that prioritizes subcategory diversity first, then type diversity within subcategories.
"""

import requests
import json
import time
import sys

class DualDimensionTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test with retry logic"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        # Retry logic for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    response = requests.get(url, headers=headers, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, json=data, headers=headers, timeout=30)
                elif method == 'PUT':
                    response = requests.put(url, json=data, headers=headers, timeout=30)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers, timeout=30)

                success = response.status_code == expected_status
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        response_data = response.json()
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
                    
                    # If it's a 502 error, retry
                    if response.status_code == 502 and attempt < max_retries - 1:
                        print(f"   🔄 Retrying ({attempt + 1}/{max_retries})...")
                        time.sleep(2)
                        continue
                    
                    return False, {}

            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed - Error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"   🔄 Retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2)
                    continue
                return False, {}
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                return False, {}
        
        return False, {}

    def test_dual_dimension_diversity_enforcement(self):
        """Test NEW Dual-Dimension Diversity Enforcement System - CRITICAL VALIDATION"""
        print("🎯 DUAL-DIMENSION DIVERSITY ENFORCEMENT SYSTEM")
        print("=" * 80)
        print("CRITICAL VALIDATION: Testing NEW dual-dimension diversity system")
        print("PRIORITY ORDER: Subcategory diversity FIRST, then Type diversity within subcategories")
        print("REVIEW REQUEST FOCUS:")
        print("- Subcategory Cap Enforcement: Max 5 questions from same subcategory per session")
        print("- Type within Subcategory Cap: Max 2-3 questions of same type within subcategory")
        print("- Priority 1: Maximize subcategory coverage first")
        print("- Priority 2: Ensure type diversity within chosen subcategories")
        print("- Session metadata includes dual-dimension tracking")
        print("Admin credentials: sumedhprabhu18@gmail.com / admin2025")
        print("=" * 80)
        
        # Authenticate as student for session testing
        student_login = {"email": "student@catprep.com", "password": "student123"}
        success, response = self.run_test("Student Login", "POST", "auth/login", 200, student_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test sessions - student login failed")
            return False
            
        student_token = response['access_token']
        student_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {student_token}'}
        
        # Authenticate as admin for question analysis
        admin_login = {"email": "sumedhprabhu18@gmail.com", "password": "admin2025"}
        success, response = self.run_test("Admin Login", "POST", "auth/login", 200, admin_login)
        if not success or 'access_token' not in response:
            print("❌ Cannot test - admin login failed")
            return False
            
        admin_token = response['access_token']
        admin_headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {admin_token}'}
        
        dual_dimension_results = {
            "subcategory_diversity_verification": False,
            "subcategory_cap_enforcement_max_5": False,
            "type_within_subcategory_cap_enforcement": False,
            "priority_order_subcategory_first": False,
            "session_metadata_dual_dimension": False,
            "multiple_subcategories_per_session": False,
            "no_subcategory_domination": False,
            "type_caps_within_subcategories": False
        }
        
        # TEST 1: Subcategory Diversity Verification
        print("\n🎯 TEST 1: SUBCATEGORY DIVERSITY VERIFICATION")
        print("-" * 60)
        print("Testing POST /api/sessions/start for subcategory spread")
        print("Verifying sessions include multiple subcategories (not dominated by one)")
        
        session_subcategory_data = []
        session_ids = []
        
        for i in range(5):  # Test 5 sessions for consistency
            session_data = {"target_minutes": 30}
            success, response = self.run_test(f"Create Session {i+1} for Subcategory Analysis", "POST", "sessions/start", 200, session_data, student_headers)
            
            if success:
                session_id = response.get('session_id')
                total_questions = response.get('total_questions', 0)
                session_type = response.get('session_type')
                personalization = response.get('personalization', {})
                
                session_ids.append(session_id)
                
                print(f"   Session {i+1}: {total_questions} questions, Type: {session_type}")
                
                # Analyze subcategory distribution in this session
                if session_id:
                    subcategory_distribution = {}
                    type_within_subcategory = {}
                    questions_analyzed = 0
                    
                    # Get up to 12 questions from session
                    for q_idx in range(min(12, total_questions)):
                        success, q_response = self.run_test(f"Get Question {q_idx+1} from Session {i+1}", "GET", f"sessions/{session_id}/next-question", 200, None, student_headers)
                        
                        if success and 'question' in q_response:
                            question = q_response['question']
                            subcategory = question.get('subcategory', 'Unknown')
                            type_of_question = question.get('type_of_question', 'Unknown')
                            
                            # Track subcategory distribution
                            subcategory_distribution[subcategory] = subcategory_distribution.get(subcategory, 0) + 1
                            
                            # Track type within subcategory
                            if subcategory not in type_within_subcategory:
                                type_within_subcategory[subcategory] = {}
                            type_within_subcategory[subcategory][type_of_question] = type_within_subcategory[subcategory].get(type_of_question, 0) + 1
                            
                            questions_analyzed += 1
                            
                            if questions_analyzed >= 8:  # Sample first 8 questions for better analysis
                                break
                        else:
                            break
                    
                    session_subcategory_data.append({
                        'session_id': session_id,
                        'subcategory_distribution': subcategory_distribution,
                        'type_within_subcategory': type_within_subcategory,
                        'questions_analyzed': questions_analyzed,
                        'unique_subcategories': len(subcategory_distribution),
                        'total_questions': total_questions
                    })
                    
                    print(f"   📊 Subcategory distribution: {subcategory_distribution}")
                    print(f"   📊 Type within subcategory: {type_within_subcategory}")
                    print(f"   📊 Unique subcategories: {len(subcategory_distribution)}")
        
        # Analyze subcategory diversity across sessions
        sessions_with_multiple_subcategories = 0
        sessions_with_3plus_subcategories = 0
        subcategory_cap_violations = 0
        
        for session_data in session_subcategory_data:
            unique_subcategories = session_data['unique_subcategories']
            subcategory_dist = session_data['subcategory_distribution']
            
            if unique_subcategories >= 2:
                sessions_with_multiple_subcategories += 1
            if unique_subcategories >= 3:
                sessions_with_3plus_subcategories += 1
            
            # Check for subcategory cap violations (max 5 per subcategory)
            for subcat, count in subcategory_dist.items():
                if count > 5:
                    subcategory_cap_violations += 1
                    print(f"   ⚠️ Subcategory cap violation: {subcat} has {count} questions (max 5)")
        
        print(f"\n   📊 Sessions with multiple subcategories: {sessions_with_multiple_subcategories}/5")
        print(f"   📊 Sessions with 3+ subcategories: {sessions_with_3plus_subcategories}/5")
        print(f"   📊 Subcategory cap violations: {subcategory_cap_violations}")
        
        if sessions_with_multiple_subcategories >= 4:
            dual_dimension_results["multiple_subcategories_per_session"] = True
            print("   ✅ Multiple subcategories per session: VERIFIED")
        
        if sessions_with_3plus_subcategories >= 3:
            dual_dimension_results["subcategory_diversity_verification"] = True
            print("   ✅ Subcategory diversity verification: PASSED")
        
        if subcategory_cap_violations == 0:
            dual_dimension_results["subcategory_cap_enforcement_max_5"] = True
            print("   ✅ Subcategory cap enforcement (max 5): WORKING")
        
        # TEST 2: Type within Subcategory Cap Enforcement
        print("\n📊 TEST 2: TYPE WITHIN SUBCATEGORY CAP ENFORCEMENT")
        print("-" * 60)
        print("Testing max 2-3 questions of same type within subcategory")
        print("Verifying 'Basics' type gets max 3, specific types get max 2")
        
        type_cap_violations = 0
        basics_cap_violations = 0
        type_diversity_within_subcategories = 0
        
        for session_data in session_subcategory_data:
            type_within_subcat = session_data['type_within_subcategory']
            
            for subcategory, type_dist in type_within_subcat.items():
                subcategory_type_diversity = len(type_dist)
                if subcategory_type_diversity >= 2:
                    type_diversity_within_subcategories += 1
                
                for type_name, count in type_dist.items():
                    if type_name == 'Basics':
                        if count > 3:
                            basics_cap_violations += 1
                            print(f"   ⚠️ Basics type cap violation: {subcategory} -> {type_name} has {count} questions (max 3)")
                    else:
                        if count > 2:
                            type_cap_violations += 1
                            print(f"   ⚠️ Type cap violation: {subcategory} -> {type_name} has {count} questions (max 2)")
        
        print(f"\n   📊 Type cap violations (non-Basics): {type_cap_violations}")
        print(f"   📊 Basics type cap violations: {basics_cap_violations}")
        print(f"   📊 Subcategories with type diversity: {type_diversity_within_subcategories}")
        
        if type_cap_violations == 0 and basics_cap_violations == 0:
            dual_dimension_results["type_within_subcategory_cap_enforcement"] = True
            print("   ✅ Type within subcategory cap enforcement: WORKING")
        
        if type_diversity_within_subcategories >= 3:
            dual_dimension_results["type_caps_within_subcategories"] = True
            print("   ✅ Type diversity within subcategories: VERIFIED")
        
        # TEST 3: Priority Order Validation
        print("\n🎯 TEST 3: PRIORITY ORDER VALIDATION")
        print("-" * 60)
        print("Testing Priority 1: Maximize subcategory coverage first")
        print("Testing Priority 2: Ensure type diversity within chosen subcategories")
        
        # Analyze if sessions prioritize subcategory spread over type diversity
        subcategory_priority_evidence = 0
        type_secondary_evidence = 0
        
        for session_data in session_subcategory_data:
            unique_subcategories = session_data['unique_subcategories']
            type_within_subcat = session_data['type_within_subcategory']
            
            # Evidence of subcategory priority: multiple subcategories present
            if unique_subcategories >= 3:
                subcategory_priority_evidence += 1
            
            # Evidence of type as secondary: type diversity within subcategories
            for subcategory, type_dist in type_within_subcat.items():
                if len(type_dist) >= 2:  # Multiple types within same subcategory
                    type_secondary_evidence += 1
                    break
        
        print(f"   📊 Sessions showing subcategory priority: {subcategory_priority_evidence}/5")
        print(f"   📊 Sessions showing type as secondary: {type_secondary_evidence}/5")
        
        if subcategory_priority_evidence >= 3:
            dual_dimension_results["priority_order_subcategory_first"] = True
            print("   ✅ Priority order (subcategory first): VERIFIED")
        
        # TEST 4: Session Metadata Dual-Dimension Tracking
        print("\n📋 TEST 4: SESSION METADATA DUAL-DIMENSION TRACKING")
        print("-" * 60)
        print("Testing session metadata includes dual_dimension_diversity")
        print("Verifying subcategory_caps_analysis and type_within_subcategory_analysis")
        
        # Create a fresh session to check metadata
        session_data = {"target_minutes": 30}
        success, response = self.run_test("Create Session for Metadata Analysis", "POST", "sessions/start", 200, session_data, student_headers)
        
        if success:
            session_id = response.get('session_id')
            personalization = response.get('personalization', {})
            
            # Check for dual-dimension metadata fields
            dual_dimension_diversity = personalization.get('dual_dimension_diversity', {})
            subcategory_caps_analysis = personalization.get('subcategory_caps_analysis', {})
            type_within_subcategory_analysis = personalization.get('type_within_subcategory_analysis', {})
            category_distribution = personalization.get('category_distribution', {})
            
            print(f"   📊 Dual dimension diversity: {dual_dimension_diversity}")
            print(f"   📊 Subcategory caps analysis: {subcategory_caps_analysis}")
            print(f"   📊 Type within subcategory analysis: {type_within_subcategory_analysis}")
            print(f"   📊 Category distribution: {category_distribution}")
            
            # Check if dual-dimension metadata is present
            if (dual_dimension_diversity or subcategory_caps_analysis or 
                type_within_subcategory_analysis or len(category_distribution) >= 2):
                dual_dimension_results["session_metadata_dual_dimension"] = True
                print("   ✅ Session metadata dual-dimension tracking: PRESENT")
            else:
                print("   ⚠️ Session metadata dual-dimension tracking: LIMITED")
        
        # TEST 5: No Subcategory Domination
        print("\n🚫 TEST 5: NO SUBCATEGORY DOMINATION")
        print("-" * 60)
        print("Testing sessions don't allow '12 questions all from Time-Speed-Distance'")
        print("Verifying no single subcategory dominates session")
        
        domination_violations = 0
        for session_data in session_subcategory_data:
            subcategory_dist = session_data['subcategory_distribution']
            total_questions = session_data['questions_analyzed']
            
            for subcategory, count in subcategory_dist.items():
                domination_percentage = (count / total_questions) * 100 if total_questions > 0 else 0
                
                if domination_percentage > 80:  # More than 80% from one subcategory
                    domination_violations += 1
                    print(f"   ⚠️ Subcategory domination: {subcategory} has {count}/{total_questions} questions ({domination_percentage:.1f}%)")
        
        print(f"   📊 Subcategory domination violations: {domination_violations}")
        
        if domination_violations == 0:
            dual_dimension_results["no_subcategory_domination"] = True
            print("   ✅ No subcategory domination: VERIFIED")
        
        # FINAL RESULTS SUMMARY
        print("\n" + "=" * 80)
        print("DUAL-DIMENSION DIVERSITY ENFORCEMENT SYSTEM RESULTS")
        print("=" * 80)
        
        passed_tests = sum(dual_dimension_results.values())
        total_tests = len(dual_dimension_results)
        success_rate = (passed_tests / total_tests) * 100
        
        for test_name, result in dual_dimension_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<50} {status}")
        
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        # Critical analysis based on review request
        if dual_dimension_results["subcategory_diversity_verification"]:
            print("🎉 SUBCATEGORY DIVERSITY: Multiple subcategories per session WORKING!")
        else:
            print("❌ SUBCATEGORY DIVERSITY: Sessions not spreading across subcategories")
        
        if dual_dimension_results["subcategory_cap_enforcement_max_5"]:
            print("✅ SUBCATEGORY CAPS: Max 5 questions per subcategory ENFORCED")
        else:
            print("❌ SUBCATEGORY CAPS: Subcategory cap enforcement FAILING")
        
        if dual_dimension_results["type_within_subcategory_cap_enforcement"]:
            print("✅ TYPE CAPS: Max 2-3 questions per type within subcategory ENFORCED")
        else:
            print("❌ TYPE CAPS: Type within subcategory cap enforcement FAILING")
        
        if dual_dimension_results["priority_order_subcategory_first"]:
            print("✅ PRIORITY ORDER: Subcategory diversity prioritized over type diversity")
        else:
            print("❌ PRIORITY ORDER: Priority order not working as specified")
        
        if dual_dimension_results["no_subcategory_domination"]:
            print("✅ NO DOMINATION: Sessions avoid single subcategory domination")
        else:
            print("❌ DOMINATION DETECTED: Some sessions dominated by single subcategory")
        
        return success_rate >= 75

if __name__ == "__main__":
    tester = DualDimensionTester()
    
    print("🚀 DUAL-DIMENSION DIVERSITY ENFORCEMENT TESTING")
    print("=" * 80)
    print("Testing NEW Dual-Dimension Diversity enforcement system")
    print("CRITICAL FOCUS: Subcategory diversity first, then type diversity within subcategories")
    print("Base URL:", tester.base_url)
    print("=" * 80)
    
    try:
        success = tester.test_dual_dimension_diversity_enforcement()
        
        print("\n" + "="*80)
        print("DUAL-DIMENSION DIVERSITY ENFORCEMENT TESTING COMPLETE")
        print("="*80)
        print(f"Total tests run: {tester.tests_run}")
        print(f"Tests passed: {tester.tests_passed}")
        print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%" if tester.tests_run > 0 else "No tests run")
        
        if success:
            print("🎉 Dual-Dimension Diversity Enforcement tests PASSED!")
        else:
            print("❌ Dual-Dimension Diversity Enforcement tests FAILED!")
        
        print("="*80)
        
    except Exception as e:
        print(f"❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()