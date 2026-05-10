"""FastAPI dependency providers for L2."""
from fastapi import Request

from src.api.rate_limit import InMemoryRateLimiter
from src.chatbot.application_service import ApplicationService
from src.chatbot.session_manager import SessionManager


def get_application_service(request: Request) -> ApplicationService:
    if not hasattr(request.app.state, "application_service"):
        request.app.state.application_service = ApplicationService()
    return request.app.state.application_service


def get_session_manager(request: Request) -> SessionManager:
    if not hasattr(request.app.state, "session_manager"):
        request.app.state.session_manager = SessionManager()
    return request.app.state.session_manager


def get_rate_limiter(request: Request) -> InMemoryRateLimiter:
    if not hasattr(request.app.state, "rate_limiter"):
        request.app.state.rate_limiter = InMemoryRateLimiter()
    return request.app.state.rate_limiter
