#!/usr/bin/env python3
"""
Test script to verify CORS headers from both backend and edge
"""

import requests
import json

def test_cors_preflight(url, origin="https://www.twelvr.com"):
    """Test CORS preflight request"""
    print(f"\n🔍 Testing CORS preflight for: {url}")
    print(f"📍 Origin: {origin}")
    
    try:
        response = requests.options(
            url,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization,Idempotency-Key,Content-Type"
            },
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers:")
        
        cors_headers = {}
        for header, value in response.headers.items():
            if header.lower().startswith('access-control'):
                cors_headers[header] = value
                print(f"   {header}: {value}")
        
        # Check specifically for Idempotency-Key
        allow_headers = cors_headers.get('Access-Control-Allow-Headers', '')
        if 'Idempotency-Key' in allow_headers:
            print("✅ Idempotency-Key is ALLOWED")
        else:
            print("❌ Idempotency-Key is BLOCKED")
            print(f"   Allowed headers: {allow_headers}")
        
        return cors_headers
        
    except Exception as e:
        print(f"❌ Error testing CORS: {str(e)}")
        return None

def main():
    print("🚀 CORS Header Analysis")
    print("=" * 50)
    
    # Test direct backend
    backend_url = "https://adaptive-quant.emergent.host/api/adapt/plan-next"
    backend_cors = test_cors_preflight(backend_url)
    
    # Test through production edge (if accessible)
    production_url = "https://www.twelvr.com/api/adapt/plan-next"
    production_cors = test_cors_preflight(production_url)
    
    print("\n📊 COMPARISON RESULTS:")
    print("=" * 50)
    
    if backend_cors and production_cors:
        backend_headers = backend_cors.get('Access-Control-Allow-Headers', '')
        production_headers = production_cors.get('Access-Control-Allow-Headers', '')
        
        print(f"Backend Headers:    {backend_headers}")
        print(f"Production Headers: {production_headers}")
        
        if backend_headers != production_headers:
            print("⚠️  HEADERS DIFFER - Edge is overriding backend CORS!")
        else:
            print("✅ Headers match - No override detected")
    
    print("\n🔚 Analysis complete")

if __name__ == "__main__":
    main()