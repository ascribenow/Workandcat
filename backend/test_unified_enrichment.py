#!/usr/bin/env python3
"""
Test Unified Enrichment Service
"""

import requests
import io

def test_unified_enrichment():
    """
    Test the unified enrichment approach
    """
    try:
        print("🎯 TESTING UNIFIED ENRICHMENT SERVICE")
        print("=" * 60)
        
        # Login first
        login_response = requests.post("http://localhost:8001/api/auth/login", json={
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        })
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Admin authentication successful")
        
        # Test unified enrichment with comprehensive question
        csv_content = """stem,answer
A car travels at 60 km/h for 2 hours and then at 80 km/h for 3 hours. What is the average speed?,70 km/h
If 3x + 5 = 20 then find x,5"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        files = {'file': ('unified_test.csv', csv_file, 'text/csv')}
        
        print("\n📋 Uploading test questions with unified enrichment...")
        
        upload_response = requests.post(
            "http://localhost:8001/api/admin/upload-questions-csv",
            files=files,
            headers=headers,
            timeout=180  # Extended timeout for comprehensive processing
        )
        
        print(f"📊 Upload response status: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            response_data = upload_response.json()
            stats = response_data.get("statistics", {})
            
            print(f"✅ Questions created: {stats.get('questions_created', 0)}")
            print(f"✅ Questions activated: {stats.get('questions_activated', 0)}")
            
            # Check enrichment results for unified fields
            enrichment_results = response_data.get("enrichment_results", [])
            
            print(f"\n🧠 UNIFIED ENRICHMENT RESULTS:")
            for i, result in enumerate(enrichment_results):
                if result.get("enrichment_success") and result.get("llm_fields"):
                    fields = result["llm_fields"]
                    print(f"\n   Question {i+1}:")
                    print(f"   📊 Basic Fields:")
                    print(f"      Category: {fields.get('category')}")
                    print(f"      Subcategory: {fields.get('subcategory')}")
                    print(f"      Type: {fields.get('type_of_question')}")
                    print(f"      Right Answer: {fields.get('right_answer')}")
                    print(f"      Difficulty Band: {fields.get('difficulty_band')}")
                    print(f"      Difficulty Score: {fields.get('difficulty_score')}")
                    
                    print(f"   🧠 Enhanced Fields:")
                    print(f"      Core Concepts: {fields.get('core_concepts')}")
                    print(f"      Solution Method: {fields.get('solution_method')}")
                    print(f"      Problem Structure: {fields.get('problem_structure')}")
                    print(f"      Quality Verified: {fields.get('quality_verified')}")
                    
                    # Check if unified fields are populated
                    unified_fields_present = all([
                        fields.get('category'),
                        fields.get('difficulty_band'),
                        fields.get('core_concepts'),
                        fields.get('solution_method'),
                        'quality_verified' in fields
                    ])
                    
                    if unified_fields_present:
                        print(f"   ✅ ALL UNIFIED FIELDS PRESENT!")
                    else:
                        print(f"   ⚠️ Some unified fields missing")
            
            # Test question retrieval to verify database storage
            print(f"\n📊 VERIFYING DATABASE STORAGE:")
            questions_response = requests.get("http://localhost:8001/api/questions?limit=5", headers=headers)
            
            if questions_response.status_code == 200:
                questions = questions_response.json().get("questions", [])
                
                for q in questions[:2]:  # Check first 2 questions
                    if q.get('category') and q.get('core_concepts'):
                        print(f"   ✅ Question with unified fields found:")
                        print(f"      Category: {q.get('category')}")
                        print(f"      Core Concepts: {q.get('core_concepts')}")
                        print(f"      Solution Method: {q.get('solution_method')}")
                        print(f"      Quality Verified: {q.get('quality_verified')}")
                        
                        print(f"\n🎉 UNIFIED ENRICHMENT SUCCESS!")
                        return True
            
        else:
            print(f"❌ Upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_unified_enrichment()
    if success:
        print(f"\n🎯 UNIFIED ENRICHMENT TEST: SUCCESS!")
    else:
        print(f"\n❌ UNIFIED ENRICHMENT TEST: FAILED!")