import requests
import json

# Test the specific failing endpoints
base_url = "https://learning-tutor.preview.emergentagent.com/api"

# Login as student first
login_data = {
    "email": "student@catprep.com",
    "password": "student123"
}

response = requests.post(f"{base_url}/auth/login", json=login_data)
if response.status_code == 200:
    token = response.json()["access_token"]
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    print("=== Testing Diagnostic Complete Issue ===")
    
    # Start a new diagnostic
    response = requests.post(f"{base_url}/diagnostic/start", json={}, headers=headers)
    if response.status_code == 200:
        diagnostic_id = response.json()["diagnostic_id"]
        print(f"Started diagnostic: {diagnostic_id}")
        
        # Submit one answer
        answer_data = {
            "diagnostic_id": diagnostic_id,
            "question_id": "14781a2b-4eef-4671-ab19-a814ea6e9b71",  # Use a known question ID
            "user_answer": "A",
            "time_sec": 45,
            "context": "diagnostic",
            "hint_used": False
        }
        
        response = requests.post(f"{base_url}/diagnostic/submit-answer", json=answer_data, headers=headers)
        print(f"Submit answer status: {response.status_code}")
        
        # Try to complete diagnostic
        response = requests.post(f"{base_url}/diagnostic/{diagnostic_id}/complete", json={}, headers=headers)
        print(f"Complete diagnostic status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error: {response.json()}")
    
    print("\n=== Testing Session Submit Answer Issue ===")
    
    # Start a session
    session_data = {"target_minutes": 30}
    response = requests.post(f"{base_url}/session/start", json=session_data, headers=headers)
    if response.status_code == 200:
        session_id = response.json()["session_id"]
        print(f"Started session: {session_id}")
        
        # Get next question
        response = requests.get(f"{base_url}/session/{session_id}/next-question", headers=headers)
        if response.status_code == 200:
            question = response.json()["question"]
            question_id = question["id"]
            print(f"Got question: {question_id}")
            
            # Submit answer
            answer_data = {
                "question_id": question_id,
                "user_answer": "A",
                "time_sec": 60,
                "context": "daily",
                "hint_used": False
            }
            
            response = requests.post(f"{base_url}/session/{session_id}/submit-answer", json=answer_data, headers=headers)
            print(f"Submit session answer status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.json()}")

else:
    print(f"Login failed: {response.status_code}")