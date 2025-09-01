#!/usr/bin/env python3
"""
Check Latest Questions with Unified Fields
"""

import requests

def check_latest_questions():
    """
    Look for the most recent questions with unified fields
    """
    try:
        # Login first
        login_response = requests.post("http://localhost:8001/api/auth/login", json={
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get more questions to find the latest ones
        response = requests.get("http://localhost:8001/api/questions?limit=20", headers=headers)
        
        if response.status_code == 200:
            questions = response.json().get("questions", [])
            print(f"Found {len(questions)} questions")
            
            # Look for questions with unified fields (created by our recent tests)
            unified_questions = []
            for q in questions:
                if (q.get('category') and 
                    q.get('right_answer') and 
                    q.get('core_concepts') is not None):
                    unified_questions.append(q)
            
            print(f"\n🎯 Questions with unified fields: {len(unified_questions)}")
            
            for i, q in enumerate(unified_questions[:3]):
                print(f"\n✅ Unified Question {i+1}:")
                print(f"  Stem: {q.get('stem', '')[:60]}...")
                print(f"  Category: {q.get('category')}")
                print(f"  Subcategory: {q.get('subcategory')}")
                print(f"  Right Answer: {q.get('right_answer')}")
                print(f"  Difficulty Band: {q.get('difficulty_band')}")
                print(f"  Core Concepts: {q.get('core_concepts')}")
                print(f"  Solution Method: {q.get('solution_method')}")
                print(f"  Problem Structure: {q.get('problem_structure')}")
                print(f"  Quality Verified: {q.get('quality_verified')}")
                
                if q.get('core_concepts'):
                    print(f"  🎉 FULL UNIFIED ENRICHMENT DETECTED!")
            
            if len(unified_questions) >= 2:
                print(f"\n🎯 SUCCESS: Found {len(unified_questions)} questions with unified enrichment!")
                return True
            else:
                print(f"\n⚠️ Only found {len(unified_questions)} unified questions")
                return False
        
        return False
    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = check_latest_questions()
    print(f"\nFinal Result: {'SUCCESS - UNIFIED ENRICHMENT WORKING!' if success else 'NEEDS MORE TESTING'}")