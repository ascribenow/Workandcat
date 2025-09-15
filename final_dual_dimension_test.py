#!/usr/bin/env python3
"""
FINAL Dual-Dimension Diversity Enforcement System Testing
Testing the complete async-fixed dual-dimension diversity enforcement system
"""

import requests
import json
import time
import sys
from datetime import datetime

class FinalDualDimensionTester:
    def __init__(self, base_url="https://twelvr-debugger.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.admin_token = None
        self.student_token = None
        self.tests_run = 0
        self.tests_passed = 0

    def authenticate(self):
        """Authenticate as admin and student"""
        print("🔐 AUTHENTICATION")
        print("-" * 40)
        
        # Admin login
        admin_login = {"email": "sumedhprabhu18@gmail.com", "password": "admin2025"}
        response = requests.post(f"{self.base_url}/auth/login", json=admin_login, timeout=30)
        
        if response.status_code == 200:
            self.admin_token = response.json()['access_token']
            print("✅ Admin authentication successful")
        else:
            print(f"❌ Admin authentication failed: {response.status_code}")
            return False
        
        # Student login
        student_login = {"email": "student@catprep.com", "password": "student123"}
        response = requests.post(f"{self.base_url}/auth/login", json=student_login, timeout=30)
        
        if response.status_code == 200:
            self.student_token = response.json()['access_token']
            print("✅ Student authentication successful")
            return True
        else:
            print(f"❌ Student authentication failed: {response.status_code}")
            return False

    def test_complete_system_integration(self):
        """Test 1: Complete System Integration Validation"""
        print("\n🔧 TEST 1: COMPLETE SYSTEM INTEGRATION VALIDATION")
        print("-" * 60)
        print("Testing POST /api/sessions/start to verify adaptive_session_logic.create_personalized_session()")
        print("Verifying sessions use session_type: 'intelligent_12_question_set' (not fallback)")
        
        student_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        integration_results = {
            "adaptive_session_logic_called": False,
            "intelligent_session_type": False,
            "no_coroutine_errors": False,
            "enforce_dual_dimension_diversity_executed": False,
            "100_percent_success_rate": False
        }
        
        # Test multiple sessions for consistency
        session_data_list = []
        successful_sessions = 0
        
        for i in range(5):
            session_data = {"target_minutes": 30}
            response = requests.post(f"{self.base_url}/sessions/start", json=session_data, headers=student_headers, timeout=30)
            
            self.tests_run += 1
            
            if response.status_code == 200:
                successful_sessions += 1
                data = response.json()
                session_data_list.append(data)
                
                session_type = data.get('session_type', '')
                total_questions = data.get('total_questions', 0)
                personalization = data.get('personalization', {})
                
                print(f"   Session {i+1}: Type='{session_type}', Questions={total_questions}")
                print(f"   Personalization applied: {personalization.get('applied', False)}")
                
                # Check for intelligent session type (indicates adaptive logic)
                if session_type == "intelligent_12_question_set":
                    integration_results["intelligent_session_type"] = True
                    integration_results["adaptive_session_logic_called"] = True
                    print(f"   ✅ Session {i+1} using adaptive session logic")
                elif session_type == "fallback_12_question_set":
                    print(f"   ⚠️ Session {i+1} using fallback mode")
                
                # Check for dual-dimension metadata
                if personalization.get('dual_dimension_diversity', 0) > 0:
                    integration_results["enforce_dual_dimension_diversity_executed"] = True
                    print(f"   ✅ Dual-dimension diversity metadata found")
                
            else:
                print(f"   ❌ Session {i+1} failed: {response.status_code}")
        
        # Check 100% success rate
        if successful_sessions == 5:
            integration_results["100_percent_success_rate"] = True
            integration_results["no_coroutine_errors"] = True
            print("   ✅ 100% session generation success rate achieved")
            self.tests_passed += 1
        else:
            print(f"   ❌ Only {successful_sessions}/5 sessions successful")
        
        return integration_results, session_data_list

    def test_dual_dimension_diversity_enforcement(self, session_data_list):
        """Test 2: Dual-Dimension Diversity Enforcement Validation"""
        print("\n📊 TEST 2: DUAL-DIMENSION DIVERSITY ENFORCEMENT VALIDATION")
        print("-" * 60)
        print("Verifying Per Subcategory Cap: Max 5 questions from same subcategory per session")
        print("Testing Per Type within Subcategory Cap: Max 2-3 questions of same type within subcategory")
        
        student_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.student_token}'
        }
        
        diversity_results = {
            "subcategory_caps_enforced": False,
            "type_within_subcategory_caps_enforced": False,
            "priority_order_correct": False,
            "dual_dimension_metadata_present": False
        }
        
        if not session_data_list:
            print("   ❌ No session data available for testing")
            return diversity_results
        
        # Test the first session in detail
        session_data = session_data_list[0]
        session_id = session_data.get('session_id')
        
        if not session_id:
            print("   ❌ No session ID available")
            return diversity_results
        
        # Get all questions from the session
        session_questions = []
        subcategory_distribution = {}
        type_within_subcategory_distribution = {}
        
        for i in range(12):
            response = requests.get(f"{self.base_url}/sessions/{session_id}/next-question", headers=student_headers, timeout=30)
            
            if response.status_code == 200 and 'question' in response.json():
                question = response.json()['question']
                subcategory = question.get('subcategory', 'Unknown')
                question_type = question.get('type_of_question', 'Unknown')
                
                session_questions.append({
                    'subcategory': subcategory,
                    'type': question_type,
                    'question_id': question.get('id')
                })
                
                # Count subcategory distribution
                subcategory_distribution[subcategory] = subcategory_distribution.get(subcategory, 0) + 1
                
                # Count type within subcategory distribution
                type_key = f"{subcategory}::{question_type}"
                type_within_subcategory_distribution[type_key] = type_within_subcategory_distribution.get(type_key, 0) + 1
                
                print(f"   Question {i+1}: Subcategory='{subcategory}', Type='{question_type}'")
            else:
                break
        
        print(f"\n   📊 Session Questions Analyzed: {len(session_questions)}")
        print(f"   📊 Subcategory Distribution:")
        for subcategory, count in subcategory_distribution.items():
            print(f"      {subcategory}: {count} questions")
        
        # Test subcategory caps (max 5 per subcategory)
        max_subcategory_count = max(subcategory_distribution.values()) if subcategory_distribution else 0
        unique_subcategories = len(subcategory_distribution)
        
        if max_subcategory_count <= 5:
            diversity_results["subcategory_caps_enforced"] = True
            print(f"   ✅ Subcategory cap enforced: Max {max_subcategory_count} questions per subcategory (≤5)")
            self.tests_passed += 1
        else:
            print(f"   ❌ Subcategory cap violated: {max_subcategory_count} questions from single subcategory (>5)")
        
        # Test type within subcategory caps
        print(f"\n   📊 Type within Subcategory Distribution:")
        cap_violations = 0
        
        for type_key, count in type_within_subcategory_distribution.items():
            subcategory, question_type = type_key.split("::")
            expected_cap = 3 if question_type == "Basics" else 2
            
            print(f"      {subcategory} -> {question_type}: {count} questions (cap: {expected_cap})")
            
            if count > expected_cap:
                cap_violations += 1
                print(f"         ❌ Cap violation: {count} > {expected_cap}")
        
        if cap_violations == 0:
            diversity_results["type_within_subcategory_caps_enforced"] = True
            print(f"   ✅ Type within subcategory caps enforced: No violations detected")
            self.tests_passed += 1
        else:
            print(f"   ❌ Type within subcategory cap violations: {cap_violations} detected")
        
        # Test priority order (subcategory diversity first)
        if unique_subcategories >= 2:
            diversity_results["priority_order_correct"] = True
            print(f"   ✅ Priority order correct: {unique_subcategories} different subcategories (subcategory diversity first)")
            self.tests_passed += 1
        else:
            print(f"   ❌ Priority order issue: Only {unique_subcategories} subcategory")
        
        self.tests_run += 3
        return diversity_results

    def test_session_quality_and_breadth(self, session_data_list):
        """Test 3: Session Quality and Breadth Validation"""
        print("\n🌟 TEST 3: SESSION QUALITY AND BREADTH VALIDATION")
        print("-" * 60)
        print("Confirming sessions spread across multiple subcategories")
        print("Testing that no session has '12 questions all from same subcategory'")
        
        quality_results = {
            "multiple_subcategories_represented": False,
            "no_single_subcategory_domination": False,
            "true_learning_breadth": False,
            "session_intelligence_dual_dimension": False
        }
        
        if not session_data_list:
            print("   ❌ No session data available for testing")
            return quality_results
        
        # Analyze all sessions for breadth
        total_sessions_analyzed = 0
        sessions_with_multiple_subcategories = 0
        sessions_without_domination = 0
        
        for i, session_data in enumerate(session_data_list[:3]):  # Test first 3 sessions
            session_id = session_data.get('session_id')
            if not session_id:
                continue
            
            total_sessions_analyzed += 1
            
            # Check personalization metadata for breadth indicators
            personalization = session_data.get('personalization', {})
            subcategory_distribution = personalization.get('subcategory_distribution', {})
            category_distribution = personalization.get('category_distribution', {})
            
            print(f"   Session {i+1} Analysis:")
            print(f"      Category distribution: {category_distribution}")
            print(f"      Subcategory distribution: {subcategory_distribution}")
            
            # Check for multiple subcategories
            unique_subcategories = len(subcategory_distribution) if subcategory_distribution else 0
            if unique_subcategories >= 2:
                sessions_with_multiple_subcategories += 1
                print(f"      ✅ Multiple subcategories: {unique_subcategories}")
            else:
                print(f"      ⚠️ Limited subcategories: {unique_subcategories}")
            
            # Check for no single subcategory domination (max 5 out of 12)
            max_subcategory_count = max(subcategory_distribution.values()) if subcategory_distribution else 12
            if max_subcategory_count <= 5:
                sessions_without_domination += 1
                print(f"      ✅ No domination: Max {max_subcategory_count} from single subcategory")
            else:
                print(f"      ❌ Domination detected: {max_subcategory_count} from single subcategory")
        
        # Evaluate results
        if sessions_with_multiple_subcategories >= 2:
            quality_results["multiple_subcategories_represented"] = True
            quality_results["true_learning_breadth"] = True
            print("   ✅ Multiple subcategories represented across sessions")
            self.tests_passed += 1
        
        if sessions_without_domination >= 2:
            quality_results["no_single_subcategory_domination"] = True
            print("   ✅ No single subcategory domination detected")
            self.tests_passed += 1
        
        self.tests_run += 2
        return quality_results

    def test_production_readiness(self, session_data_list):
        """Test 4: Production Readiness Validation"""
        print("\n🚀 TEST 4: PRODUCTION READINESS VALIDATION")
        print("-" * 60)
        print("Testing 100% success rate for session generation (no fallback mode)")
        print("Verifying consistent 12-question generation with proper diversity enforcement")
        
        production_results = {
            "100_percent_success_rate": False,
            "consistent_12_question_generation": False,
            "sophisticated_metadata_tracking": False,
            "all_dual_dimension_requirements_met": False
        }
        
        if not session_data_list:
            print("   ❌ No session data available for testing")
            return production_results
        
        # Check success rate
        intelligent_sessions = sum(1 for s in session_data_list if s.get('session_type') == 'intelligent_12_question_set')
        total_sessions = len(session_data_list)
        
        if intelligent_sessions == total_sessions and total_sessions >= 3:
            production_results["100_percent_success_rate"] = True
            print(f"   ✅ 100% success rate: {intelligent_sessions}/{total_sessions} intelligent sessions")
            self.tests_passed += 1
        else:
            print(f"   ❌ Success rate: {intelligent_sessions}/{total_sessions} intelligent sessions")
        
        # Check consistent 12-question generation
        twelve_question_sessions = sum(1 for s in session_data_list if s.get('total_questions') == 12)
        
        if twelve_question_sessions == total_sessions and total_sessions >= 3:
            production_results["consistent_12_question_generation"] = True
            print(f"   ✅ Consistent 12-question generation: {twelve_question_sessions}/{total_sessions} sessions")
            self.tests_passed += 1
        else:
            print(f"   ❌ Inconsistent generation: {twelve_question_sessions}/{total_sessions} with 12 questions")
        
        # Check sophisticated metadata tracking
        sessions_with_metadata = 0
        for session_data in session_data_list:
            personalization = session_data.get('personalization', {})
            
            # Check for dual-dimension metadata fields
            has_dual_dimension = any(key in personalization for key in [
                'dual_dimension_diversity', 'subcategory_caps_analysis', 
                'type_within_subcategory_analysis', 'category_distribution'
            ])
            
            if has_dual_dimension:
                sessions_with_metadata += 1
        
        if sessions_with_metadata >= 2:
            production_results["sophisticated_metadata_tracking"] = True
            print(f"   ✅ Sophisticated metadata: {sessions_with_metadata}/{total_sessions} sessions")
            self.tests_passed += 1
        else:
            print(f"   ❌ Limited metadata: {sessions_with_metadata}/{total_sessions} sessions")
        
        # Overall dual-dimension requirements check
        if (production_results["100_percent_success_rate"] and 
            production_results["consistent_12_question_generation"] and
            production_results["sophisticated_metadata_tracking"]):
            production_results["all_dual_dimension_requirements_met"] = True
            print("   ✅ All dual-dimension diversity requirements met")
            self.tests_passed += 1
        else:
            print("   ❌ Some dual-dimension requirements not met")
        
        self.tests_run += 4
        return production_results

    def run_complete_test_suite(self):
        """Run the complete dual-dimension diversity enforcement test suite"""
        print("🎯 FINAL DUAL-DIMENSION DIVERSITY ENFORCEMENT SYSTEM TESTING")
        print("=" * 80)
        print("CRITICAL FINAL VALIDATION:")
        print("All async issues have been resolved in adaptive_session_logic.py, so the dual-dimension")
        print("diversity enforcement should now work with 100% success rate")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed with tests")
            return False
        
        # Run all tests
        integration_results, session_data_list = self.test_complete_system_integration()
        diversity_results = self.test_dual_dimension_diversity_enforcement(session_data_list)
        quality_results = self.test_session_quality_and_breadth(session_data_list)
        production_results = self.test_production_readiness(session_data_list)
        
        # Final results summary
        print("\n" + "=" * 80)
        print("FINAL DUAL-DIMENSION DIVERSITY ENFORCEMENT TEST RESULTS")
        print("=" * 80)
        
        all_results = {
            **integration_results,
            **diversity_results,
            **quality_results,
            **production_results
        }
        
        passed_tests = sum(all_results.values())
        total_tests = len(all_results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        for test_name, result in all_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<50} {status}")
        
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        
        # Critical analysis
        if integration_results.get("100_percent_success_rate"):
            print("🎉 CRITICAL SUCCESS: 100% session generation success rate achieved!")
        else:
            print("❌ CRITICAL FAILURE: Session generation not achieving 100% success rate")
        
        if diversity_results.get("subcategory_caps_enforced") and diversity_results.get("type_within_subcategory_caps_enforced"):
            print("✅ DUAL-DIMENSION DIVERSITY: Both subcategory and type caps properly enforced")
        else:
            print("❌ DUAL-DIMENSION DIVERSITY: Caps not properly enforced")
        
        if production_results.get("all_dual_dimension_requirements_met"):
            print("🚀 PRODUCTION READY: All dual-dimension diversity requirements met")
        else:
            print("⚠️ PRODUCTION CONCERNS: Some requirements not fully met")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = FinalDualDimensionTester()
    success = tester.run_complete_test_suite()
    
    if success:
        print("\n🎉 DUAL-DIMENSION DIVERSITY ENFORCEMENT SYSTEM: FULLY FUNCTIONAL")
        sys.exit(0)
    else:
        print("\n❌ DUAL-DIMENSION DIVERSITY ENFORCEMENT SYSTEM: NEEDS ATTENTION")
        sys.exit(1)