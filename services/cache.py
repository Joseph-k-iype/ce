"""
Cache Service
=============
In-memory caching with TTL support for frequently accessed data.
"""

import logging
import time
from typing import Optional, Any, Dict, Callable, TypeVar
from functools import wraps
from collections import OrderedDict
from threading import Lock

from config.settings import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheEntry:
    """Single cache entry with expiration tracking"""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.expires_at = time.time() + ttl_seconds
        self.created_at = time.time()
        self.access_count = 0

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def access(self) -> Any:
        self.access_count += 1
        return self.value


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    Used for caching query results, dropdown values, etc.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats['misses'] += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats['hits'] += 1
            return entry.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache"""
        if ttl is None:
            ttl = self._default_ttl

        with self._lock:
            # Remove if exists to update position
            if key in self._cache:
                del self._cache[key]

            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._stats['evictions'] += 1

            self._cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """Clear all cache entries, return count of cleared entries"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], T],
        ttl: Optional[int] = None
    ) -> T:
        """Get from cache or compute and cache the value"""
        value = self.get(key)
        if value is not None:
            return value

        # Compute value outside lock
        value = factory()

        # Cache the computed value
        self.set(key, value, ttl)
        return value

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (
                self._stats['hits'] / total_requests
                if total_requests > 0
                else 0.0
            )
            return {
                **self._stats,
                'size': len(self._cache),
                'max_size': self._max_size,
                'hit_rate': hit_rate
            }

    def cleanup_expired(self) -> int:
        """Remove all expired entries, return count removed"""
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            self._stats['expirations'] += len(expired_keys)
            return len(expired_keys)


class CacheService:
    """
    Cache service providing multiple cache namespaces.
    """

    _instance: Optional['CacheService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._enabled = settings.cache.enable_cache
        self._default_ttl = settings.cache.cache_ttl_seconds
        self._max_size = settings.cache.max_cache_size

        # Separate caches for different data types
        self._caches: Dict[str, LRUCache] = {
            'queries': LRUCache(max_size=self._max_size, default_ttl=self._default_ttl),
            'metadata': LRUCache(max_size=500, default_ttl=600),  # Longer TTL for metadata
            'rules': LRUCache(max_size=100, default_ttl=3600),  # Even longer for rules
        }

        self._initialized = True
        logger.info(f"Cache service initialized (enabled={self._enabled})")

    def get_cache(self, namespace: str = 'queries') -> LRUCache:
        """Get a cache by namespace"""
        if namespace not in self._caches:
            self._caches[namespace] = LRUCache(
                max_size=self._max_size,
                default_ttl=self._default_ttl
            )
        return self._caches[namespace]

    def get(self, key: str, namespace: str = 'queries') -> Optional[Any]:
        """Get value from cache"""
        if not self._enabled:
            return None
        return self.get_cache(namespace).get(key)

    def set(
        self,
        key: str,
        value: Any,
        namespace: str = 'queries',
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache"""
        if not self._enabled:
            return
        self.get_cache(namespace).set(key, value, ttl)

    def delete(self, key: str, namespace: str = 'queries') -> bool:
        """Delete key from cache"""
        return self.get_cache(namespace).delete(key)

    def clear(self, namespace: Optional[str] = None) -> int:
        """Clear cache(s)"""
        if namespace:
            return self.get_cache(namespace).clear()

        total = 0
        for cache in self._caches.values():
            total += cache.clear()
        return total

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all caches"""
        return {
            name: cache.stats
            for name, cache in self._caches.items()
        }

    def cleanup_all(self) -> int:
        """Cleanup expired entries in all caches"""
        total = 0
        for cache in self._caches.values():
            total += cache.cleanup_expired()
        return total


# Decorator for caching function results
def cached(
    namespace: str = 'queries',
    ttl: Optional[int] = None,
    key_prefix: str = ''
):
    """
    Decorator to cache function results.

    Usage:
        @cached(namespace='metadata', ttl=600)
        def get_countries():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache = get_cache_service()

            # Build cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ':'.join(key_parts)

            # Try to get from cache
            result = cache.get(cache_key, namespace)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, namespace, ttl)
            return result

        return wrapper
    return decorator


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
