"""Small service contracts for the L1 Sharia compliance engine."""
from typing import Any, Dict, List, Optional, Protocol

from src.models.ruling import AAOIFICitation


class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5, threshold: float = 0.3) -> List[Any]:
        ...


class LLMClient(Protocol):
    model_name: str

    def generate(self, prompt: str) -> str:
        ...


class PromptBuilder(Protocol):
    prompt_version: str

    def build(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        ...


class CitationValidator(Protocol):
    def validate(self, answer: str, chunks: List[Any]) -> List[AAOIFICitation]:
        ...


class ClarificationService(Protocol):
    def ask_if_needed(self, query: str, session_id: Optional[str] = None) -> Optional[str]:
        ...


class SessionStore(Protocol):
    def history_for(self, session_id: Optional[str]) -> List[Dict[str, str]]:
        ...
