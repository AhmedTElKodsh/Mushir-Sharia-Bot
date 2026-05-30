"""
Contract Family Router — Pre-Retrieval Gate
============================================
Classifies a query into an Islamic contract family BEFORE any embedding or
retrieval is performed. This is the critical architectural fix for the
false-fatwa path identified in the party-mode rethink (2026-05-28):

  Query "هل شرط غرامة التآخير في عقود المقاولات شرط ربوي؟"
  ──────────────────────────────────────────────────────────
  Surface signal: غرامة التأخير  → (weak) Riba / debt context
  Container signal: عقود المقاولات → MUQAWALA (Istisna construction)
  Container OVERRIDES surface → routes to SS-10 + SS-05, not SS-19.

Architecture decision: Returns an immutable ContractFamilyResult.
Callers construct a new QueryContext with this result — nothing is
mutated in-place (Option A, confirmed by Winston in Round 2).

References:
  - AAOIFI SS-10 (Istisna')
  - AAOIFI SS-05 (Guarantees)
  - AAOIFI SS-09 (Ijarah)
  - AAOIFI SS-28 (Murabaha)
  - AAOIFI SS-13 (Mudaraba)
  - AAOIFI SS-12 (Musharaka)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ContractFamily(str, Enum):
    """Islamic contract families used for routing and retrieval targeting."""

    MURABAHA = "murabaha"           # بيع المرابحة — cost-plus sale
    IJARA = "ijara"                 # الإجارة — lease (incl. IML)
    MUQAWALA = "muqawala"           # المقاولة / الاستصناع — construction
    MUSHARAKA = "musharaka"         # المشاركة — equity partnership
    MUDHARABA = "mudharaba"         # المضاربة — profit-sharing investment
    WAKALA = "wakala"               # الوكالة — agency
    KAFALA = "kafala"               # الكفالة — guarantee / suretyship
    GENERAL_SHARIA = "general_sharia"  # فقه عام — no specific contract context
    AMBIGUOUS = "ambiguous"         # Could not resolve — triggers clarification


class RetrievalMode(str, Enum):
    """Downstream retrieval strategy based on classification confidence."""

    SINGLE_PATH = "single_path"     # confidence > THRESHOLD_SINGLE (0.80)
    MULTI_PATH = "multi_path"       # confidence THRESHOLD_MULTI–THRESHOLD_SINGLE (0.50–0.80)
    CLARIFICATION = "clarification" # confidence < THRESHOLD_MULTI (0.50)


@dataclass(frozen=True)
class ContractFamilyResult:
    """
    Immutable classification result returned by ContractFamilyRouter.classify().

    Downstream pipeline stages read this result and construct their own state —
    they do NOT mutate this object.

    Attributes:
        primary_family: The dominant contract family detected.
        adjacent_families: Families to include in multi-path retrieval.
        confidence: Score 0.0–1.0 from the deterministic confidence model.
        mode: Retrieval strategy derived from confidence thresholds.
        signals: Audit trail — {signal_label: weight_contribution}.
        clarification_hint: Passed to ClarificationEngine when mode==CLARIFICATION.
        query_intent: 'STANDARD' | 'COMPARATIVE' — comparative queries force MULTI_PATH.
    """

    primary_family: ContractFamily
    adjacent_families: tuple[ContractFamily, ...] = field(default_factory=tuple)
    confidence: float = 0.0
    mode: RetrievalMode = RetrievalMode.CLARIFICATION
    signals: dict[str, float] = field(default_factory=dict)
    clarification_hint: Optional[str] = None
    query_intent: str = "STANDARD"


# ---------------------------------------------------------------------------
# Signal lexicons
# ---------------------------------------------------------------------------

# Container signals — structural contract phrases that identify the CONTRACT
# TYPE, not a clause within the contract.  A match here OVERRIDES all surface
# signals for competing families.
#
def _normalize_arabic(text: str) -> str:
    """
    Strip Arabic diacritics (tashkeel), normalize hamza variants and
    alif maqsura. Keeps script characters intact.
    """
    # Remove combining diacritics (tashkeel: U+064B–U+065F, U+0670)
    text = "".join(
        c for c in text
        if not (0x064B <= ord(c) <= 0x065F or ord(c) == 0x0670)
    )
    # Normalize hamza variants → plain alif (ء أ إ آ ٱ → ا)
    for variant in ("أ", "إ", "آ", "ٱ"):
        text = text.replace(variant, "ا")
    # Normalize alif maqsura → ya
    text = text.replace("ى", "ي")
    # Normalize teh marbuta → ha
    text = text.replace("ة", "ه")
    return text

# High-confidence container signals (strong semantic boundaries).
_CONTAINER_PATTERNS: dict[ContractFamily, list[re.Pattern[str]]] = {
    ContractFamily.MUQAWALA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+المقاولة")),
        re.compile(_normalize_arabic(r"عقود\s+المقاولات")),
        re.compile(_normalize_arabic(r"المقاول\s+(الرئيسي|الفرعي|من\s+الباطن)")),
        re.compile(_normalize_arabic(r"مقاولة\s+الباطن")),
        re.compile(_normalize_arabic(r"عقد[ي]?\s+الاستصناع")),
        re.compile(_normalize_arabic(r"عقود\s+الاستصناع")),
        re.compile(_normalize_arabic(r"مشروع\s+(البناء|الإنشاء|التشييد|الإنشائي)")),
        re.compile(_normalize_arabic(r"استصناع\s+(موازي|متوازي)")),
        re.compile(r"\bistisna['']?\b", re.IGNORECASE),
        re.compile(r"\bmuqawala\b", re.IGNORECASE),
        re.compile(r"\bconstruction\s+contracts?\b", re.IGNORECASE),
    ],
    ContractFamily.MURABAHA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+المرابحة")),
        re.compile(_normalize_arabic(r"عقود\s+المرابحة")),
        re.compile(_normalize_arabic(r"عقد[ي]?\s+مرابحة")),   # bare (without ال)
        re.compile(_normalize_arabic(r"المرابحة")),
        re.compile(_normalize_arabic(r"مرابحة")),              # bare form
        re.compile(_normalize_arabic(r"بيع\s+المرابحة")),
        re.compile(_normalize_arabic(r"ثمن\s+المرابحة")),
        re.compile(_normalize_arabic(r"هامش\s+الربح")),
        re.compile(_normalize_arabic(r"مرابحة\s+(للآمر|بالأمر|بالأمانة)\s+بالشراء")),
        re.compile(r"\bmurabaha\b", re.IGNORECASE),
        re.compile(r"\bmurabahah\b", re.IGNORECASE),
    ],
    ContractFamily.IJARA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+الإجارة")),
        re.compile(_normalize_arabic(r"عقود\s+الإجارة")),
        re.compile(_normalize_arabic(r"الإجارة\s+المنتهية\s+بالتمليك")),
        re.compile(_normalize_arabic(r"إجارة\s+منتهية\s+بالتمليك")),
        re.compile(_normalize_arabic(r"الإجارة")),
        re.compile(_normalize_arabic(r"الأجرة\s+المسماة")),
        re.compile(_normalize_arabic(r"منفعة\s+الأصل")),
        re.compile(r"\bijarah?\b", re.IGNORECASE),
        re.compile(r"\bijarah\s+muntahia\b", re.IGNORECASE),
    ],
    ContractFamily.MUSHARAKA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+المشاركة")),
        re.compile(_normalize_arabic(r"المشاركة\s+المتناقصة")),
        re.compile(_normalize_arabic(r"المشاركة")),
        re.compile(_normalize_arabic(r"حصة\s+(في\s+)?(الربح|الشركة|رأس\s+المال)")),
        re.compile(r"\bmusharaka\b", re.IGNORECASE),
        re.compile(r"\bmusharakah\b", re.IGNORECASE),
        re.compile(r"\bdiminishing\s+musharaka\b", re.IGNORECASE),
    ],
    ContractFamily.MUDHARABA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+المضاربة")),
        re.compile(_normalize_arabic(r"المضاربة")),
        re.compile(_normalize_arabic(r"رب\s+المال\s+والمضارب")),
        re.compile(_normalize_arabic(r"المضارب\s+(والربح|والخسارة)")),
        re.compile(r"\bmudaraba\b", re.IGNORECASE),
        re.compile(r"\bmudarabah\b", re.IGNORECASE),
        re.compile(r"\bmudarib\b", re.IGNORECASE),
    ],
    ContractFamily.WAKALA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+الوكالة")),
        re.compile(_normalize_arabic(r"الوكالة")),
        re.compile(_normalize_arabic(r"وكالة\s+الاستثمار")),
        re.compile(_normalize_arabic(r"الوكيل\s+(بالاستثمار|الاستثماري)")),
        re.compile(r"\bwakalah?\b", re.IGNORECASE),
        re.compile(r"\bwakala\s+investment\b", re.IGNORECASE),
    ],
    ContractFamily.KAFALA: [
        re.compile(_normalize_arabic(r"عقد[ي]?\s+الكفالة")),
        re.compile(_normalize_arabic(r"الكفالة")),
        re.compile(_normalize_arabic(r"كفالة\s+(الأداء|الدفع|الجودة|الرد)")),
        re.compile(_normalize_arabic(r"الكفيل\s+(والمكفول|والمكفول\s+له)")),
        re.compile(r"\bkafalah?\b", re.IGNORECASE),
        re.compile(r"\bsuretyship\b", re.IGNORECASE),
        re.compile(r"\bperformance\s+bond\b", re.IGNORECASE),
    ],
}

# Surface signals — semantic terms that weakly imply a contract family.
# These are OVERRIDDEN by any container signal from a different family.
# {term: (ContractFamily, weight)}
_RAW_SURFACE_SIGNALS: dict[str, tuple[ContractFamily, float]] = {
    # Murabaha surface
    "هامش ربح":         (ContractFamily.MURABAHA, 0.40),
    "سعر التكلفة":      (ContractFamily.MURABAHA, 0.35),
    "markup":           (ContractFamily.MURABAHA, 0.35),
    "cost-plus":        (ContractFamily.MURABAHA, 0.35),
    # Ijara surface
    "أجرة":             (ContractFamily.IJARA, 0.35),
    "مدة الإيجار":      (ContractFamily.IJARA, 0.40),
    "lease":            (ContractFamily.IJARA, 0.35),
    "rent":             (ContractFamily.IJARA, 0.30),
    # Muqawala / construction surface — NOTE: weak because غرامة appears in debt too
    "غرامة التأخير":    (ContractFamily.MUQAWALA, 0.30),
    "تسليم المشروع":    (ContractFamily.MUQAWALA, 0.40),
    "كفيل الأداء":      (ContractFamily.MUQAWALA, 0.35),
    "liquidated damages": (ContractFamily.MUQAWALA, 0.35),
    # Musharaka surface
    "نسبة المشاركة":    (ContractFamily.MUSHARAKA, 0.40),
    "شريك":             (ContractFamily.MUSHARAKA, 0.25),
    "equity partner":   (ContractFamily.MUSHARAKA, 0.35),
    # Mudharaba surface
    "المضارب":          (ContractFamily.MUDHARABA, 0.40),
    "رب المال":         (ContractFamily.MUDHARABA, 0.40),
    "profit-sharing":   (ContractFamily.MUDHARABA, 0.35),
    # Wakala surface
    "الوكيل":           (ContractFamily.WAKALA, 0.30),
    "agent":            (ContractFamily.WAKALA, 0.25),
    # Kafala surface
    "ضمان الأداء":      (ContractFamily.KAFALA, 0.45),
    "كفيل":             (ContractFamily.KAFALA, 0.35),
    "guarantor":        (ContractFamily.KAFALA, 0.35),
}

_SURFACE_SIGNALS = {_normalize_arabic(k): v for k, v in _RAW_SURFACE_SIGNALS.items()}

# Adjacency map — families to include in MULTI_PATH retrieval when primary
# confidence is 0.50–0.80.  Max 2 adjacents used; reranked 0.60/0.20/0.20.
FAMILY_ADJACENCY: dict[ContractFamily, tuple[ContractFamily, ...]] = {
    ContractFamily.MURABAHA:  (ContractFamily.MUSHARAKA, ContractFamily.WAKALA),
    ContractFamily.IJARA:     (ContractFamily.MURABAHA,  ContractFamily.MUQAWALA),
    ContractFamily.MUQAWALA:  (ContractFamily.IJARA,     ContractFamily.KAFALA),
    ContractFamily.MUSHARAKA: (ContractFamily.MUDHARABA, ContractFamily.MURABAHA),
    ContractFamily.MUDHARABA: (ContractFamily.MUSHARAKA, ContractFamily.WAKALA),
    ContractFamily.WAKALA:    (ContractFamily.MUDHARABA, ContractFamily.KAFALA),
    ContractFamily.KAFALA:    (ContractFamily.WAKALA,    ContractFamily.MUQAWALA),
    ContractFamily.GENERAL_SHARIA: (),
    ContractFamily.AMBIGUOUS:       (),
}

# Comparative-intent phrases — force MULTI_PATH regardless of confidence (FM1 defense).
_COMPARATIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"قارن\s+بين"),
    re.compile(r"الفرق\s+بين"),
    re.compile(r"أيهما\s+أفضل"),
    re.compile(r"compare\b", re.IGNORECASE),
    re.compile(r"difference\s+between\b", re.IGNORECASE),
    re.compile(r"vs\.?\s+\w", re.IGNORECASE),
]

# Confidence thresholds
_THRESHOLD_SINGLE  = 0.80
_THRESHOLD_MULTI   = 0.50
_CONTAINER_WEIGHT  = 0.85
_SURFACE_WEIGHT    = 0.35   # applied per unique term match
_SESSION_BONUS     = 0.10   # per confirmed prior turn (capped at 0.20)
_CONFLICT_PENALTY  = 0.15   # per competing container family


class ContractFamilyRouter:
    """
    Pre-retrieval classifier that identifies the Islamic contract family of a
    query before any embedding or vector search is performed.

    This is Stage 1 of the revised ApplicationService pipeline:

        QueryAnalyzer → ContractFamilyRouter → StandardResolver
                     → Retriever → Reranker → AnswerBuilder → CitationValidator

    The router is stateless per call. Session context (confirmed family from
    prior turns) is passed in explicitly and acts as a high-weight soft signal.

    Returns an immutable ContractFamilyResult.  Callers do NOT mutate this object.
    """

    def classify(
        self,
        query: str,
        session_family: Optional[ContractFamily] = None,
        session_confirmation_turns: int = 0,
    ) -> ContractFamilyResult:
        """
        Evaluate container patterns and surface signals to determine routing
        mode, adjacent_families, signals dict, and clarification_hint.
        """
        normalized = _normalize_arabic(query)

        # Detect comparative intent — forces MULTI_PATH (FM1 defense)
        query_intent = "STANDARD"
        if any(p.search(normalized) or p.search(query) for p in _COMPARATIVE_PATTERNS):
            query_intent = "COMPARATIVE"

        container_hits = self._extract_container_signals(normalized)
        surface_hits   = self._extract_surface_signals(normalized)

        # Override rule: if any container fires, discard surface signals for OTHER families
        if container_hits:
            dominant_family = max(container_hits, key=lambda f: container_hits[f])
            surface_hits = {f: v for f, v in surface_hits.items() if f == dominant_family}

        # Session context guard (FM2): new container from different family suspends session bonus
        effective_session_family = session_family
        if session_family and container_hits:
            # If a container for a DIFFERENT family fires, session bonus is suspended
            all_container_families = set(container_hits.keys())
            if all_container_families and session_family not in all_container_families:
                effective_session_family = None   # session momentum suspended this turn

        # Find primary family and compute confidence
        all_families: dict[ContractFamily, float] = {}
        for fam, count in container_hits.items():
            all_families[fam] = all_families.get(fam, 0.0) + count * _CONTAINER_WEIGHT
        for fam, weight in surface_hits.items():
            all_families[fam] = all_families.get(fam, 0.0) + weight

        if effective_session_family:
            bonus = min(session_confirmation_turns, 2) * _SESSION_BONUS
            all_families[effective_session_family] = (
                all_families.get(effective_session_family, 0.0) + bonus
            )

        if not all_families:
            # Zero signals: FM3 — check if session gives us enough to avoid clarification
            if effective_session_family and session_confirmation_turns >= 1:
                # Soft container from session (weight 0.60) — below THRESHOLD_SINGLE
                # but above THRESHOLD_MULTI: MULTI_PATH with session family as primary
                soft_confidence = 0.60
                return ContractFamilyResult(
                    primary_family=effective_session_family,
                    adjacent_families=FAMILY_ADJACENCY.get(effective_session_family, ()),
                    confidence=soft_confidence,
                    mode=RetrievalMode.MULTI_PATH,
                    signals={"session_soft_container": soft_confidence},
                    query_intent=query_intent,
                )
            return ContractFamilyResult(
                primary_family=ContractFamily.AMBIGUOUS,
                confidence=0.0,
                mode=RetrievalMode.CLARIFICATION,
                signals={},
                clarification_hint=(
                    "ما نوع العقد الذي تسأل عنه؟ (مرابحة، إجارة، استصناع، مشاركة، مضاربة؟)"
                ),
                query_intent=query_intent,
            )

        primary = max(all_families, key=lambda f: all_families[f])
        confidence = self._compute_confidence(
            primary, container_hits, surface_hits, effective_session_family,
            session_confirmation_turns, all_families,
        )
        confidence = max(0.0, min(1.0, confidence))

        # Comparative intent always forces MULTI_PATH
        if query_intent == "COMPARATIVE":
            mode = RetrievalMode.MULTI_PATH
        elif confidence >= _THRESHOLD_SINGLE:
            mode = RetrievalMode.SINGLE_PATH
        elif confidence >= _THRESHOLD_MULTI:
            mode = RetrievalMode.MULTI_PATH
        else:
            mode = RetrievalMode.CLARIFICATION

        adjacent = FAMILY_ADJACENCY.get(primary, ())[:2] if mode == RetrievalMode.MULTI_PATH else ()

        hint = None
        if mode == RetrievalMode.CLARIFICATION:
            hint = self._build_clarification_hint(primary, container_hits, surface_hits)

        # Build audit-trail signals dict
        signals: dict[str, float] = {}
        for fam, count in container_hits.items():
            signals[f"container:{fam.value}"] = count * _CONTAINER_WEIGHT
        for fam, w in surface_hits.items():
            signals[f"surface:{fam.value}"] = w
        if effective_session_family:
            signals["session_bonus"] = min(session_confirmation_turns, 2) * _SESSION_BONUS
        competing = [f for f in container_hits if f != primary]
        if competing:
            signals["conflict_penalty"] = -len(competing) * _CONFLICT_PENALTY

        return ContractFamilyResult(
            primary_family=primary,
            adjacent_families=adjacent,
            confidence=confidence,
            mode=mode,
            signals=signals,
            clarification_hint=hint,
            query_intent=query_intent,
        )

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    def _extract_container_signals(self, text: str) -> dict[ContractFamily, int]:
        """Count container pattern matches per family (case-insensitive, diacritic-stripped)."""
        hits: dict[ContractFamily, int] = {}
        for family, patterns in _CONTAINER_PATTERNS.items():
            count = sum(1 for p in patterns if p.search(text))
            if count:
                hits[family] = count
        return hits

    def _extract_surface_signals(self, text: str) -> dict[ContractFamily, float]:
        """Sum surface signal weights per family for all matching terms."""
        weights: dict[ContractFamily, float] = {}
        for term, (family, weight) in _SURFACE_SIGNALS.items():
            if term in text:
                weights[family] = weights.get(family, 0.0) + weight
        return weights

    def _compute_confidence(
        self,
        primary: ContractFamily,
        container_hits: dict[ContractFamily, int],
        surface_hits: dict[ContractFamily, float],
        session_family: Optional[ContractFamily],
        session_turns: int,
        all_families: dict[ContractFamily, float],
    ) -> float:
        raw = min(container_hits.get(primary, 0) * _CONTAINER_WEIGHT, 0.90)
        raw += min(surface_hits.get(primary, 0.0), 0.70)
        if session_family == primary:
            raw += min(session_turns, 2) * _SESSION_BONUS
        # Conflict penalty per competing container
        competing = [f for f in container_hits if f != primary and container_hits[f] > 0]
        raw -= len(competing) * _CONFLICT_PENALTY
        return raw

    def _build_clarification_hint(
        self,
        primary: ContractFamily,
        container_hits: dict[ContractFamily, int],
        surface_hits: dict[ContractFamily, float],
    ) -> str:
        """Generate a context-appropriate clarification hint for ClarificationEngine."""
        if not container_hits and not surface_hits:
            return (
                "ما نوع العقد الذي تسأل عنه؟\n"
                "(مرابحة، إجارة، استصناع/مقاولة، مشاركة، مضاربة، وكالة، أم كفالة؟)"
            )
        if len(container_hits) >= 2:
            families_ar = "، ".join(f.value for f in container_hits)
            return f"يبدو أن سؤالك يتعلق بأكثر من نوع عقد ({families_ar}). هل يمكنك تحديد نوع العقد الرئيسي؟"
        return (
            "هل يمكنك تحديد نوع العقد الذي يتعلق به سؤالك؟ "
            "(على سبيل المثال: عقد استصناع، عقد مرابحة، عقد إجارة؟)"
        )
