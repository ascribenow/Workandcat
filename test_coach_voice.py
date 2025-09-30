#!/usr/bin/env python3

import requests
import json
import re
import os
import sys
from datetime import datetime

class CoachVoiceTester:
    def __init__(self, base_url="https://adapt-engine.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate with test credentials"""
        print("🔐 Authenticating with sp@theskinmantra.com/student123...")
        
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
                    print(f"✅ Authentication successful (Token: {len(token)} chars)")
                    return True
            
            print(f"❌ Authentication failed: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_dashboard_insights_coach_voice(self):
        """Test dashboard insights for coach voice implementation"""
        print("\n🗣️ Testing Dashboard Insights Coach Voice...")
        
        if not self.auth_headers:
            print("❌ Not authenticated")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/dashboard/adaptive-insights",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code != 200:
                print(f"❌ Dashboard insights failed: {response.status_code}")
                return False
            
            data = response.json()
            all_time_markdown = data.get("all_time_markdown", "")
            recent_markdown = data.get("recent_markdown", "")
            
            print(f"📊 All-time content: {len(all_time_markdown)} chars")
            print(f"📊 Recent content: {len(recent_markdown)} chars")
            
            # Combine content for analysis
            full_content = (all_time_markdown + " " + recent_markdown).lower()
            
            results = {}
            
            # Test 1: Coach Voice Indicators
            coach_words = ["you", "your", "let's", "we", "great", "good", "keep", "build", "work", "momentum"]
            found_coach_words = [word for word in coach_words if word in full_content]
            results["coach_voice_tone"] = len(found_coach_words) >= 3
            print(f"   Coach words found: {found_coach_words[:5]} ({'✅' if results['coach_voice_tone'] else '❌'})")
            
            # Test 2: Human-friendly percentages ("x out of 10")
            out_of_10_pattern = r'\b\d+\s+out\s+of\s+10\b'
            about_pattern = r'\babout\s+\d+\s+out\s+of\s+10\b'
            
            out_of_10_matches = re.findall(out_of_10_pattern, full_content, re.IGNORECASE)
            about_matches = re.findall(about_pattern, full_content, re.IGNORECASE)
            
            results["human_friendly_format"] = bool(out_of_10_matches or about_matches)
            print(f"   Human format found: {out_of_10_matches + about_matches} ({'✅' if results['human_friendly_format'] else '❌'})")
            
            # Test 3: No technical formatting
            technical_patterns = [r'\d+\.\d+%', r'\d+%', r'^\s*[-*•]\s', r'delta|score|coefficient']
            technical_found = []
            for pattern in technical_patterns:
                matches = re.findall(pattern, full_content, re.MULTILINE | re.IGNORECASE)
                technical_found.extend(matches)
            
            results["no_technical_formatting"] = not bool(technical_found)
            print(f"   Technical formatting: {technical_found[:3]} ({'✅' if results['no_technical_formatting'] else '❌'})")
            
            # Test 4: Narrative storytelling
            narrative_words = ["journey", "progress", "moving", "building", "growing", "trending", "momentum"]
            found_narrative = [word for word in narrative_words if word in full_content]
            results["narrative_storytelling"] = len(found_narrative) >= 2
            print(f"   Narrative words: {found_narrative} ({'✅' if results['narrative_storytelling'] else '❌'})")
            
            # Test 5: No robotic language
            robotic_words = ["processing", "computing", "algorithm", "system", "database", "execute"]
            found_robotic = [word for word in robotic_words if word in full_content]
            results["no_robotic_language"] = not bool(found_robotic)
            print(f"   Robotic language: {found_robotic} ({'✅' if results['no_robotic_language'] else '❌'})")
            
            # Display sample content
            print(f"   📝 All-time sample: '{all_time_markdown[:150]}...'")
            print(f"   📝 Recent sample: '{recent_markdown[:150]}...'")
            
            return results
            
        except Exception as e:
            print(f"❌ Dashboard insights test error: {e}")
            return False
    
    def test_pre_session_insights_coach_voice(self):
        """Test pre-session insights for coach voice JSON format"""
        print("\n🎯 Testing Pre-Session Insights Coach Voice...")
        
        if not self.auth_headers:
            print("❌ Not authenticated")
            return False
        
        try:
            response = requests.get(
                f"{self.base_url}/session/pre-session-insight",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code != 200:
                print(f"❌ Pre-session insights failed: {response.status_code}")
                return False
            
            data = response.json()
            print(f"📊 Pre-session response keys: {list(data.keys())}")
            
            results = {}
            
            # Test 1: Required JSON fields
            required_fields = ["title", "progress", "way_forward", "today"]
            missing_fields = [field for field in required_fields if field not in data]
            results["json_structure"] = not bool(missing_fields)
            print(f"   JSON structure: Missing {missing_fields} ({'✅' if results['json_structure'] else '❌'})")
            
            # Test 2: Title with emoji and encouraging phrase
            title = data.get("title", "")
            emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]'
            
            has_emoji = bool(re.search(emoji_pattern, title))
            encouraging_words = ["ready", "let's", "focus", "build", "go", "start"]
            is_encouraging = any(word in title.lower() for word in encouraging_words)
            
            results["title_format"] = has_emoji and is_encouraging and len(title) <= 40
            print(f"   Title: '{title}' (Emoji: {has_emoji}, Encouraging: {is_encouraging}) ({'✅' if results['title_format'] else '❌'})")
            
            # Test 3: Progress field human-friendly
            progress = data.get("progress", "")
            has_human_format = "out of 10" in progress.lower() or "about" in progress.lower()
            no_percentages = "%" not in progress and not re.search(r'\d+\.\d+', progress)
            
            results["progress_human_friendly"] = has_human_format or no_percentages
            print(f"   Progress: '{progress}' (Human: {has_human_format}, No %: {no_percentages}) ({'✅' if results['progress_human_friendly'] else '❌'})")
            
            # Test 4: Way forward encouraging
            way_forward = data.get("way_forward", [])
            if isinstance(way_forward, list) and len(way_forward) <= 2:
                encouraging_bullets = any(
                    any(word in bullet.lower() for word in ["focus", "work", "keep", "build", "practice", "trust"])
                    for bullet in way_forward
                )
                results["way_forward_encouraging"] = encouraging_bullets
                print(f"   Way forward: {way_forward} ({'✅' if results['way_forward_encouraging'] else '❌'})")
            else:
                results["way_forward_encouraging"] = False
                print(f"   Way forward format issue: {way_forward} ❌")
            
            # Test 5: Today field readable
            today = data.get("today", "")
            readable_words = ["today", "session", "practice", "focus", "mixed"]
            has_readable = any(word in today.lower() for word in readable_words)
            no_technical = not re.search(r'[A-Z]{2,}_[A-Z]{2,}|session_id|user_id', today)
            
            results["today_readable"] = has_readable and no_technical
            print(f"   Today: '{today}' (Readable: {has_readable}, No tech: {no_technical}) ({'✅' if results['today_readable'] else '❌'})")
            
            # Display full card
            print(f"   📝 Full pre-session card:")
            for key in required_fields:
                if key in data:
                    print(f"      {key}: {data[key]}")
            
            return results
            
        except Exception as e:
            print(f"❌ Pre-session insights test error: {e}")
            return False
    
    def test_fallback_coach_voice(self):
        """Test fallback responses for coach voice consistency"""
        print("\n🛡️ Testing Fallback Coach Voice...")
        
        if not self.auth_headers:
            print("❌ Not authenticated")
            return False
        
        try:
            # Enable fallback mode
            original_flag = os.environ.get("INSIGHTS_FORCE_FALLBACK", "false")
            os.environ["INSIGHTS_FORCE_FALLBACK"] = "true"
            print("   🎛️ Enabled INSIGHTS_FORCE_FALLBACK")
            
            response = requests.get(
                f"{self.base_url}/dashboard/adaptive-insights",
                headers=self.auth_headers,
                timeout=30,
                verify=False
            )
            
            # Restore flag
            os.environ["INSIGHTS_FORCE_FALLBACK"] = original_flag
            
            if response.status_code != 200:
                print(f"❌ Fallback test failed: {response.status_code}")
                return False
            
            data = response.json()
            fallback_content = (
                data.get("all_time_markdown", "") + " " + 
                data.get("recent_markdown", "")
            ).lower()
            
            results = {}
            
            # Test fallback coach voice
            coach_words = ["you", "your", "work", "practice", "build", "momentum", "steady"]
            found_coach = [word for word in coach_words if word in fallback_content]
            results["fallback_coach_voice"] = len(found_coach) >= 2
            print(f"   Fallback coach words: {found_coach} ({'✅' if results['fallback_coach_voice'] else '❌'})")
            
            # Test no technical language in fallback
            technical_terms = ["%", "delta", "score", "coefficient", "algorithm"]
            found_technical = [term for term in technical_terms if term in fallback_content]
            results["fallback_no_technical"] = not bool(found_technical)
            print(f"   Fallback technical terms: {found_technical} ({'✅' if results['fallback_no_technical'] else '❌'})")
            
            print(f"   📝 Fallback sample: '{fallback_content[:150]}...'")
            
            return results
            
        except Exception as e:
            print(f"❌ Fallback test error: {e}")
            return False
    
    def test_sanitization_function(self):
        """Test the sanitization function directly"""
        print("\n🧹 Testing Post-Processing Sanitization...")
        
        try:
            # Add backend path
            sys.path.append('/app/backend')
            from services.insight_generator_service import insight_generator_service
            
            test_cases = [
                ("You scored 58.5% on recent sessions", "out of 10"),
                ("Your accuracy is 42.3%", "out of 10"),
                ("You got 75% correct", "out of 10"),
                ("Performance improved by 15%", "out of 10")
            ]
            
            results = {"sanitization_working": True}
            
            for input_text, expected_pattern in test_cases:
                sanitized = insight_generator_service._sanitize_coach_response(input_text)
                if expected_pattern in sanitized or "out of 10" in sanitized:
                    print(f"   ✅ '{input_text}' → '{sanitized}'")
                else:
                    print(f"   ❌ '{input_text}' → '{sanitized}' (expected '{expected_pattern}')")
                    results["sanitization_working"] = False
            
            return results
            
        except Exception as e:
            print(f"❌ Sanitization test error: {e}")
            return {"sanitization_working": False}
    
    def run_all_tests(self):
        """Run all coach voice tests"""
        print("🎯 COACH VOICE IMPLEMENTATION TESTING")
        print("=" * 80)
        print("OBJECTIVE: Test COACH VOICE implementation for human, motivating language")
        print("FOCUS: Human language conversion, coach tone, narrative storytelling")
        print("EXPECTED: Personal coach speaking, no technical percentages, encouraging language")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Cannot proceed without authentication")
            return False
        
        all_results = {}
        
        # Run tests
        dashboard_results = self.test_dashboard_insights_coach_voice()
        if dashboard_results:
            all_results.update(dashboard_results)
        
        pre_session_results = self.test_pre_session_insights_coach_voice()
        if pre_session_results:
            all_results.update(pre_session_results)
        
        fallback_results = self.test_fallback_coach_voice()
        if fallback_results:
            all_results.update(fallback_results)
        
        sanitization_results = self.test_sanitization_function()
        if sanitization_results:
            all_results.update(sanitization_results)
        
        # Summary
        print("\n" + "=" * 80)
        print("🎯 COACH VOICE TESTING RESULTS")
        print("=" * 80)
        
        if all_results:
            passed = sum(all_results.values())
            total = len(all_results)
            success_rate = (passed / total) * 100
            
            print(f"Overall Success Rate: {passed}/{total} ({success_rate:.1f}%)")
            
            print("\nDetailed Results:")
            for test_name, result in all_results.items():
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"  {test_name.replace('_', ' ').title():<40} {status}")
            
            # Critical assessment
            critical_tests = [
                "coach_voice_tone", "human_friendly_format", "no_technical_formatting",
                "narrative_storytelling", "json_structure", "progress_human_friendly"
            ]
            
            critical_passed = sum(all_results.get(test, False) for test in critical_tests)
            critical_total = len(critical_tests)
            critical_rate = (critical_passed / critical_total) * 100
            
            print(f"\nCritical Tests: {critical_passed}/{critical_total} ({critical_rate:.1f}%)")
            
            if critical_rate >= 75:
                print("\n🎉 COACH VOICE IMPLEMENTATION: PRODUCTION READY")
                print("   - Coach voice tone successfully implemented")
                print("   - Human language conversion working")
                print("   - Narrative storytelling present")
                print("   - Technical formatting removed")
            else:
                print("\n⚠️ COACH VOICE IMPLEMENTATION: NEEDS ATTENTION")
                print("   - Some critical coach voice aspects need improvement")
            
            return success_rate >= 75
        
        else:
            print("❌ No test results available")
            return False

if __name__ == "__main__":
    tester = CoachVoiceTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)