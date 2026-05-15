"""Cache adapters for L4 response and retrieval caching."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, Optional


class CacheStore:
    def get_json(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set_json(self, namespace: str, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError

    @staticmethod
    def stable_key(value: str) -> str:
        return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


class InMemoryCacheStore(CacheStore):
    MAX_ENTRIES = 10000
    EVICT_BATCH = 500

    def __init__(self):
        self._values: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get_json(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        record = self._values.get(self._cache_key(namespace, key))
        if not record:
            return None
        expires_at, value = record
        if expires_at <= time.time():
            self._values.pop(self._cache_key(namespace, key), None)
            return None
        return value

    def set_json(self, namespace: str, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        full_key = self._cache_key(namespace, key)
        with self._lock:
            if len(self._values) >= self.MAX_ENTRIES and full_key not in self._values:
                self._evict()
            self._values[full_key] = (time.time() + ttl_seconds, value)

    def _evict(self) -> None:
        """Evict expired entries or a single random entry — amortized O(1)."""
        now = time.time()
        expired = [k for k, (exp, _) in self._values.items() if exp <= now]
        if expired:
            for k in expired[:self.EVICT_BATCH]:
                self._values.pop(k, None)
        else:
            import random
            victim = random.choice(list(self._values.keys()))
            self._values.pop(victim, None)

    @staticmethod
    def _cache_key(namespace: str, key: str) -> str:
        return f"{namespace}:{key}"


class RedisCacheStore(CacheStore):
    def __init__(self, redis_url: Optional[str] = None):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is required when CACHE_STORE_TYPE=redis") from exc
        self.client = redis.Redis.from_url(
            redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_timeout=float(os.getenv("REDIS_TIMEOUT_SECONDS", "2")),
        )
        self.client.ping()

    def get_json(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        raw = self.client.get(self._cache_key(namespace, key))
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def set_json(self, namespace: str, key: str, value: Dict[str, Any], ttl_seconds: int) -> None:
        self.client.setex(self._cache_key(namespace, key), ttl_seconds, json.dumps(value))

    @staticmethod
    def _cache_key(namespace: str, key: str) -> str:
        return f"mushir:cache:{namespace}:{key}"
