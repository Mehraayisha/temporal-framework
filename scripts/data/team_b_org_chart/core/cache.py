"""
Query Result Caching for Privacy Firewall
Simple TTL-based in-memory cache with LRU eviction
"""
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json


class TTLCache:
    """
    Time-To-Live cache with automatic expiration
    Thread-safe for single-process usage
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize TTL cache
        
        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
        """
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_times: Dict[str, float] = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        # Combine args and kwargs into a stable string
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if expired/missing
        """
        if key not in self._cache:
            self._misses += 1
            return None
            
        value, expiry_time = self._cache[key]
        
        # Check if expired
        if time.time() > expiry_time:
            # Remove expired entry
            del self._cache[key]
            del self._access_times[key]
            self._misses += 1
            return None
            
        # Update access time for LRU
        self._access_times[key] = time.time()
        self._hits += 1
        return value
        
    def set(self, key: str, value: Any, ttl_seconds: int):
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        # Check if we need to evict (LRU)
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._evict_lru()
            
        expiry_time = time.time() + ttl_seconds
        self._cache[key] = (value, expiry_time)
        self._access_times[key] = time.time()
        
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._access_times:
            return
            
        # Find least recently accessed key
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        
        # Remove it
        del self._cache[lru_key]
        del self._access_times[lru_key]
        
    def delete(self, key: str):
        """Delete specific key from cache"""
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]
            
    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()
        self._access_times.clear()
        self._hits = 0
        self._misses = 0
        
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2)
        }
        
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = []
        
        for key, (value, expiry_time) in self._cache.items():
            if current_time > expiry_time:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self._cache[key]
            del self._access_times[key]
            
        return len(expired_keys)


class PrivacyFirewallCache:
    """
    Specialized cache for Privacy Firewall with multiple TTL levels
    """
    
    # Cache TTL settings (seconds)
    EMPLOYEE_CONTEXT_TTL = 300  # 5 minutes
    POLICY_RESULT_TTL = 60      # 1 minute
    RELATIONSHIP_TTL = 180       # 3 minutes
    RESOURCE_ACCESS_TTL = 120    # 2 minutes
    
    def __init__(self, max_size: int = 2000):
        """Initialize privacy firewall cache"""
        self._cache = TTLCache(max_size=max_size)
        
    def get_employee_context(self, email: str) -> Optional[Dict]:
        """Get cached employee context"""
        key = f"employee_context:{email}"
        return self._cache.get(key)
        
    def set_employee_context(self, email: str, context: Dict):
        """Cache employee context"""
        key = f"employee_context:{email}"
        self._cache.set(key, context, self.EMPLOYEE_CONTEXT_TTL)
        
    def get_policy_result(
        self, 
        employee_id: str, 
        resource_id: str, 
        resource_type: str,
        classification: str
    ) -> Optional[bool]:
        """Get cached policy decision"""
        key = f"policy:{employee_id}:{resource_id}:{resource_type}:{classification}"
        return self._cache.get(key)
        
    def set_policy_result(
        self,
        employee_id: str,
        resource_id: str,
        resource_type: str,
        classification: str,
        result: bool
    ):
        """Cache policy decision"""
        key = f"policy:{employee_id}:{resource_id}:{resource_type}:{classification}"
        self._cache.set(key, result, self.POLICY_RESULT_TTL)
        
    def get_relationship(
        self,
        employee1_id: str,
        employee2_id: str,
        relationship_type: str
    ) -> Optional[bool]:
        """Get cached relationship check"""
        # Normalize order for bidirectional relationships
        ids = tuple(sorted([employee1_id, employee2_id]))
        key = f"relationship:{ids[0]}:{ids[1]}:{relationship_type}"
        return self._cache.get(key)
        
    def set_relationship(
        self,
        employee1_id: str,
        employee2_id: str,
        relationship_type: str,
        exists: bool
    ):
        """Cache relationship check result"""
        ids = tuple(sorted([employee1_id, employee2_id]))
        key = f"relationship:{ids[0]}:{ids[1]}:{relationship_type}"
        self._cache.set(key, exists, self.RELATIONSHIP_TTL)
        
    def invalidate_employee(self, email: str):
        """Invalidate all cache entries for an employee"""
        # This is a simplified version - in production you'd want
        # more sophisticated invalidation
        key = f"employee_context:{email}"
        self._cache.delete(key)
        
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        base_stats = self._cache.stats()
        
        # Return stats broken down by cache type
        return {
            "employee_context": {
                "size": base_stats["size"],
                "hits": base_stats["hits"],
                "misses": base_stats["misses"],
                "hit_rate": base_stats["hit_rate_percent"] / 100.0,  # Convert to 0-1 range
                "ttl_seconds": self.EMPLOYEE_CONTEXT_TTL
            },
            "policy_results": {
                "size": 0,  # Not separately tracked yet
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0,
                "ttl_seconds": self.POLICY_RESULT_TTL
            },
            "relationships": {
                "size": 0,  # Not separately tracked yet
                "hits": 0,
                "misses": 0,
                "hit_rate": 0.0,
                "ttl_seconds": self.RELATIONSHIP_TTL
            }
        }
        
    def cleanup(self) -> int:
        """Clean up expired entries"""
        return self._cache.cleanup_expired()


# Global cache instance
_firewall_cache: Optional[PrivacyFirewallCache] = None


def get_cache() -> PrivacyFirewallCache:
    """Get or create the global cache instance"""
    global _firewall_cache
    if _firewall_cache is None:
        _firewall_cache = PrivacyFirewallCache()
    return _firewall_cache


def clear_cache():
    """Clear the global cache"""
    global _firewall_cache
    if _firewall_cache:
        _firewall_cache.clear()
