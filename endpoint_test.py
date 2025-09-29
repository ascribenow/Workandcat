#!/usr/bin/env python3

import requests
import json
import uuid
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EndpointTester:
    def __init__(self, base_url="https://llm-prompt-repair.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.auth_headers = None
        self.user_id = None
        
    def authenticate(self):
        """Authenticate with the specific user credentials"""
        print("🔐 AUTHENTICATING...")
        
        auth_data = {
            "email": "sp@theskinmantra.com",
            "password": "student123"
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/auth/login", 
                json=auth_data, 
                timeout=30, 
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                self.user_id = data.get('user', {}).get('id')
                
                self.auth_headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                print(f"✅ Authentication successful")
                print(f"📊 User ID: {self.user_id}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def test_endpoint(self, method, endpoint, data=None, expected_status=None):
        """Test a specific endpoint"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.auth_headers, timeout=30, verify=False)
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.auth_headers, timeout=30, verify=False)
            else:
                print(f"❌ Unsupported method: {method}")
                return False
            
            print(f"📊 {method} {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"✅ Success: {type(response_data)} response")
                    if isinstance(response_data, dict):
                        keys = list(response_data.keys())[:5]  # Show first 5 keys
                        print(f"📋 Keys: {keys}")
                    elif isinstance(response_data, list):
                        print(f"📋 List length: {len(response_data)}")
                    return True
                except:
                    print(f"✅ Success: Non-JSON response")
                    return True
            else:
                try:
                    error_data = response.json()
                    print(f"❌ Error: {error_data}")
                except:
                    print(f"❌ Error: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
    
    def run_endpoint_discovery(self):
        """Test various endpoints to understand the API structure"""
        print("🔍 ENDPOINT DISCOVERY")
        print("=" * 60)
        
        if not self.authenticate():
            return False
        
        # Test basic endpoints
        endpoints_to_test = [
            ("GET", "health"),
            ("GET", "dashboard/simple-taxonomy"),
            ("GET", "questions?limit=1"),
            ("GET", f"sessions/last-completed-id?user_id={self.user_id}"),
            ("GET", f"session-progress/current/{self.user_id}"),
        ]
        
        print("\n📋 TESTING BASIC ENDPOINTS:")
        for method, endpoint in endpoints_to_test:
            self.test_endpoint(method, endpoint)
        
        # Test session-related endpoints
        print("\n📋 TESTING SESSION ENDPOINTS:")
        session_endpoints = [
            ("POST", "sessions/start", {"user_id": self.user_id}),
            ("POST", "adapt/plan-next", {
                "user_id": self.user_id,
                "last_session_id": "S0",
                "next_session_id": str(uuid.uuid4())
            }),
        ]
        
        for method, endpoint, data in session_endpoints:
            self.test_endpoint(method, endpoint, data)
        
        # Test Blueprint sessions
        print("\n📋 TESTING BLUEPRINT SESSION ENDPOINTS:")
        blueprint_endpoints = [
            ("GET", "blueprint/health"),
            ("POST", "blueprint/session/start", {"user_id": self.user_id}),
        ]
        
        for method, endpoint, *data in blueprint_endpoints:
            test_data = data[0] if data else None
            self.test_endpoint(method, endpoint, test_data)

def main():
    tester = EndpointTester()
    tester.run_endpoint_discovery()

if __name__ == "__main__":
    main()