#!/usr/bin/env python3
"""
Check Database State
"""

import requests

def check_database_state():
    """
    Check current database state
    """
    try:
        # Login first
        login_response = requests.post("http://localhost:8001/api/auth/login", json={
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get questions
        response = requests.get("http://localhost:8001/api/questions?limit=10", headers=headers)
        
        if response.status_code == 200:
            questions = response.json().get("questions", [])
            print(f"Found {len(questions)} questions")
            
            for i, q in enumerate(questions[:3]):
                print(f"\nQuestion {i+1}:")
                print(f"  ID: {q.get('id')}")
                print(f"  Stem: {q.get('stem', '')[:50]}...")
                print(f"  Category: {q.get('category')}")
                print(f"  Subcategory: {q.get('subcategory')}")
                print(f"  Difficulty Band: {q.get('difficulty_band')}")
                print(f"  Right Answer: {q.get('right_answer')}")
                print(f"  PYQ Frequency: {q.get('pyq_frequency_score')}")
                print(f"  Frequency Method: {q.get('frequency_analysis_method')}")
                print(f"  Is Active: {q.get('is_active')}")
        
        else:
            print(f"Failed to get questions: {response.status_code}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database_state()