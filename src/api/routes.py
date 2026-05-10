import json
from fastapi import APIRouter, HTTPException, Body, Path
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import uuid
from pydantic import BaseModel
from src.chatbot.clarification_engine import ClarificationEngine
from src.chatbot.session_manager import SessionManager
from src.models.schema import ComplianceRuling
from src.models.session import SessionState

router = APIRouter()
session_manager = SessionManager()
RAGPipeline = None

AAOIFI_ADHERENCE_SYSTEM_PROMPT = """You are a Sharia compliance assistant specializing in AAOIFI standards.

Answer only from the provided AAOIFI excerpts. If the excerpts do not cover the question, reply:
"Not addressed in retrieved AAOIFI standards." Always cite the standard_id and section when available."""

TEMPLATE = """Excerpts from AAOIFI Standards:

{chunks}

Question: {question}

Answer with citations in format [standard_id §section]:"""

# Request/Response models
class QueryRequest(BaseModel):
    content: str
    context: Optional[Dict[str, Any]] = None

class ClarificationResponse(BaseModel):
    status: str
    questions: Optional[List[str]] = None
    message: Optional[str] = None

class RulingResponse(BaseModel):
    ruling_id: str
    status: str
    reasoning: str
    citations: List[Dict]
    recommendations: List[str]
    warnings: List[str]

# Session management
@router.post("/sessions", response_model=Dict[str, str])
async def create_session():
    """Create new session."""
    session_id = str(uuid.uuid4())
    session_manager.create_session(session_id)
    return {"session_id": session_id, "status": "created"}

@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get session conversation history."""
    state = session_manager.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return state.to_dict()

# Query submission
@router.post("/sessions/{session_id}/query", response_model=ClarificationResponse)
async def submit_query(
    session_id: str,
    request: QueryRequest = Body(...),
):
    """Submit query for compliance analysis."""
    engine = ClarificationEngine()
    state = session_manager.get_session(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    result = engine.process_query(state, request.content)
    session_manager.update_session(state)
    return result


@router.post("/query")
async def stream_query(request: QueryRequest = Body(...)):
    """Stream L2 query progress as server-sent events."""
    session_state = _session_from_request_context(request)
    return StreamingResponse(
        _query_events(session_state, request.content),
        media_type="text/event-stream",
    )

# Ruling retrieval
@router.get("/rulings/{ruling_id}", response_model=Optional[RulingResponse])
async def get_ruling(ruling_id: str = Path(...)):
    """Get compliance ruling by ID."""
    # Placeholder - ruling storage TBD
    raise HTTPException(status_code=404, detail="Ruling storage not yet implemented")

# Auth (simplified for MVP)
@router.post("/auth/login")
async def login(username: str = Body(...), password: str = Body(...)):
    """Login endpoint (simplified)."""
    return {"token": "dummy-token", "expires_in": 86400, "message": "Auth not fully implemented in MVP"}


def _session_from_request_context(request: QueryRequest) -> SessionState:
    context = request.context or {}
    session_id = context.get("session_id") or str(uuid.uuid4())
    state = session_manager.get_session(session_id) or session_manager.create_session(session_id)
    if "extracted_variables" in context:
        state.extracted_variables.update(context["extracted_variables"])
    if "awaiting_variable" in context:
        state.metadata["awaiting_variable"] = context["awaiting_variable"]
    return state


def _sse(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _context_payload(session_state: SessionState) -> Dict[str, Any]:
    return {
        "session_id": session_state.session_id,
        "extracted_variables": session_state.extracted_variables,
        "awaiting_variable": session_state.metadata.get("awaiting_variable"),
    }


def format_chunks(chunks) -> str:
    formatted = []
    for chunk in chunks:
        citation = chunk.citation
        formatted.append(f"[{citation.standard_id}] (Score: {chunk.score:.2f})\n{chunk.text}\n")
    return "\n---\n".join(formatted)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    from src.chatbot.cli import call_llm as cli_call_llm

    return cli_call_llm(system_prompt, user_prompt)


def get_rag_pipeline():
    global RAGPipeline
    if RAGPipeline is None:
        from src.rag.pipeline import RAGPipeline as LoadedRAGPipeline

        RAGPipeline = LoadedRAGPipeline
    return RAGPipeline()


def _query_events(session_state: SessionState, content: str):
    yield _sse({"type": "thinking"})

    engine = ClarificationEngine()
    result = engine.process_query(session_state, content)
    session_manager.update_session(session_state)
    if result["status"] == "clarifying":
        yield _sse(
            {
                "type": "clarifying",
                "questions": result.get("questions", []),
                "context": _context_payload(session_state),
            }
        )
        return

    rag = get_rag_pipeline()
    clarified_query = engine.build_clarified_query(session_state)
    chunks = rag.retrieve(clarified_query, k=5)
    yield _sse({"type": "retrieving", "chunks": len(chunks)})

    yield _sse({"type": "generating"})
    if not chunks:
        answer = "Not addressed in retrieved AAOIFI standards."
    else:
        prompt = TEMPLATE.format(chunks=format_chunks(chunks), question=clarified_query)
        try:
            answer = call_llm(AAOIFI_ADHERENCE_SYSTEM_PROMPT, prompt)
        except Exception as exc:
            yield _sse(
                {
                    "type": "error",
                    "message": "The model provider failed while generating this answer.",
                    "detail": str(exc),
                    "retryable": True,
                    "context": _context_payload(session_state),
                }
            )
            return

    yield _sse({"type": "chunk", "text": answer})
    ruling = ComplianceRuling(
        question=clarified_query,
        answer=answer,
        chunks=chunks,
        confidence=sum(chunk.score for chunk in chunks) / len(chunks) if chunks else 0.0,
    )
    yield _sse(
        {
            "type": "complete",
            "context": _context_payload(session_state),
            "ruling": {
                "question": ruling.question,
                "answer": ruling.answer,
                "confidence": ruling.confidence,
                "sources": [
                    {
                        "standard_id": chunk.citation.standard_id,
                        "section": chunk.citation.section,
                        "score": chunk.score,
                    }
                    for chunk in ruling.chunks
                ],
            },
        }
    )
