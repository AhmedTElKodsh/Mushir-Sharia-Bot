from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import UTC, datetime, timedelta
from enum import Enum

class ClarificationState(Enum):
    INITIAL = "INITIAL"
    ANALYZING = "ANALYZING"
    CLARIFYING = "CLARIFYING"
    READY = "READY"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"

@dataclass
class Message:
    role: str  # "user" or "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SessionState:
    """Session state for clarification engine."""
    session_id: str
    state: ClarificationState = ClarificationState.INITIAL
    user_input: str = ""
    extracted_variables: Dict[str, Any] = field(default_factory=dict)
    missing_variables: List[str] = field(default_factory=list)
    clarifying_questions: List[str] = field(default_factory=list)
    conversation_history: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        return datetime.now(UTC) - self.last_activity > timedelta(minutes=timeout_minutes)

    def update_activity(self):
        self.last_activity = datetime.now(UTC)

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        self.conversation_history.append(Message(role=role, content=content, metadata=metadata or {}))
        self.update_activity()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "user_input": self.user_input,
            "extracted_variables": self.extracted_variables,
            "missing_variables": self.missing_variables,
            "clarifying_questions": self.clarifying_questions,
            "conversation_history": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
                for m in self.conversation_history
            ],
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata,
        }
