#!/usr/bin/env python3
"""
Direct OpenAI API Test
"""

import os
import requests
import json

def test_openai_api_direct():
    """
    Test OpenAI API directly with curl-like approach
    """
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"API Key loaded: {api_key[:20]}..." if api_key else "No API key found")
    
    if not api_key:
        return False
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Say 'Hello' if you can hear me."}
        ],
        "max_tokens": 10
    }
    
    try:
        print("Testing direct API call to OpenAI...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print(f"✅ OpenAI API working: {message}")
            return True
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_api_direct()
    print(f"Result: {'SUCCESS' if success else 'FAILED'}")