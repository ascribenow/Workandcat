#!/usr/bin/env python3
"""
Quick check for PYQ enrichment status
"""

import requests
import json

def check_pyq_enrichment():
    base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
    
    # Login as admin
    login_data = {
        "email": "sumedhprabhu18@gmail.com",
        "password": "admin2025"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, verify=False)
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    token = response.json()['access_token']
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Check PYQ questions
    response = requests.get(f"{base_url}/admin/pyq/questions?limit=10", headers=headers, verify=False)
    if response.status_code != 200:
        print("❌ Failed to get PYQ questions")
        return
    
    questions = response.json().get('questions', [])
    print(f"📊 Found {len(questions)} PYQ questions")
    
    # Check for category and subcategory data
    enriched_questions = 0
    for q in questions:
        category = q.get('category')
        subcategory = q.get('subcategory')
        difficulty_score = q.get('difficulty_score')
        
        if category and category != "To be classified by LLM" and subcategory and subcategory != "To be classified by LLM":
            enriched_questions += 1
            print(f"✅ Question enriched: Category='{category}', Subcategory='{subcategory}', Difficulty={difficulty_score}")
        else:
            print(f"⚠️ Question not enriched: Category='{category}', Subcategory='{subcategory}', Difficulty={difficulty_score}")
    
    print(f"\n📊 Summary: {enriched_questions}/{len(questions)} questions have category×subcategory data")
    
    if enriched_questions > 0:
        print("✅ PYQ enrichment is working - category×subcategory data available")
        return True
    else:
        print("❌ PYQ enrichment incomplete - no category×subcategory data")
        return False

if __name__ == "__main__":
    check_pyq_enrichment()