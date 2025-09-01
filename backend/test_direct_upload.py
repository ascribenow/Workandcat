#!/usr/bin/env python3
"""
Test Direct Upload to Server
"""

import requests
import io

def test_direct_upload():
    """
    Test direct upload to running server
    """
    try:
        # Login first
        login_data = {
            "email": "sumedhprabhu18@gmail.com",
            "password": "admin2025"
        }
        
        print("🔐 Logging in...")
        login_response = requests.post("http://localhost:8001/api/auth/login", json=login_data)
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("✅ Login successful")
        
        # Create simple CSV
        csv_content = """stem,answer
What is 2+2?,4"""
        
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        files = {'file': ('test.csv', csv_file, 'text/csv')}
        
        print("📋 Uploading CSV...")
        
        # Upload CSV
        upload_response = requests.post(
            "http://localhost:8001/api/admin/upload-questions-csv",
            files=files,
            headers=headers,
            timeout=120
        )
        
        print(f"📊 Upload response status: {upload_response.status_code}")
        print(f"📊 Upload response: {upload_response.text[:500]}...")
        
        if upload_response.status_code == 200:
            response_data = upload_response.json()
            print("✅ Upload successful!")
            
            # Check enrichment results
            enrichment_results = response_data.get("enrichment_results", [])
            if enrichment_results:
                result = enrichment_results[0]
                print(f"📊 First question enrichment:")
                print(f"   Success: {result.get('enrichment_success')}")
                if result.get('llm_fields'):
                    fields = result['llm_fields']
                    print(f"   Category: {fields.get('category')}")
                    print(f"   Difficulty: {fields.get('difficulty_level')}")
                    print(f"   Right Answer: {fields.get('right_answer')}")
                    
                    if fields.get('category') and fields.get('category') != 'General':
                        print("✅ Real LLM content detected!")
                        return True
                    else:
                        print("⚠️ Fallback content detected")
                        return False
            
        return upload_response.status_code == 200
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_upload()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")