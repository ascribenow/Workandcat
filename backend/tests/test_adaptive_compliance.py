"""
Adaptive System Integration Tests
Validates v1.1 handoff compliance
"""

import pytest
import requests
import json
from typing import Dict, Any

class TestAdaptiveSystemCompliance:
    """Test suite for v1.1 handoff compliance validation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.base_url = "http://localhost:8001/api"
        self.test_user = "test_user_adaptive"
        self.auth_headers = {
            "Authorization": "Bearer test_jwt_token",  # Replace with actual token
            "Content-Type": "application/json"
        }
    
    def test_plan_next_idempotent_and_shape(self):
        """Test idempotency and 12/3-6-3 pack shape validation"""
        user_id = self.test_user
        last_session = "S42"
        next_session = "S43"
        idem_key = f"{user_id}:{last_session}:{next_session}"
        
        payload = {
            "user_id": user_id,
            "last_session_id": last_session,
            "next_session_id": next_session
        }
        headers = {**self.auth_headers, "Idempotency-Key": idem_key}
        
        # First request
        r1 = requests.post(f"{self.base_url}/adapt/plan-next", 
                          json=payload, headers=headers)
        
        # Second request with same idempotency key
        r2 = requests.post(f"{self.base_url}/adapt/plan-next",
                          json=payload, headers=headers)
        
        assert r1.status_code == 200, f"First request failed: {r1.text}"
        assert r2.status_code == 200, f"Second request failed: {r2.text}"
        
        # Verify idempotency - both responses should be identical
        assert r1.json() == r2.json(), "Responses not identical - idempotency violated"
        
        # Get pack and verify shape
        pack_response = requests.get(f"{self.base_url}/adapt/pack",
                                   params={"user_id": user_id, "session_id": next_session},
                                   headers=self.auth_headers)
        
        assert pack_response.status_code == 200, f"Pack request failed: {pack_response.text}"
        
        pack_data = pack_response.json()
        pack = pack_data.get("pack", [])
        
        # Validate pack shape
        assert len(pack) == 12, f"Expected 12 questions, got {len(pack)}"
        
        easy_count = sum(1 for p in pack if p.get("bucket") == "Easy")
        medium_count = sum(1 for p in pack if p.get("bucket") == "Medium")  
        hard_count = sum(1 for p in pack if p.get("bucket") == "Hard")
        
        assert easy_count == 3, f"Expected 3 Easy questions, got {easy_count}"
        assert medium_count == 6, f"Expected 6 Medium questions, got {medium_count}"
        assert hard_count == 3, f"Expected 3 Hard questions, got {hard_count}"
    
    def test_forbidden_relaxations_never_relaxed(self):
        """Test that forbidden relaxations never appear in constraint reports"""
        user_id = self.test_user
        last_session = "S1"
        next_session = "S2"
        idem_key = f"{user_id}:{last_session}:{next_session}"
        
        payload = {
            "user_id": user_id,
            "last_session_id": last_session,
            "next_session_id": next_session
        }
        headers = {**self.auth_headers, "Idempotency-Key": idem_key}
        
        response = requests.post(f"{self.base_url}/adapt/plan-next",
                               json=payload, headers=headers)
        
        assert response.status_code == 200, f"Plan-next request failed: {response.text}"
        
        plan_data = response.json()
        constraint_report = plan_data.get("constraint_report", {})
        relaxed_constraints = constraint_report.get("relaxed", [])
        
        # Check that forbidden constraints never appear in relaxed list
        forbidden = {"band_shape", "pyq_1.0", "pyq_1.5"}
        relaxed_names = {r.get("name") for r in relaxed_constraints if isinstance(r, dict)}
        
        illegal = relaxed_names & forbidden
        assert not illegal, f"Forbidden relaxations found: {illegal}"
        
        # Verify required constraints are met
        met_constraints = set(constraint_report.get("met", []))
        required_met = {"band_shape", "pyq_1.0", "pyq_1.5"}
        
        missing_required = required_met - met_constraints
        assert not missing_required, f"Required constraints not met: {missing_required}"
    
    def test_idempotency_key_required(self):
        """Test that Idempotency-Key header is required"""
        payload = {
            "user_id": self.test_user,
            "last_session_id": "S1",
            "next_session_id": "S2"
        }
        
        # Request without idempotency key should fail
        response = requests.post(f"{self.base_url}/adapt/plan-next",
                               json=payload, headers=self.auth_headers)
        
        assert response.status_code == 400, f"Expected 400 for missing idempotency key, got {response.status_code}"
        
        error_data = response.json()
        assert error_data.get("detail", {}).get("code") == "IDEMPOTENCY_KEY_REQUIRED"
    
    def test_adaptive_gate_enforcement(self):
        """Test that adaptive gate properly blocks requests when disabled"""
        # This would need to be run with ADAPTIVE_GLOBAL=false or user without adaptive_enabled
        # For now, just verify the endpoints exist and are protected
        
        payload = {"user_id": "invalid_user", "last_session_id": "S1", "next_session_id": "S2"}
        headers = {"Content-Type": "application/json"}  # No auth header
        
        response = requests.post(f"{self.base_url}/adapt/plan-next",
                               json=payload, headers=headers)
        
        # Should get 401/403 for authentication/authorization issue
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}"


# Utility functions for testing
def generate_test_jwt(user_id: str) -> str:
    """Generate test JWT token for authenticated requests"""
    # This would integrate with your actual auth system
    pass

def setup_test_user(user_id: str, adaptive_enabled: bool = True):
    """Setup test user in database"""
    # This would create a test user with specified adaptive settings
    pass

if __name__ == "__main__":
    # Run basic smoke tests
    test_suite = TestAdaptiveSystemCompliance()
    test_suite.setup_method()
    
    try:
        print("🧪 Running adaptive system compliance tests...")
        test_suite.test_idempotency_key_required()
        print("✅ Idempotency key requirement test passed")
        
        # Additional tests would need proper auth setup
        print("⚠️ Additional tests require authentication setup")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise