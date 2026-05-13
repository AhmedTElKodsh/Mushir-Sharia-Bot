"""Unit and integration tests for rate limiting behavior."""
import pytest
import time
from src.api.rate_limit import InMemoryRateLimiter, RateLimitDecision


@pytest.mark.unit
def test_rate_limiter_allows_requests_under_limit():
    limiter = InMemoryRateLimiter(limit=5, window_seconds=3600, clock=lambda: time.time())
    for i in range(5):
        decision = limiter.check("client-1")
        assert decision.allowed is True, f"Request {i+1}/5 should be allowed"
    decision = limiter.check("client-1")
    assert decision.allowed is False


@pytest.mark.unit
def test_rate_limiter_enforces_limit_after_threshold():
    limiter = InMemoryRateLimiter(limit=3, window_seconds=3600, clock=lambda: time.time())
    limiter.check("client-1")
    limiter.check("client-1")
    limiter.check("client-1")
    decision = limiter.check("client-1")
    assert decision.allowed is False
    assert decision.remaining == 0


@pytest.mark.unit
def test_rate_limiter_per_client_isolation():
    limiter = InMemoryRateLimiter(limit=2, window_seconds=3600, clock=lambda: time.time())
    limiter.check("client-1")
    limiter.check("client-1")
    decision = limiter.check("client-2")
    assert decision.allowed is True


@pytest.mark.unit
def test_rate_limiter_window_resets():
    t = [1000.0]

    def clock():
        return t[0]

    limiter = InMemoryRateLimiter(limit=2, window_seconds=10, clock=clock)
    limiter.check("client-1")
    limiter.check("client-1")
    assert limiter.check("client-1").allowed is False
    t[0] = 1011.0
    assert limiter.check("client-1").allowed is True


@pytest.mark.unit
def test_rate_limit_decision_headers():
    decision = RateLimitDecision(allowed=True, limit=100, remaining=50, reset_at=1234567890)
    headers = decision.headers()
    assert headers["X-RateLimit-Limit"] == "100"
    assert headers["X-RateLimit-Remaining"] == "50"
    assert headers["X-RateLimit-Reset"] == "1234567890"


@pytest.mark.unit
def test_rate_limit_decision_denied_has_zero_remaining():
    decision = RateLimitDecision(allowed=False, limit=10, remaining=0, reset_at=1234567890)
    headers = decision.headers()
    assert headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.unit
def test_rate_limiter_rejects_invalid_limit():
    with pytest.raises(ValueError, match="limit must be at least 1"):
        InMemoryRateLimiter(limit=0)


@pytest.mark.unit
def test_rate_limiter_rejects_invalid_window():
    with pytest.raises(ValueError, match="window_seconds must be at least 1"):
        InMemoryRateLimiter(limit=1, window_seconds=0)


@pytest.mark.unit
def test_rate_limiter_remaining_decrements_correctly():
    limiter = InMemoryRateLimiter(limit=3, window_seconds=3600, clock=lambda: time.time())
    d1 = limiter.check("client")
    assert d1.remaining == 2
    d2 = limiter.check("client")
    assert d2.remaining == 1
    d3 = limiter.check("client")
    assert d3.remaining == 0
    d4 = limiter.check("client")
    assert d4.remaining == 0
    assert d4.allowed is False


@pytest.mark.unit
def test_rate_limiter_reset_at_is_future_window():
    t = [1000.0]

    def clock():
        return t[0]

    limiter = InMemoryRateLimiter(limit=10, window_seconds=3600, clock=clock)
    decision = limiter.check("client")
    assert decision.reset_at == 4600  # 1000 + 3600