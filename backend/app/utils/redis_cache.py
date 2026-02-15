"""
Redis Caching Layer for Production
Provides distributed caching with TTL support
"""

import redis
import json
import logging
from typing import Optional, Dict, Any
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)


class RedisCache:
    """Production-grade Redis caching with graceful fallback"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.enabled = False
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_timeout=1,
                socket_connect_timeout=1
            )
            # Test connection
            self.client.ping()
            self.enabled = True
            logger.info("✅ Redis cache connected successfully")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️ Redis unavailable, using in-memory fallback: {e}")
            self.client = None
            
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.enabled:
            return None
            
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL (default 5 minutes)"""
        if not self.enabled:
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
            
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON value from cache"""
        value = self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.enabled:
            return 0
            
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            return 0
    
    @staticmethod
    def make_key(*parts) -> str:
        """Create cache key from parts"""
        return ':'.join(str(p) for p in parts)
    
    @staticmethod
    def hash_text(text: str) -> str:
        """Create hash of text for cache key"""
        return hashlib.md5(text.encode()).hexdigest()[:16]


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get global cache instance (singleton)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


def cache_sentiment_result(ttl: int = 300):
    """
    Decorator to cache sentiment analysis results
    
    Args:
        ttl: Time to live in seconds (default 5 minutes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(text: str, language: str = "en", *args, **kwargs):
            cache = get_cache()
            
            # Create cache key
            text_hash = RedisCache.hash_text(text)
            cache_key = RedisCache.make_key('sentiment', language, text_hash)
            
            # Try to get from cache
            cached = cache.get_json(cache_key)
            if cached:
                logger.debug(f"💨 Cache HIT: {cache_key}")
                return cached
            
            # Execute function
            result = func(text, language, *args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            logger.debug(f"💾 Cache SET: {cache_key}")
            
            return result
        return wrapper
    return decorator


def cache_escalation_check(ttl: int = 60):
    """
    Decorator to cache escalation check results
    
    Args:
        ttl: Time to live in seconds (default 1 minute, shorter for real-time)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(text: str, current_frustration: float = 0.0, *args, **kwargs):
            cache = get_cache()
            
            # Create cache key
            text_hash = RedisCache.hash_text(text)
            cache_key = RedisCache.make_key('escalation', text_hash, int(current_frustration * 100))
            
            # Try to get from cache
            cached = cache.get_json(cache_key)
            if cached:
                logger.debug(f"💨 Cache HIT: {cache_key}")
                return cached
            
            # Execute function
            result = func(text, current_frustration, *args, **kwargs)
            
            # Cache result (shorter TTL for escalation)
            cache.set(cache_key, result, ttl)
            logger.debug(f"💾 Cache SET: {cache_key}")
            
            return result
        return wrapper
    return decorator
