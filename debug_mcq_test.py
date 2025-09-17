#!/usr/bin/env python3

import requests
import json
import uuid
from datetime import datetime

# Test the MCQ answer comparison issue
def test_mcq_debug():
    base_url = "https://learning-tutor.preview.emergentagent.com/api"
    
    # Authenticate
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    print("🔐 Authenticating...")
    response = requests.post(f"{base_url}/auth/login", json=auth_data, verify=False)
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return
    
    token = response.json()['access_token']
    user_id = response.json()['user']['id']
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print(f"✅ Authenticated as user: {user_id}")
    
    # Get a sample question
    print("\n📋 Getting sample question...")
    response = requests.get(f"{base_url}/questions?limit=1", headers=headers, verify=False)
    if response.status_code != 200:
        print(f"❌ Failed to get questions: {response.status_code}")
        return
    
    questions = response.json()
    if not questions:
        print("❌ No questions found")
        return
    
    question = questions[0]
    question_id = question['id']
    stored_answer = question.get('right_answer', '')  # This is what the API returns
    
    print(f"📊 Question ID: {question_id}")
    print(f"📊 Question stem: {question['stem'][:100]}...")
    print(f"📊 Stored answer (right_answer): '{stored_answer}'")
    
    # Test different answer scenarios
    test_cases = [
        {
            "name": "Direct Match",
            "user_answer": stored_answer,
            "expected": True
        },
        {
            "name": "MCQ Prefix (A)",
            "user_answer": f"(A) {stored_answer}",
            "expected": True
        },
        {
            "name": "MCQ Prefix (B)", 
            "user_answer": f"(B) {stored_answer}",
            "expected": True
        },
        {
            "name": "Wrong Answer",
            "user_answer": "Wrong answer",
            "expected": False
        }
    ]
    
    print(f"\n🧪 Testing answer comparison scenarios...")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   Test {i}: {test_case['name']}")
        print(f"   User Answer: '{test_case['user_answer']}'")
        print(f"   Expected: {'CORRECT' if test_case['expected'] else 'INCORRECT'}")
        
        # Submit answer
        session_id = f"debug_test_{uuid.uuid4()}"
        answer_data = {
            "session_id": session_id,
            "question_id": question_id,
            "action": "submit",
            "data": {
                "user_answer": test_case['user_answer'],
                "time_taken": 30
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = requests.post(f"{base_url}/log/question-action", json=answer_data, headers=headers, verify=False)
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                actual_correct = result['result']['correct']
                status = result['result']['status']
                print(f"   Result: {status.upper()} (correct={actual_correct})")
                
                if actual_correct == test_case['expected']:
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL - Expected {test_case['expected']}, got {actual_correct}")
                    
                # Show backend comparison details if available
                if 'user_answer' in result['result'] and 'correct_answer' in result['result']:
                    print(f"   📊 Backend user_answer: '{result['result']['user_answer']}'")
                    print(f"   📊 Backend correct_answer: '{result['result']['correct_answer']}'")
            else:
                print(f"   ❌ No result in response: {result}")
        else:
            print(f"   ❌ Request failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_mcq_debug()