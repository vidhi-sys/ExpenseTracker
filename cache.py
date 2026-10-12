"""
SpendSense / Expense Tracker - Redis Caching Module
Supports production Redis (Upstash/Local) with automatic in-memory fallback.
"""

import json
import os

try:
    import redis
except ImportError:
    redis = None

class RedisCache:
    def __init__(self, host="127.0.0.1", port=6379, password=None, url=None):
        self.client = None
        self.is_connected = False
        self._local_fallback = {}

        # Allow REDIS_URL from environment if deployed (e.g., Upstash Redis)
        redis_url = url or os.environ.get("REDIS_URL")

        if redis is not None:
            try:
                if redis_url:
                    self.client = redis.from_url(redis_url, socket_timeout=1)
                else:
                    self.client = redis.Redis(
                        host=host,
                        port=port,
                        password=password,
                        socket_timeout=1,
                        decode_responses=True
                    )
                # Quick ping to test availability
                self.client.ping()
                self.is_connected = True
            except Exception:
                # Redis not running locally or unreachable
                self.client = None
                self.is_connected = False

    def get(self, key):
        if self.is_connected and self.client:
            try:
                val = self.client.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass
        return self._local_fallback.get(key)

    def set(self, key, value, ttl_seconds=300):
        if self.is_connected and self.client:
            try:
                self.client.setex(key, ttl_seconds, json.dumps(value))
                return True
            except Exception:
                pass
        self._local_fallback[key] = value
        return True

    def clear(self):
        if self.is_connected and self.client:
            try:
                self.client.flushdb()
            except Exception:
                pass
        self._local_fallback.clear()

# Global cache instance
cache = RedisCache()
