#!/usr/bin/env python3

import requests
import json
import time

def test_stratified_difficulty_distribution():
    """Simple test for stratified difficulty distribution"""
    base_url = "http://localhost:8001/api"
    
    print("🎯 STRATIFIED DIFFICULTY DISTRIBUTION TEST")
    print("=" * 60)
    
    # Test 1: Basic API connectivity
    print("\n🔍 TEST 1: API Connectivity")
    try:
        response = requests.get(f"{base_url}/", timeout=30)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API is accessible: {data.get('message', 'Unknown')}")
        else:
            print(f"   ❌ API not accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ API connection failed: {e}")
        return False
    
    # Test 2: Student Login
    print("\n🔍 TEST 2: Student Authentication")
    try:
        login_data = {
            "email": "student@catprep.com",
            "password": "student123"
        }
        response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            auth_data = response.json()
            token = auth_data.get('access_token')
            print(f"   ✅ Student login successful")
            
            # Test 3: Session Creation with Difficulty Analysis
            print("\n🔍 TEST 3: Phase A Session Creation and Difficulty Analysis")
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            session_results = []
            
            # Create 3 sessions to test difficulty distribution
            for i in range(3):
                try:
                    session_data = {"target_minutes": 30}
                    response = requests.post(f"{base_url}/sessions/start", json=session_data, headers=headers, timeout=60)
                    print(f"   Session {i+1} Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        session_response = response.json()
                        questions = session_response.get('questions', [])
                        phase_info = session_response.get('phase_info', {})
                        session_type = session_response.get('session_type', 'unknown')
                        
                        print(f"   Session {i+1}: {len(questions)} questions, Type: {session_type}")
                        print(f"   Phase Info: {phase_info}")
                        
                        # Analyze difficulty distribution
                        if questions:
                            difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0}
                            for q in questions:
                                difficulty = q.get('difficulty_band', 'Medium')
                                if difficulty in difficulty_counts:
                                    difficulty_counts[difficulty] += 1
                            
                            total = len(questions)
                            difficulty_percentages = {}
                            for diff, count in difficulty_counts.items():
                                difficulty_percentages[diff] = (count / total) * 100 if total > 0 else 0
                            
                            session_results.append({
                                'session': i+1,
                                'counts': difficulty_counts,
                                'percentages': difficulty_percentages,
                                'total': total,
                                'phase_info': phase_info,
                                'session_type': session_type
                            })
                            
                            print(f"   Difficulty Distribution: {difficulty_counts}")
                            print(f"   Percentages: {difficulty_percentages}")
                            print(f"   Target: 75% Medium, 20% Easy, 5% Hard")
                            
                            # Check if NOT 100% Medium (the critical issue)
                            medium_pct = difficulty_percentages.get('Medium', 0)
                            if medium_pct < 95:
                                print(f"   ✅ NOT 100% Medium: {medium_pct:.1f}% - Diversity achieved!")
                            else:
                                print(f"   ❌ Still 100% Medium: {medium_pct:.1f}% - Issue persists")
                        
                        time.sleep(2)  # Brief pause between sessions
                    else:
                        print(f"   ❌ Session {i+1} creation failed: {response.status_code}")
                        try:
                            error_data = response.json()
                            print(f"   Error: {error_data}")
                        except:
                            print(f"   Error: {response.text}")
                
                except Exception as e:
                    print(f"   ❌ Session {i+1} failed: {e}")
            
            # Analyze overall results
            print("\n📊 OVERALL ANALYSIS:")
            if session_results:
                total_easy = sum(r['counts']['Easy'] for r in session_results)
                total_medium = sum(r['counts']['Medium'] for r in session_results)
                total_hard = sum(r['counts']['Hard'] for r in session_results)
                total_questions = sum(r['total'] for r in session_results)
                
                if total_questions > 0:
                    overall_easy_pct = (total_easy / total_questions) * 100
                    overall_medium_pct = (total_medium / total_questions) * 100
                    overall_hard_pct = (total_hard / total_questions) * 100
                    
                    print(f"   Total Questions Analyzed: {total_questions}")
                    print(f"   Overall Distribution:")
                    print(f"     Easy: {total_easy} ({overall_easy_pct:.1f}%)")
                    print(f"     Medium: {total_medium} ({overall_medium_pct:.1f}%)")
                    print(f"     Hard: {total_hard} ({overall_hard_pct:.1f}%)")
                    print(f"   Target: 75% Medium, 20% Easy, 5% Hard")
                    
                    # Success criteria
                    success_criteria = []
                    
                    # Check NOT 100% Medium
                    if overall_medium_pct < 95:
                        success_criteria.append("✅ NOT 100% Medium - Original issue resolved")
                    else:
                        success_criteria.append("❌ Still 100% Medium - Issue persists")
                    
                    # Check reasonable distribution
                    if 50 <= overall_medium_pct <= 90 and overall_easy_pct >= 5:
                        success_criteria.append("✅ Reasonable difficulty distribution achieved")
                    else:
                        success_criteria.append("❌ Distribution not meeting targets")
                    
                    # Check phase info populated
                    phase_info_populated = any(r['phase_info'] and len(r['phase_info']) > 0 for r in session_results)
                    if phase_info_populated:
                        success_criteria.append("✅ Phase info field populated")
                    else:
                        success_criteria.append("❌ Phase info field still empty")
                    
                    print(f"\n🎯 SUCCESS CRITERIA:")
                    for criterion in success_criteria:
                        print(f"   {criterion}")
                    
                    success_count = sum(1 for c in success_criteria if c.startswith("✅"))
                    success_rate = (success_count / len(success_criteria)) * 100
                    
                    print(f"\n📊 SUCCESS RATE: {success_count}/{len(success_criteria)} ({success_rate:.1f}%)")
                    
                    if success_rate >= 66:
                        print("🎉 STRATIFIED DIFFICULTY DISTRIBUTION: MOSTLY WORKING")
                        return True
                    else:
                        print("❌ STRATIFIED DIFFICULTY DISTRIBUTION: NEEDS FIXES")
                        return False
                else:
                    print("   ❌ No questions to analyze")
                    return False
            else:
                print("   ❌ No successful sessions created")
                return False
        else:
            print(f"   ❌ Student login failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error: {response.text}")
            return False
    
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    success = test_stratified_difficulty_distribution()
    print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}")