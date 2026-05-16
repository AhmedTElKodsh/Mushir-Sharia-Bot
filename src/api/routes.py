import json
import uuid
from inspect import Parameter, signature
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.dependencies import get_application_service, get_rate_limiter, get_session_manager
from src.api.rate_limit import InMemoryRateLimiter, RateLimitDecision
from src.api.schemas import ErrorResponse, QueryRequest, QueryResponse
from src.chatbot.application_service import ApplicationService
from src.chatbot.llm_client import LLMConfigurationError, LLMRateLimitError, LLMResponseError
from src.chatbot.session_manager import SessionManager
from src.models.ruling import AnswerContract
from src.models.session import SessionState
from src.security.input_validator import InputValidator

router = APIRouter()
SAFE_SERVICE_ERROR_MESSAGE = "The answer service could not complete the request. Please try again later."
SAFE_PROVIDER_CONFIG_MESSAGE = (
    "The answer provider is not configured for this deployment. Ask the operator to check the provider API key."
)
SAFE_PROVIDER_RATE_LIMIT_MESSAGE = (
    "The answer provider is out of credits or rate-limiting requests. Ask the operator to check provider billing, quota, or model access."
)
SAFE_PROVIDER_RESPONSE_MESSAGE = (
    "The answer provider returned an unusable response. Please try again with a shorter, plain-text question."
)


@router.post("/sessions", response_model=Dict[str, str])
async def create_session(session_manager: SessionManager = Depends(get_session_manager)):
    session_id = str(uuid.uuid4())
    session_manager.create_session(session_id)
    return {"session_id": session_id, "status": "created"}


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
):
    state = session_manager.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return state.to_dict()


@router.post("/sessions/{session_id}/query")
async def submit_session_query(
    session_id: str,
    request: QueryRequest = Body(...),
    session_manager: SessionManager = Depends(get_session_manager),
):
    """Legacy prototype endpoint kept disabled so it cannot bypass /query gates."""
    state = session_manager.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    raise HTTPException(
        status_code=501,
        detail="Session-scoped query is disabled; use /api/v1/query or /api/v1/query/stream",
    )


@router.post("/query", response_model=QueryResponse)
async def query(
    payload: QueryRequest,
    request: Request,
    response: Response,
    application_service: ApplicationService = Depends(get_application_service),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
):
    rate_decision = rate_limiter.check(_rate_limit_key(request))
    if not rate_decision.allowed:
        return _rate_limit_response(request.state.request_id, rate_decision)
    _apply_rate_limit_headers(response, rate_decision)
    validation_error = _validate_query(payload)
    if validation_error:
        return _error_response("VALIDATION_ERROR", validation_error, request.state.request_id, status_code=422)
    try:
        answer = _answer_service(application_service, payload, request.state.request_id)
    except Exception as exc:
        request_id = request.state.request_id
        return _error_response("SERVICE_ERROR", _service_error_message(exc), request_id, status_code=500)
    return _query_response(answer)


@router.post("/query/stream")
async def query_stream(
    payload: QueryRequest,
    request: Request,
    application_service: ApplicationService = Depends(get_application_service),
    rate_limiter: InMemoryRateLimiter = Depends(get_rate_limiter),
):
    request_id = request.state.request_id
    rate_decision = rate_limiter.check(_rate_limit_key(request))
    if not rate_decision.allowed:
        return _rate_limit_response(request_id, rate_decision)
    validation_error = _validate_query(payload)
    if validation_error:
        return _error_response("VALIDATION_ERROR", validation_error, request_id, status_code=422)
    return StreamingResponse(
        _query_events(application_service, payload, request_id),
        media_type="text/event-stream",
        headers=rate_decision.headers(),
    )


@router.get("/rulings/{ruling_id}", response_model=None)
async def get_ruling(ruling_id: str = Path(...)):
    raise HTTPException(status_code=501, detail="Ruling storage is not enabled in this deployment")


@router.post("/auth/login")
async def login(username: str = Body(...), password: str = Body(...)):
    raise HTTPException(status_code=501, detail="Token login is not enabled in this deployment")


@router.get("/compliance/disclaimer")
async def compliance_disclaimer():
    return {
        "version": "l5-bilingual-disclaimer-v1",
        "requires_acknowledgement": True,
        "default_language": "en",
        "supported_languages": ["en", "ar"],
        "text": (
            "Mushir provides informational guidance grounded in retrieved AAOIFI excerpts. "
            "It does not provide a binding Sharia ruling, fatwa, legal advice, or financial advice. "
            "Consult a qualified Sharia scholar before relying on any conclusion."
        ),
        "translations": {
            "ar": (
                "يقدم مشير إرشادا معلوماتيا مستندا إلى المقاطع المسترجعة من معايير أيوفي. "
                "ولا يقدم حكما شرعيا ملزما أو فتوى أو نصيحة قانونية أو مالية. "
                "استشر عالما شرعيا مؤهلا قبل الاعتماد على أي نتيجة."
            )
        },
    }


def _query_response(answer: AnswerContract) -> QueryResponse:
    return QueryResponse(**answer.to_dict())


def _answer_service(application_service: ApplicationService, payload: QueryRequest, request_id: str):
    optional_kwargs = {
        "session_id": payload.resolved_session_id(),
        "request_id": request_id,
        "disclaimer_acknowledged": bool(payload.context.get("disclaimer_acknowledged", False)),
        "conversation_history": payload.conversation_history,
    }
    answer_signature = signature(application_service.answer)
    params = answer_signature.parameters
    accepts_kwargs = any(param.kind == Parameter.VAR_KEYWORD for param in params.values())
    kwargs = {
        key: value
        for key, value in optional_kwargs.items()
        if accepts_kwargs or key in params
    }
    return application_service.answer(payload.query, **kwargs)


def _error_response(code: str, message: str, request_id: str, status_code: int):
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(code=code, message=message, request_id=request_id).model_dump(),
    )


def _service_error_message(exc: Exception) -> str:
    if isinstance(exc, LLMConfigurationError):
        return SAFE_PROVIDER_CONFIG_MESSAGE
    if isinstance(exc, LLMRateLimitError):
        return SAFE_PROVIDER_RATE_LIMIT_MESSAGE
    if isinstance(exc, LLMResponseError):
        return SAFE_PROVIDER_RESPONSE_MESSAGE
    return SAFE_SERVICE_ERROR_MESSAGE


def _validate_query(payload: QueryRequest) -> str | None:
    valid, error = InputValidator().validate_query(payload.query)
    return None if valid else error


def _rate_limit_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown-client"


def _apply_rate_limit_headers(response: Response, decision: RateLimitDecision) -> None:
    for header, value in decision.headers().items():
        response.headers[header] = value


def _rate_limit_response(request_id: str, decision: RateLimitDecision) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded",
            request_id=request_id,
        ).model_dump(),
        headers=decision.headers(),
    )


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _query_events(application_service: ApplicationService, payload: QueryRequest, request_id: str):
    yield _sse("started", {"request_id": request_id})
    try:
        answer = _answer_service(application_service, payload, request_id)
        response = _query_response(answer).model_dump(mode="json")
        yield _sse("retrieval", {"confidence": response["metadata"].get("confidence", 0.0)})
        yield _sse("token", {"text": response["answer"]})
        for citation in response["citations"]:
            yield _sse("citation", citation)
        yield _sse("done", response)
    except Exception as exc:
        yield _sse(
            "error",
            ErrorResponse(
                code="SERVICE_ERROR",
                message=_service_error_message(exc),
                request_id=request_id,
            ).model_dump()["error"],
        )


def _session_from_request_context(request: QueryRequest) -> SessionState:
    """Kept for older tests/importers; route logic now uses ApplicationService."""
    return SessionState(session_id=request.resolved_session_id() or str(uuid.uuid4()))
