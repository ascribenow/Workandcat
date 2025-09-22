"""
Idempotency Service for Coverage System
Provides canonical session_id generation and duplicate request protection
"""

import time
import logging
from typing import Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

class IdempotencyService:
    """Simple in-memory idempotency cache (upgrade to Redis later if needed)"""
    
    def __init__(self, ttl_seconds=3600):  # 1 hour TTL
        self._cache: Dict[str, Dict] = {}
        self.ttl = ttl_seconds
    
    def get_or_create_session_id(self, idempotency_key: str, proposed_id: Optional[str] = None) -> str:
        """Get existing session_id for key or create new canonical one"""
        
        # Clean expired entries
        self._cleanup_expired()
        
        if idempotency_key in self._cache:
            cached_data = self._cache[idempotency_key]
            logger.info(f"Idempotency hit: {idempotency_key} → {cached_data['session_id'][:8]}...")
            return cached_data['session_id']
        
        # Create new canonical session_id
        session_id = proposed_id or f"cvg1_{int(time.time())}_{uuid4().hex[:8]}"
        
        self._cache[idempotency_key] = {
            'session_id': session_id,
            'created_at': time.time(),
            'proposed_id': proposed_id,
            'id_source': 'backend_generated' if not proposed_id else 'client_proposed'
        }
        
        logger.info(f"Idempotency miss: {idempotency_key} → created {session_id[:8]}...")
        return session_id
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._cache.items()
            if current_time - data['created_at'] > self.ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired idempotency entries")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring"""
        self._cleanup_expired()
        return {
            "total_entries": len(self._cache),
            "oldest_entry_age": min([
                time.time() - data['created_at'] 
                for data in self._cache.values()
            ]) if self._cache else 0
        }

# Global instance
idempotency_service = IdempotencyService()

# Test function
def test_idempotency_service():
    """Test idempotency service functionality"""
    service = IdempotencyService(ttl_seconds=60)  # 1 minute for testing
    
    # Test 1: New key creates new session_id
    key1 = "test_key_1"
    session_id_1 = service.get_or_create_session_id(key1)
    print(f"Test 1: Created {session_id_1}")
    
    # Test 2: Same key returns same session_id
    session_id_1_repeat = service.get_or_create_session_id(key1)
    assert session_id_1 == session_id_1_repeat
    print(f"Test 2: Idempotency working - {session_id_1_repeat}")
    
    # Test 3: Proposed ID accepted
    key2 = "test_key_2"
    proposed_id = "client_proposed_session_123"
    session_id_2 = service.get_or_create_session_id(key2, proposed_id)
    assert session_id_2 == proposed_id
    print(f"Test 3: Proposed ID accepted - {session_id_2}")
    
    # Test 4: Cache stats
    stats = service.get_cache_stats()
    print(f"Test 4: Cache stats - {stats}")
    
    print("✅ All idempotency tests passed")

if __name__ == "__main__":
    test_idempotency_service()