#!/usr/bin/env python3
"""
Focused Phase 3B Test - Test the critical fixes
"""

import requests
import json

def test_critical_fixes():
    """Test the critical fixes for Phase 3B"""
    
    base_url = "https://learning-tutor.preview.emergentagent.com/api"
    
    print("🎯 FOCUSED PHASE 3B TEST - CRITICAL FIXES VALIDATION")
    print("=" * 60)
    
    # Step 1: Admin Authentication
    print("\n🔐 Step 1: Admin Authentication")
    admin_login_data = {
        "email": "sumedhprabhu18@gmail.com",
        "password": "admin2025"
    }
    
    try:
        response = requests.post(f"{base_url}/auth/login", json=admin_login_data, timeout=30, verify=False)
        if response.status_code == 200:
            admin_token = response.json()['access_token']
            admin_headers = {
                'Authorization': f'Bearer {admin_token}',
                'Content-Type': 'application/json'
            }
            print("✅ Admin authentication successful")
        else:
            print(f"❌ Admin authentication failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Admin authentication error: {e}")
        return False
    
    # Step 2: Test Frequency Analysis Report (was failing)
    print("\n📊 Step 2: Test Frequency Analysis Report")
    try:
        response = requests.get(f"{base_url}/admin/frequency-analysis-report", headers=admin_headers, timeout=30, verify=False)
        if response.status_code == 200:
            print("✅ Frequency analysis report working")
        else:
            print(f"❌ Frequency analysis report failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Frequency analysis report error: {e}")
    
    # Step 3: Test Admin Questions Endpoint (was missing)
    print("\n📋 Step 3: Test Admin Questions Endpoint")
    try:
        response = requests.get(f"{base_url}/admin/questions?limit=5", headers=admin_headers, timeout=30, verify=False)
        if response.status_code == 200:
            data = response.json()
            questions = data.get('questions', [])
            print(f"✅ Admin questions endpoint working - {len(questions)} questions retrieved")
            
            # Check for snap_read field
            if questions and 'snap_read' in questions[0]:
                print("✅ snap_read field present in questions")
            else:
                print("⚠️ snap_read field missing in questions")
                
        else:
            print(f"❌ Admin questions endpoint failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Admin questions endpoint error: {e}")
    
    # Step 4: Test CSV Upload
    print("\n📄 Step 4: Test CSV Upload")
    test_csv_content = """stem,answer,solution_approach,detailed_solution,principle_to_remember,snap_read,image_url,mcq_options
"What is 5 + 3?","8","Add the numbers","5 + 3 = 8","Addition is commutative","Quick mental math","","A) 6, B) 7, C) 8, D) 9"
"""
    
    try:
        files = {'file': ('test_questions.csv', test_csv_content, 'text/csv')}
        headers_for_upload = {'Authorization': f'Bearer {admin_token}'}
        
        response = requests.post(f"{base_url}/admin/upload-questions-csv", files=files, headers=headers_for_upload, timeout=30, verify=False)
        
        if response.status_code in [200, 201]:
            data = response.json()
            print("✅ CSV upload working")
            print(f"   📊 Response: {data.get('message', 'No message')}")
            
            # Check for enrichment triggering
            if 'enrichment' in str(data).lower():
                print("✅ Enrichment triggering detected")
            else:
                print("⚠️ Enrichment triggering not clearly detected")
                
        else:
            print(f"❌ CSV upload failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ CSV upload error: {e}")
    
    # Step 5: Test Enrich Checker
    print("\n🧠 Step 5: Test Enrich Checker")
    try:
        response = requests.post(f"{base_url}/admin/enrich-checker/regular-questions", 
                               json={"limit": 2}, headers=admin_headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Enrich checker working")
            print(f"   📊 Response: {data.get('success', False)}")
        else:
            print(f"❌ Enrich checker failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Enrich checker error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 FOCUSED PHASE 3B TEST COMPLETED")
    print("Check the results above to see which critical issues are resolved")
    print("=" * 60)

if __name__ == "__main__":
    test_critical_fixes()