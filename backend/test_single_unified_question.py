#!/usr/bin/env python3
"""
Test Single Unified Question
"""

import requests
import io
import time

def test_single_unified_question():
    """
    Test single question with unified enrichment
    """
    try:
        print("🎯 TESTING SINGLE UNIFIED QUESTION")
        print("=" * 60)
        
        # Login
        login_response = requests.post("http://localhost:8001/api/auth/login", json={
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Admin authentication successful")
        
        # Simple test question
        csv_content = """stem,answer
What is 6 x 7?,42"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        files = {'file': ('single_test.csv', csv_file, 'text/csv')}
        
        print("\n📋 Uploading single test question...")
        
        upload_response = requests.post(
            "http://localhost:8001/api/admin/upload-questions-csv",
            files=files,
            headers=headers,
            timeout=180
        )
        
        print(f"📊 Upload status: {upload_response.status_code}")
        
        if upload_response.status_code == 200:
            response_data = upload_response.json()
            stats = response_data.get("statistics", {})
            
            print(f"✅ Questions created: {stats.get('questions_created', 0)}")
            print(f"✅ Questions activated: {stats.get('questions_activated', 0)}")
            
            # Check enrichment results
            enrichment_results = response_data.get("enrichment_results", [])
            if enrichment_results:
                result = enrichment_results[0]
                print(f"\n🧠 ENRICHMENT RESULT:")
                print(f"   Success: {result.get('enrichment_success')}")
                
                if result.get('llm_fields'):
                    fields = result['llm_fields']
                    print(f"   📊 LLM Fields Generated:")
                    
                    for field_name, field_value in fields.items():
                        print(f"      {field_name}: {field_value}")
                    
                    # Count unified fields
                    unified_field_count = len([f for f in fields.keys() if f in [
                        'category', 'right_answer', 'core_concepts', 'solution_method', 
                        'quality_verified', 'difficulty_band', 'concept_extraction_status'
                    ]])
                    
                    print(f"\n   🎯 Unified fields generated: {unified_field_count}/7")
                    
                    if unified_field_count >= 6:
                        print(f"   ✅ UNIFIED ENRICHMENT SUCCESS!")
                        return True
                    else:
                        print(f"   ⚠️ Missing some unified fields")
        
        print(f"❌ Test failed or incomplete")
        return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_single_unified_question()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")