import pytest
from fastapi.testclient import TestClient


class FakeClock:
    def __init__(self, now=1000):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class CountingService:
    def __init__(self):
        self.calls = 0

    def answer(self, query, session_id=None):
        from src.models.ruling import AnswerContract, ComplianceStatus

        self.calls += 1
        return AnswerContract(
            answer=f"answer for {query}",
            status=ComplianceStatus.INSUFFICIENT_DATA,
            citations=[],
            reasoning_summary="fake",
        )


@pytest.mark.api
def test_query_returns_429_after_limit_and_skips_service():
    from src.api.dependencies import get_application_service, get_rate_limiter
    from src.api.main import create_app
    from src.api.rate_limit import InMemoryRateLimiter

    service = CountingService()
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    with TestClient(app) as client:
        first = client.post("/api/v1/query", json={"query": "one"})
        second = client.post("/api/v1/query", json={"query": "two"})
        third = client.post("/api/v1/query", json={"query": "three"})

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "2"
    assert first.headers["X-RateLimit-Remaining"] == "1"
    assert second.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] == "0"
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert third.headers["X-RateLimit-Remaining"] == "0"
    assert service.calls == 2


@pytest.mark.api
def test_query_rate_limit_resets_after_window():
    from src.api.dependencies import get_application_service, get_rate_limiter
    from src.api.main import create_app
    from src.api.rate_limit import InMemoryRateLimiter

    clock = FakeClock()
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60, clock=clock)
    service = CountingService()
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    with TestClient(app) as client:
        accepted = client.post("/api/v1/query", json={"query": "one"})
        limited = client.post("/api/v1/query", json={"query": "two"})
        clock.advance(60)
        reset = client.post("/api/v1/query", json={"query": "three"})

    assert accepted.status_code == 200
    assert limited.status_code == 429
    assert reset.status_code == 200
    assert reset.headers["X-RateLimit-Remaining"] == "0"
    assert service.calls == 2


@pytest.mark.api
def test_query_stream_includes_rate_limit_headers_and_blocks_when_limited():
    from src.api.dependencies import get_application_service, get_rate_limiter
    from src.api.main import create_app
    from src.api.rate_limit import InMemoryRateLimiter

    service = CountingService()
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60, clock=FakeClock())
    app = create_app()
    app.dependency_overrides[get_application_service] = lambda: service
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    with TestClient(app) as client:
        streamed = client.post("/api/v1/query/stream", json={"query": "one"})
        limited = client.post("/api/v1/query/stream", json={"query": "two"})

    assert streamed.status_code == 200
    assert streamed.headers["content-type"].startswith("text/event-stream")
    assert streamed.headers["X-RateLimit-Limit"] == "1"
    assert streamed.headers["X-RateLimit-Remaining"] == "0"
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert service.calls == 1
