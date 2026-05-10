"""Validate that answer citations are backed by retrieved AAOIFI chunks."""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models.ruling import AAOIFICitation


class CitationValidator:
    """Extracts answer citations and keeps only references present in retrieval."""

    citation_pattern = re.compile(r"\[([^\]§]+)\s*§\s*([^\]]+)\]")

    def validate(self, answer: str, chunks: List[Any]) -> List[AAOIFICitation]:
        supported = self._supported_refs(chunks)
        citations = []
        seen = set()
        for standard, section in self.citation_pattern.findall(answer):
            normalized = (standard.strip(), section.strip())
            if normalized not in supported or normalized in seen:
                continue
            seen.add(normalized)
            citations.append(
                AAOIFICitation(
                    document_id=self._document_id_for(normalized, chunks),
                    standard_number=normalized[0],
                    section_number=normalized[1],
                    excerpt=self._excerpt_for(normalized, chunks),
                )
            )
        if not citations and chunks:
            citations = [self._citation_from_chunk(chunks[0])]
        return citations

    def _supported_refs(self, chunks: List[Any]) -> Set[Tuple[str, str]]:
        refs = set()
        for chunk in chunks:
            standard, section = self._chunk_ref(chunk)
            if standard and section:
                refs.add((standard, section))
        return refs

    def _chunk_ref(self, chunk: Any) -> Tuple[Optional[str], Optional[str]]:
        if isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
            return (
                metadata.get("standard_number") or metadata.get("source_file"),
                metadata.get("section_number") or metadata.get("section") or metadata.get("section_title"),
            )
        citation = getattr(chunk, "citation", None)
        return (
            getattr(citation, "standard_id", None),
            getattr(citation, "section", None),
        )

    def _citation_from_chunk(self, chunk: Any) -> AAOIFICitation:
        standard, section = self._chunk_ref(chunk)
        quote, start, end = self._quote_for_chunk(chunk)
        return AAOIFICitation(
            document_id=self._metadata(chunk).get("document_id") or standard or "unknown",
            standard_number=standard or "Unknown",
            section_number=section,
            section_title=self._metadata(chunk).get("section_title"),
            excerpt=quote,
            confidence_score=self._chunk_score(chunk),
            quote_start=start,
            quote_end=end,
        )

    def _document_id_for(self, ref: Tuple[str, str], chunks: List[Any]) -> str:
        for chunk in chunks:
            if self._chunk_ref(chunk) == ref:
                return self._metadata(chunk).get("document_id") or ref[0]
        return ref[0]

    def _excerpt_for(self, ref: Tuple[str, str], chunks: List[Any]) -> str:
        for chunk in chunks:
            if self._chunk_ref(chunk) == ref:
                quote, _, _ = self._quote_for_chunk(chunk)
                return quote
        return ""

    def _quote_for_chunk(self, chunk: Any) -> Tuple[str, int, int]:
        text = self._chunk_text(chunk).strip()
        if not text:
            return "", 0, 0
        sentences = re.split(r"(?<=[.!?])\s+", text)
        quote = next((sentence for sentence in sentences if len(sentence) >= 40), sentences[0])
        quote = quote[:500]
        start = text.find(quote)
        if start < 0:
            start = 0
        return quote, start, start + len(quote)

    @staticmethod
    def _metadata(chunk: Any) -> Dict[str, Any]:
        if isinstance(chunk, dict):
            return chunk.get("metadata", {})
        citation = getattr(chunk, "citation", None)
        return {
            "document_id": getattr(citation, "source_file", None),
            "section_title": getattr(citation, "section", None),
        }

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        if isinstance(chunk, dict):
            return str(chunk.get("content") or chunk.get("text") or "")
        return str(getattr(chunk, "text", ""))

    @staticmethod
    def _chunk_score(chunk: Any) -> float:
        if isinstance(chunk, dict):
            return float(chunk.get("similarity") or chunk.get("score") or 0.0)
        return float(getattr(chunk, "score", 0.0) or 0.0)
