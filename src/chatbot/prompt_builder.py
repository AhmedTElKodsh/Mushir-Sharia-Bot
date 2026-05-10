"""Deterministic prompt construction for AAOIFI-grounded answers."""
from typing import Any, Dict, List, Optional

AAOIFI_GROUNDING_SYSTEM_PROMPT = """You are a Sharia compliance assistant specializing in AAOIFI standards.

Answer only from the provided AAOIFI excerpts. If the excerpts do not cover the question, say so.
Always cite the standard_id and section using the format [standard_id §section].
Do not provide a binding Sharia ruling, fatwa, legal advice, or financial advice.
Every material compliance claim must be directly supported by the provided excerpts.
If citation support is missing, respond with INSUFFICIENT_DATA instead of guessing.
Prefer asking for clarification over inferring missing transaction facts.
Do not use uncited external knowledge."""


class PromptBuilder:
    """Builds prompts from system instructions, recent history, chunks, and query."""

    prompt_version = "l1-aaoifi-grounded-v1"

    def __init__(
        self,
        system_prompt: str = AAOIFI_GROUNDING_SYSTEM_PROMPT,
        max_history_turns: int = 3,
        max_history_chars: int = 4000,
    ):
        self.system_prompt = system_prompt
        self.max_history_turns = max_history_turns
        self.max_history_chars = max_history_chars

    def build(
        self,
        query: str,
        chunks: List[Any],
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        sections = [self.system_prompt.strip()]
        rendered_history = self._format_history(history or [])
        if rendered_history:
            sections.append(f"Recent conversation:\n{rendered_history}")
        sections.append(f"AAOIFI excerpts:\n{self.format_chunks(chunks)}")
        sections.append(f"Current question:\n{query.strip()}")
        sections.append(
            "Return a concise answer, compliance status, reasoning, and citations. "
            "Use INSUFFICIENT_DATA when the excerpts do not support an answer."
        )
        return "\n\n".join(sections)

    def format_chunks(self, chunks: List[Any]) -> str:
        if not chunks:
            return "No retrieved AAOIFI excerpts."
        formatted = []
        for index, chunk in enumerate(chunks, 1):
            text = self._chunk_text(chunk)
            standard = self._chunk_standard(chunk)
            section = self._chunk_section(chunk)
            score = self._chunk_score(chunk)
            formatted.append(f"[{index}] {standard} §{section} (score: {score:.2f})\n{text}")
        return "\n\n---\n\n".join(formatted)

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        recent = history[-self.max_history_turns :]
        lines = []
        for turn in recent:
            user = (turn.get("user") or "").strip()
            assistant = (turn.get("assistant") or "").strip()
            if user:
                lines.append(f"User: {user}")
            if assistant:
                lines.append(f"Assistant: {assistant}")
        rendered = "\n".join(lines)
        return rendered[-self.max_history_chars :]

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        if isinstance(chunk, dict):
            return str(chunk.get("content") or chunk.get("text") or "")
        return str(getattr(chunk, "text", ""))

    @staticmethod
    def _chunk_standard(chunk: Any) -> str:
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            return str(metadata.get("standard_number") or metadata.get("source_file") or "Unknown")
        return str(getattr(getattr(chunk, "citation", None), "standard_id", "Unknown"))

    @staticmethod
    def _chunk_section(chunk: Any) -> str:
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            return str(
                metadata.get("section_number")
                or metadata.get("section_title")
                or metadata.get("section")
                or "Unknown"
            )
        return str(getattr(getattr(chunk, "citation", None), "section", None) or "Unknown")

    @staticmethod
    def _chunk_score(chunk: Any) -> float:
        if isinstance(chunk, dict):
            return float(chunk.get("similarity") or chunk.get("score") or 0.0)
        return float(getattr(chunk, "score", 0.0) or 0.0)
