import pytest
from src.models.session import SessionState, ClarificationState, Message
from datetime import UTC, datetime, timedelta
from src.chatbot.session_manager import SessionManager

pytestmark = pytest.mark.service

def test_session_creation():
    state = SessionState(session_id="test-1")
    assert state.session_id == "test-1"
    assert state.state == ClarificationState.INITIAL

def test_session_expiry():
    state = SessionState(session_id="test-2")
    state.last_activity = datetime.now(UTC) - timedelta(minutes=31)
    assert state.is_expired(30) == True

def test_session_not_expired():
    state = SessionState(session_id="test-3")
    assert state.is_expired(30) == False

def test_add_message():
    state = SessionState(session_id="test-4")
    state.add_message("user", "Test query")
    assert len(state.conversation_history) == 1
    assert state.conversation_history[0].role == "user"

def test_session_manager_create():
    manager = SessionManager()
    state = manager.create_session("sess-1")
    assert state.session_id == "sess-1"
    retrieved = manager.get_session("sess-1")
    assert retrieved is not None

def test_session_manager_expiry():
    manager = SessionManager(expiry_minutes=30)
    manager.create_session("sess-2")
    state = manager.get_session("sess-2")
    state.last_activity = datetime.now(UTC) - timedelta(minutes=31)
    expired = manager.get_session("sess-2")
    assert expired is None
