"""Validate that answer citations are backed by retrieved AAOIFI chunks."""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from src.models.ruling import AAOIFICitation


class CitationValidator:
    """Extracts explicit answer citations and keeps only retrieved references."""

    citation_pattern = re.compile(r"\[(?:AAOIFI\s+)?FAS-?(\d+)[^\]]*\]")

    def validate(self, answer: str, chunks: List[Any]) -> List[AAOIFICitation]:
        """Extract citations from answer and match against retrieved chunks."""
        citations = []
        seen = set()
        
        # Find all FAS-XX references in the answer
        for match in self.citation_pattern.finditer(answer):
            standard_num = match.group(1)
            standard = f"FAS-{standard_num}"
            
            # Find chunks that match this standard
            for chunk in chunks:
                chunk_standard, chunk_section = self._chunk_ref(chunk)
                ref = (chunk_standard, chunk_section)
                
                # Match if standard matches (section can be None for definitions)
                if chunk_standard == standard and ref not in seen:
                    seen.add(ref)
                    citations.append(
                        AAOIFICitation(
                            document_id=self._document_id_for(ref, chunks),
                            standard_number=standard,
                            section_number=chunk_section,
                            excerpt=self._excerpt_for(ref, chunks),
                            confidence_score=self._score_for(ref, chunks),
                            quote_start=self._quote_offsets_for(ref, chunks)[0],
                            quote_end=self._quote_offsets_for(ref, chunks)[1],
                        )
                    )
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
            # Handle various formats: standard_number, source_file, document_id
            standard = (
                metadata.get("standard_number") 
                or metadata.get("source_file") 
                or metadata.get("document_id")
            )
            # Normalize standard name (e.g., "AAOIFI_Standard_28_en_..." -> "FAS-28")
            if standard:
                standard = self._normalize_standard(standard)
            section = (
                metadata.get("section_number") 
                or metadata.get("section") 
                or metadata.get("section_title")
            )
            return (standard, section)
        citation = getattr(chunk, "citation", None)
        standard = getattr(citation, "standard_id", None)
        if standard:
            standard = self._normalize_standard(standard)
        return (
            standard,
            getattr(citation, "section", None),
        )

    @staticmethod
    def _normalize_standard(standard: str) -> str:
        """Normalize standard reference to FAS-XX format."""
        import re
        # Match patterns like: AAOIFI_Standard_28, FAS-28, Standard_28
        match = re.search(r'[Ss]tandard[_\s]*(\d+)', standard) or re.search(r'FAS-?(\d+)', standard)
        if match:
            return f"FAS-{match.group(1)}"
        return standard

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

    def _score_for(self, ref: Tuple[str, str], chunks: List[Any]) -> float:
        for chunk in chunks:
            if self._chunk_ref(chunk) == ref:
                return self._chunk_score(chunk)
        return 0.0

    def _quote_offsets_for(self, ref: Tuple[str, str], chunks: List[Any]) -> Tuple[int, int]:
        for chunk in chunks:
            if self._chunk_ref(chunk) == ref:
                _, start, end = self._quote_for_chunk(chunk)
                return start, end
        return 0, 0

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
