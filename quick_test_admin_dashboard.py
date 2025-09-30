#!/usr/bin/env python3
"""
Quick test of the admin dashboard endpoint
"""

import requests
import json

# Test configuration
BASE_URL = "https://adapt-engine.preview.emergentagent.com/api"

def test_admin_dashboard():
    print("🎯 QUICK PHASE 4 ADMIN DASHBOARD TEST")
    print("=" * 60)
    
    # Step 1: Authenticate as student (dashboard should work with any authenticated user)
    print("🔐 Step 1: Authentication")
    login_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data, verify=False)
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return False
    
    auth_data = response.json()
    token = auth_data.get('access_token')
    
    print(f"✅ Authentication successful")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: Test admin dashboard
    print("\n📊 Step 2: Testing admin dashboard")
    
    response = requests.get(f"{BASE_URL}/adapt/admin/dashboard", headers=headers, verify=False)
    
    print(f"📊 Response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"✅ Admin dashboard endpoint working!")
        print(f"📊 Response keys: {list(result.keys())}")
        
        # Check for expected dashboard data
        if result.get('statistics'):
            stats = result.get('statistics', {})
            print(f"📊 Statistics keys: {list(stats.keys())}")
            
            # Check for expected statistics
            expected_stats = ['pack_status', 'strategy_distribution', 'mode_distribution', 'recent_activity']
            found_stats = [stat for stat in expected_stats if stat in stats]
            
            print(f"📊 Found statistics: {found_stats}")
            print(f"✅ Dashboard monitoring data present!")
            return True
        else:
            print(f"⚠️ No statistics found in dashboard response")
            return False
    else:
        print(f"❌ Admin dashboard failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"📊 Error: {error_data}")
        except:
            print(f"📊 Error text: {response.text}")
        return False

if __name__ == "__main__":
    success = test_admin_dashboard()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'NEEDS ATTENTION'}")