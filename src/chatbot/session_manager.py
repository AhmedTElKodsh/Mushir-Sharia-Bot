import threading
from typing import Dict, Optional
from datetime import datetime, timedelta
from src.models.session import SessionState, ClarificationState
from src.config.logging_config import setup_logging

logger = setup_logging()

SESSION_EXPIRY_MINUTES = 30

class SessionManager:
    """In-memory session store for MVP."""

    def __init__(self, expiry_minutes: int = SESSION_EXPIRY_MINUTES):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()
        self.expiry_minutes = expiry_minutes

    def create_session(self, session_id: str) -> SessionState:
        with self._lock:
            state = SessionState(session_id=session_id)
            self._sessions[session_id] = state
            logger.info(f"Created session: {session_id}")
            return state

    def get_session(self, session_id: str) -> Optional[SessionState]:
        with self._lock:
            state = self._sessions.get(session_id)
            if state:
                if state.is_expired(self.expiry_minutes):
                    logger.info(f"Session expired: {session_id}")
                    del self._sessions[session_id]
                    return None
                state.update_activity()
            return state

    def update_session(self, state: SessionState) -> None:
        with self._lock:
            state.update_activity()
            self._sessions[state.session_id] = state

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session: {session_id}")

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count removed."""
        with self._lock:
            expired = [
                sid for sid, state in self._sessions.items()
                if state.is_expired(self.expiry_minutes)
            ]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")
            return len(expired)
