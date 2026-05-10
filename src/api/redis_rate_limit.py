"""Redis fixed-window rate limiting for L3 multi-instance deployments."""
from __future__ import annotations

import os
import time
from typing import Callable, Optional

from src.api.rate_limit import RateLimitDecision


class RedisRateLimiter:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        limit: int = 100,
        window_seconds: int = 3600,
        clock: Callable[[], float] | None = None,
    ):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is required when RATE_LIMIT_STORE_TYPE=redis") from exc
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock or time.time
        self.client = redis.Redis.from_url(
            redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_timeout=float(os.getenv("REDIS_TIMEOUT_SECONDS", "2")),
        )
        self.client.ping()

    def check(self, key: str) -> RateLimitDecision:
        now = int(self.clock())
        window_start = now - (now % self.window_seconds)
        reset_at = window_start + self.window_seconds
        redis_key = f"mushir:rate:{key}:{window_start}"
        count = int(self.client.incr(redis_key))
        if count == 1:
            self.client.expire(redis_key, self.window_seconds)
        allowed = count <= self.limit
        return RateLimitDecision(
            allowed=allowed,
            limit=self.limit,
            remaining=max(self.limit - count, 0) if allowed else 0,
            reset_at=reset_at,
        )
