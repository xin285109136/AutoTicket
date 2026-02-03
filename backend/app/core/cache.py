import time
from typing import Any, Optional
import threading

class SimpleCache:
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                value, expire_at = self._store[key]
                if time.time() < expire_at:
                    return value
                else:
                    del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        with self._lock:
            expire_at = time.time() + ttl_seconds
            self._store[key] = (value, expire_at)

    def clear(self):
        with self._lock:
            self._store.clear()

# Global cache instance
cache = SimpleCache()
