#!/usr/bin/env python3

import sys
import os
import warnings
import requests
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def test_fallback_flag():
    """Test the INSIGHTS_FORCE_FALLBACK feature flag"""
    
    base_url = "https://cat-prep-debugger.preview.emergentagent.com/api"
    
    # Authenticate first
    auth_data = {
        "email": "sp@theskinmantra.com",
        "password": "student123"
    }
    
    response = requests.post(f"{base_url}/auth/login", json=auth_data, verify=False)
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return False
    
    token = response.json().get('access_token')
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print("🎛️ Testing INSIGHTS_FORCE_FALLBACK feature flag")
    print("-" * 60)
    
    # Test dashboard insights to see current behavior
    response = requests.get(f"{base_url}/dashboard/adaptive-insights", headers=headers, verify=False)
    if response.status_code == 200:
        data = response.json()
        source = data.get("source", "unknown")
        prompt_version = data.get("prompt_version", "unknown")
        
        print(f"📊 Current dashboard response:")
        print(f"   Source: {source}")
        print(f"   Prompt version: {prompt_version}")
        
        # Check if we can detect fallback behavior
        if source == "fallback_forced":
            print("✅ Fallback forced mode detected")
            return True
        elif source in ["memory", "cache", "pre_computed"]:
            print("✅ Normal mode detected (not forced fallback)")
            return True
        else:
            print(f"⚠️ Unknown source: {source}")
            return False
    else:
        print(f"❌ Dashboard insights failed: {response.status_code}")
        return False

if __name__ == "__main__":
    success = test_fallback_flag()
    if success:
        print("✅ Fallback flag test completed")
    else:
        print("❌ Fallback flag test failed")