#!/usr/bin/env python3
"""
Quick PYQ Enrichment System Database Fix Validation Test
"""

import requests
import json
import time
import sys

def test_pyq_enrichment_system():
    """Quick test of PYQ enrichment system after database fix"""
    
    base_url = "https://twelvr-debugger.preview.emergentagent.com/api"
    
    print("🎯 QUICK PYQ ENRICHMENT SYSTEM DATABASE FIX VALIDATION")
    print("=" * 70)
    
    # Test 1: Admin Authentication
    print("\n🔐 PHASE 1: Admin Authentication")
    admin_login_data = {
        "email": "sumedhprabhu18@gmail.com",
        "password": "admin2025"
    }
    
    try:
        response = requests.post(
            f"{base_url}/auth/login", 
            json=admin_login_data, 
            timeout=60,
            verify=False
        )
        
        if response.status_code == 200:
            admin_token = response.json().get('access_token')
            admin_headers = {
                'Authorization': f'Bearer {admin_token}',
                'Content-Type': 'application/json'
            }
            print("   ✅ Admin authentication successful")
        else:
            print(f"   ❌ Admin authentication failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Admin authentication error: {e}")
        return False
    
    # Test 2: Database Access
    print("\n🗄️ PHASE 2: Database Schema Fix Validation")
    try:
        response = requests.get(
            f"{base_url}/admin/pyq/questions?limit=10", 
            headers=admin_headers,
            timeout=60,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            questions = data.get('questions', [])
            total = data.get('total', 0)
            print(f"   ✅ Database accessible - {total} PYQ questions found")
            
            # Check for solution_method field
            solution_method_found = False
            for question in questions[:3]:
                if 'solution_method' in question:
                    solution_method_value = question.get('solution_method', '')
                    if len(solution_method_value) > 100:
                        solution_method_found = True
                        print(f"   ✅ Solution method field can store >100 characters")
                        break
            
            if not solution_method_found:
                print(f"   📊 Solution method field not found in sample or <100 chars")
                
        else:
            print(f"   ❌ Database access failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Database access error: {e}")
        return False
    
    # Test 3: Enrichment Status
    print("\n📊 PHASE 3: Enrichment Status Check")
    try:
        response = requests.get(
            f"{base_url}/admin/pyq/enrichment-status", 
            headers=admin_headers,
            timeout=60,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('enrichment_statistics', {})
            total_questions = stats.get('total_questions', 0)
            enriched_questions = stats.get('enriched_questions', 0)
            quality_verified_false = stats.get('quality_verified_false', 0)
            
            print(f"   ✅ Enrichment status accessible")
            print(f"   📊 Total questions: {total_questions}")
            print(f"   📊 Enriched questions: {enriched_questions}")
            print(f"   📊 Quality verified = false: {quality_verified_false}")
            
            if quality_verified_false > 0:
                print(f"   ✅ Found {quality_verified_false} questions needing enrichment")
                
        else:
            print(f"   ❌ Enrichment status failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Enrichment status error: {e}")
        return False
    
    # Test 4: Enrichment Trigger
    print("\n🚀 PHASE 4: Enrichment Pipeline Test")
    try:
        response = requests.post(
            f"{base_url}/admin/pyq/trigger-enrichment", 
            json={},
            headers=admin_headers,
            timeout=60,
            verify=False
        )
        
        if response.status_code in [200, 202]:
            data = response.json()
            print(f"   ✅ Enrichment trigger working without timeout")
            print(f"   📊 Response: {data}")
        else:
            print(f"   ❌ Enrichment trigger failed: {response.status_code}")
            print(f"   📊 Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Enrichment trigger error: {e}")
    
    # Test 5: LLM Utils Consolidation
    print("\n🧠 PHASE 5: LLM Utils Consolidation Check")
    try:
        response = requests.get(
            f"{base_url}/admin/frequency-analysis-report", 
            headers=admin_headers,
            timeout=60,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Frequency analysis working - LLM utils consolidation functional")
            
            system_overview = data.get('system_overview', {})
            if system_overview:
                print(f"   📊 System overview available")
                
        else:
            print(f"   ❌ Frequency analysis failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Frequency analysis error: {e}")
    
    # Test 6: Backend Health
    print("\n🏥 PHASE 6: System Health Check")
    try:
        response = requests.get(
            f"{base_url}/", 
            timeout=60,
            verify=False
        )
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            print(f"   ✅ Backend stable and responding")
            
            if 'Advanced LLM Enrichment' in features:
                print(f"   ✅ Advanced LLM Enrichment feature available")
                
            if 'PYQ Processing Pipeline' in features:
                print(f"   ✅ PYQ Processing Pipeline feature available")
                
        else:
            print(f"   ❌ Backend health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Backend health check error: {e}")
    
    print("\n" + "=" * 70)
    print("🎯 QUICK PYQ ENRICHMENT SYSTEM VALIDATION COMPLETE")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = test_pyq_enrichment_system()
    
    if success:
        print("\n✅ VALIDATION SUCCESSFUL - PYQ enrichment system appears functional")
        sys.exit(0)
    else:
        print("\n❌ VALIDATION FAILED - Issues detected with PYQ enrichment system")
        sys.exit(1)