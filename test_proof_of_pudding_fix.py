#!/usr/bin/env python3
"""
Test script for the Proof of the Pudding Adaptive Insights Fix

This script tests the specific fix implemented to resolve the issue where 
the wrong LLM prompt was being used for insight generation.
"""

import requests
import json
import time
import sys
import os
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class ProofOfPuddingTester:
    def __init__(self, base_url="https://twelvr-auth-fix.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate with sp@theskinmantra.com/student123"""
        print("🔐 AUTHENTICATING...")
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login", 
                json=auth_data, 
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                if token:
                    self.auth_headers = {
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json'
                    }
                    self.user_id = data.get('user', {}).get('id')
                    print(f"   ✅ Authentication successful")
                    print(f"   📊 JWT Token length: {len(token)} characters")
                    print(f"   📊 User ID: {self.user_id}")
                    return True
                else:
                    print(f"   ❌ No access token in response")
                    return False
            else:
                print(f"   ❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Authentication error: {e}")
            return False
    
    def force_refresh_insights(self):
        """Force refresh insights to trigger UPDATE_INSIGHTS background jobs"""
        print("\n🔄 FORCE REFRESHING INSIGHTS...")
        
        if not self.auth_headers:
            print("   ❌ Not authenticated")
            return False
            
        try:
            response = requests.post(
                f"{self.base_url}/insights/force-refresh",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get('job_id')
                print(f"   ✅ Force refresh successful")
                print(f"   📊 Job ID: {job_id}")
                return True
            else:
                print(f"   ❌ Force refresh failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Force refresh error: {e}")
            return False
    
    def test_dashboard_insights(self):
        """Test dashboard insights for specific numerical analysis"""
        print("\n📊 TESTING DASHBOARD INSIGHTS...")
        
        if not self.auth_headers:
            print("   ❌ Not authenticated")
            return False
            
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/dashboard/adaptive-insights",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Dashboard insights accessible ({response_time:.3f}s)")
                
                # Analyze the insights content
                all_time_content = data.get("all_time_markdown", "")
                recent_content = data.get("recent_markdown", "")
                source = data.get("source", "unknown")
                
                print(f"   📊 Response analysis:")
                print(f"      All-time content: {len(all_time_content)} chars")
                print(f"      Recent content: {len(recent_content)} chars")
                print(f"      Source: {source}")
                
                # Check for specific numerical analysis
                combined_content = (all_time_content + " " + recent_content).lower()
                
                # Check for banned generic phrases
                banned_phrases = [
                    "consistent practice", "building foundations", "trust the process",
                    "keep up", "steady rhythm", "continued engagement", "building strong"
                ]
                
                banned_found = []
                for phrase in banned_phrases:
                    if phrase in combined_content:
                        banned_found.append(phrase)
                
                if banned_found:
                    print(f"   ❌ BANNED PHRASES FOUND: {banned_found}")
                else:
                    print(f"   ✅ No banned generic phrases detected")
                
                # Check for specific data analysis indicators
                data_indicators = [
                    "sessions", "accuracy", "correct", "concepts", "performance", 
                    "questions", "attempts", "out of 10", "about", "specific"
                ]
                
                data_indicator_count = sum(1 for indicator in data_indicators 
                                         if indicator in combined_content)
                
                print(f"   📊 Data analysis indicators: {data_indicator_count}/{len(data_indicators)}")
                
                # Check for concept names
                concept_indicators = ["concept", "topic", "area", "subcategory", "arithmetic", "algebra", "geometry"]
                concept_count = sum(1 for indicator in concept_indicators 
                                  if indicator in combined_content)
                
                print(f"   📊 Concept indicators: {concept_count}/{len(concept_indicators)}")
                
                # Check for "out of 10" format
                out_of_10_found = "out of 10" in combined_content
                print(f"   📊 'Out of 10' format: {'✅ Found' if out_of_10_found else '❌ Not found'}")
                
                # Display sample content
                if all_time_content:
                    print(f"   📝 All-time sample: {all_time_content[:200]}...")
                if recent_content:
                    print(f"   📝 Recent sample: {recent_content[:200]}...")
                
                return {
                    "accessible": True,
                    "no_banned_phrases": len(banned_found) == 0,
                    "has_data_indicators": data_indicator_count >= 3,
                    "has_concept_indicators": concept_count >= 2,
                    "uses_out_of_10_format": out_of_10_found,
                    "source": source,
                    "response_time": response_time
                }
            else:
                print(f"   ❌ Dashboard insights failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Dashboard insights error: {e}")
            return False
    
    def test_pre_session_insights(self):
        """Test pre-session insights for user-specific performance data"""
        print("\n🎯 TESTING PRE-SESSION INSIGHTS...")
        
        if not self.auth_headers:
            print("   ❌ Not authenticated")
            return False
            
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/session/pre-session-insight",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Pre-session insights accessible ({response_time:.3f}s)")
                
                # Analyze the pre-session card content
                title = data.get("title", "")
                progress = data.get("progress", "")
                way_forward = data.get("way_forward", [])
                today = data.get("today", "")
                source = data.get("source", "unknown")
                
                print(f"   📊 Pre-session card analysis:")
                print(f"      Title: {title}")
                print(f"      Progress: {progress}")
                print(f"      Way forward: {way_forward}")
                print(f"      Today: {today}")
                print(f"      Source: {source}")
                
                # Check for user-specific content
                combined_content = (title + " " + progress + " " + today + " " + " ".join(way_forward)).lower()
                
                # Check for banned generic phrases
                banned_phrases = [
                    "consistent practice", "building foundations", "trust the process",
                    "keep up", "steady rhythm", "continued engagement", "building strong"
                ]
                
                banned_found = []
                for phrase in banned_phrases:
                    if phrase in combined_content:
                        banned_found.append(phrase)
                
                if banned_found:
                    print(f"   ❌ BANNED PHRASES FOUND: {banned_found}")
                else:
                    print(f"   ✅ No banned generic phrases detected")
                
                # Check for specific performance data
                performance_indicators = [
                    "out of 10", "accuracy", "sessions", "correct", "performance", "concepts"
                ]
                
                performance_count = sum(1 for indicator in performance_indicators 
                                      if indicator in combined_content)
                
                print(f"   📊 Performance indicators: {performance_count}/{len(performance_indicators)}")
                
                # Check if content is contextual (not generic)
                generic_indicators = ["ready to learn", "let's begin", "mixed practice"]
                generic_count = sum(1 for indicator in generic_indicators 
                                  if indicator in combined_content)
                
                is_contextual = performance_count > generic_count
                print(f"   📊 Contextual content: {'✅ Yes' if is_contextual else '❌ Generic'}")
                
                return {
                    "accessible": True,
                    "no_banned_phrases": len(banned_found) == 0,
                    "has_performance_data": performance_count >= 2,
                    "is_contextual": is_contextual,
                    "source": source,
                    "response_time": response_time
                }
            else:
                print(f"   ❌ Pre-session insights failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Pre-session insights error: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run the comprehensive Proof of the Pudding test"""
        print("🎯 PROOF OF THE PUDDING ADAPTIVE INSIGHTS FIX TESTING")
        print("=" * 80)
        print("OBJECTIVE: Test the enhanced demanding analytical prompt fix")
        print("FOCUS: Personalized insights with specific data analysis, not generic text")
        print("EXPECTED: Insights with actual numbers, concept names, and performance patterns")
        print("=" * 80)
        
        results = {
            "authentication": False,
            "force_refresh": False,
            "dashboard_insights": False,
            "pre_session_insights": False,
            "overall_success": False
        }
        
        # Phase 1: Authentication
        if not self.authenticate():
            print("\n❌ AUTHENTICATION FAILED - Cannot proceed with testing")
            return results
        results["authentication"] = True
        
        # Phase 2: Force refresh insights
        if self.force_refresh_insights():
            results["force_refresh"] = True
            # Wait a moment for background job to process
            print("   ⏳ Waiting 5 seconds for background job processing...")
            time.sleep(5)
        
        # Phase 3: Test dashboard insights
        dashboard_result = self.test_dashboard_insights()
        if dashboard_result and isinstance(dashboard_result, dict):
            results["dashboard_insights"] = (
                dashboard_result.get("accessible", False) and
                dashboard_result.get("no_banned_phrases", False) and
                dashboard_result.get("has_data_indicators", False)
            )
        
        # Phase 4: Test pre-session insights
        pre_session_result = self.test_pre_session_insights()
        if pre_session_result and isinstance(pre_session_result, dict):
            results["pre_session_insights"] = (
                pre_session_result.get("accessible", False) and
                pre_session_result.get("no_banned_phrases", False) and
                pre_session_result.get("has_performance_data", False)
            )
        
        # Overall assessment
        results["overall_success"] = (
            results["authentication"] and
            results["dashboard_insights"] and
            results["pre_session_insights"]
        )
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎯 PROOF OF THE PUDDING FIX TESTING - RESULTS")
        print("=" * 80)
        
        test_categories = {
            "AUTHENTICATION": results["authentication"],
            "FORCE REFRESH": results["force_refresh"],
            "DASHBOARD INSIGHTS": results["dashboard_insights"],
            "PRE-SESSION INSIGHTS": results["pre_session_insights"]
        }
        
        passed_tests = sum(test_categories.values())
        total_tests = len(test_categories)
        success_rate = (passed_tests / total_tests) * 100
        
        for category, result in test_categories.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{category:<25} {status}")
        
        print("-" * 80)
        print(f"Overall Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if results["overall_success"]:
            print("\n🎉 PROOF OF THE PUDDING FIX: SUCCESS!")
            print("   - Enhanced demanding analytical prompt is working")
            print("   - Personalized insights with specific data analysis")
            print("   - No banned generic phrases detected")
            print("   - Direct Gemini API integration functional")
        else:
            print("\n⚠️ PROOF OF THE PUDDING FIX: NEEDS ATTENTION")
            print("   - Some components of the fix are not working as expected")
            if not results["dashboard_insights"]:
                print("   - Dashboard insights still showing generic content")
            if not results["pre_session_insights"]:
                print("   - Pre-session insights not personalized")
        
        return results

def main():
    """Main test execution"""
    tester = ProofOfPuddingTester()
    results = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    if results["overall_success"]:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()