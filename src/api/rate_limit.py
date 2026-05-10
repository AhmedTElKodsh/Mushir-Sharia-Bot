"""In-memory fixed-window rate limiting for the L2 API."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Tuple


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int

    def headers(self) -> Dict[str, str]:
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset_at),
        }


class InMemoryRateLimiter:
    """Simple fixed-window limiter with an injectable clock for tests."""

    def __init__(
        self,
        limit: int = 100,
        window_seconds: int = 3600,
        clock: Callable[[], float] | None = None,
    ):
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock or time.time
        self._buckets: Dict[str, Tuple[int, int]] = {}

    def check(self, key: str) -> RateLimitDecision:
        now = int(self.clock())
        count, reset_at = self._buckets.get(key, (0, now + self.window_seconds))

        if now >= reset_at:
            count = 0
            reset_at = now + self.window_seconds

        if count >= self.limit:
            return RateLimitDecision(
                allowed=False,
                limit=self.limit,
                remaining=0,
                reset_at=reset_at,
            )

        count += 1
        self._buckets[key] = (count, reset_at)
        return RateLimitDecision(
            allowed=True,
            limit=self.limit,
            remaining=max(self.limit - count, 0),
            reset_at=reset_at,
        )
