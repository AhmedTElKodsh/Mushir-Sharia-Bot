"""Deterministic contract-family classifier for the first routing gate."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from src.models.commercial import ContractFamily
from src.rag.query_preprocessor import QueryPreprocessor


@dataclass(frozen=True)
class ContractClassification:
    contract_family: ContractFamily
    confidence: float
    matched_terms: Tuple[str, ...] = ()


class ContractTypeClassifier:
    """Keyword/regex first classifier used before source-family routing."""

    FAMILY_PATTERNS: Dict[ContractFamily, Tuple[str, ...]] = {
        ContractFamily.ISTISNA: (
            r"\bistisna'?a?\b",
            r"\bconstruction\b",
            r"\bcontractor\b",
            r"\bmuqawala\b",
            r"\bfidic\b",
            r"\bmanufactur(?:e|ing|ed)\b",
            "\u0627\u0633\u062a\u0635\u0646\u0627\u0639",
            "\u0639\u0642\u0648\u062f \u0627\u0644\u0645\u0642\u0627\u0648\u0644\u0627\u062a",
            "\u0645\u0642\u0627\u0648\u0644\u0627\u062a",
            "\u0645\u0642\u0627\u0648\u0644\u0629",
            "\u0645\u0642\u0627\u0648\u0644",
            "\u062a\u0635\u0646\u064a\u0639",
            "\u062a\u0648\u0631\u064a\u062f",
        ),
        ContractFamily.MURABAHA: (
            r"\bmurabaha(?:h)?\b",
            r"\binstall?ment sale\b",
            r"\bdeferred sale\b",
            r"\bbnpl\b",
            "\u0645\u0631\u0627\u0628\u062d\u0629",
            "\u0645\u0631\u0627\u0628\u062d\u0647",
            "\u062a\u0642\u0633\u064a\u0637",
            "\u0627\u0642\u0633\u0627\u0637",
            "\u0628\u064a\u0639 \u0645\u0624\u062c\u0644",
        ),
        ContractFamily.IJARAH: (
            r"\bijara(?:h)?\b",
            r"\blease\b",
            r"\blessee\b",
            r"\blessor\b",
            r"\brent(?:al)?\b",
            "\u0625\u062c\u0627\u0631\u0629",
            "\u0627\u064a\u062c\u0627\u0631",
            "\u062a\u0623\u062c\u064a\u0631",
            "\u0645\u0633\u062a\u0623\u062c\u0631",
            "\u0645\u0624\u062c\u0631",
            "\u062a\u0645\u0648\u064a\u0644 \u0639\u0642\u0627\u0631\u064a",
            "real estate financing",
        ),
        ContractFamily.MUDARABA: (r"\bmudaraba(?:h)?\b", "\u0645\u0636\u0627\u0631\u0628\u0629"),
        ContractFamily.MUSHARAKA: (r"\bmusharaka(?:h)?\b", "\u0645\u0634\u0627\u0631\u0643\u0629"),
        ContractFamily.SALAM: (r"\bsalam\b", "\u0633\u0644\u0645"),
        ContractFamily.WAKALA: (r"\bwakala(?:h)?\b", "\u0648\u0643\u0627\u0644\u0629", "\u062a\u0623\u0645\u064a\u0646", "\u062a\u0643\u0627\u0641\u0644\u064a", "takaful", "insurance"),
        ContractFamily.QARD: (
            r"\bqard\b",
            r"\bloan\b",
            r"\bdebt\b",
            r"\breceivable(?:s)?\b",
            r"\bcash advance\b",
            "\u0642\u0631\u0636",
            "\u062f\u064a\u0646",
            "\u0646\u0642\u062f",
        ),
        ContractFamily.KAFALA: (r"\bkafala(?:h)?\b", r"\bguarantee\b", "\u0643\u0641\u0627\u0644\u0629", "\u0636\u0645\u0627\u0646"),
        ContractFamily.TAWARRUQ: (r"\btawarruq\b", "\u062a\u0648\u0631\u0642"),
        ContractFamily.SUKUK: (r"\bsukuk\b", "\u0635\u0643\u0648\u0643"),
    }

    def classify(self, query: str) -> Optional[ContractClassification]:
        text = QueryPreprocessor.normalize(query or "")
        lowered = text.lower()
        expanded = QueryPreprocessor.expand_terms(query or "")
        best: Optional[ContractClassification] = None
        for family, patterns in self.FAMILY_PATTERNS.items():
            matches = self._matches(lowered, expanded, patterns)
            if not matches:
                continue
            confidence = min(0.99, 0.72 + (0.08 * len(matches)))
            candidate = ContractClassification(family, confidence, tuple(matches))
            if best is None or candidate.confidence > best.confidence:
                best = candidate
        return best

    @staticmethod
    def _matches(lowered: str, expanded: Iterable[str], patterns: Iterable[str]) -> Tuple[str, ...]:
        expanded_terms = {term.lower() for term in expanded}
        matches = []
        for pattern in patterns:
            normalized = QueryPreprocessor.normalize(pattern).lower()
            if pattern.startswith(r"\b"):
                if re.search(pattern, lowered, flags=re.IGNORECASE):
                    matches.append(pattern)
            elif normalized in lowered or normalized in expanded_terms:
                matches.append(pattern)
        return tuple(matches)
