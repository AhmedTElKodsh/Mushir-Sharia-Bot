from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Dict, Any
import uuid
from datetime import UTC, datetime
from src.config.logging_config import setup_logging

logger = setup_logging()

class ErrorResponse:
    """Standardized error response."""
    @staticmethod
    def create(error_code: str, message: str, request_id: str = None) -> Dict[str, Any]:
        return {
            "error": {
                "code": error_code,
                "message": message,
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        }

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except HTTPException as e:
            logger.warning(f"HTTP {e.status_code}: {e.detail} (req={request_id})")
            return JSONResponse(
                status_code=e.status_code,
                content=ErrorResponse.create(f"HTTP_{e.status_code}", e.detail, request_id),
            )
        except Exception as e:
            logger.error(f"Unhandled error (req={request_id}): {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content=ErrorResponse.create("INTERNAL_ERROR", "An internal error occurred", request_id),
            )
