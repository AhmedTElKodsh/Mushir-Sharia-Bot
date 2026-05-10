"""Redis-backed session storage for L3 horizontal scaling."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from src.chatbot.session_manager import SESSION_EXPIRY_MINUTES
from src.config.logging_config import setup_logging
from src.models.session import ClarificationState, Message, SessionState

logger = setup_logging()


class RedisSessionManager:
    """Session manager compatible with the in-memory L1/L2 manager API."""

    def __init__(self, redis_url: Optional[str] = None, expiry_minutes: int = SESSION_EXPIRY_MINUTES):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis is required when SESSION_STORE_TYPE=redis") from exc

        self.expiry_minutes = expiry_minutes
        self.ttl_seconds = expiry_minutes * 60
        self.client = redis.Redis.from_url(
            redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_timeout=float(os.getenv("REDIS_TIMEOUT_SECONDS", "2")),
        )
        self.client.ping()

    def create_session(self, session_id: str) -> SessionState:
        state = SessionState(session_id=session_id)
        self.update_session(state)
        logger.info(f"Created Redis session: {session_id}")
        return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        raw = self.client.get(self._key(session_id))
        if not raw:
            return None
        state = self._decode(raw)
        state.update_activity()
        self.update_session(state)
        return state

    def update_session(self, state: SessionState) -> None:
        state.update_activity()
        self.client.setex(self._key(state.session_id), self.ttl_seconds, json.dumps(state.to_dict()))

    def delete_session(self, session_id: str) -> None:
        self.client.delete(self._key(session_id))

    def cleanup_expired(self) -> int:
        return 0

    @staticmethod
    def _key(session_id: str) -> str:
        return f"mushir:session:{session_id}"

    @staticmethod
    def _decode(raw: str) -> SessionState:
        data = json.loads(raw)
        state = SessionState(
            session_id=data["session_id"],
            state=ClarificationState(data.get("state", ClarificationState.INITIAL.value)),
            user_input=data.get("user_input", ""),
            extracted_variables=data.get("extracted_variables", {}),
            missing_variables=data.get("missing_variables", []),
            clarifying_questions=data.get("clarifying_questions", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            metadata=data.get("metadata", {}),
        )
        state.conversation_history = [
            Message(
                role=message["role"],
                content=message["content"],
                timestamp=datetime.fromisoformat(message["timestamp"]),
                metadata=message.get("metadata", {}),
            )
            for message in data.get("conversation_history", [])
        ]
        return state
