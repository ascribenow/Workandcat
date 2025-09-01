#!/usr/bin/env python3
"""
Test Database Verification
"""

import requests

def test_database_verification():
    """
    Test if database verification works
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
                print(f"  Stem: {q.get('stem', '')[:50]}...")
                print(f"  Category: {q.get('category')}")
                print(f"  Right Answer: {q.get('right_answer')}")
                print(f"  Core Concepts: {q.get('core_concepts')}")
                print(f"  Solution Method: {q.get('solution_method')}")
                print(f"  Quality Verified: {q.get('quality_verified')}")
                
                if q.get('category') and q.get('core_concepts'):
                    print(f"  ✅ Question has unified fields!")
                    return True
                else:
                    print(f"  ❌ Missing unified fields")
        
        return False
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_verification()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")