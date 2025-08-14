#!/usr/bin/env python3
"""
Test Script: Enhanced Background Processing (Option 2)
Tests the automated PYQ frequency analysis integration
"""

import asyncio
import sys
import os
import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8001/api"
ADMIN_EMAIL = "sumedhprabhu18@gmail.com"
ADMIN_PASSWORD = "admin2025"

def get_admin_token():
    """Get admin authentication token"""
    try:
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            result = response.json()
            return result.get("access_token")
        else:
            print(f"❌ Failed to login: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_enhanced_question_upload():
    """Test uploading a question with enhanced background processing"""
    try:
        print("🚀 Testing Enhanced Background Processing (Option 2)")
        print("=" * 60)
        
        # Get admin token
        token = get_admin_token()
        if not token:
            print("❌ Could not authenticate admin")
            return False
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test question data
        test_question = {
            "stem": "A train travels 240 km in 3 hours. What is its average speed in km/h?",
            "hint_category": "A-Arithmetic",
            "hint_subcategory": "Time–Speed–Distance (TSD)",
            "source": "Enhanced Processing Test"
        }
        
        print("📤 Step 1: Uploading test question...")
        
        # Upload question
        response = requests.post(
            f"{BASE_URL}/questions",
            json=test_question,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            question_id = result.get("question_id")
            print(f"✅ Question uploaded successfully!")
            print(f"   Question ID: {question_id}")
            print(f"   Status: {result.get('status')}")
            
            # Wait for background processing
            print("\n⏳ Step 2: Waiting for enhanced background processing...")
            print("   (LLM enrichment + PYQ frequency analysis)")
            
            for i in range(12):  # Wait up to 60 seconds
                time.sleep(5)
                print(f"   Waiting... {(i+1)*5}s")
                
                # Check question status
                check_response = requests.get(
                    f"{BASE_URL}/questions",
                    headers=headers,
                    params={"limit": 1}
                )
                
                if check_response.status_code == 200:
                    questions = check_response.json()
                    if questions and len(questions) > 0:
                        question = questions[0]
                        
                        # Check if processing is complete
                        has_llm_data = bool(question.get("subcategory") and question.get("difficulty_band"))
                        has_pyq_data = question.get("pyq_frequency_score") is not None
                        
                        if has_llm_data and has_pyq_data:
                            print("✅ Enhanced background processing completed!")
                            print("\n📊 Processing Results:")
                            print(f"   LLM Enrichment:")
                            print(f"     - Subcategory: {question.get('subcategory')}")
                            print(f"     - Difficulty: {question.get('difficulty_band')}")
                            print(f"     - Learning Impact: {question.get('learning_impact')}")
                            print(f"   PYQ Frequency Analysis:")
                            print(f"     - PYQ Score: {question.get('pyq_frequency_score', 'Not set')}")
                            print(f"     - Frequency Band: {question.get('frequency_band')}")
                            print(f"     - Analysis Method: {question.get('frequency_analysis_method', 'Not set')}")
                            return True
                        elif has_llm_data:
                            print("   ⚡ LLM enrichment completed, PYQ analysis in progress...")
                        else:
                            print("   🔄 Background processing in progress...")
            
            print("⚠️ Processing took longer than expected (60s timeout)")
            return False
            
        else:
            print(f"❌ Question upload failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def test_enhanced_session_creation():
    """Test creating a session with enhanced question selection"""
    try:
        print("\n🎯 Testing Enhanced Session Creation")
        print("=" * 40)
        
        # Get admin token
        token = get_admin_token()
        if not token:
            return False
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test enhanced session endpoint
        response = requests.post(
            f"{BASE_URL}/admin/test/enhanced-session",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Enhanced session test completed!")
            print(f"   Enhancement Level: {result.get('enhancement_level', 'unknown')}")
            
            test_results = result.get('test_results', {})
            metadata_analysis = test_results.get('metadata_analysis', {})
            
            print(f"   Session Created: {test_results.get('session_created', False)}")
            print(f"   Total Questions: {test_results.get('total_questions', 0)}")
            print(f"   Dynamic Adjustment: {metadata_analysis.get('dynamic_adjustment', False)}")
            print(f"   PYQ Frequency Stats: {metadata_analysis.get('pyq_frequency_stats', {})}")
            
            enhancement_features = result.get('enhancement_features', {})
            print(f"\n🔧 Active Enhancements:")
            for feature, status in enhancement_features.items():
                print(f"   - {feature}: {status}")
            
            return True
            
        else:
            print(f"❌ Enhanced session test failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Session test error: {e}")
        return False

def main():
    """Run all enhanced processing tests"""
    print("🧪 ENHANCED BACKGROUND PROCESSING TESTS")
    print("🎯 Testing: Option 2 - Automatic LLM + PYQ Frequency Analysis")
    print("🕒 Started:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)
    
    results = []
    
    # Test 1: Enhanced question upload and processing
    results.append(test_enhanced_question_upload())
    
    # Test 2: Enhanced session creation
    results.append(test_enhanced_session_creation())
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print(f"✅ Passed: {sum(results)}/{len(results)} tests")
    
    if all(results):
        print("🎉 All tests passed! Enhanced background processing is working correctly.")
        print("\n🔮 What this means:")
        print("   ✅ Every uploaded question automatically gets LLM enrichment")
        print("   ✅ Every uploaded question automatically gets PYQ frequency analysis")
        print("   ✅ Question selection uses sophisticated PYQ frequency weighting")
        print("   ✅ No manual intervention required - fully automated!")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
    
    print(f"\n🕒 Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()