"""
Sentiment Analysis Caching Layer
Reduces redundant BERT model calls
"""

import hashlib
import time
from typing import Dict, Optional
from functools import lru_cache


class SentimentCache:
    """In-memory cache for sentiment analysis results"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        """
        Initialize cache
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default: 5 minutes)
            max_size: Maximum number of cached entries
        """
        self.cache = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def _get_cache_key(self, text: str, language: str) -> str:
        """Generate cache key from text and language"""
        content = f"{text}:{language}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, language: str) -> Optional[Dict]:
        """Get cached sentiment result"""
        key = self._get_cache_key(text, language)
        
        if key in self.cache:
            entry = self.cache[key]
            # Check if expired
            if time.time() - entry['timestamp'] < self.ttl:
                self.hits += 1
                return entry['result']
            else:
                # Remove expired entry
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, text: str, language: str, result: Dict):
        """Cache sentiment result"""
        key = self._get_cache_key(text, language)
        
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'result': result,
            'timestamp': time.time()
        }
    
    def clear(self):
        """Clear all cache entries"""
        self.cache = {}
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'current_size': len(self.cache),
            'max_size': self.max_size,
            'ttl_seconds': self.ttl
        }


# Global cache instance
_sentiment_cache = SentimentCache(ttl_seconds=300, max_size=1000)


def get_sentiment_cache() -> SentimentCache:
    """Get the global sentiment cache instance"""
    return _sentiment_cache


def cached_sentiment_analysis(text: str, language: str, analyzer_func):
    """
    Wrapper for sentiment analysis with caching
    
    Args:
        text: Message text
        language: Language code
        analyzer_func: Function that performs sentiment analysis
    
    Returns:
        Sentiment analysis result (cached or fresh)
    """
    cache = get_sentiment_cache()
    
    # Try cache first
    cached_result = cache.get(text, language)
    if cached_result is not None:
        cached_result['cached'] = True
        return cached_result
    
    # Cache miss - perform analysis
    result = analyzer_func(text, language)
    
    # Cache the result
    cache.set(text, language, result)
    result['cached'] = False
    
    return result
