#!/usr/bin/env python3
"""
Test script for Skip Question functionality
"""

import requests
import json

# Test data
BASE_URL = "http://localhost:8001"

def test_logging_endpoint():
    """Test the question action logging endpoint"""
    print("🧪 Testing question action logging endpoint...")
    
    # Test data
    log_data = {
        "session_id": "test-session-123",
        "question_id": "test-question-456", 
        "action": "skip",
        "data": {},
        "timestamp": "2024-12-07T10:30:00Z"
    }
    
    # Test without authentication (should fail)
    response = requests.post(f"{BASE_URL}/api/log/question-action", json=log_data)
    print(f"   Without auth: {response.status_code} - {'✅ PASS' if response.status_code == 401 else '❌ FAIL'}")
    
    # Test admin get endpoint without auth (should fail)
    response = requests.get(f"{BASE_URL}/api/admin/log/question-actions")
    print(f"   Admin endpoint without auth: {response.status_code} - {'✅ PASS' if response.status_code == 401 else '❌ FAIL'}")
    
    print("✅ Basic endpoint tests completed!")

def test_session_endpoints():
    """Test the temporary session endpoints"""
    print("🧪 Testing temporary session endpoints...")
    
    # Test get next question without auth (should fail)
    response = requests.get(f"{BASE_URL}/api/sessions/test-session/next-question")
    print(f"   Next question without auth: {response.status_code} - {'✅ PASS' if response.status_code == 401 else '❌ FAIL'}")
    
    # Test submit answer without auth (should fail)
    answer_data = {
        "question_id": "test-question",
        "user_answer": "A"
    }
    response = requests.post(f"{BASE_URL}/api/sessions/test-session/submit-answer", json=answer_data)
    print(f"   Submit answer without auth: {response.status_code} - {'✅ PASS' if response.status_code == 401 else '❌ FAIL'}")
    
    print("✅ Session endpoint tests completed!")

if __name__ == "__main__":
    print("🚀 Starting Skip Question functionality tests...")
    test_logging_endpoint()
    test_session_endpoints()
    print("🎉 All tests completed!")